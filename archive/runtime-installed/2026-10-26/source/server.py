"""
Flynn Web API & Lethe Visual Surface Gateway.
Provides:
- Lethe Causal Sigil & Observability UI (CONTACT mode & LAB mode)
- Read-only telemetry: /api/lethe/state, /api/lethe/projection, /api/lethe/replays, /api/lethe/replay/{modality}
- Health & Gateway APIs: /api/health, /api/state
- Audio PTT gateway (preserved for compatibility)
"""
import os
import sys
import time
import json
import sqlite3
import secrets
import hashlib
import ipaddress
import threading
import urllib.request
from urllib.parse import quote
from datetime import datetime, timezone
import httpx
import uvicorn
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from pydantic import BaseModel, Field
from fastapi.responses import HTMLResponse, RedirectResponse, Response, JSONResponse
from app.local_operator_auth import (
    SESSION_COOKIE as LOCAL_OPERATOR_COOKIE,
    SESSION_TTL_SECONDS as LOCAL_OPERATOR_SESSION_TTL,
    is_loopback_request,
    local_mode_enabled,
    local_mode_kind,
    local_operator_sessions,
    same_origin_request,
)

APPROVED_V783_MANIFEST_SHA256 = "499c77e789f2abeac9d21739ae106054381ad7758ab68caee9e0834dc0580045"
APPROVED_V783_MATRIX_SHA256 = "efeb23fb99098e9c390f6869969b2a121a2ee92c833cfc45ecb2c1d8e1af0347"
APPROVED_V783_ROOTS_SHA256 = "7c7b7e818e9232e5ab64793d52ba20574dbe9da3a6509fbc74193b0f259a01be"
APPROVED_V783_MAPPING_SHA256 = "23de4f221e330dc5b298ee9ade27ec2a15555db9e3f8af4436652c8301def3cf"
# Static Lethe topology counts from the existing canonical UI configuration.
# Keep the observer independent of Pinocchio's optional NumPy runtime.
LETHE_SIGIL_NODE_COUNT = 23
LETHE_SIGIL_EDGE_COUNT = 30

PROJECT_ROOT = Path(__file__).resolve().parent
RUNTIME_ROOT = Path(os.environ.get("FLYNN_RUNTIME_ROOT", "/home/ubuntu/Portifolio/flynn-max/runtime"))
if RUNTIME_ROOT.is_dir():
    sys.path.insert(0, str(RUNTIME_ROOT))

# The canonical checkout can run the Lethe shell without the separately deployed
# resident runtime. Missing legacy services stay unavailable; they never get a
# synthetic state or an authentication bypass.
LEGACY_IMPORT_ERROR = None
def _legacy_unavailable(*_args, **_kwargs):
    raise HTTPException(status_code=503, detail="Legacy resident runtime is unavailable in this checkout")

try:
    from app.stt.stt import transcribe_audio
    from app.nlu.parser import parse_utterance
    from app.web.caverna import caverna_router, load_world_dict, _get_authoritative_homeostasis_state
    from app.experiment_ledger import (
        start_session as ledger_start_session,
        end_session as ledger_end_session,
        get_sessions as get_ledger_sessions,
        get_events as get_ledger_events,
        get_latest_events as get_latest_ledger_events,
        export_session_json,
        export_session_csv,
        get_ledger_stats,
        start_snapshot_worker,
        get_causal_trace,
    )
    import app.ledger as canonical_ledger
    from app.web.security import OperatorAuthorizationMiddleware, is_authorized_operator
    from app.web.auth import (
        CSRF_COOKIE, SESSION_COOKIE, create_session, get_session, revoke_session,
        session_payload, verify_passphrase, record_login_attempt, rate_limited,
        failure_backoff_seconds, cookie_options,
    )
except (ImportError, ModuleNotFoundError) as exc:
    LEGACY_IMPORT_ERROR = f"{type(exc).__name__}: {exc}"
    from fastapi import APIRouter
    from starlette.middleware.base import BaseHTTPMiddleware

    caverna_router = APIRouter()
    canonical_ledger = None
    transcribe_audio = parse_utterance = load_world_dict = _get_authoritative_homeostasis_state = _legacy_unavailable
    ledger_start_session = ledger_end_session = get_ledger_sessions = get_ledger_events = _legacy_unavailable
    get_latest_ledger_events = export_session_json = export_session_csv = get_ledger_stats = _legacy_unavailable
    start_snapshot_worker = get_causal_trace = _legacy_unavailable
    CSRF_COOKIE, SESSION_COOKIE = "flynn_csrf", "flynn_session"
    create_session = get_session = revoke_session = session_payload = verify_passphrase = _legacy_unavailable
    record_login_attempt = rate_limited = failure_backoff_seconds = cookie_options = _legacy_unavailable
    def is_authorized_operator(_request):
        return False
    class OperatorAuthorizationMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            local_auth_routes = {
                "/api/local-operator/session",
                "/api/local-operator/login",
                "/api/local-operator/logout",
            }
            if (request.url.path.startswith("/api/")
                    and request.url.path != "/api/flynn/v2/observer"
                    and not (local_mode_enabled() and request.url.path in local_auth_routes)):
                return JSONResponse(status_code=503, content={"detail": "Legacy resident runtime unavailable"})
            return await call_next(request)


PUBLIC_LETHE_HOST = "lethe.nomosludens.ia.br"
PUBLIC_LETHE_PATHS = frozenset({"/", "/api/flynn/v2/public-observer", "/favicon.ico"})
_PUBLIC_RATE_LOCK = threading.Lock()
_PUBLIC_RATE_BUCKETS: dict[str, tuple[float, int]] = {}
_PUBLIC_CACHE_LOCK = threading.Lock()
_PUBLIC_CACHE: tuple[float, dict[str, Any]] | None = None
_PUBLIC_DB_READER_GATE = threading.BoundedSemaphore(4)


def _public_cloudflare_client_ip(request: Request) -> str | None:
    if not request.headers.get("cf-ray"):
        return None
    raw = request.headers.get("cf-connecting-ip", "")
    try:
        return str(ipaddress.ip_address(raw))
    except ValueError:
        return None


class PublicLetheBoundaryMiddleware(BaseHTTPMiddleware):
    """Exact host/path allowlist: public requests cannot reach private viewer routes."""
    async def dispatch(self, request, call_next):
        host = request.headers.get("host", "").split(":", 1)[0].lower().rstrip(".")
        if host != PUBLIC_LETHE_HOST:
            return await call_next(request)
        if (request.method != "GET" or request.url.path not in PUBLIC_LETHE_PATHS
                or request.url.query or _public_cloudflare_client_ip(request) is None):
            return JSONResponse(status_code=404, content={"detail": "Not found"}, headers={"Cache-Control": "no-store"})
        request.state.public_client_ip = _public_cloudflare_client_ip(request)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        if "Vary" in response.headers:
            del response.headers["Vary"]
        if request.url.path == "/api/flynn/v2/public-observer" and response.status_code == 200:
            response.headers["Cache-Control"] = "public, max-age=2, s-maxage=4, stale-while-revalidate=6"
        else:
            response.headers["Cache-Control"] = "no-cache, max-age=0, must-revalidate"
        return response


class LocalInstrumentalBoundaryMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        host = request.headers.get("host", "").split(":", 1)[0].lower().rstrip(".")
        server = request.scope.get("server") or (None, None)
        trusted_public_origin = (
            host == PUBLIC_LETHE_HOST and server[0] == "127.0.0.1"
            and request.method == "GET" and request.url.path in PUBLIC_LETHE_PATHS
        )
        if local_mode_enabled() and not is_loopback_request(request) and not trusted_public_origin:
            response = JSONResponse(status_code=403, content={"detail": "Local LETHE observer mode is loopback-only"})
        elif (local_mode_enabled() and request.url.path.startswith("/api/")
              and request.url.path not in {
                  "/api/local-operator/session",
                  "/api/local-operator/login",
                  "/api/local-operator/logout",
                  "/api/flynn/v2/observer",
                  "/api/flynn/v2/public-observer",
              }):
            response = JSONResponse(status_code=503, content={"detail": "Unavailable in local instrumental mode"})
        else:
            response = await call_next(request)
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, private"
            response.headers["Pragma"] = "no-cache"
            response.headers["Vary"] = "Cookie"
        return response
import asyncio

app = FastAPI(title="Flynn Web Gateway & Lethe Surface", version="0.7.1")
if not local_mode_enabled():
    app.add_middleware(OperatorAuthorizationMiddleware)
app.add_middleware(LocalInstrumentalBoundaryMiddleware)
app.add_middleware(PublicLetheBoundaryMiddleware)
app.include_router(caverna_router)


