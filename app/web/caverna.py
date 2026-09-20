"""
Caverna de Hipnos - Umwelt Backend & World Model (Flynn Gate 07.1 / Phase A, B, C)
Strict Closed Causal Loop & Biological Provenance Architecture:
- Real Stimulus Bridge: World Fulfill -> Resident Daemon (139,255 LIF neurons)
- Real Action Bridge: Resident Readout (MN9, DNa, DNp, MDN) -> World Consequence
- Strict Provenance Enforcement: Zero fake Flynn events, persistent instance guard.
- Experimental Ledger: Append-only dual-logging into caverna_experiment.db
- Feeding Homeostasis v2: authoritative neural-time energy bookkeeping; modulation overlay blocked
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import sqlite3
import json
import os
import datetime
import uuid
import urllib.request
import urllib.error
import time
from pathlib import Path

from app.ledger import (
    record_ledger_event,
    record_snapshot,
    get_ledger_conn,
    get_ledger_counts,
    start_session,
    end_session,
    ACTIVE_SESSION_ID,
    CURRENT_EXPERIMENT_ID
)
from app.body.adapter import BODY_ADAPTER
from app.experience import record_experience, get_experiences, get_latest_experience
from app.experiment_ledger import (
    log_event as log_experiment_event,
    start_session as start_ledger_session,
    end_session as end_ledger_session,
    start_observation_window,
    cancel_observation_window,
    get_events as get_ledger_events,
    get_latest_events as get_latest_ledger_events,
    get_sessions as get_ledger_sessions,
    get_ledger_stats,
    export_session_json,
    export_session_csv
)

caverna_router = APIRouter(prefix="/api/caverna", tags=["caverna"])

DB_PATH = Path("/home/ubuntu/Portifolio/flynn-max/runtime/data/caverna.db")
DAEMON_URL = "http://127.0.0.1:8100"
RESIDENT_INSTANCE_ID = "759f27b3-84a9-4071-b29e-20adc1d4fc50"


def _get_authoritative_homeostasis_state() -> Dict[str, Any]:
    """Read Homeostasis v2 from the resident daemon; never fall back to legacy v0.1."""
    try:
        with urllib.request.urlopen(f"{DAEMON_URL}/caverna/homeostasis/state", timeout=3.0) as response:
            state = json.loads(response.read().decode("utf-8"))
        if state.get("schema_version") != "2.0.0" or state.get("epoch") != "v2":
            raise RuntimeError("authoritative Homeostasis v2 contract missing")
        return state
    except Exception as exc:
        raise RuntimeError(f"authoritative Homeostasis v2 unavailable: {exc}") from exc


def _post_authoritative_homeostasis(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    request = urllib.request.Request(
        f"{DAEMON_URL}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=3.0) as response:
            state = json.loads(response.read().decode("utf-8"))
        if state.get("schema_version") != "2.0.0" or state.get("epoch") != "v2":
            raise RuntimeError("authoritative Homeostasis v2 contract missing")
        return state
    except Exception as exc:
        raise RuntimeError(f"authoritative Homeostasis v2 mutation unavailable: {exc}") from exc

# Grammar: 3 Actions per Variable
ACTION_GRAMMAR = {
    "sweet": [
        {"id": 1, "key": "pedir_repor", "label": "Pedir / Repor Doce"},
        {"id": 2, "key": "acabou_ausente", "label": "Acabou / Ausente"},
        {"id": 3, "key": "retirar_recusar", "label": "Retirar / Recusar Doce"}
    ],
    "bitter": [
        {"id": 1, "key": "pedir_repor", "label": "Pedir / Repor Amargo"},
        {"id": 2, "key": "acabou_ausente", "label": "Acabou / Ausente"},
        {"id": 3, "key": "retirar_recusar", "label": "Retirar / Recusar Amargo"}
    ],
    "wind": [
        {"id": 1, "key": "pedir_forte", "label": "Pedir Vento Forte"},
        {"id": 2, "key": "pedir_fraco", "label": "Pedir Vento Fraco"},
        {"id": 3, "key": "pedir_retirar", "label": "Pedir Cessar Vento"}
    ],
    "sound": [
        {"id": 1, "key": "pedir_forte", "label": "Pedir Som Forte"},
        {"id": 2, "key": "pedir_fraco", "label": "Pedir Som Fraco"},
        {"id": 3, "key": "pedir_retirar", "label": "Pedir Silêncio"}
    ],
    "looming": [
        {"id": 1, "key": "pedir_receber", "label": "Pedir Receber Looming"},
        {"id": 2, "key": "pedir_fazer", "label": "Pedir Gerar Estímulo"},
        {"id": 3, "key": "nao_querer", "label": "Não Querer / Evasão"}
    ],
    "contact": [
        {"id": 1, "key": "pedir_contato", "label": "Pedir Contato"},
        {"id": 2, "key": "contato_leve", "label": "Contato Leve / Manter"},
        {"id": 3, "key": "parar", "label": "Parar / Não Querer"}
    ]
}

STIMULUS_BRIDGE_MAP = {
    "sweet": {"modality": "taste_sugar", "target_neuron": "GRN_Sugar_SEZ", "desc": "Estimulação gustatória doce via receptores labelares"},
    "bitter": {"modality": "taste_bitter", "target_neuron": "GRN_Bitter_SEZ", "desc": "Estimulação aversiva amarga restrita à SEZ"},
    "wind": {"modality": "wind", "target_neuron": "AMMC_Mechanosensory", "desc": "Corrente mecano-aérea nos órgãos de Johnston"},
    "sound": {"modality": "sound", "target_neuron": "AMMC_Auditory", "desc": "Pulso vibracional acústico (canção de cortejo)"},
    "looming": {"modality": "looming", "target_neuron": "LPLC2_LC4_Lobula", "desc": "Ameaça de aproximação visual rápida"},
    "contact": {"modality": "touch_head", "target_neuron": "Bristle_Mechanosensory", "desc": "Toque tátil cefálico mecânico"}
}


def get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS world_state (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        sweet_available BOOLEAN NOT NULL DEFAULT 0,
        sweet_offered BOOLEAN NOT NULL DEFAULT 0,
        bitter_available BOOLEAN NOT NULL DEFAULT 0,
        bitter_offered BOOLEAN NOT NULL DEFAULT 0,
        wind_level TEXT NOT NULL DEFAULT 'off',
        wind_offered_level TEXT NOT NULL DEFAULT 'none',
        sound_level TEXT NOT NULL DEFAULT 'off',
        sound_offered_level TEXT NOT NULL DEFAULT 'none',
        looming_state TEXT NOT NULL DEFAULT 'none',
        looming_offered BOOLEAN NOT NULL DEFAULT 0,
        contact_available BOOLEAN NOT NULL DEFAULT 0,
        contact_offered BOOLEAN NOT NULL DEFAULT 0,
        window_variable TEXT NOT NULL DEFAULT 'sweet',
        window_action INTEGER NOT NULL DEFAULT 1,
        live_mode BOOLEAN NOT NULL DEFAULT 1,
        replay_mode BOOLEAN NOT NULL DEFAULT 0,
        pending_human_offer TEXT,
        pending_flynn_request TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS caverna_events (
        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT NOT NULL,
        origin_type TEXT NOT NULL,
        instance_id TEXT,
        brain_session_id TEXT,
        timestamp TEXT NOT NULL,
        stimulus_id TEXT,
        measured_output TEXT,
        measured_rate_hz REAL DEFAULT 0.0,
        world_before TEXT,
        world_after TEXT,
        event_type TEXT NOT NULL,
        variable TEXT NOT NULL,
        action TEXT,
        context TEXT,
        evidence_class TEXT,
        notes TEXT,
        created_at TEXT NOT NULL
    )
    """)

    # Seed default row if empty
    c.execute("SELECT COUNT(*) FROM world_state")
    if c.fetchone()[0] == 0:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        c.execute("""
        INSERT INTO world_state (
            id, sweet_available, sweet_offered, bitter_available, bitter_offered,
            wind_level, wind_offered_level, sound_level, sound_offered_level,
            looming_state, looming_offered, contact_available, contact_offered,
            window_variable, window_action, live_mode, replay_mode,
            pending_human_offer, pending_flynn_request, created_at, updated_at
        ) VALUES (
            1, 0, 0, 0, 0,
            'off', 'none', 'off', 'none',
            'none', 0, 0, 0,
            'sweet', 1, 1, 0,
            NULL, NULL, ?, ?
        )
        """, (now, now))
    conn.commit()
    conn.close()


