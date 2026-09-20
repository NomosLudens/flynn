"""
Flynn Experiment Ledger Compatibility Adapter (Gate 012B).
Delegates ALL operations directly to the canonical ledger writer (app.ledger) targeting:
/home/ubuntu/Portifolio/flynn-max/runtime/data/flynn_ledger.db

Dual writing to flynn_experiment.db is completely eliminated.
"""

import sys
import time
import json
import uuid
import csv
import io
import threading
import math
from typing import Optional, Dict, Any, List, Tuple

import app.ledger as canonical

# Re-export core functions from canonical
get_ledger_conn = canonical.get_ledger_conn
start_session = canonical.start_session
end_session = canonical.end_session
log_event = canonical.log_event
log_snapshot = canonical.record_snapshot
record_snapshot = canonical.record_snapshot
get_sessions = canonical.get_sessions
get_events = canonical.get_events
get_latest_events = canonical.get_latest_events
get_ledger_stats = canonical.get_ledger_stats
get_causal_trace = canonical.get_causal_trace

_SNAPSHOT_WORKER_THREAD: Optional[threading.Thread] = None
_SNAPSHOT_WORKER_RUNNING = False
_ACTIVE_OBSERVATION_WINDOWS: Dict[str, Dict[str, Any]] = {}
_WINDOW_LOCK = threading.Lock()


def export_session_json(session_id: str) -> Dict[str, Any]:
    sess = canonical.get_session(session_id)
    events = canonical.get_events(session_id=session_id, limit=5000)
    return {
        "session": sess,
        "event_count": len(events),
        "events": events
    }


def export_session_csv(session_id: str) -> str:
    events = canonical.get_events(session_id=session_id, limit=5000)
    if not events:
        return "event_id,timestamp_utc,source,origin_type,event_type,variable,action,causal_chain_id,parent_event_id\n"
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "event_id", "timestamp_utc", "source", "origin_type", "event_type",
        "variable", "action", "causal_chain_id", "parent_event_id", "evidence_class"
    ])
    for e in events:
        writer.writerow([
            e.get("event_id"), e.get("timestamp_utc"), e.get("source"),
            e.get("origin_type"), e.get("event_type"), e.get("variable"),
            e.get("action"), e.get("causal_chain_id"), e.get("parent_event_id"),
            e.get("evidence_class")
        ])
    return output.getvalue()


def start_observation_window(
    variable: str,
    action_id: int,
    causal_chain_id: str,
    timeout_sec: float = 3.0,
    criterion: str = "feeding_extension"
) -> str:
    """Abre uma janela de observação experimental registrando OBSERVATION_WINDOW_OPEN no ledger canônico."""
    window_id = f"win_{uuid.uuid4().hex[:8]}"
    now_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # Log OBSERVATION_WINDOW_OPEN
    window_ev_id = canonical.log_event(
        source="system",
        origin_type="system",
        event_type="OBSERVATION_WINDOW_OPEN",
        variable=variable,
        action=str(action_id),
        causal_chain_id=causal_chain_id,
        observation_window_id=window_id,
        evidence_class="observed",
        notes=f"Observation window open for {variable} (criterion: {criterion}, timeout: {timeout_sec}s)"
    )

    with _WINDOW_LOCK:
        _ACTIVE_OBSERVATION_WINDOWS[causal_chain_id] = {
            "window_id": window_id,
            "window_event_id": window_ev_id,
            "variable": variable,
            "action_id": action_id,
            "opened_at": now_utc,
            "active": True
        }

    def _timeout_cb():
        time.sleep(timeout_sec)
        with _WINDOW_LOCK:
            win_info = _ACTIVE_OBSERVATION_WINDOWS.get(causal_chain_id)
            if not win_info or not win_info.get("active"):
                return
            win_info["active"] = False

        # Timeout: Log NO_RESPONSE as child of OBSERVATION_WINDOW_OPEN (Sections 19, 43)
        try:
            canonical.create_child_event(
                parent_event_id=win_info["window_event_id"],
                causal_chain_id=causal_chain_id,
                source="system",
                origin_type="system",
                event_type="NO_RESPONSE",
                variable=variable,
                action=str(action_id),
                observation_window_id=win_info["window_id"],
                evidence_class="observed",
                notes=f"Observation window {win_info['window_id']} closed with NO_RESPONSE after {timeout_sec}s timeout"
            )
        except Exception as e:
            print(f"Error logging NO_RESPONSE in canonical ledger: {e}")

    t = threading.Thread(target=_timeout_cb, daemon=True)
    t.start()
    return window_id


def cancel_observation_window(causal_chain_id: str):
    with _WINDOW_LOCK:
        win_info = _ACTIVE_OBSERVATION_WINDOWS.get(causal_chain_id)
        if win_info:
            win_info["active"] = False