def validate_instrumental_database(path: Path) -> dict[str, Any]:
    """Validate an existing instrumental episode without creating or writing rows."""
    if not path.is_file():
        raise RuntimeError("Configured FLYNN_V2_DB does not exist")
    uri = f"file:{quote(str(path.resolve()), safe='/')}?mode=ro"
    try:
        with sqlite3.connect(uri, uri=True, timeout=2.0) as connection:
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            required = {"metadata", "events", "component_states", "neuron_mapping"}
            if not required.issubset(tables):
                raise RuntimeError("Configured database is not a Flynn V2 SQLite store")
            schema = connection.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()
            if not schema or schema[0] != "1":
                raise RuntimeError("Unsupported Flynn V2 SQLite schema version")
            mapping = connection.execute(
                "SELECT COUNT(*), MIN(mapping_sha256), MAX(mapping_sha256), "
                "MIN(source_sha256), MAX(source_sha256) FROM neuron_mapping "
                "WHERE dataset_version='fafb-v783'"
            ).fetchone()
            if mapping != (
                139255,
                APPROVED_V783_MAPPING_SHA256,
                APPROVED_V783_MAPPING_SHA256,
                APPROVED_V783_ROOTS_SHA256,
                APPROVED_V783_ROOTS_SHA256,
            ):
                raise RuntimeError("Configured Flynn V2 SQLite does not contain the verified canonical v783 root map")
            rows = connection.execute(
                "SELECT component, state_json FROM component_states "
                "WHERE component IN ('neuro_world_coordinator', 'integrated_world_neural_checkpoint', "
                "'neural_activity_aggregator', 'picoclaw_cerebellar_coordinator', 'continuous_world') "
                "ORDER BY rowid DESC"
            ).fetchall()
    except sqlite3.Error as exc:
        raise RuntimeError("Unable to validate configured Flynn V2 SQLite database") from exc

    latest: dict[str, dict[str, Any]] = {}
    for component, encoded in rows:
        if component in latest:
            continue
        try:
            latest[component] = json.loads(encoded)
        except (TypeError, json.JSONDecodeError) as exc:
            raise RuntimeError("Malformed state in configured Flynn V2 SQLite database") from exc
    checkpoint = latest.get("integrated_world_neural_checkpoint")
    cycle = latest.get("neuro_world_coordinator")
    frame = latest.get("neural_activity_aggregator")
    pico = latest.get("picoclaw_cerebellar_coordinator")
    world = latest.get("continuous_world")
    if not all((checkpoint, cycle, frame, pico, world)):
        raise RuntimeError("Configured Flynn V2 SQLite database lacks the complete instrumental observation")
    episode_id = checkpoint.get("episode_id")
    if (not episode_id or checkpoint.get("execution_kind") != "INSTRUMENTAL_LOCAL_ONLY"
            or cycle.get("episode_id") != episode_id
            or cycle.get("execution_kind") != "INSTRUMENTAL_LOCAL_ONLY"
            or frame.get("episode_id") != episode_id
            or frame.get("core_id") != "flynn-neural-core-python-v1"
            or frame.get("dataset_version") != "fafb-v783"
            or frame.get("manifest_sha256") != APPROVED_V783_MANIFEST_SHA256
            or frame.get("connectome_sha256") != APPROVED_V783_MATRIX_SHA256
            or frame.get("mapping_sha256") != APPROVED_V783_MAPPING_SHA256
            or pico.get("episode_id") != episode_id
            or pico.get("source_provenance_sha256") != frame.get("input_sha256")
            or pico.get("sequence") != frame.get("sequence")
            or pico.get("neural_time_ms") != frame.get("neural_time_ms")
            or world.get("episode_id") != episode_id
            or world.get("world_time_ms") != checkpoint.get("world_time_ms")
            or cycle.get("end_neural_time_ms") != frame.get("neural_time_ms")):
        raise RuntimeError("Configured Flynn V2 data is not one provenance-consistent instrumental LIF episode")
    checkpoint_path = Path(str(checkpoint.get("checkpoint_file", ""))).resolve()
    checkpoint_root = path.resolve().parent / "checkpoints"
    if (checkpoint_root not in checkpoint_path.parents or not checkpoint_path.is_file()
            or hashlib.sha256(checkpoint_path.read_bytes()).hexdigest() != checkpoint.get("checkpoint_sha256")):
        raise RuntimeError("Instrumental checkpoint is missing or its SHA-256 does not match SQLite")
    return {"episode_id": episode_id, "dataset_version": frame["dataset_version"]}


def validate_resident_database(path: Path) -> dict[str, Any]:
    """Read-only startup check for the dedicated, real RESIDENT episode."""
    if not path.is_file():
        raise RuntimeError("Configured resident FLYNN_V2_DB does not exist")
    uri = f"file:{quote(str(path.resolve()), safe='/')}?mode=ro"
    try:
        with sqlite3.connect(uri, uri=True, timeout=2.0) as connection:
            tables = {row[0] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )}
            required = {"metadata", "events", "component_states", "neuron_mapping"}
            if not required.issubset(tables):
                raise RuntimeError("Configured resident database is not a Flynn V2 store")
            metadata = dict(connection.execute("SELECT key, value FROM metadata"))
            if metadata.get("schema_version") != "1" or metadata.get("execution_kind") != "RESIDENT":
                raise RuntimeError("Configured V2 database is not explicitly identified as RESIDENT")
            mapping = connection.execute(
                "SELECT COUNT(*), MIN(mapping_sha256), MAX(mapping_sha256), "
                "MIN(source_sha256), MAX(source_sha256) FROM neuron_mapping "
                "WHERE dataset_version='fafb-v783'"
            ).fetchone()
            if mapping != (
                139255, APPROVED_V783_MAPPING_SHA256, APPROVED_V783_MAPPING_SHA256,
                APPROVED_V783_ROOTS_SHA256, APPROVED_V783_ROOTS_SHA256,
            ):
                raise RuntimeError("Resident V2 database does not contain the verified v783 root map")
            cursor = connection.execute(
                "SELECT episode_id, active_generation_id, checkpoint_state_id, checkpoint_sha256, checkpoint_tick "
                "FROM causal_generation_control WHERE singleton=1"
            ).fetchone()
            if not cursor:
                raise RuntimeError("Resident causal checkpoint cursor is unavailable")
            checkpoint_row = connection.execute(
                "SELECT state_json FROM component_states WHERE state_id=? "
                "AND component='integrated_world_neural_checkpoint'", (cursor[2],)
            ).fetchone()
            if not checkpoint_row:
                raise RuntimeError("Resident causal cursor does not reference a persisted checkpoint")
            cursor_checkpoint = json.loads(checkpoint_row[0])
            if (cursor_checkpoint.get("episode_id") != cursor[0]
                    or cursor_checkpoint.get("causal_generation_id") != cursor[1]
                    or cursor_checkpoint.get("checkpoint_sha256") != cursor[3]
                    or cursor_checkpoint.get("neural_tick") != cursor[4]):
                raise RuntimeError("Resident causal cursor and checkpoint provenance disagree")
            checkpoint_time_ms = cursor[4] / 10.0
            components = (
                "continuous_world", "neural_activity_aggregator", "neuro_world_coordinator",
                "picoclaw_cerebellar_coordinator", "integrated_world_neural_checkpoint",
                "pinocchio_body_checkpoint", "synthetic_proprioceptive_readout",
            )
            rows = []
            for component in components:
                row = connection.execute(
                    "SELECT component, state_json FROM component_states "
                    "WHERE json_extract(state_json, '$.causal_generation_id')=? AND component=? "
                    "AND neural_time_ms<=? ORDER BY neural_time_ms DESC, rowid DESC LIMIT 1",
                    (cursor[1], component, checkpoint_time_ms)
                ).fetchone()
                if row is not None:
                    rows.append(row)
    except sqlite3.Error as exc:
        raise RuntimeError("Unable to validate configured resident V2 database") from exc
    latest: dict[str, dict[str, Any]] = {}
    for component, encoded in rows:
        if component not in latest:
            latest[component] = json.loads(encoded)
    checkpoint = latest.get("integrated_world_neural_checkpoint")
    cycle = latest.get("neuro_world_coordinator")
    frame = latest.get("neural_activity_aggregator")
    pico = latest.get("picoclaw_cerebellar_coordinator")
    world = latest.get("continuous_world")
    if not all((checkpoint, cycle, frame, pico, world)):
        raise RuntimeError("Resident V2 database lacks a complete persisted world/LIF/PicoClaw checkpoint")
    episode_id = checkpoint.get("episode_id")
    if (not isinstance(episode_id, str) or not episode_id.startswith("resident-v2:")
            or checkpoint.get("execution_kind") != "RESIDENT"
            or cycle.get("episode_id") != episode_id or cycle.get("execution_kind") != "RESIDENT"
            or frame.get("episode_id") != episode_id
            or frame.get("manifest_sha256") != APPROVED_V783_MANIFEST_SHA256
            or frame.get("connectome_sha256") != APPROVED_V783_MATRIX_SHA256
            or frame.get("mapping_sha256") != APPROVED_V783_MAPPING_SHA256
            or pico.get("episode_id") != episode_id
            or pico.get("source_provenance_sha256") != frame.get("input_sha256")
            or pico.get("sequence") != frame.get("sequence")
            or world.get("episode_id") != episode_id
            or world.get("world_time_ms") != checkpoint.get("world_time_ms")):
        raise RuntimeError("Resident V2 snapshots do not form one provenance-consistent episode")
    if not latest.get("pinocchio_body_checkpoint") or not latest.get("synthetic_proprioceptive_readout"):
        raise RuntimeError("Resident V2 episode has no persisted Pinocchio/proprioceptive readback")
    return {"episode_id": episode_id, "dataset_version": frame.get("dataset_version")}