init_db()


def load_world_dict():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM world_state WHERE id = 1")
    row = c.fetchone()
    conn.close()
    if not row:
        return {}

    return {
        "sweet": {
            "available": bool(row["sweet_available"]),
            "offered": bool(row["sweet_offered"])
            ,"position": [3.0, 0.0]
            ,"resource_id": "sweet"
            ,"contact_radius": 0.5
        },
        "bitter": {
            "available": bool(row["bitter_available"]),
            "offered": bool(row["bitter_offered"])
            ,"position": [-3.0, 0.0]
            ,"resource_id": "bitter"
            ,"contact_radius": 0.5
        },
        "wind": {
            "level": row["wind_level"],
            "offered_level": row["wind_offered_level"]
        },
        "sound": {
            "level": row["sound_level"],
            "offered_level": row["sound_offered_level"]
        },
        "looming": {
            "state": row["looming_state"],
            "offered": bool(row["looming_offered"])
        },
        "contact": {
            "available": bool(row["contact_available"]),
            "offered": bool(row["contact_offered"])
        },
        "window": {
            "selected_variable": row["window_variable"],
            "selected_action": row["window_action"],
            "action_details": next((a for a in ACTION_GRAMMAR.get(row["window_variable"], []) if a["id"] == row["window_action"]), None),
            "pending_human_offer": json.loads(row["pending_human_offer"]) if row["pending_human_offer"] else None,
            "pending_flynn_request": json.loads(row["pending_flynn_request"]) if row["pending_flynn_request"] else None
        },
        "live_mode": bool(row["live_mode"]),
        "replay_mode": bool(row["replay_mode"]),
        "timestamps": {
            "created_at": row["created_at"],
            "updated_at": row["updated_at"]
        }
    }


