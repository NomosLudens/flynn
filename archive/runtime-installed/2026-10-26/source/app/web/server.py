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
import urllib.request
from datetime import datetime, timezone
import httpx
import uvicorn
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from pydantic import BaseModel, Field
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse, Response, JSONResponse

os.environ.setdefault("FLYWIRE_V783_DIR", "/home/ubuntu/Portifolio/flynn-max/data/flywire-v783")
sys.path.insert(0, "/home/ubuntu/Portifolio/flynn-max/runtime")

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
    get_causal_trace
)
import app.ledger as canonical_ledger

from app.web.security import OperatorAuthorizationMiddleware, is_authorized_operator
from app.web.auth import (
    CSRF_COOKIE,
    SESSION_COOKIE,
    create_session,
    get_session,
    revoke_session,
    session_payload,
    verify_passphrase,
    record_login_attempt,
    rate_limited,
    failure_backoff_seconds,
    cookie_options,
)
import asyncio

app = FastAPI(title="Flynn Web Gateway & Lethe Surface", version="0.7.1")
app.add_middleware(OperatorAuthorizationMiddleware)
app.include_router(caverna_router)

# ---------------------------------------------------------------------------
# OPERATOR SECURITY & AUTHORIZATION ENDPOINTS
# ---------------------------------------------------------------------------
class InteractionLoginPayload(BaseModel):
    passphrase: str = Field(min_length=1, max_length=512)
    remember_device: bool = False


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

STATIC_DIR = Path("/home/ubuntu/Portifolio/flynn-max/runtime/app/web/static")
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
DB_PATH = "/home/ubuntu/Portifolio/flynn-max/runtime/data/flynn.db"
EVIDENCE_DIR = Path("/home/ubuntu/Portifolio/flynn-max/runtime/evidence")


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



from app.experience import get_experiences, get_latest_experience, get_experience_stats

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
    service_worker_file = STATIC_DIR / "sw.js"
    if not service_worker_file.exists():
        raise HTTPException(status_code=404, detail="Service worker unavailable")
    return Response(
        content=service_worker_file.read_text(),
        media_type="application/javascript",
        headers={"Cache-Control": "no-cache"},
    )


# Serve static files
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
@app.get("/flynn")
@app.get("/caverna")
@app.get("/caverna/")
@app.get("/flynn/")
async def get_index(request: Request):
    if request.url.path == "/flynn":
        return RedirectResponse(url="/flynn/")
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text())
    return HTMLResponse("<h2>Lethe Surface Running</h2>")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8200, log_level="info")