def validate_resident_public_cursor(path: Path) -> dict[str, Any]:
    """Bounded startup check for public read-only mode; incomplete components render STALE."""
    if not path.is_file():
        raise RuntimeError("Configured resident FLYNN_V2_DB does not exist")
    uri = f"file:{quote(str(path.resolve()), safe='/')}?mode=ro"
    try:
        with sqlite3.connect(uri, uri=True, timeout=0.5) as connection:
            connection.execute("PRAGMA query_only=ON")
            metadata = dict(connection.execute("SELECT key, value FROM metadata WHERE key IN ('schema_version','execution_kind')"))
            if metadata.get("schema_version") != "1" or metadata.get("execution_kind") != "RESIDENT":
                raise RuntimeError("Configured V2 database is not explicitly identified as RESIDENT")
            cursor = connection.execute(
                "SELECT episode_id, active_generation_id, checkpoint_state_id, checkpoint_sha256, checkpoint_tick "
                "FROM causal_generation_control WHERE singleton=1"
            ).fetchone()
            if not cursor:
                raise RuntimeError("Resident causal checkpoint cursor is unavailable")
            checkpoint_row = connection.execute(
                "SELECT state_json FROM component_states WHERE state_id=? "
                "AND component='integrated_world_neural_checkpoint'", (cursor[2],)
            ).fetchone()
            if not checkpoint_row:
                raise RuntimeError("Resident causal cursor does not reference a persisted checkpoint")
            checkpoint = json.loads(checkpoint_row[0])
            if (checkpoint.get("episode_id") != cursor[0]
                    or checkpoint.get("causal_generation_id") != cursor[1]
                    or checkpoint.get("checkpoint_sha256") != cursor[3]
                    or checkpoint.get("neural_tick") != cursor[4]):
                raise RuntimeError("Resident causal cursor and checkpoint provenance disagree")
    except sqlite3.Error as exc:
        raise RuntimeError("Unable to validate configured resident V2 SQLite cursor") from exc
    return {"episode_id": cursor[0], "causal_generation_id": cursor[1], "neural_tick": cursor[4]}


@app.on_event("startup")
async def start_local_instrumental_observation():
    if not local_mode_enabled():
        return
    database_value = os.environ.get("FLYNN_V2_DB")
    if not database_value:
        raise RuntimeError("FLYNN_LOCAL_INSTRUMENTAL requires an explicit FLYNN_V2_DB")
    if local_mode_kind() == "RESIDENT":
        if os.environ.get("FLYNN_PUBLIC_OBSERVER") == "1":
            validate_resident_public_cursor(Path(database_value).expanduser())
        else:
            validate_resident_database(Path(database_value).expanduser())
    else:
        validate_instrumental_database(Path(database_value).expanduser())
    hash_file = local_operator_sessions.start()
    print(f"FLYNN_LOCAL_OPERATOR_HASH_FILE={hash_file}", file=sys.stderr, flush=True)


@app.on_event("shutdown")
async def stop_local_instrumental_observation():
    local_operator_sessions.stop()

# ---------------------------------------------------------------------------
# OPERATOR SECURITY & AUTHORIZATION ENDPOINTS
# ---------------------------------------------------------------------------
class InteractionLoginPayload(BaseModel):
    passphrase: str = Field(min_length=1, max_length=512)
    remember_device: bool = False


class LocalOperatorLoginPayload(BaseModel):
    passphrase: str = Field(min_length=7, max_length=7)


@app.get("/api/local-operator/session")
async def local_operator_session(request: Request):
    if not local_mode_enabled():
        raise HTTPException(status_code=404, detail="Local instrumental authorization is disabled")
    token = request.cookies.get(LOCAL_OPERATOR_COOKIE)
    return {
        "instrumental_mode": local_mode_kind() == "INSTRUMENTAL_LOCAL_ONLY",
        "resident_mode": local_mode_kind() == "RESIDENT",
        "authenticated": local_operator_sessions.is_authorized(token),
        "session_ttl_seconds": LOCAL_OPERATOR_SESSION_TTL,
    }


@app.post("/api/local-operator/login")
async def local_operator_login(payload: LocalOperatorLoginPayload, request: Request):
    if not local_mode_enabled():
        raise HTTPException(status_code=404, detail="Local instrumental authorization is disabled")
    if not is_loopback_request(request) or not same_origin_request(request):
        raise HTTPException(status_code=403, detail="Same-origin loopback request required")
    source = request.client.host if request.client else "unknown"
    token = local_operator_sessions.login(source, payload.passphrase)
    if token is None:
        return JSONResponse(status_code=401, content={"authenticated": False, "detail": "Operator authorization failed"})
    response = JSONResponse(content={"authenticated": True, "mode": local_mode_kind()})
    response.set_cookie(
        LOCAL_OPERATOR_COOKIE,
        token,
        max_age=LOCAL_OPERATOR_SESSION_TTL,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="strict",
        path="/",
    )
    return response


@app.post("/api/local-operator/logout")
async def local_operator_logout(request: Request):
    if not local_mode_enabled():
        raise HTTPException(status_code=404, detail="Local instrumental authorization is disabled")
    if not is_loopback_request(request) or not same_origin_request(request):
        raise HTTPException(status_code=403, detail="Same-origin loopback request required")
    token = request.cookies.get(LOCAL_OPERATOR_COOKIE)
    local_operator_sessions.logout(token)
    response = JSONResponse(content={"authenticated": False})
    response.delete_cookie(LOCAL_OPERATOR_COOKIE, path="/", secure=request.url.scheme == "https", samesite="strict")
    return response


@app.post("/api/auth/interaction/login")
async def interaction_login(payload: InteractionLoginPayload, request: Request):
    source_key = request.client.host if request.client else "unknown"
    if rate_limited(source_key):
        return JSONResponse(status_code=429, content={"detail": "Too many attempts"})

    valid = verify_passphrase(payload.passphrase)
    record_login_attempt(source_key, valid)
    if not valid:
        delay = failure_backoff_seconds(source_key)
        if delay:
            await asyncio.sleep(delay)
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})

    token, csrf, _expires_at, max_age = create_session(payload.remember_device)
    session = get_session(token, touch=False)
    if not session:
        return JSONResponse(status_code=503, content={"detail": "Authentication unavailable"})
    response = JSONResponse(content=session_payload(session, csrf))
    secure, same_site = cookie_options()
    response.set_cookie(
        SESSION_COOKIE, token, max_age=max_age, httponly=True, secure=secure,
        samesite=same_site, path="/"
    )
    response.set_cookie(
        CSRF_COOKIE, csrf, max_age=max_age, httponly=False, secure=secure,
        samesite=same_site, path="/"
    )
    return response


@app.get("/api/auth/interaction/session")
async def interaction_session(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    session = get_session(token)
    if not session:
        return {"authenticated": False}
    csrf = request.cookies.get(CSRF_COOKIE)
    if not csrf:
        csrf = secrets.token_urlsafe(32)
        conn = sqlite3.connect("/home/ubuntu/Portifolio/flynn-max/runtime/data/flynn_auth.db")
        conn.execute(
            "UPDATE interaction_sessions SET csrf_hash = ? WHERE id = ?",
            (hashlib.sha256(csrf.encode()).hexdigest(), session["id"]),
        )
        conn.commit()
        conn.close()
    response = JSONResponse(content=session_payload(session, csrf))
    secure, same_site = cookie_options()
    expires = datetime.fromisoformat(session["expires_at"])
    max_age = max(60, int((expires - datetime.now(timezone.utc)).total_seconds()))
    response.set_cookie(
        CSRF_COOKIE, csrf, max_age=max_age, httponly=False, secure=secure,
        samesite=same_site, path="/"
    )
    return response


@app.post("/api/auth/interaction/logout")
async def interaction_logout(request: Request):
    revoke_session(request.cookies.get(SESSION_COOKIE))
    response = JSONResponse(content={"authenticated": False})
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
    return response


@app.get("/api/security/operator")
async def api_security_operator(request: Request):
    if is_authorized_operator(request):
        return {"authenticated": True, "role": "operator"}
    return {"authenticated": False}


@app.post("/api/security/operator/probe")
async def api_security_operator_probe(request: Request):
    return {"ok": True, "status": "authorized_probe"}

STATIC_DIR = Path(os.environ.get("FLYNN_STATIC_DIR", str(RUNTIME_ROOT / "app/web/static")))
LOCAL_STATIC_ASSETS = {"icon.svg": PROJECT_ROOT / "icon.svg", "manifest.webmanifest": PROJECT_ROOT / "manifest.webmanifest"}
DAEMON_URL = "http://127.0.0.1:8100"


def _get_authoritative_brain_snapshot() -> Optional[Dict[str, Any]]:
    """Read the resident's immutable snapshot for the canonical writer."""
    try:
        with urllib.request.urlopen(f"{DAEMON_URL}/api/brain/clock", timeout=3.0) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception:
        return None


def _get_authoritative_world_snapshot() -> Optional[Dict[str, Any]]:
    """Read Umwelt state from the resident; never synthesize trajectory context."""
    try:
        with urllib.request.urlopen(f"{DAEMON_URL}/caverna/state", timeout=3.0) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data.get("world")
    except Exception:
        return None
DB_PATH = str(RUNTIME_ROOT / "data/flynn.db")
EVIDENCE_DIR = RUNTIME_ROOT / "evidence"


@app.get("/api/flynn/v2/public-observer")
def flynn_v2_public_observer(request: Request):
    """Small allowlisted projection from the confirmed resident cursor; never writes SQLite."""
    global _PUBLIC_CACHE
    client_ip = getattr(request.state, "public_client_ip", None)
    if not client_ip:
        raise HTTPException(status_code=404, detail="Not found")
    now_mono = time.monotonic()
    with _PUBLIC_RATE_LOCK:
        previous = _PUBLIC_RATE_BUCKETS.get(client_ip)
        if previous is None or now_mono - previous[0] >= 60.0:
            _PUBLIC_RATE_BUCKETS[client_ip] = (now_mono, 1)
        elif previous[1] >= 20:
            raise HTTPException(status_code=429, detail="Rate limit exceeded", headers={"Retry-After": "60"})
        else:
            _PUBLIC_RATE_BUCKETS[client_ip] = (previous[0], previous[1] + 1)
        if len(_PUBLIC_RATE_BUCKETS) > 512:
            expired = [key for key, (started, _count) in _PUBLIC_RATE_BUCKETS.items() if now_mono - started >= 60.0]
            for key in expired:
                _PUBLIC_RATE_BUCKETS.pop(key, None)
            while len(_PUBLIC_RATE_BUCKETS) > 512:
                _PUBLIC_RATE_BUCKETS.pop(next(iter(_PUBLIC_RATE_BUCKETS)))
    with _PUBLIC_CACHE_LOCK:
        if _PUBLIC_CACHE and now_mono - _PUBLIC_CACHE[0] < 10.0:
            return JSONResponse(_PUBLIC_CACHE[1])
    if not _PUBLIC_DB_READER_GATE.acquire(blocking=False):
        raise HTTPException(status_code=503, detail="Observer temporarily busy", headers={"Retry-After": "2"})
    try:
        result = _read_public_flynn_snapshot()
    finally:
        _PUBLIC_DB_READER_GATE.release()
    with _PUBLIC_CACHE_LOCK:
        _PUBLIC_CACHE = (now_mono, result)
    return JSONResponse(result)


def _public_scalar(value: Any) -> Any:
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float)) and abs(float(value)) < 1e15:
        return value
    if isinstance(value, str) and len(value) <= 64 and all(char.isalnum() or char in " ._:-" for char in value):
        return value
    return None