def record_event(
    source: str,
    origin_type: str,
    event_type: str,
    variable: str,
    action: Optional[str] = None,
    context: Optional[dict] = None,
    instance_id: Optional[str] = None,
    brain_session_id: Optional[str] = None,
    stimulus_id: Optional[str] = None,
    measured_output: Optional[dict] = None,
    measured_rate_hz: float = 0.0,
    world_before: Optional[dict] = None,
    world_after: Optional[dict] = None,
    evidence_class: Optional[str] = None,
    notes: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None
):
    # Absolute rule check
    if source == "flynn":
        if origin_type != "resident_brain":
            raise ValueError("Provenance Violation: source='flynn' must have origin_type='resident_brain'")
        if instance_id != RESIDENT_INSTANCE_ID:
            raise ValueError(f"Instance Guard: Flynn events must originate from resident instance {RESIDENT_INSTANCE_ID}")

    should_close = False
    if conn is None:
        conn = get_db()
        should_close = True
    c = conn.cursor()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    ctx_str = json.dumps(context or {}, ensure_ascii=False)
    out_str = json.dumps(measured_output, ensure_ascii=False) if measured_output is not None else None
    wb_str = json.dumps(world_before, ensure_ascii=False) if world_before is not None else None
    wa_str = json.dumps(world_after, ensure_ascii=False) if world_after is not None else None

    c.execute("""
    INSERT INTO caverna_events (
        source, origin_type, instance_id, brain_session_id, timestamp, stimulus_id,
        measured_output, measured_rate_hz, world_before, world_after,
        event_type, variable, action, context, evidence_class, notes, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        source, origin_type, instance_id, brain_session_id, now, stimulus_id,
        out_str, measured_rate_hz, wb_str, wa_str,
        event_type, variable, action, ctx_str, evidence_class, notes, now
    ))
    event_id = c.lastrowid
    c.execute("UPDATE world_state SET updated_at = ? WHERE id = 1", (now,))
    conn.commit()
    if should_close:
        conn.close()

    # Mirror to append-only experimental ledger
    try:
        int_state = _get_authoritative_homeostasis_state()
        record_ledger_event(
            source=source,
            origin_type=origin_type,
            event_type=event_type,
            variable=variable,
            action=action,
            world_before=world_before,
            world_after=world_after,
            internal_state_before=int_state,
            internal_state_after=int_state,
            stimulus={"stimulus_id": stimulus_id, "variable": variable} if stimulus_id else None,
            brain_instance_id=instance_id,
            brain_session_id=brain_session_id,
            neural_summary=context.get("channels") if context else None,
            descending_outputs=measured_output,
            window_focus_before=world_before.get("window", {}).get("selected_variable") if world_before else None,
            window_focus_after=world_after.get("window", {}).get("selected_variable") if world_after else None,
            human_offer_id=context.get("offer_id") if context else None,
            parent_event_id=context.get("parent_event_id") if context else None,
            causal_chain_id=stimulus_id or (context.get("causal_chain_id") if context else None),
            evidence_class=evidence_class or ("HOMEOSTATIC_MEASURED" if origin_type == "resident_brain" else ("DIAGNOSTIC" if source == "diagnostic" else "HUMAN_INPUT")),
            notes=notes or (context.get("biological_basis") if context else None)
        )
    except Exception as e:
        print(f"Ledger mirror warning: {e}")

    # Mirror to append-only episodic experience store (Section 8, 10, 18)
    try:
        int_state = _get_authoritative_homeostasis_state()
        record_experience(
            session_id="session_embodied_caverna",
            world_before=world_before or {},
            world_after=world_after or {},
            internal_state_before=int_state,
            internal_state_after=int_state,
            origin_type=origin_type,
            evidence_class=evidence_class or ("HOMEOSTATIC_MEASURED" if origin_type == "resident_brain" else ("DIAGNOSTIC" if source == "diagnostic" else "HUMAN_INPUT")),
            causal_chain_id=stimulus_id or f"chain_{event_id}",
            causal_parent=None,
            sensory_input={"variable": variable, "stimulus_id": stimulus_id} if stimulus_id else None,
            brain_summary={"instance_id": instance_id, "brain_session_id": brain_session_id, "channels": context.get("channels") if context else None} if instance_id else None,
            descending_outputs=measured_output,
            body_action={"body_component": "virtual_effector", "primitive": action or "none"},
            environment_consequence=f"{variable} {event_type}",
            human_action={"action_type": event_type, "variable": variable} if source == "human" else None,
            human_offer={"variable": variable, "level": context.get("level")} if event_type == "OFFER" else None,
            window_focus=variable,
            raw_ledger_event_id=str(event_id)
        )
    except Exception as e:
        print(f"Experience mirror warning: {e}")

    # Dual-write eliminated in Gate 012B: Single canonical write path via record_ledger_event above

    return event_id


class HumanActionPayload(BaseModel):
    action_type: str  # offer, fulfill, deny, remove, select_window
    variable: str     # sweet, bitter, wind, sound, looming, contact
    action_id: Optional[int] = 1
    level: Optional[str] = None # low, high, none
    source: Optional[str] = None
    firing_rate_hz: Optional[float] = None
    observation_window_sec: Optional[float] = None


class DiagnosticActionPayload(BaseModel):
    action_bridge_name: str # turn, backward_walk, proboscis_drive, stop_freeze, escape_takeoff
    source_neurons: List[str] = []
    firing_rate_hz: float = 0.0
    variable_target: Optional[str] = None
    action_target: Optional[int] = None


@caverna_router.get("/state")
async def get_caverna_state():
    """Retorna o modelo de mundo atualizado, fisiologia e eventos recentes."""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM caverna_events ORDER BY event_id DESC LIMIT 25")
    raw_events = c.fetchall()
    conn.close()

    events = []
    for r in raw_events:
        d = dict(r)
        for k in ("measured_output", "world_before", "world_after", "context"):
            if d.get(k) and isinstance(d[k], str):
                try:
                    d[k] = json.loads(d[k])
                except Exception:
                    pass
        events.append(d)

    # Query authoritative continuous world & body from brain daemon
    world = None
    body_st = None
    homeo_state = None
    try:
        req = urllib.request.Request(f"{DAEMON_URL}/caverna/state", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            d_st = json.loads(resp.read().decode("utf-8"))
            world = d_st.get("world")
            body_st = d_st.get("body")
            homeo_state = d_st.get("homeostasis")
    except Exception:
        pass

    if world is None:
        world = load_world_dict()
        body_st = BODY_ADAPTER.status()
        # Do not substitute the rejected legacy v0.1 object when the daemon is unavailable.
        homeo_state = None

    return {
        "status": "ok",
        "world": world,
        "homeostasis": homeo_state,
        "body": body_st,
        "action_grammar": ACTION_GRAMMAR,
        "stimulus_bridge": STIMULUS_BRIDGE_MAP,
        "recent_events": events
    }


@caverna_router.get("/body/status")
async def get_caverna_body_status():
    """Retorna o status do adaptador de embodiment (FlynnBodyAdapter)."""
    return {
        "status": "ok",
        "body": BODY_ADAPTER.status(),
        "capabilities": BODY_ADAPTER.capabilities()
    }


@caverna_router.get("/experience")
async def caverna_get_experiences_route(
    session: Optional[str] = None,
    time_start: Optional[str] = None,
    time_end: Optional[str] = None,
    variable: Optional[str] = None,
    origin: Optional[str] = None,
    causal_chain: Optional[str] = None,
    limit: int = 50
):
    """Consulta histórico factual biográfico de experiências da Flynn."""
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


@caverna_router.get("/experience/latest")
async def caverna_get_latest_experience_route():
    """Retorna a experiência mais recente da Flynn."""
    return {
        "status": "ok",
        "latest_experience": get_latest_experience()
    }


@caverna_router.get("/homeostasis/state")
async def get_homeostasis_state():
    """Retorna o estado Homeostasis v2 autoritativo do daemon residente."""
    try:
        return _get_authoritative_homeostasis_state()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@caverna_router.post("/homeostasis/set")
async def set_homeostasis_state(payload: dict):
    """Ajusta Homeostasis v2 para controles experimentais técnicos."""
    try:
        return _post_authoritative_homeostasis("/caverna/homeostasis/set", payload)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@caverna_router.post("/human/action")
async def execute_human_action(payload: HumanActionPayload):
    """
    Executa e registra uma ação do operador humano (select_window, offer, fulfill, deny, remove).
    Se a ação for FULFILL, dispara o Pipeline Obrigatório 1 (Mundo -> Flynn) e
    o Pipeline Obrigatório 2 (Flynn -> Caverna) de forma 100% causal e biológica.
    """
    conn = get_db()
    c = conn.cursor()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    var = payload.variable
    act_type = payload.action_type.lower()

    if payload.source and payload.source.lower() == "flynn":
        conn.close()
        raise HTTPException(
            status_code=403,
            detail="Provenance Violation: Frontend or human caller cannot forge source='flynn'. source=flynn is assigned exclusively by the resident brain backend."
        )
    if payload.firing_rate_hz is not None:
        conn.close()
        raise HTTPException(
            status_code=403,
            detail="Provenance Violation: Frontend or human caller cannot forge firing_rate_hz. Firing rates are measured exclusively from the resident brain."
        )

    if var not in ACTION_GRAMMAR:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Invalid variable: {var}")

    chain_id = f"CC-{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6]}"
    world_before = load_world_dict()
    # Notify continuous world engine on brain daemon
    try:
        req_notify = urllib.request.Request(
            f"{DAEMON_URL}/caverna/action",
            data=json.dumps({
                "action_type": act_type,
                "variable": var,
                "level": payload.level,
                "action_id": payload.action_id,
                "duration_ms": 500.0 if var == "looming" else 100.0
            }).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req_notify, timeout=1.0)
    except Exception:
        pass

    context = {
        "operator": "human",
        "payload": payload.dict(),
        "bridge": STIMULUS_BRIDGE_MAP.get(var),
        "causal_chain_id": chain_id
    }

    if act_type == "select_window":
        c.execute("""
        UPDATE world_state
        SET window_variable = ?, window_action = ?, updated_at = ?
        WHERE id = 1
        """, (var, payload.action_id or 1, now))
        conn.commit()
        world_after = load_world_dict()
        record_event(
            source="human",
            origin_type="human_operator",
            event_type="WINDOW_SELECTION",
            variable=var,
            action=f"select_action_{payload.action_id}",
            context=context,
            world_before=world_before,
            world_after=world_after,
            evidence_class="HUMAN_INTERACTION",
            conn=conn
        )

    elif act_type == "offer":
        offer_data = {
            "variable": var,
            "action_id": payload.action_id or 1,
            "level": payload.level or "high",
            "offered_at": now
        }
        if var == "sweet":
            c.execute("UPDATE world_state SET sweet_available = 1, sweet_offered = 1, pending_human_offer = ?, updated_at = ? WHERE id = 1", (json.dumps(offer_data), now))
        elif var == "bitter":
            c.execute("UPDATE world_state SET bitter_available = 1, bitter_offered = 1, pending_human_offer = ?, updated_at = ? WHERE id = 1", (json.dumps(offer_data), now))
        elif var == "wind":
            lvl = payload.level if payload.level in ("low", "high") else "high"
            c.execute("UPDATE world_state SET wind_offered_level = ?, pending_human_offer = ?, updated_at = ? WHERE id = 1", (lvl, json.dumps(offer_data), now))
        elif var == "sound":
            lvl = payload.level if payload.level in ("low", "high") else "high"
            c.execute("UPDATE world_state SET sound_offered_level = ?, pending_human_offer = ?, updated_at = ? WHERE id = 1", (lvl, json.dumps(offer_data), now))
        elif var == "looming":
            c.execute("UPDATE world_state SET looming_offered = 1, pending_human_offer = ?, updated_at = ? WHERE id = 1", (json.dumps(offer_data), now))
        elif var == "contact":
            c.execute("UPDATE world_state SET contact_offered = 1, pending_human_offer = ?, updated_at = ? WHERE id = 1", (json.dumps(offer_data), now))

        conn.commit()
        world_after = load_world_dict()
        record_event(
            source="human",
            origin_type="human_operator",
            event_type="OFFER",
            variable=var,
            action=f"offer_{var}",
            context=context,
            world_before=world_before,
            world_after=world_after,
            evidence_class="HUMAN_OFFER",
            conn=conn
        )
        # Start observation window (Section 13 & 29)
        obs_dur = float(payload.observation_window_sec) if payload.observation_window_sec else 30.0
        start_observation_window(variable=var, causal_chain_id=chain_id, duration_sec=obs_dur)

    elif act_type == "deny":
        cancel_observation_window(chain_id)
        if var == "sweet":
            c.execute("UPDATE world_state SET sweet_offered = 0, pending_human_offer = NULL, updated_at = ? WHERE id = 1", (now,))
        elif var == "bitter":
            c.execute("UPDATE world_state SET bitter_offered = 0, pending_human_offer = NULL, updated_at = ? WHERE id = 1", (now,))
        elif var == "wind":
            c.execute("UPDATE world_state SET wind_offered_level = 'none', pending_human_offer = NULL, updated_at = ? WHERE id = 1", (now,))
        elif var == "sound":
            c.execute("UPDATE world_state SET sound_offered_level = 'none', pending_human_offer = NULL, updated_at = ? WHERE id = 1", (now,))
        elif var == "looming":
            c.execute("UPDATE world_state SET looming_offered = 0, pending_human_offer = NULL, updated_at = ? WHERE id = 1", (now,))
        elif var == "contact":
            c.execute("UPDATE world_state SET contact_offered = 0, pending_human_offer = NULL, updated_at = ? WHERE id = 1", (now,))

        conn.commit()
        world_after = load_world_dict()
        record_event(
            source="human",
            origin_type="human_operator",
            event_type="DENY",
            variable=var,
            action="offer_denied",
            context=context,
            world_before=world_before,
            world_after=world_after,
            evidence_class="HUMAN_DENIAL",
            conn=conn
        )

    elif act_type == "remove":
        cancel_observation_window(chain_id)
        if var == "sweet":
            c.execute("UPDATE world_state SET sweet_available = 0, sweet_offered = 0, updated_at = ? WHERE id = 1", (now,))
        elif var == "bitter":
            c.execute("UPDATE world_state SET bitter_available = 0, bitter_offered = 0, updated_at = ? WHERE id = 1", (now,))
        elif var == "wind":
            c.execute("UPDATE world_state SET wind_level = 'off', wind_offered_level = 'none', updated_at = ? WHERE id = 1", (now,))
        elif var == "sound":
            c.execute("UPDATE world_state SET sound_level = 'off', sound_offered_level = 'none', updated_at = ? WHERE id = 1", (now,))
        elif var == "looming":
            c.execute("UPDATE world_state SET looming_state = 'none', looming_offered = 0, updated_at = ? WHERE id = 1", (now,))
        elif var == "contact":
            c.execute("UPDATE world_state SET contact_available = 0, contact_offered = 0, updated_at = ? WHERE id = 1", (now,))

        conn.commit()
        world_after = load_world_dict()
        record_event(
            source="human",
            origin_type="human_operator",
            event_type="REMOVE",
            variable=var,
            action="stimulus_removed",
            context=context,
            world_before=world_before,
            world_after=world_after,
            evidence_class="HUMAN_REMOVAL",
            conn=conn
        )

    elif act_type == "set_level":
        cancel_observation_window(chain_id)
        lvl = payload.level if payload.level in ("low", "high", "off") else "high"
        if var == "wind":
            c.execute("UPDATE world_state SET wind_level = ?, updated_at = ? WHERE id = 1", (lvl, now))
        elif var == "sound":
            c.execute("UPDATE world_state SET sound_level = ?, updated_at = ? WHERE id = 1", (lvl, now))

        conn.commit()
        world_after = load_world_dict()
        record_event(
            source="human",
            origin_type="human_operator",
            event_type="SET_LEVEL",
            variable=var,
            action=f"set_{var}_{lvl}",
            context=context,
            world_before=world_before,
            world_after=world_after,
            evidence_class="HUMAN_INTERACTION",
            conn=conn
        )

    elif act_type == "fulfill" and var in ("sweet", "bitter"):
        # Nutritive resources are now resident-world objects.  Fulfill only
        # makes the resource available; it must not inject a synthetic brain
        # stimulus or consume/replenish through the HTTP request.  Sensation
        # and ingestion are owned by the continuous resident loop and its
        # physical contact check.
        cancel_observation_window(chain_id)
        column = "sweet" if var == "sweet" else "bitter"
        c.execute(
            f"UPDATE world_state SET {column}_available = 1, {column}_offered = 0, pending_human_offer = NULL, updated_at = ? WHERE id = 1",
            (now,),
        )
        conn.commit()
        world_after = load_world_dict()
        record_event(
            source="human",
            origin_type="human_operator",
            event_type="FULFILL",
            variable=var,
            action="resource_available_in_resident_world",
            context={**context, "brain_stimulus_injected": False, "consumption_owner": "ContinuousWorldEngine"},
            world_before=world_before,
            world_after=world_after,
            evidence_class="HUMAN_FULFILL",
            conn=conn,
        )
        log_experiment_event(
            source="human",
            origin_type="human_operator",
            event_type="FULFILL",
            variable=var,
            action="resource_available_in_resident_world",
            world_before=world_before,
            world_after=world_after,
            causal_chain_id=chain_id,
            evidence_class="observed",
            notes="No direct stimulus, movement, or homeostasis mutation; resident world owns contact consumption.",
        )
        conn.close()
        return {
            "status": "ok",
            "world": world_after,
            "causal_chain_id": chain_id,
            "resident_world_action": "RESOURCE_AVAILABLE_ONLY",
        }

    elif act_type == "fulfill":
        stimulus_id = f"stim_{uuid.uuid4().hex[:8]}"
        if var == "sweet":
            c.execute("UPDATE world_state SET sweet_available = 1, sweet_offered = 0, pending_human_offer = NULL, updated_at = ? WHERE id = 1", (now,))
        elif var == "bitter":
            c.execute("UPDATE world_state SET bitter_available = 1, bitter_offered = 0, pending_human_offer = NULL, updated_at = ? WHERE id = 1", (now,))
        elif var == "wind":
            c.execute("UPDATE world_state SET wind_level = wind_offered_level, wind_offered_level = 'none', pending_human_offer = NULL, updated_at = ? WHERE id = 1", (now,))
        elif var == "sound":
            c.execute("UPDATE world_state SET sound_level = sound_offered_level, sound_offered_level = 'none', pending_human_offer = NULL, updated_at = ? WHERE id = 1", (now,))
        elif var == "looming":
            c.execute("UPDATE world_state SET looming_state = 'world', looming_offered = 0, pending_human_offer = NULL, updated_at = ? WHERE id = 1", (now,))
        elif var == "contact":
            c.execute("UPDATE world_state SET contact_available = 1, contact_offered = 0, pending_human_offer = NULL, updated_at = ? WHERE id = 1", (now,))

        conn.commit()
        world_after_human = load_world_dict()

        context["sensory_consequence"] = STIMULUS_BRIDGE_MAP.get(var)
        record_event(
            source="human",
            origin_type="human_operator",
            event_type="FULFILL",
            variable=var,
            action="stimulus_active_in_world",
            context=context,
            stimulus_id=stimulus_id,
            world_before=world_before,
            world_after=world_after_human,
            evidence_class="HUMAN_FULFILL",
            conn=conn
        )

        # Causal Chain Event 1: HUMAN FULFILL
        ev_human = log_experiment_event(
            source="human",
            origin_type="human_operator",
            event_type="FULFILL",
            variable=var,
            action="fulfill",
            world_before=world_before,
            world_after=world_after_human,
            causal_chain_id=chain_id,
            evidence_class="observed",
            notes=f"Human fulfilled offer for {var}"
        )

        # Causal Chain Event 2: WORLD sweet=present
        ev_world = log_experiment_event(
            source="world",
            origin_type="world_environment",
            event_type="WORLD_STATE_CHANGE",
            variable=var,
            action=f"{var}=present",
            world_before=world_before,
            world_after=world_after_human,
            causal_chain_id=chain_id,
            parent_event_id=ev_human,
            evidence_class="observed"
        )

        # ============================================================
        # PIPELINE 1: MUNDO -> FLYNN (ESTÍMULO REAL NO CÉREBRO RESIDENTE)
        # ============================================================
        modality_key = STIMULUS_BRIDGE_MAP[var]["modality"]
        stim_data = {
            "modality": modality_key,
            "intensity": 1.0,
            "duration_ms": 100.0,
            "target_population": STIMULUS_BRIDGE_MAP[var].get("target_neuron", "SEZ")
        }

        # Causal Chain Event 3: STIMULUS taste_sugar delivered
        ev_stim = log_experiment_event(
            source="world",
            origin_type="world_environment",
            event_type="STIMULUS_DELIVERED",
            variable=var,
            action=modality_key,
            stimulus=stim_data,
            world_before=world_after_human,
            world_after=world_after_human,
            causal_chain_id=chain_id,
            parent_event_id=ev_world,
            evidence_class="observed"
        )

        try:
            req_data = json.dumps({
                "modality": modality_key,
                "intensity": 1.0,
                "duration_ms": 100.0
            }).encode("utf-8")
            req = urllib.request.Request(
                f"{DAEMON_URL}/caverna/stimulate",
                data=req_data,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                brain_res = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            conn.close()
            raise HTTPException(status_code=502, detail=f"Failed to communicate with Flynn brain daemon: {e}")

        # ============================================================
        # PIPELINE 2: FLYNN -> CAVERNA (PRIMITIVAS MOTORAS BIOLÓGICAS)
        # ============================================================
        inst_id = brain_res.get("instance_id")
        brain_sess_id = brain_res.get("brain_session_id")
        channels = brain_res.get("channels", {})
        rates = brain_res.get("rates", {})
        prob_drive = float(brain_res.get("proboscis_drive", 0.0))
        prob_hz = float(brain_res.get("proboscis_hz", 0.0))

        cancel_observation_window(chain_id)

        # Causal Chain Event 4: FLYNN NEURAL_RESPONSE
        ev_neural = log_experiment_event(
            source="flynn",
            origin_type="resident_brain",
            event_type="NEURAL_RESPONSE",
            variable=var,
            neural_summary={
                "total_spikes": brain_res.get("total_spikes", 0),
                "active_neurons": brain_res.get("active_neurons", 0),
                "duration_ms": brain_res.get("duration_ms", 120.0),
                "proboscis_drive": prob_drive,
                "proboscis_hz": prob_hz
            },
            descending_outputs=channels,
            brain_instance_id=inst_id,
            brain_session_id=brain_sess_id,
            causal_chain_id=chain_id,
            parent_event_id=ev_stim,
            evidence_class="measured"
        )
        last_causal_ev = ev_neural

        # Primitiva 1: INTERACT (MN9 proboscis drive)
        if prob_drive >= 0.20:
            world_before_flynn = load_world_dict()
            cur_focus = world_before_flynn.get("window", {}).get("selected_variable", "sweet")
            is_sweet_available = bool(world_before_flynn.get("sweet", {}).get("available", False))

            # Causal Chain Event 5: FLYNN BODY_ACTION interact
            ev_body = log_experiment_event(
                source="flynn",
                origin_type="resident_brain",
                event_type="BODY_ACTION",
                variable=cur_focus,
                action="interact",
                causal_chain_id=chain_id,
                parent_event_id=last_causal_ev,
                evidence_class="measured"
            )
            last_causal_ev = ev_body

            if cur_focus == "sweet" and is_sweet_available:
                homeo_before = _get_authoritative_homeostasis_state()
                en_before = float(homeo_before["energy_reserve"])
                homeo_after = _post_authoritative_homeostasis("/caverna/homeostasis/replenish", {})
                en_after = float(homeo_after["energy_reserve"])

                # Causal Chain Event 6: HOMEOSTASIS energy reserve change
                ev_homeo = log_experiment_event(
                    source="homeostasis",
                    origin_type="internal_homeostasis",
                    event_type="INTERNAL_STATE_CHANGE",
                    variable="energy_reserve",
                    action=f"energy {en_before:.2f} -> {en_after:.2f}",
                    internal_state_before={"energy_reserve": round(en_before, 3)},
                    internal_state_after={"energy_reserve": round(en_after, 3)},
                    causal_chain_id=chain_id,
                    parent_event_id=last_causal_ev,
                    evidence_class="measured"
                )
                last_causal_ev = ev_homeo

                flynn_req = {
                    "variable": "sweet",
                    "action_id": 1,
                    "requested_at": now,
                    "driving_motor": "MN9 / SEZ",
                    "primitive": "INTERACT",
                    "hz": prob_hz,
                    "drive": prob_drive
                }
                c.execute("UPDATE world_state SET pending_flynn_request = ?, sweet_available = 0, updated_at = ? WHERE id = 1", (json.dumps(flynn_req), now))
                conn.commit()
                world_after_flynn = load_world_dict()

                # Causal Chain Event 7: WORLD sweet=consumed
                log_experiment_event(
                    source="world",
                    origin_type="world_environment",
                    event_type="WORLD_STATE_CHANGE",
                    variable="sweet",
                    action="sweet=consumed",
                    world_before=world_before_flynn,
                    world_after=world_after_flynn,
                    causal_chain_id=chain_id,
                    parent_event_id=last_causal_ev,
                    evidence_class="observed"
                )

                record_event(
                    source="flynn",
                    origin_type="resident_brain",
                    event_type="INGESTION_EVENT",
                    variable="sweet",
                    action="ingestion_consume_sweet",
                    context={
                        "biological_basis": "MN9 proboscis extension reflex encountering available sweet affordance",
                        "primitive": "INTERACT",
                        "driving_motor": "MN9",
                        "proboscis_drive": prob_drive,
                        "proboscis_hz": prob_hz,
                        "nutritive_replenishment": homeo_after["nutritive_increment"],
                        "new_energy_reserve": homeo_after["energy_reserve"],
                        "channels": channels
                    },
                    instance_id=inst_id,
                    brain_session_id=brain_sess_id,
                    stimulus_id=stimulus_id,
                    measured_output={"proboscis_drive": prob_drive, "proboscis_hz": prob_hz, "channels": channels, "rates": rates},
                    measured_rate_hz=prob_hz,
                    world_before=world_before_flynn,
                    world_after=world_after_flynn,
                    evidence_class="VALID_INGESTION",
                    notes="Ingestion event: Flynn oriented to Sweet + proboscis activation with food available replenished energy reserve.",
                    conn=conn
                )
            else:
                # Interação com affordance sem ingestão
                log_experiment_event(
                    source="world",
                    origin_type="world_environment",
                    event_type="WORLD_STATE_CHANGE",
                    variable=cur_focus,
                    action=f"interaction_without_resource_{cur_focus}",
                    world_before=world_before_flynn,
                    world_after=load_world_dict(),
                    causal_chain_id=chain_id,
                    parent_event_id=last_causal_ev,
                    evidence_class="observed"
                )
                record_event(
                    source="flynn",
                    origin_type="resident_brain",
                    event_type="WINDOW_INTERACTION",
                    variable=cur_focus,
                    action=f"proboscis_probe_{cur_focus}",
                    context={
                        "biological_basis": "Proboscis extension without active food consumption",
                        "primitive": "INTERACT",
                        "driving_motor": "MN9",
                        "proboscis_drive": prob_drive,
                        "proboscis_hz": prob_hz
                    },
                    instance_id=inst_id,
                    brain_session_id=brain_sess_id,
                    stimulus_id=stimulus_id,
                    measured_output={"proboscis_drive": prob_drive, "proboscis_hz": prob_hz, "channels": channels, "rates": rates},
                    measured_rate_hz=prob_hz,
                    world_before=world_before_flynn,
                    world_after=load_world_dict(),
                    evidence_class="INTERACTION_WITHOUT_RESOURCE",
                    conn=conn
                )

        # Primitiva 2: ESCAPE (Giant Fiber / DNp01 / DNp02 / DNp11)
        elif channels.get("escape_takeoff", 0.0) >= 0.5 or channels.get("escape_long_mode", 0.0) >= 0.5:
            world_before_flynn = load_world_dict()
            if var == "looming":
                c.execute("UPDATE world_state SET looming_state = 'evaded', updated_at = ? WHERE id = 1", (now,))
            conn.commit()
            world_after_flynn = load_world_dict()

            max_escape_rate = max(
                rates.get("DNp01_left", 0.0), rates.get("DNp01_right", 0.0),
                rates.get("DNp02_left", 0.0), rates.get("DNp02_right", 0.0),
                rates.get("DNp04_left", 0.0), rates.get("DNp04_right", 0.0),
                rates.get("DNp11_left", 0.0), rates.get("DNp11_right", 0.0),
                0.0
            )

            record_event(
                source="flynn",
                origin_type="resident_brain",
                event_type="RESPONSE_TO_OFFER",
                variable=var,
                action="abrupt_evasive_displacement",
                context={
                    "biological_basis": "Giant Fiber (DNp01) / Lobula LC4/LPLC2 looming escape pathway",
                    "primitive": "ESCAPE",
                    "driving_dn": "DNp01 / DNp02 / DNp11",
                    "escape_takeoff": channels.get("escape_takeoff"),
                    "escape_long_mode": channels.get("escape_long_mode"),
                    "channels": channels
                },
                instance_id=inst_id,
                brain_session_id=brain_sess_id,
                stimulus_id=stimulus_id,
                measured_output={"channels": channels, "rates": rates},
                measured_rate_hz=max_escape_rate,
                world_before=world_before_flynn,
                world_after=world_after_flynn,
                evidence_class="EVASION_RESPONSE",
                conn=conn
            )

        # Primitiva 3: BACKWARD (MDN Moonwalker)
        elif channels.get("backward_walk", 0.0) >= 0.20:
            world_before_flynn = load_world_dict()
            world_after_flynn = load_world_dict()
            mdn_rate = max(rates.get("MDN_left", 0.0), rates.get("MDN_right", 0.0), 0.0)

            record_event(
                source="flynn",
                origin_type="resident_brain",
                event_type="RESPONSE_TO_OFFER",
                variable=var,
                action="sagittal_retraction_retreat",
                context={
                    "biological_basis": "Bidaye et al. Moonwalker Descending Neuron (MDN)",
                    "primitive": "BACKWARD",
                    "driving_dn": "MDN",
                    "backward_walk": channels.get("backward_walk"),
                    "channels": channels
                },
                instance_id=inst_id,
                brain_session_id=brain_sess_id,
                stimulus_id=stimulus_id,
                measured_output={"channels": channels, "rates": rates},
                measured_rate_hz=mdn_rate,
                world_before=world_before_flynn,
                world_after=world_after_flynn,
                evidence_class="RETRACTION_RESPONSE",
                conn=conn
            )

        # Primitiva 4: TURN (DNa01 / DNa02 Steering)
        elif channels.get("turn", 0.0) >= 0.50 and abs(channels.get("turn_bias", 0.0)) >= 0.03:
            world_before_flynn = load_world_dict()
            c.execute("UPDATE world_state SET window_variable = ?, updated_at = ? WHERE id = 1", (var, now))
            conn.commit()
            world_after_flynn = load_world_dict()

            turn_rate = max(
                rates.get("DNa01_left", 0.0), rates.get("DNa01_right", 0.0),
                rates.get("DNa02_left", 0.0), rates.get("DNa02_right", 0.0),
                0.0
            )

            record_event(
                source="flynn",
                origin_type="resident_brain",
                event_type="ORIENTING_RESPONSE",
                variable=var,
                action=f"reorient_window_{var}",
                context={
                    "biological_basis": "Rayshubskiy et al. DNa01/DNa02 ipsilateral steering",
                    "primitive": "TURN",
                    "driving_dn": "DNa01/DNa02",
                    "turn_bias": channels.get("turn_bias"),
                    "channels": channels
                },
                instance_id=inst_id,
                brain_session_id=brain_sess_id,
                stimulus_id=stimulus_id,
                measured_output={"channels": channels, "rates": rates},
                measured_rate_hz=turn_rate,
                world_before=world_before_flynn,
                world_after=world_after_flynn,
                evidence_class="STEERING_RESPONSE",
                conn=conn
            )

    conn.close()
    return {"status": "ok", "world": load_world_dict(), "homeostasis": _get_authoritative_homeostasis_state()}


@caverna_router.post("/diagnostic/action")
async def execute_diagnostic_action(payload: DiagnosticActionPayload):
    """
    Injeção manual para diagnóstico técnico.
    REGRA ABSOLUTA: Registra SEMPRE source='diagnostic' e origin_type='diagnostic_injection'.
    PROIBIDO salvar como 'flynn'.
    """
    conn = get_db()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    bridge = payload.action_bridge_name.lower()
    target_var = payload.variable_target or "sweet"
    target_act = payload.action_target or 1

    world_before = load_world_dict()
    if bridge == "turn":
        conn.execute("UPDATE world_state SET window_variable = ?, updated_at = ? WHERE id = 1", (target_var, now))
    elif bridge == "proboscis_drive":
        diag_req = {
            "variable": target_var,
            "action_id": target_act,
            "requested_at": now,
            "driving_motor": "DIAGNOSTIC_INJECTION_MN9",
            "hz": payload.firing_rate_hz
        }
        conn.execute("UPDATE world_state SET pending_flynn_request = ?, updated_at = ? WHERE id = 1", (json.dumps(diag_req), now))

    conn.commit()
    world_after = load_world_dict()

    record_event(
        source="diagnostic",
        origin_type="diagnostic_injection",
        event_type="MANUAL_DIAGNOSTIC_INJECTION",
        variable=target_var,
        action=f"MANUAL_DIAGNOSTIC_INJECTION_{bridge}",
        context={
            "label": "MANUAL_DIAGNOSTIC_INJECTION",
            "bridge": bridge,
            "source_neurons": payload.source_neurons,
            "firing_rate_hz": payload.firing_rate_hz
        },
        measured_output={"injected_bridge": bridge, "source_neurons": payload.source_neurons},
        measured_rate_hz=payload.firing_rate_hz,
        world_before=world_before,
        world_after=world_after,
        evidence_class="INVALID_AS_SPONTANEOUS_BEHAVIOR",
        notes="Diagnostic injection: artificial test payload, not evidence of Flynn spontaneous behavior.",
        conn=conn
    )
    conn.close()
    return {"status": "ok", "world": load_world_dict()}


@caverna_router.post("/flynn/action")
async def execute_flynn_action_forbidden():
    """Endpoint bloqueado por violar a causalidade biológica de Flynn."""
    raise HTTPException(
        status_code=403,
        detail="FORBIDDEN: Direct injection of events with source='flynn' is prohibited. Flynn events can only originate causally from the resident whole-brain daemon."
    )


@caverna_router.get("/events")
async def get_caverna_events(limit: int = Query(50, ge=1, le=500)):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
    SELECT
        event_id, source, origin_type, instance_id, brain_session_id,
        timestamp, stimulus_id, measured_output, measured_rate_hz,
        world_before, world_after, event_type, variable, action, context,
        evidence_class, notes, created_at
    FROM caverna_events
    ORDER BY event_id DESC
    LIMIT ?
    """, (limit,))
    rows = c.fetchall()
    conn.close()

    result = []
    for r in rows:
        d = dict(r)
        for k in ("measured_output", "world_before", "world_after", "context"):
            if d.get(k) and isinstance(d[k], str):
                try:
                    d[k] = json.loads(d[k])
                except Exception:
                    pass
        result.append(d)

    return {"total": len(result), "events": result}


@caverna_router.get("/ledger/events")
async def get_experimental_ledger_events(limit: int = Query(50, ge=1, le=500)):
    """Consulta os registros do ledger experimental canônico (flynn_ledger.db)."""
    from app.ledger import get_events
    events = get_events(limit=limit)
    return {"total": len(events), "events": events}


@caverna_router.get("/ledger/sessions")
async def get_experimental_sessions():
    """Consulta as sessões experimentais registradas no ledger canônico."""
    from app.ledger import get_sessions
    sessions = get_sessions()
    return {"total": len(sessions), "sessions": sessions}


@caverna_router.get("/ledger/stats")
async def get_ledger_statistics():
    """Retorna estatísticas gerais do ledger experimental."""
    return get_ledger_counts()