def start_snapshot_worker(get_world_fn, get_internal_fn, get_brain_fn=None, interval_sec: float = 1.0):
    """Inicia o snapshot worker que grava SOMENTE no ledger canônico (flynn_ledger.db)."""
    global _SNAPSHOT_WORKER_THREAD, _SNAPSHOT_WORKER_RUNNING
    if _SNAPSHOT_WORKER_RUNNING:
        return

    _SNAPSHOT_WORKER_RUNNING = True

    previous_position = None
    previous_state = None

    def _decorate_brain_snapshot(brain: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Attach factual trajectory data to the canonical brain snapshot."""
        nonlocal previous_position, previous_state
        if not isinstance(brain, dict):
            return None
        body = brain.get("sigil_body")
        nodes = body.get("nodes") if isinstance(body, dict) else None
        if not isinstance(nodes, dict) or not nodes:
            return brain

        points = [[float(p[0]), float(p[1])] for p in nodes.values() if isinstance(p, list) and len(p) >= 2]
        if not points:
            return brain
        local_centroid = [sum(p[0] for p in points) / len(points), sum(p[1] for p in points) / len(points)]
        raw_world_position = brain.get("body_position")
        position = ([float(raw_world_position[0]), float(raw_world_position[1])]
                    if isinstance(raw_world_position, (list, tuple)) and len(raw_world_position) >= 2
                    else list(local_centroid))
        before = list(previous_position) if previous_position is not None else None
        displacement = [position[i] - before[i] for i in (0, 1)] if before else [0.0, 0.0]
        distance = math.hypot(displacement[0], displacement[1])
        direction = math.degrees(math.atan2(displacement[1], displacement[0])) if distance > 0 else None
        q = body.get("q") or []
        qdot = body.get("qdot") or []
        body_capacity = float(body.get("body_capacity", brain.get("energy_reserve", 1.0)))
        trajectory = {
            "event_id": str(uuid.uuid4()),
            "event_kind": "MOVEMENT" if distance >= 0.00001 else "SNAPSHOT",
            "position_before": before,
            "position_after": [round(x, 8) for x in position],
            "displacement": [round(x, 8) for x in displacement],
            "distance": round(distance, 8),
            "direction_degrees": round(direction, 4) if direction is not None else None,
            "state_before": previous_state,
            "state_after": {
                "state_seq": body.get("state_seq"),
                "neural_time_ms": brain.get("neural_time_ms"),
                "energy_reserve": brain.get("energy_reserve"),
                "feeding_drive": brain.get("feeding_drive"),
                "body_capacity": round(body_capacity, 8),
                "q_norm": round(math.sqrt(sum(float(x) * float(x) for x in q)), 8),
                "qdot_norm": round(math.sqrt(sum(float(x) * float(x) for x in qdot)), 8),
            },
            "energy_reserve": brain.get("energy_reserve"),
            "feeding_drive": brain.get("feeding_drive"),
            "body_capacity": round(body_capacity, 8),
            "requested_actuation": body.get("requested_actuation", []),
            "executed_actuation": body.get("executed_actuation", body.get("motor_vector", [])),
            "geometry_summary": {
                "body_id": body.get("body_id"),
                "node_count": len(nodes),
                "local_centroid": [round(x, 8) for x in local_centroid],
                "centroid_definition": "arithmetic mean of the 23 Pinocchio frame x/y positions; not world locomotion",
            },
            "world": {
                "position": [round(x, 8) for x in position],
                "displacement": brain.get("world_displacement", displacement),
                "distance_to_resource": brain.get("distance_to_resource", {}),
                "contact_state": brain.get("contact_state", {}),
                "last_contact": brain.get("last_contact"),
                "last_consumption": brain.get("last_consumption"),
                "world_scale": brain.get("world_scale", 1.0),
                "locomotion_reference": brain.get("locomotion_reference", "PINOCCHIO_FRAME_CENTROID_DELTA"),
            },
            "sensory_return": brain.get("sensory_return", {}),
            "neural": {
                "active_dn_count": body.get("dn_active_neurons", 0),
                "total_spikes": body.get("dn_spike_sum", 0),
                "top_active_dns": body.get("top_active_dns", []),
            },
            "provenance": {
                "body": "PINOCCHIO_RESIDENT",
                "neural": "REAL_DN_ACTIVITY",
                "homeostasis": "RESIDENT_HOMEOSTASIS",
                "world": "CAVERNA_RESIDENT",
            },
        }
        decorated = dict(brain)
        decorated["trajectory"] = trajectory
        previous_position = position
        previous_state = trajectory["state_after"]
        return decorated

    def _worker():
        while _SNAPSHOT_WORKER_RUNNING:
            try:
                w = get_world_fn() if get_world_fn else None
                i = get_internal_fn() if get_internal_fn else None
                b = get_brain_fn() if get_brain_fn else None
                b = _decorate_brain_snapshot(b)
                b_inst = b.get("instance_id") if isinstance(b, dict) else None

                canonical.record_snapshot(
                    world_state=w,
                    internal_state=i,
                    brain_state=b,
                    window_state=w.get("window_variable") if isinstance(w, dict) else None,
                    brain_instance_id=b_inst
                )
            except Exception as e:
                pass
            time.sleep(interval_sec)

    _SNAPSHOT_WORKER_THREAD = threading.Thread(target=_worker, daemon=True, name="CanonicalSnapshotWorker")
    _SNAPSHOT_WORKER_THREAD.start()


def stop_snapshot_worker():
    global _SNAPSHOT_WORKER_RUNNING
    _SNAPSHOT_WORKER_RUNNING = False