def _public_environment(world: dict[str, Any]) -> dict[str, Any]:
    allowed = ("illumination", "wind", "sound", "contact", "looming", "window")
    scalar_fields = ("available", "offered", "contact", "active", "intensity", "value", "consumed", "speed_m_s", "level")
    output: dict[str, Any] = {}
    for key in allowed:
        value = world.get(key)
        if isinstance(value, dict):
            summary = {field: _public_scalar(value.get(field)) for field in scalar_fields if field in value}
            output[key] = {field: item for field, item in summary.items() if item is not None}
        else:
            scalar = _public_scalar(value)
            if scalar is not None:
                output[key] = scalar
    return output


def _bounded_numeric_array(value: Any, maximum: int = 32) -> list[float] | None:
    if not isinstance(value, list) or len(value) > maximum:
        return None
    try:
        values = [float(item) for item in value]
    except (TypeError, ValueError):
        return None
    return values if all(__import__("math").isfinite(item) for item in values) else None


def _read_public_flynn_snapshot() -> dict[str, Any]:
    empty = {"status": "OFFLINE", "resident_episode": False, "observation_class": "UNAVAILABLE", "observed_at_utc": None}
    value = os.environ.get("FLYNN_V2_DB")
    if not value:
        return empty
    database = Path(value).expanduser().resolve()
    if not database.is_file():
        return empty
    uri = f"file:{quote(str(database), safe='/')}?mode=ro"
    components = ("integrated_world_neural_checkpoint", "continuous_world", "neural_activity_aggregator", "picoclaw_cerebellar_coordinator", "pinocchio_body_checkpoint", "synthetic_proprioceptive_readout")
    try:
        with sqlite3.connect(uri, uri=True, timeout=0.5) as connection:
            connection.execute("PRAGMA query_only=ON")
            control = connection.execute(
                "SELECT episode_id, active_generation_id, checkpoint_state_id, checkpoint_sha256, checkpoint_tick "
                "FROM causal_generation_control WHERE singleton=1"
            ).fetchone()
            if not control:
                return empty
            episode_id, generation_id, checkpoint_state_id, expected_hash, checkpoint_tick = control
            safe_id = lambda item: isinstance(item, str) and 1 <= len(item) <= 160 and all(char.isalnum() or char in ":_-" for char in item)
            if not safe_id(episode_id) or not safe_id(generation_id):
                return empty
            checkpoint_row = connection.execute(
                "SELECT s.state_json, e.occurred_at_utc FROM component_states s JOIN events e USING(event_id) "
                "WHERE s.state_id=? AND s.component='integrated_world_neural_checkpoint' LIMIT 1", (checkpoint_state_id,)
            ).fetchone()
            if not checkpoint_row:
                return empty
            checkpoint = json.loads(checkpoint_row[0])
            if (checkpoint.get("episode_id") != episode_id or checkpoint.get("causal_generation_id") != generation_id
                    or checkpoint.get("checkpoint_sha256") != expected_hash or checkpoint.get("neural_tick") != checkpoint_tick):
                return empty
            cutoff_ms = float(checkpoint_tick) / 10.0
            rows: dict[str, tuple[dict[str, Any], str, float]] = {}
            for component in components:
                row = connection.execute(
                    "SELECT s.state_json, e.occurred_at_utc, s.neural_time_ms FROM component_states s "
                    "JOIN events e USING(event_id) WHERE json_extract(s.state_json, '$.causal_generation_id')=? "
                    "AND s.component=? AND s.neural_time_ms<=? ORDER BY s.neural_time_ms DESC,s.rowid DESC LIMIT 1",
                    (generation_id, component, cutoff_ms),
                ).fetchone()
                if row:
                    rows[component] = (json.loads(row[0]), row[1], float(row[2]))
    except (sqlite3.Error, TypeError, ValueError, json.JSONDecodeError, OSError):
        return empty

    checkpoint_state, checkpoint_observed_at, _ = rows.get(
        "integrated_world_neural_checkpoint", (checkpoint, checkpoint_row[1], cutoff_ms)
    )
    observed = {}
    now = datetime.now(timezone.utc)
    for component, (_state, occurred_at, neural_time) in rows.items():
        try:
            timestamp = datetime.fromisoformat(occurred_at.replace("Z", "+00:00"))
            age = max(0.0, (now - timestamp).total_seconds())
            observed[component] = {"observed_at_utc": occurred_at, "age_seconds": round(age, 2), "fresh": age <= 60.0, "neural_time_ms": neural_time}
        except (AttributeError, TypeError, ValueError):
            observed[component] = {"observed_at_utc": None, "age_seconds": None, "fresh": False, "neural_time_ms": neural_time}
    latest_observation = observed.get("integrated_world_neural_checkpoint", {})
    required = ("integrated_world_neural_checkpoint", "continuous_world", "neural_activity_aggregator", "pinocchio_body_checkpoint")
    status = "LIVE" if all(observed.get(name, {}).get("fresh") is True for name in required) else "STALE"
    world_state = rows.get("continuous_world", ({}, "", 0.0))[0]
    world = world_state.get("world") if isinstance(world_state.get("world"), dict) else {}
    lif = rows.get("neural_activity_aggregator", ({}, "", 0.0))[0]
    pico = rows.get("picoclaw_cerebellar_coordinator", ({}, "", 0.0))[0]
    body = rows.get("pinocchio_body_checkpoint", ({}, "", 0.0))[0]
    proprio = rows.get("synthetic_proprioceptive_readout", ({}, "", 0.0))[0]
    body_state = body.get("body_state") if isinstance(body.get("body_state"), dict) else {}
    paired_nodes = proprio.get("nodes") if isinstance(proprio.get("nodes"), dict) else {}
    valid_nodes = {}
    if (proprio.get("episode_id") == episode_id and proprio.get("causal_generation_id") == generation_id
            and body.get("neural_time_ms") == cutoff_ms and proprio.get("time_ms") == cutoff_ms
            and proprio.get("time_ms") == body.get("neural_time_ms") and len(paired_nodes) == LETHE_SIGIL_NODE_COUNT):
        for node_id, node in paired_nodes.items():
            position = node.get("position") if isinstance(node, dict) else None
            if not isinstance(position, list) or len(position) < 2:
                valid_nodes = {}
                break
            point = _bounded_numeric_array(position[:2], 2)
            if point is None:
                valid_nodes = {}
                break
            valid_nodes[node_id] = {"position": point}
    if len(valid_nodes) != LETHE_SIGIL_NODE_COUNT:
        valid_nodes = {}
    selected_pose = {"nodes": valid_nodes, "time_ms": proprio.get("time_ms"), "episode_id": episode_id,
                     "causal_generation_id": generation_id, "body_model": {"node_count": LETHE_SIGIL_NODE_COUNT, "canonical_edge_count": LETHE_SIGIL_EDGE_COUNT}} if valid_nodes else None
    body_state_public = {key: value for key in ("state_seq", "dn_active_neurons", "dn_spike_sum") if (value := _public_scalar(body_state.get(key))) is not None}
    for key in ("q", "qdot"):
        vector = _bounded_numeric_array(body_state.get(key))
        if vector is not None:
            body_state_public[key] = vector
    checkpoint_public = {
        "neural_tick": int(checkpoint_tick), "neural_time_ms": cutoff_ms,
        "checkpoint_sha256": str(expected_hash)[:12], "causal_generation_id": generation_id,
    }
    data = {
        "status": status, "resident_episode": True, "observation_class": "RESIDENT", "execution_kind": "RESIDENT",
        "episode_id": episode_id, "causal_generation_id": generation_id,
        "observed_at_utc": checkpoint_observed_at, "component_observations": observed,
        "latest_frame": {key: lif.get(key) for key in ("sequence", "neural_time_ms", "total_spikes", "active_neuron_count") if key in lif},
        "lif": {key: lif.get(key) for key in ("sequence", "neural_time_ms", "total_spikes", "active_neuron_count", "window_start_ms", "window_end_ms", "frame_count") if key in lif},
        "world": {"world_time_ms": _public_scalar(world_state.get("world_time_ms", world.get("neural_time_ms"))), "world": _public_environment(world)},
        "picoclaw": {key: _public_scalar(pico.get(key)) for key in ("sequence", "pico_version", "effect") if key in pico},
        "checkpoint": checkpoint_public,
        "pinocchio": {"status": "PINOCCHIO_STATE_PERSISTED" if body_state else "NO_BODY_STATE"},
        "pinocchio_body": {"status": "RESIDENT_PHYSICAL_STATE" if body_state else "NO_BODY_STATE", "checkpoint": {"body_state": body_state_public, "neural_time_ms": body.get("neural_time_ms"), "episode_id": episode_id, "causal_generation_id": generation_id}, "proprioceptive_readout": selected_pose},
        "geometry": {"node_count": LETHE_SIGIL_NODE_COUNT, "edge_count": LETHE_SIGIL_EDGE_COUNT, "source": "canonical static Lethe topology", "runtime_pose": "PINOCCHIO_PAIRED_READOUT" if selected_pose else "STATIC_GLYPH_NO_PAIRED_DYNAMIC_POSE"},
    }
    return data


@app.get("/api/flynn/v2/observer")
async def flynn_v2_observer(request: Request):
    """Read the configured V2 SQLite snapshots without creating or mutating state."""
    if local_mode_enabled():
        authorized = local_operator_sessions.is_authorized(request.cookies.get(LOCAL_OPERATOR_COOKIE))
    else:
        authorized = is_authorized_operator(request)
    if not authorized:
        raise HTTPException(status_code=403, detail="Operator authorization required")
    expected_execution_kind = (
        "RESIDENT" if local_mode_kind() == "RESIDENT" else "INSTRUMENTAL_LOCAL_ONLY"
    )
    value = os.environ.get("FLYNN_V2_DB")
    if not value:
        raise HTTPException(status_code=503, detail="FLYNN_V2_DB is not configured")
    database = Path(value).expanduser().resolve()
    if not database.is_file():
        raise HTTPException(status_code=503, detail="Configured Flynn V2 database does not exist")
    uri = f"file:{quote(str(database), safe='/')}?mode=ro"
    try:
        connection = sqlite3.connect(uri, uri=True, timeout=2.0)
        try:
            available = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='component_states'"
            ).fetchone()
            if not available:
                raise HTTPException(status_code=503, detail="Database has no Flynn V2 component states")
            if expected_execution_kind == "RESIDENT":
                cursor = connection.execute(
                    "SELECT episode_id, active_generation_id, checkpoint_state_id, checkpoint_sha256, checkpoint_tick "
                    "FROM causal_generation_control WHERE singleton=1"
                ).fetchone()
                if not cursor:
                    raise HTTPException(status_code=503, detail="Resident causal checkpoint cursor is unavailable")
                checkpoint_row = connection.execute(
                    "SELECT state_json FROM component_states WHERE state_id=? "
                    "AND component='integrated_world_neural_checkpoint'", (cursor[2],)
                ).fetchone()
                if not checkpoint_row:
                    raise HTTPException(status_code=503, detail="Resident cursor checkpoint is not persisted")
                cursor_checkpoint = json.loads(checkpoint_row[0])
                if (cursor_checkpoint.get("episode_id") != cursor[0]
                        or cursor_checkpoint.get("causal_generation_id") != cursor[1]
                        or cursor_checkpoint.get("checkpoint_sha256") != cursor[3]
                        or cursor_checkpoint.get("neural_tick") != cursor[4]):
                    raise HTTPException(status_code=503, detail="Resident cursor checkpoint provenance mismatch")
                checkpoint_time_ms = cursor[4] / 10.0
                generation_pattern = f"%generation:{cursor[1]}%"
            else:
                checkpoint_time_ms = float("inf")
                generation_pattern = "%"
            components = (
                "continuous_world", "neural_activity_aggregator", "neuro_world_coordinator",
                "picoclaw_cerebellar_coordinator", "integrated_world_neural_checkpoint",
                "pinocchio_body_checkpoint", "pinocchio_motor_actuation",
                "synthetic_proprioceptive_readout",
            )
            rows = []
            for component in components:
                if expected_execution_kind == "RESIDENT":
                    row = connection.execute(
                        "SELECT s.component, s.state_json, e.occurred_at_utc, s.neural_time_ms, s.schema_version "
                        "FROM component_states AS s JOIN events AS e ON e.event_id=s.event_id "
                        "WHERE json_extract(s.state_json, '$.causal_generation_id')=? AND s.component=? "
                        "AND s.neural_time_ms<=? ORDER BY s.neural_time_ms DESC, s.rowid DESC LIMIT 1",
                        (cursor[1], component, checkpoint_time_ms)
                    ).fetchone()
                else:
                    row = connection.execute(
                        "SELECT s.component, s.state_json, e.occurred_at_utc, s.neural_time_ms, s.schema_version "
                        "FROM component_states AS s JOIN events AS e ON e.event_id=s.event_id "
                        "WHERE s.component=? AND s.neural_time_ms<=? AND s.state_id LIKE ? "
                        "ORDER BY s.rowid DESC LIMIT 1", (component, checkpoint_time_ms, generation_pattern)
                    ).fetchone()
                if row is not None:
                    rows.append(row)
        finally:
            connection.close()
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail=f"Flynn V2 snapshot read failed: {exc}") from exc
    decoded_rows = []
    for row in rows:
        try:
            decoded_rows.append((row, json.loads(row[1])))
        except (TypeError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=503, detail="Malformed persisted Flynn V2 state") from exc
    checkpoint_episode = next((
        state.get("episode_id") for (component, *_rest), state in decoded_rows
        if component == "integrated_world_neural_checkpoint"
        and state.get("execution_kind") == expected_execution_kind
    ), None)
    states: dict[str, dict[str, Any]] = {}
    selected_rows: dict[str, tuple] = {}
    for row, state in decoded_rows:
        component = row[0]
        if component not in states and state.get("episode_id") == checkpoint_episode:
            states[component] = state
            selected_rows[component] = row
    observed_now = datetime.now(timezone.utc)
    component_observations = {}
    for component, (_name, _state_json, occurred_at_utc, neural_time_ms, schema_version) in selected_rows.items():
        try:
            observed_at = datetime.fromisoformat(occurred_at_utc.replace("Z", "+00:00"))
            age_seconds = max(0.0, (observed_now - observed_at).total_seconds())
            component_observations[component] = {
                "observed_at_utc": occurred_at_utc,
                "age_seconds": round(age_seconds, 3),
                "fresh": age_seconds <= 30.0,
                "freshness_limit_seconds": 30,
                "neural_time_ms": neural_time_ms,
                "schema_version": schema_version,
            }
        except (AttributeError, TypeError, ValueError):
            component_observations[component] = {"fresh": False, "status": "INVALID_OBSERVATION_TIME"}
    world = states.get("continuous_world")
    lif = states.get("neural_activity_aggregator")
    cycle = states.get("neuro_world_coordinator")
    pico = states.get("picoclaw_cerebellar_coordinator")
    checkpoint = states.get("integrated_world_neural_checkpoint")
    body_checkpoint = states.get("pinocchio_body_checkpoint")
    body_actuation = states.get("pinocchio_motor_actuation")
    proprioception = states.get("synthetic_proprioceptive_readout")
    body_readout = proprioception or body_checkpoint
    resident_episode = bool(checkpoint_episode and expected_execution_kind == "RESIDENT")
    return {
        "source": "configured_flynn_v2_sqlite_read_only",
        "execution_kind": cycle.get("execution_kind") if cycle else None,
        "observation_class": "RESIDENT" if resident_episode else (
            "HISTORICAL_INSTRUMENTAL" if checkpoint_episode else "UNAVAILABLE"
        ),
        "resident_episode": resident_episode,
        "episode_id": checkpoint_episode,
        "dataset_version": lif.get("dataset_version") if lif else None,
        "provenance": {
            "manifest_sha256": lif.get("manifest_sha256") if lif else None,
            "connectome_sha256": lif.get("connectome_sha256") if lif else None,
            "mapping_sha256": lif.get("mapping_sha256") if lif else None,
            "root_ids_sha256": APPROVED_V783_ROOTS_SHA256 if lif else None,
            "frame_sha256": lif.get("input_sha256") if lif else None,
        },
        "latest_frame": {
            "sequence": lif.get("sequence"),
            "neural_time_ms": lif.get("neural_time_ms"),
            "total_spikes": lif.get("total_spikes"),
            "core_id": lif.get("core_id"),
        } if lif else None,
        "observed_at_utc": observed_now.isoformat(),
        "component_observations": component_observations,
        "world": world,
        "lif": lif,
        "cycle": cycle,
        "picoclaw": pico,
        "checkpoint": checkpoint,
        "pinocchio": (
            ("PINOCCHIO_BODY_STATE_AVAILABLE_IN_RESIDENT_EPISODE" if resident_episode
             else "PINOCCHIO_BODY_STATE_AVAILABLE_IN_INSTRUMENTAL_EPISODE")
            if body_checkpoint else "NOT_CONNECTED_NO_PHYSICAL_BODY_STATE"
        ),
        "pinocchio_body": {
            "status": "RESIDENT_PHYSICAL_STATE" if resident_episode else "INSTRUMENTAL_PHYSICAL_STATE_NOT_RESIDENT",
            "checkpoint": body_checkpoint,
            "last_actuation": body_actuation,
            "proprioceptive_readout": proprioception,
            "neural_projection": (
                proprioception.get("neural_projection") if proprioception
                else "NOT_MEASURED"
            ),
        } if body_checkpoint or proprioception else None,
        "energy": "NOT_AVAILABLE_NO_APPROVED_ENERGY_STATE",
        "geometry": {
            "node_count": body_readout.get("body_model", {}).get("node_count", LETHE_SIGIL_NODE_COUNT)
                if body_readout else LETHE_SIGIL_NODE_COUNT,
            "edge_count": body_readout.get("body_model", {}).get("canonical_edge_count", LETHE_SIGIL_EDGE_COUNT)
                if body_readout else LETHE_SIGIL_EDGE_COUNT,
            "source": "Pinocchio physical readback plus canonical static Lethe topology"
                if body_readout else "canonical static Lethe UI configuration; dynamic pose not present in selected episode",
            "runtime_pose": "PINOCCHIO_STATE_READBACK_CENTRAL_EB_ANCHORED"
                if body_checkpoint else "NOT_CONNECTED_NO_DYNAMIC_BODY_SNAPSHOT",
            "dynamic_joint_links": body_readout.get("body_model", {}).get("dynamic_tree_link_count")
                if body_readout else None,
            "graph_only_edges": body_readout.get("body_model", {}).get("graph_only_edge_count")
                if body_readout else None,
        },
        "blocked": {
            "sensory_transduction": (
                "WORLD_SENSORS_AVAILABLE; SYNTHETIC_BODY_READOUT"
                if proprioception and resident_episode else
                "WORLD_SENSORS_AVAILABLE; BODY_READOUT_SYNTHETIC"
                if proprioception else "NO_BODY_PROPRIOCEPTIVE_READOUT_IN_SELECTED_EPISODE"
            ),
            "dn_to_actuator_mapping": (
                "OFFICIAL_1303_DN_READOUT_AND_PINOCCHIO_PATH_AVAILABLE_IN_RESIDENT_RUN"
                if body_actuation and resident_episode else
                "OFFICIAL_1303_DN_READOUT_AND_PINOCCHIO_PATH_AVAILABLE_IN_INSTRUMENTAL_RUN"
                if body_actuation else "OFFICIAL_1303_DN_READOUT_AVAILABLE; NO_BODY_ACTUATION_IN_SELECTED_EPISODE"
            ),
            "physical_actuation": (
                "PINOCCHIO_PHYSICAL_STATE_PERSISTED_IN_RESIDENT_EPISODE"
                if body_actuation and resident_episode else
                "INSTRUMENTAL_PINOCCHIO_STATE_ONLY_NOT_RESIDENT"
                if body_actuation else "NOT_CONNECTED_IN_SELECTED_EPISODE"
            ),
            "body_world_feedback": (
                "SYNTHETIC_PROPRIOCEPTION_PROJECTED_TO_LIF"
                if proprioception and resident_episode else
                "PROPRIOCEPTIVE_MEASUREMENT_NOT_PROJECTED_TO_LIF"
                if proprioception else "NO_BODY_PROPRIOCEPTION_IN_SELECTED_EPISODE"
            ),
        },
    }


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# HEALTH & COMPATIBILITY ENDPOINTS
# ---------------------------------------------------------------------------
@app.get("/api/health")
@app.get("/flynn/api/health")
async def health():
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            r = await client.get(f"{DAEMON_URL}/health")
            brain_health = r.json() if r.status_code == 200 else {"status": "error"}
        except Exception:
            brain_health = {"status": "unreachable"}

    return {
        "status": "active",
        "gateway": "online",
        "surface": "Lethe 0.6.0",
        "brain_daemon": brain_health
    }


@app.get("/api/state")
@app.get("/flynn/api/state")
async def state():
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            r = await client.get(f"{DAEMON_URL}/health")
            return r.json()
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Brain daemon unreachable: {e}")


# ---------------------------------------------------------------------------
# LETHE READ-ONLY TELEMETRY & OBSERVABILITY ENDPOINTS
# ---------------------------------------------------------------------------
@app.get("/api/lethe/state")
@app.get("/flynn/api/lethe/state")
async def lethe_state():
    """
    Returns real-time operational telemetry of Flynn resident without mutation:
    - Daemon state (QUIESCENT vs STIMULATED)
    - Instance ID, session time, RSS memory
    - Latest event recorded in SQLite (read-only)
    """
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            r = await client.get(f"{DAEMON_URL}/health")
            daemon_info = r.json() if r.status_code == 200 else {}
        except Exception:
            daemon_info = {"status": "unreachable", "state": "UNKNOWN"}

    # Query last event read-only from sqlite
    last_event = None
    try:
        con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        cur = con.cursor()
        row = cur.execute("SELECT id, modality, raw_text, neural_json, response, created_at FROM events ORDER BY id DESC LIMIT 1").fetchone()
        if row:
            neural_data = json.loads(row[3]) if row[3] else {}
            last_event = {
                "id": row[0],
                "modality": row[1],
                "raw_text": row[2],
                "neural": neural_data,
                "response": row[4],
                "created_at": row[5]
            }
        con.close()
    except Exception:
        pass

    return {
        "status": "active",
        "surface": "Lethe",
        "instance_id": daemon_info.get("instance_id"),
        "quiescent": daemon_info.get("state") == "QUIESCENT",
        "state": daemon_info.get("state", "QUIESCENT"),
        "session_t_ms": daemon_info.get("session_t_ms", 0.0),
        "connectome_load_count": daemon_info.get("connectome_load_count", 1),
        "session_create_count": daemon_info.get("session_create_count", 1),
        "neurons": daemon_info.get("neurons", 139255),
        "rss_mb": daemon_info.get("rss_mb", 0.0),
        "body_engine": daemon_info.get("body_engine"),
        "sigil_body": daemon_info.get("sigil_body"),
        "last_event": last_event,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }


def _read_trajectory_window(window_sec: int = 300, limit: int = 600) -> Dict[str, Any]:
    """Read resident trajectory snapshots from the canonical append-only ledger."""
    window_sec = max(1, min(int(window_sec), 86400))
    limit = max(1, min(int(limit), 1000))
    conn = canonical_ledger.get_ledger_conn()
    rows = conn.execute(
        """SELECT snapshot_id, timestamp_utc, monotonic_ms, brain_state_json,
                  internal_state_json, world_state_json
           FROM periodic_snapshots
             WHERE brain_state_json IS NOT NULL
           ORDER BY timestamp_utc DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()

    now = datetime.now(timezone.utc)
    points: List[Dict[str, Any]] = []
    for row in reversed(rows):
        try:
            brain = json.loads(row[3])
            trajectory = brain.get("trajectory") or {}
            if not trajectory:
                continue
            timestamp = str(row[1])
            parsed_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            if (now - parsed_time).total_seconds() > window_sec:
                continue
            body = brain.get("sigil_body") or {}
            internal = json.loads(row[4]) if row[4] else {}
            world = json.loads(row[5]) if row[5] else {}
            points.append({
                "snapshot_id": row[0],
                "wall_time": timestamp,
                "monotonic_ms": row[2],
                "neural_time": brain.get("neural_time_ms"),
                "event_id": trajectory.get("event_id"),
                "event_kind": trajectory.get("event_kind", "SNAPSHOT"),
                "body": {
                    "q": body.get("q", []),
                    "qdot": body.get("qdot", []),
                    "requested_actuation": trajectory.get("requested_actuation", body.get("requested_actuation", [])),
                    "executed_actuation": trajectory.get("executed_actuation", body.get("executed_actuation", body.get("motor_vector", []))),
                    "motor_vector": body.get("motor_vector", []),
                    "body_capacity": trajectory.get("body_capacity", body.get("body_capacity")),
                    "body_capacity_function": body.get("body_capacity_function", "f(E)=clip(E,0,1)"),
                    "active_body_output_capacity": body.get("active_body_output_capacity", body.get("body_capacity")),
                    "position_before": trajectory.get("position_before"),
                    "position_after": trajectory.get("position_after"),
                    "displacement": trajectory.get("displacement", [0.0, 0.0]),
                    "distance": trajectory.get("distance", 0.0),
                    "direction_degrees": trajectory.get("direction_degrees"),
                    "geometry": body.get("nodes", {}),
                    "geometry_summary": trajectory.get("geometry_summary", {}),
                },
                "neural": trajectory.get("neural", {
                    "active_dn_count": body.get("dn_active_neurons", 0),
                    "total_spikes": body.get("dn_spike_sum", 0),
                    "top_active_dns": body.get("top_active_dns", []),
                }),
                "homeostasis": {
                    "energy_reserve": internal.get("energy_reserve"),
                    "feeding_drive": internal.get("feeding_drive"),
                    "body_capacity": trajectory.get("body_capacity", body.get("body_capacity")),
                },
                "umwelt": world,
                "provenance": trajectory.get("provenance", {}),
            })
        except Exception:
            continue

    path_points = [p["body"]["position_after"] for p in points if p["body"].get("position_after")]
    current = points[-1] if points else None
    start_position = (points[0]["body"].get("position_before") or points[0]["body"].get("position_after")) if points else None
    current_position = current["body"].get("position_after") if current else None
    displacement = [current_position[i] - start_position[i] for i in (0, 1)] if start_position and current_position else [0.0, 0.0]
    return {
        "status": "ok",
        "source": "RESIDENT",
        "window_sec": window_sec,
        "path_points": path_points,
        "summary": {
            "start_position": start_position,
            "current_position": current_position,
            "displacement_from_start": displacement,
            "total_distance": round(sum(float(p["body"].get("distance") or 0.0) for p in points), 8),
            "snapshot_count": len(points),
        },
        "current": current,
        "recent_events": [p for p in points if p["event_kind"] == "MOVEMENT"][-12:],
        "history_persistent": True,
        "body_state_source": "PINOCCHIO_RESIDENT",
        "replay_included": False,
    }


@app.get("/api/trajectory/state")
async def trajectory_state(window_sec: int = 300, limit: int = 600):
    """Read-only resident trajectory view backed by canonical ledger snapshots."""
    return _read_trajectory_window(window_sec=window_sec, limit=limit)


@app.get("/api/lethe/projection")
@app.get("/flynn/api/lethe/projection")
async def lethe_projection():
    """Returns the 23-module structural projection graph of FAFB v783."""
    proj_file = EVIDENCE_DIR / "lethe_structural_projection.json"
    if not proj_file.exists():
        raise HTTPException(status_code=404, detail="Projection data file not found")
    with open(proj_file, "r") as f:
        data = json.load(f)
    return data


@app.get("/api/lethe/replays")
@app.get("/flynn/api/lethe/replays")
async def lethe_replays_list():
    """Lists available canonical empirical traces from Gate 03 / Gate 04."""
    return [
        {
            "id": "looming",
            "label": "Looming Visual Threat (Aproximação Visual)",
            "sensory_origin": "LC4 (104) / LPLC2 (210) Optic Lobes",
            "expected_canonical": "Takeoff (DNp01 220Hz) + Long Mode (0.83)",
            "expected_candidate": "None",
            "expected_unknown": "None",
            "description": "Estímulo visual de predador em rota de colisão. Dispara escape balístico pelo neurônio Gigante DNp01."
        },
        {
            "id": "taste_sugar",
            "label": "Taste Sugar (Açúcar no Labelo)",
            "sensory_origin": "sugar_grn (78) Gnathal Ganglion / SEZ",
            "expected_canonical": "Proboscis Extension Reflex (MN9 58.7Hz)",
            "expected_candidate": "DNg103 Feeding Posture",
            "expected_unknown": "None",
            "description": "Sensação gustativa doce. Recruta reflexo de extensão da probóscide (PER) pelos neurônios motores MN9."
        },
        {
            "id": "taste_bitter",
            "label": "Taste Bitter (Amargo Aversivo)",
            "sensory_origin": "bitter_grn (54) Gnathal Ganglion / SEZ",
            "expected_canonical": "0.0 em todos os 6 canais motores canônicos (Supressão)",
            "expected_candidate": "DNpe007 (82Hz) + DNg80 Gumdrop (34Hz)",
            "expected_unknown": "UNKNOWN_06 (DNpe030)",
            "description": "Sabor amargo/tóxico. Canais motores canônicos permanecem em 0, mas ativam vias aversivas DNpe007 e Gumdrop."
        },
        {
            "id": "sound",
            "label": "Courtship Song / Acoustic Pulse (Canto de Cortejo)",
            "sensory_origin": "JO-A / JO-B (456) Órgão de Johnston",
            "expected_canonical": "Turn / Steering (0.50) + Long Mode (0.75)",
            "expected_candidate": "DNg24 (244Hz) + DNge130 (198Hz)",
            "expected_unknown": "None",
            "description": "Vibração acústica na antena. Recruta canais descendentes de orientação auditiva DNg24 e torção lateral DNa."
        },
        {
            "id": "touch_head",
            "label": "Touch Head (Mecanossensação Cefálica)",
            "sensory_origin": "BM Head Bristles (120) Cerda Cefálica",
            "expected_canonical": "Backward Walk (MDN 75Hz) + Proboscis Retract",
            "expected_candidate": "DNge104 Grooming (270Hz) + DNge122 (324Hz)",
            "expected_unknown": "UNKNOWN_05 (DNge002) + UNKNOWN_08 (DNge048)",
            "description": "Deflexão de cerdas na cabeça. Recruta caminhada para trás pelo MDN e grooming anterior por DNge104."
        }
    ]


@app.get("/api/lethe/replay/{modality}")
@app.get("/flynn/api/lethe/replay/{modality}")
async def lethe_replay_trace(modality: str):
    """
    Returns the real empirical time-resolved activation trace for the given modality,
    compiled from real Gate 03 / Gate 04 simulation logs.
    """
    g3_path = EVIDENCE_DIR / "flynn_gate03_raw.json"
    if not g3_path.exists():
        raise HTTPException(status_code=404, detail="Gate 03 evidence raw file missing")

    with open(g3_path, "r") as f:
        g3 = json.load(f)

    target_trial = None
    for t in g3.get("trials", []):
        if t["modality"] == modality and t.get("seed", 0) == 0:
            target_trial = t
            break

    if not target_trial:
        raise HTTPException(status_code=404, detail=f"No empirical trial found for modality '{modality}'")

    # Add candidate outputs and unknown signals from Gate 04 decode findings
    candidate_profiles = {
        "looming": {"candidates": {}, "unknowns": {}},
        "taste_sugar": {
            "candidates": {
                "DNg103": {"hz": 116.0, "role": "feeding_posture", "citation": "Shiu et al. 2024", "evidence": "LEVEL_2"}
            },
            "unknowns": {}
        },
        "taste_bitter": {
            "candidates": {
                "DNpe007": {"hz": 82.0, "role": "bitter_rejection", "citation": "Shiu et al. 2024", "evidence": "LEVEL_2"},
                "DNg80": {"hz": 34.0, "role": "ingestion_termination", "citation": "Sterne et al. 2021", "evidence": "LEVEL_3"}
            },
            "unknowns": {
                "DNpe030": {"hz": 22.0, "label": "UNKNOWN_06", "neuropil": "SMP"}
            }
        },
        "sound": {
            "candidates": {
                "DNg24": {"hz": 244.0, "role": "song_orientation", "citation": "Kamikouchi et al. 2009", "evidence": "LEVEL_2"},
                "DNge130": {"hz": 198.0, "role": "acoustic_descending", "citation": "Shiu et al. 2024", "evidence": "LEVEL_2"}
            },
            "unknowns": {}
        },
        "touch_head": {
            "candidates": {
                "DNge104": {"hz": 270.0, "role": "anterior_grooming", "citation": "Hampel et al. 2015", "evidence": "LEVEL_2"},
                "DNge122": {"hz": 324.0, "role": "grooming_sweep", "citation": "Hampel et al. 2015", "evidence": "LEVEL_2"},
                "DNg83": {"hz": 130.0, "role": "maxillary_grooming", "citation": "Seeds et al. 2014", "evidence": "LEVEL_2"}
            },
            "unknowns": {
                "DNge002": {"hz": 146.0, "label": "UNKNOWN_05", "neuropil": "GNG"},
                "DNge048": {"hz": 102.0, "label": "UNKNOWN_08", "neuropil": "GNG"},
                "DNg81": {"hz": 280.0, "label": "UNKNOWN_09", "neuropil": "GNG"}
            }
        }
    }

    # State circuit status
    female_state = {
        "pC1d_hz": target_trial.get("populations", {}).get("pC1d", {}).get("peak_window_hz", 0.0),
        "aIPg_hz": target_trial.get("populations", {}).get("all_aIPg", {}).get("peak_window_hz", 0.0),
        "persisting": False
    }

    c_meta = candidate_profiles.get(modality, {"candidates": {}, "unknowns": {}})

    # Construct clean time series phases (t0..t5)
    phases = [
        {"t_ms": 0.0, "stage": "T0_STIMULUS_ONSET", "label": "Gatilho Sensorial Periférico", "active_zone": "PERIPHERAL"},
        {"t_ms": 25.0, "stage": "T1_SENSORY_TRANSDUCTION", "label": "Despolarização de População Sensorial", "active_zone": "SENSORY_LOBE"},
        {"t_ms": 75.0, "stage": "T2_INTERNEURON_PROPAGATION", "label": "Propagação Sináptica através do Conectoma", "active_zone": "CENTRAL_TRACTS"},
        {"t_ms": 140.0, "stage": "T3_CENTRAL_INTEGRATION", "label": "Integração Multimodal / Centro Premotor", "active_zone": "CENTRAL_COMPLEX"},
        {"t_ms": 220.0, "stage": "T4_DESCENDING_MOTOR_PEAK", "label": "Ativação Máxima dos Canais Descendentes", "active_zone": "DESCENDING_AXIS"},
        {"t_ms": 420.0, "stage": "T5_DECAY_RELAXATION", "label": "Cessação do Estímulo e Retorno ao Repouso", "active_zone": "QUIESCENT"}
    ]

    return {
        "replay_mode": True,
        "modality": modality,
        "duration_ms": target_trial.get("duration_ms", 400.0),
        "seed": target_trial.get("seed", 0),
        "total_brain_spikes": target_trial.get("total_brain_spikes", 0),
        "active_brain_neurons": target_trial.get("active_brain_neurons", 0),
        "channels_peak": target_trial.get("channels_peak", {}),
        "proboscis_drive_peak": target_trial.get("proboscis_drive_peak", 0.0),
        "populations": target_trial.get("populations", {}),
        "candidates": c_meta.get("candidates", {}),
        "unknowns": c_meta.get("unknowns", {}),
        "female_circuit_state": female_state,
        "phases": phases
    }


# ---------------------------------------------------------------------------
# AUDIO PTT GATEWAY (PRESERVED FOR COMPATIBILITY)
# ---------------------------------------------------------------------------
@app.post("/api/ptt")
@app.post("/flynn/api/ptt")
async def push_to_talk(file: UploadFile = File(...)):
    t0 = time.perf_counter()
    tmp_audio_path = Path(f"/home/ubuntu/Portifolio/flynn-max/runtime/tmp/upload_{int(time.time()*1000)}.wav")
    tmp_audio_path.parent.mkdir(parents=True, exist_ok=True)

    with open(tmp_audio_path, "wb") as f:
        content = await file.read()
        f.write(content)

    wav_target = tmp_audio_path
    if not file.filename.endswith(".wav"):
        wav_target = tmp_audio_path.with_suffix(".pcm.wav")
        import subprocess
        subprocess.run([
            "ffmpeg", "-y", "-i", str(tmp_audio_path),
            "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(wav_target)
        ], capture_output=True, timeout=10)

    t_stt0 = time.perf_counter()
    stt_res = transcribe_audio(wav_target)
    stt_latency_ms = (time.perf_counter() - t_stt0) * 1000.0
    transcript = stt_res["text"] or "..."

    try:
        tmp_audio_path.unlink(missing_ok=True)
        if wav_target != tmp_audio_path:
            wav_target.unlink(missing_ok=True)
    except Exception:
        pass

    t_nlu0 = time.perf_counter()
    semantic_json = parse_utterance(transcript)
    nlu_latency_ms = (time.perf_counter() - t_nlu0) * 1000.0

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            r = await client.post(f"{DAEMON_URL}/stimulate", json={
                "text": transcript,
                "semantic": semantic_json
            })
            daemon_res = r.json()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error communicating with brain daemon: {e}")

    total_latency_ms = (time.perf_counter() - t0) * 1000.0
    return {
        "answer": daemon_res.get("answer"),
        "transcript": transcript,
        "semantic": semantic_json,
        "stimulus": daemon_res.get("stimulus"),
        "neural_readout": daemon_res.get("neural_readout"),
        "pulse_profile": daemon_res.get("pulse_profile", []),
        "connectome_load_count": daemon_res.get("connectome_load_count"),
        "session_create_count": daemon_res.get("session_create_count"),
        "instance_id": daemon_res.get("instance_id"),
        "latencies_ms": {
            "stt": round(stt_latency_ms, 2),
            "nlu": round(nlu_latency_ms, 2),
            "end_to_end": round(total_latency_ms, 2)
        }
    }



try:
    from app.experience import get_experiences, get_latest_experience, get_experience_stats
except (ImportError, ModuleNotFoundError):
    get_experiences = get_latest_experience = get_experience_stats = _legacy_unavailable

# ---------------------------------------------------------------------------
# FLYNN EPISODIC EXPERIENCE STORE (READ-ONLY BIOGRAPHY - GATE 08)
# ---------------------------------------------------------------------------
@app.get("/api/flynn/experience")
async def api_get_experiences(
    session: str = None,
    time_start: str = None,
    time_end: str = None,
    variable: str = None,
    origin: str = None,
    causal_chain: str = None,
    limit: int = 50
):
    return {
        "status": "ok",
        "experiences": get_experiences(
            session_id=session,
            time_start=time_start,
            time_end=time_end,
            variable=variable,
            origin=origin,
            causal_chain=causal_chain,
            limit=limit
        )
    }

@app.get("/api/flynn/experience/latest")
async def api_get_latest_experience():
    return {
        "status": "ok",
        "latest_experience": get_latest_experience()
    }

@app.get("/api/flynn/experience/stats")
async def api_get_experience_stats():
    return {
        "status": "ok",
        "stats": get_experience_stats()
    }


# ---------------------------------------------------------------------------
# STARTUP BACKGROUND TASKS (1-SECOND SNAPSHOT WORKER)
# ---------------------------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    # Start periodic 1-second snapshot worker in background thread
    if LEGACY_IMPORT_ERROR is None and os.environ.get("FLYNN_PUBLIC_OBSERVER") != "1":
        start_snapshot_worker(
            get_world_fn=_get_authoritative_world_snapshot,
            get_internal_fn=_get_authoritative_homeostasis_state,
            get_brain_fn=_get_authoritative_brain_snapshot,
            interval_sec=1.0
        )


# ---------------------------------------------------------------------------
# FLYNN EXPERIMENTAL LEDGER API (GATE 07.1 / SECTIONS 21 & 22)
# ---------------------------------------------------------------------------
@app.post("/api/experiment/session/start")
async def api_start_experiment_session(payload: Optional[Dict[str, Any]] = None):
    p = payload or {}
    exp_id = p.get("experiment_id", "DEFAULT_EXPERIMENT")
    sess_id = p.get("session_id")
    config = p.get("configuration")
    sid = ledger_start_session(
        experiment_id=exp_id,
        session_id=sess_id,
        configuration=config,
        initial_world_state=load_world_dict(),
        initial_internal_state=_get_authoritative_homeostasis_state()
    )
    return {"status": "ok", "session_id": sid, "experiment_id": exp_id}


@app.post("/api/experiment/session/end")
async def api_end_experiment_session(payload: Optional[Dict[str, Any]] = None):
    p = payload or {}
    sess_id = p.get("session_id")
    reason = p.get("termination_reason", "completed")
    sid = ledger_end_session(session_id=sess_id, termination_reason=reason)
    return {"status": "ok", "session_id": sid, "termination_reason": reason}


@app.get("/api/experiment/sessions")
async def api_get_experiment_sessions():
    return {
        "status": "ok",
        "sessions": get_ledger_sessions()
    }


@app.get("/api/experiment/events")
async def api_get_experiment_events(
    session_id: Optional[str] = None,
    experiment_id: Optional[str] = None,
    source: Optional[str] = None,
    event_type: Optional[str] = None,
    variable: Optional[str] = None,
    causal_chain_id: Optional[str] = None,
    evidence_class: Optional[str] = None,
    time_from: Optional[str] = None,
    time_to: Optional[str] = None,
    limit: int = 100
):
    return {
        "status": "ok",
        "events": get_ledger_events(
            session_id=session_id,
            experiment_id=experiment_id,
            source=source,
            event_type=event_type,
            variable=variable,
            causal_chain_id=causal_chain_id,
            evidence_class=evidence_class,
            from_time=time_from,
            to_time=time_to,
            limit=limit
        )
    }


@app.get("/api/experiment/events/latest")
async def api_get_latest_experiment_events(limit: int = 100):
    return {
        "status": "ok",
        "events": get_latest_ledger_events(limit=limit)
    }


@app.get("/api/experiment/stats")
async def api_get_experiment_stats():
    return {
        "status": "ok",
        "stats": get_ledger_stats()
    }


@app.get("/api/experiment/trace/{causal_chain_id}")
async def api_get_experiment_trace(causal_chain_id: str):
    trace = get_causal_trace(causal_chain_id)
    return {
        "status": "ok",
        "trace": trace
    }


@app.get("/api/experiment/session/{session_id}")
async def api_get_experiment_session_details(session_id: str):
    sess = canonical_ledger.get_session(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return {
        "status": "ok",
        "session": sess
    }


@app.get("/api/experiment/export/{session_id}")
async def api_export_experiment_session(session_id: str, format: Optional[str] = "json"):
    if format and format.lower() == "csv":
        csv_str = export_session_csv(session_id)
        return Response(
            content=csv_str,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=ledger_{session_id}.csv"}
        )
    data = export_session_json(session_id)
    return JSONResponse(content=data)


@app.get("/sw.js")
async def service_worker():
    service_worker_file = PROJECT_ROOT / "sw.js"
    if not service_worker_file.exists():
        raise HTTPException(status_code=404, detail="Service worker unavailable")
    return Response(
        content=service_worker_file.read_text(),
        media_type="application/javascript",
        headers={"Cache-Control": "no-cache"},
    )


@app.get("/static/{asset_name}")
async def local_static_asset(asset_name: str):
    """Serve only the UI's known public assets; never mount the repository tree."""
    asset = LOCAL_STATIC_ASSETS.get(asset_name)
    if asset is None:
        raise HTTPException(status_code=404, detail="Static asset unavailable")
    if not asset.is_file():
        runtime_asset = STATIC_DIR / asset_name
        if not runtime_asset.is_file():
            raise HTTPException(status_code=404, detail="Static asset unavailable")
        asset = runtime_asset
    media_type = "image/svg+xml" if asset_name.endswith(".svg") else "application/manifest+json"
    return Response(asset.read_bytes(), media_type=media_type, headers={"Cache-Control": "public, max-age=3600"})


@app.get("/")
@app.get("/flynn")
@app.get("/caverna")
@app.get("/caverna/")
@app.get("/flynn/")
async def get_index(request: Request):
    host = request.headers.get("host", "").split(":", 1)[0].lower().rstrip(".")
    if host == PUBLIC_LETHE_HOST:
        if os.environ.get("FLYNN_PUBLIC_OBSERVER") != "1":
            raise HTTPException(status_code=404, detail="Public observation is not configured")
        public_file = PROJECT_ROOT / "lethe_public.html"
        if not public_file.is_file():
            raise HTTPException(status_code=404, detail="Public observation is unavailable")
        return HTMLResponse(
            content=public_file.read_text(encoding="utf-8"),
            headers={
                "Cache-Control": "no-store, max-age=0, must-revalidate",
                "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'; img-src data:; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
                "X-Content-Type-Options": "nosniff",
                "Referrer-Policy": "no-referrer",
                "X-Frame-Options": "DENY",
            },
        )
    if request.url.path == "/flynn":
        return RedirectResponse(url="/flynn/")
    configured_index = os.environ.get("FLYNN_V2_INDEX_PATH")
    index_file = Path(configured_index).expanduser().resolve() if configured_index else PROJECT_ROOT / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(), headers={"Cache-Control": "no-store, private"})
    raise HTTPException(status_code=404, detail="Lethe Surface unavailable")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8200, log_level="info")
