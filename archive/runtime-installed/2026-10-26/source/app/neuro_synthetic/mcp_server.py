"""Bounded stdio MCP tools for PicoClaw's deterministic coordination.

Only real persisted state, a durable pause/resume gate, provenance-checked
neural frame acknowledgement, and an explicitly separate instrumental motor
calibration route are exposed. No shell, filesystem, neural-parameter or
stimulus tools exist.
"""

from __future__ import annotations

import json
import hashlib
import math
import os
import atexit
import selectors
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .sqlite_store import FlynnStore, picoclaw_frame_digest


SERVER_INFO = {"name": "flynn-neurosynthetic", "version": "0.1.0"}
_PINOCCHIO_WORKER: subprocess.Popen[str] | None = None
_PINOCCHIO_WORKER_LOCK = threading.Lock()
_NEURAL_FRAME_CACHE: dict[str, list[dict[str, Any]]] = {}
_NEURAL_FRAME_CURSOR: dict[str, tuple[int, float]] = {}
_DN_MANIFEST_CACHE: dict[str, dict[str, Any]] = {}
TOOLS = [
    {
        "name": "flynn_status",
        "description": "Read Flynn V2 integration status, persisted component snapshots, and the ingestion gate.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "flynn_world_state",
        "description": "Read the latest persisted snapshot from Flynn's existing ContinuousWorldEngine.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "pause_activity_ingestion",
        "description": "Pause acceptance of neural activity frames in the Python observation pipeline.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "resume_activity_ingestion",
        "description": "Resume acceptance of provenance-valid neural activity frames in the Python observation pipeline.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "flynn_coordinate_neural_frame",
        "description": "Validate and persist a real LIF frame observation. This deterministic coordinator does not create motor commands or actuate the body.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "event_id": {"type": "string"},
                "episode_id": {"type": "string"},
                "source_component": {"const": "neural_activity_aggregator"},
                "event_type": {"const": "NEURAL_FRAME_OBSERVED"},
                "simulation_time_ms": {"type": "number", "minimum": 0},
                "sequence": {"type": "integer", "minimum": 0},
                "occurred_at_utc": {"type": "string"},
                "provenance_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                "payload": {"type": "object"},
                "dn_readout": {"type": "object"},
            },
            "required": ["event_id", "episode_id", "source_component", "event_type", "simulation_time_ms", "sequence", "occurred_at_utc", "provenance_sha256", "payload"],
            "additionalProperties": False,
        },
    },
    {
        "name": "flynn_dispatch_motor_calibration",
        "description": "Apply a separately identified artificial DN calibration packet through the existing Pinocchio body mapping; never records it as neural activity.",
        "inputSchema": {"type": "object", "properties": {
            "calibration_id": {"type": "string"}, "sequence": {"type": "integer", "minimum": 0},
            "neural_time_ms": {"type": "number", "minimum": 0}, "occurred_at_utc": {"type": "string"},
            "manifest_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
            "mapping_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
            "connectome_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
            "compact_indices": {"type": "array", "items": {"type": "integer"}, "minItems": 1303, "maxItems": 1303},
            "root_ids": {"type": "array", "items": {"type": "integer"}, "minItems": 1303, "maxItems": 1303},
            "spike_counts": {"type": "array", "items": {"type": "integer", "minimum": 0}, "minItems": 1303, "maxItems": 1303},
            "chunk_ms": {"const": 20.0},
            "body_episode_id": {"type": "string", "minLength": 1},
            "body_stream_id": {"type": "string", "minLength": 1},
        }, "required": ["calibration_id", "sequence", "neural_time_ms", "occurred_at_utc", "manifest_sha256", "mapping_sha256", "connectome_sha256", "compact_indices", "root_ids", "spike_counts", "chunk_ms"], "additionalProperties": False},
    },
]


def _stop_pinocchio_worker() -> None:
    global _PINOCCHIO_WORKER
    process, _PINOCCHIO_WORKER = _PINOCCHIO_WORKER, None
    if process is None:
        return
    if process.stdin is not None:
        process.stdin.close()
    try:
        process.wait(timeout=2.0)
    except subprocess.TimeoutExpired:
        process.terminate()
        try:
            process.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


atexit.register(_stop_pinocchio_worker)


def _database_path() -> Path:
    value = os.environ.get("FLYNN_V2_DB")
    if not value:
        raise RuntimeError("FLYNN_V2_DB must point to the shared V2 SQLite database")
    path = Path(value).expanduser()
    if not path.is_file():
        raise RuntimeError("V2 SQLite database does not exist yet; start the integrated Python runtime first")
    return path


def _with_store(callback):
    # A resident MCP/PicoClaw subprocess is a compute/read path.  Only the
    # resident coordinator process may write the episode SQLite.
    readonly = os.environ.get("FLYNN_RESIDENT_SINGLE_WRITER") == "1"
    store = FlynnStore(_database_path(), readonly=readonly)
    try:
        return callback(store)
    finally:
        store.close()


def _status(store: FlynnStore) -> dict[str, Any]:
    world = store.latest_component_state("continuous_world")
    aggregator = store.latest_component_state("neural_activity_aggregator")
    coordinated = store.latest_component_state("neuro_world_coordinator")
    checkpoint = store.latest_component_state("integrated_world_neural_checkpoint")
    homeostasis = (checkpoint["state"].get("homeostasis_state") if checkpoint else None)
    picoclaw = store.latest_component_state("picoclaw_cerebellar_coordinator")
    sensory = store.latest_component_state("visual_light_transducer")
    motor = store.latest_component_state("descending_motor_readout_v2")
    body = store.latest_component_state("pinocchio_body_checkpoint")
    proprioception = store.latest_component_state("synthetic_proprioceptive_readout")
    proprio_input = store.latest_component_state("proprioceptive_neural_transduction")
    actuation = store.latest_component_state("pinocchio_motor_actuation")
    cycle_state = coordinated["state"] if coordinated else None
    return {
        "integration": "PARTIAL",
        "world_snapshot": "AVAILABLE" if world else "NOT_RECORDED",
        "world_snapshot_sequence": world["state"].get("snapshot_sequence") if world else None,
        "world_snapshot_episode": world["state"].get("episode_id") if world else None,
        "world_snapshot_timestamp_utc": world["state"].get("timestamp_utc") if world else None,
        "activity_observation": "AVAILABLE" if aggregator else "NOT_RECORDED",
        "activity_sequence": aggregator["state"].get("sequence") if aggregator else None,
        "activity_episode": aggregator["state"].get("episode_id") if aggregator else None,
        "homeostasis_v2": (
            {"status": "AVAILABLE_FROM_CONFIRMED_CHECKPOINT", **homeostasis}
            if isinstance(homeostasis, dict) else
            {"status": "NOT_INTEGRATED_NO_CONFIRMED_STATE"}
        ),
        "core_lif": (
            "INSTRUMENTAL_CYCLE_INCOMPLETE_RESTORE_REQUIRED"
            if cycle_state and cycle_state.get("cycle_status") == "CYCLE_ADVANCING"
            else (
                "AVAILABLE_IN_INSTRUMENTAL_RUNTIME_NOT_RESIDENT"
                if cycle_state and cycle_state.get("execution_kind") == "INSTRUMENTAL_LOCAL_ONLY"
                else "BLOCKED_NOT_CONNECTED"
            )
        ),
        "body_actuation": (
            "AVAILABLE_IN_INSTRUMENTAL_RUNTIME_NOT_RESIDENT"
            if body else "BLOCKED_NOT_CONNECTED"
        ),
        "body_checkpoint_latest": body["state"] if body else None,
        "body_actuation_latest": actuation["state"] if actuation else None,
        "synthetic_proprioceptive_readout": proprioception["state"] if proprioception else None,
        "proprioceptive_neural_projection": (
            "PASS_REAL_INSTRUMENTAL"
            if proprio_input and proprio_input["state"].get("effect") == "PROPRIOCEPTIVE_INPUT_APPLIED_TO_LIF"
            else "NO_PHYSICAL_DEVIATION_NO_NEURAL_INPUT"
            if proprio_input and proprio_input["state"].get("effect") == "NO_PHYSICAL_DEVIATION_NO_NEURAL_INPUT"
            else proprioception["state"].get("neural_projection", "BLOCKED_NO_APPROVED_NEURAL_TARGET_OR_TRANSDUCTION_GAIN")
            if proprioception else "NOT_MEASURED"
        ),
        "proprioceptive_neural_input_latest": proprio_input["state"] if proprio_input else None,
        "world_neural_coordination": (
            "LAST_CYCLE_INCOMPLETE_RESTORE_REQUIRED"
            if cycle_state and cycle_state.get("cycle_status") == "CYCLE_ADVANCING"
            else ("LAST_INSTRUMENTAL_CYCLE_RECORDED" if cycle_state else "NOT_RECORDED")
        ),
        "last_instrumental_cycle": ({
            "cycle_sequence": cycle_state.get("cycle_sequence"),
            "cycle_status": cycle_state.get("cycle_status"),
            "start_world_time_ms": cycle_state.get("start_world_time_ms"),
            "end_world_time_ms": cycle_state.get("end_world_time_ms"),
            "start_neural_time_ms": cycle_state.get("start_neural_time_ms"),
            "end_neural_time_ms": cycle_state.get("end_neural_time_ms"),
            "synchronization_error_ms": cycle_state.get("synchronization_error_ms"),
            "elapsed_real_ms": cycle_state.get("elapsed_real_ms"),
            "neural_simulation_speed": cycle_state.get("neural_simulation_speed"),
            "sensory_transduction_status": cycle_state.get("sensory_transduction_status"),
            "motor_mapping_status": cycle_state.get("motor_mapping_status"),
            "execution_kind": cycle_state.get("execution_kind"),
        } if cycle_state else None),
        "integrated_checkpoint": "WORLD_NEURAL_PARTIAL_AVAILABLE" if checkpoint else "NOT_RECORDED",
        "integrated_checkpoint_time_ms": checkpoint["state"].get("neural_time_ms") if checkpoint else None,
        "sensory_transduction": (
            sensory["state"].get("calibration_status", "UNVERIFIED")
            if sensory else "NOT_CONNECTED"
        ),
        "motor_mapping": (
            "OFFICIAL_DN_READOUT_ZERO_OUTPUT"
            if motor and motor["state"].get("total_spikes") == 0
            else "OFFICIAL_DN_READOUT_NONZERO_BODY_NOT_CONNECTED"
            if motor
            else "BLOCKED_NO_APPROVED_DN_MAPPING"
        ),
        "picoclaw_cerebellar_function": (
            "DETERMINISTIC_FRAME_COORDINATION_OBSERVATION_ONLY"
            if picoclaw else "BRIDGE_NOT_OBSERVED"
        ),
        "picoclaw_latest_frame": picoclaw["state"] if picoclaw else None,
        "visual_transduction_latest": sensory["state"] if sensory else None,
        "descending_readout_latest": motor["state"] if motor else None,
        "ingestion": store.coordinator_status(),
        "resident_episode": "NOT_STARTED_E02_BLOCKED",
        "boundary": "LOCAL_INSTRUMENTAL_STATUS_CONTROL_AND_FRAME_OBSERVATION_ONLY",
    }


def _call(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "flynn_coordinate_neural_frame":
        value = _with_store(lambda store: _coordinate_neural_frame(store, arguments))
        return {"content": [{"type": "text", "text": json.dumps(value, sort_keys=True)}], "structuredContent": value}
    if name == "flynn_dispatch_motor_calibration":
        value = _with_store(lambda store: _dispatch_motor_calibration(store, arguments))
        return {"content": [{"type": "text", "text": json.dumps(value, sort_keys=True)}], "structuredContent": value}
    if arguments not in ({}, None):
        raise ValueError("these tools accept no arguments")
    if name == "flynn_status":
        value = _with_store(_status)
    elif name == "flynn_world_state":
        def read_world(store: FlynnStore):
            snapshot = store.latest_component_state("continuous_world")
            if snapshot is None:
                raise RuntimeError("no real world snapshot has been persisted yet")
            return snapshot["state"]
        value = _with_store(read_world)
    elif name in {"pause_activity_ingestion", "resume_activity_ingestion"}:
        paused = name == "pause_activity_ingestion"
        value = _with_store(lambda store: store.set_ingestion_paused(
            paused, occurred_at_utc=datetime.now(timezone.utc).isoformat()
        ))
    else:
        raise ValueError(f"unknown tool: {name}")
    return {"content": [{"type": "text", "text": json.dumps(value, sort_keys=True)}], "structuredContent": value}


def _coordinate_neural_frame(store: FlynnStore, arguments: dict[str, Any]) -> dict[str, Any]:
    required = {"event_id", "episode_id", "source_component", "event_type", "simulation_time_ms", "sequence", "occurred_at_utc", "provenance_sha256", "payload"}
    if not isinstance(arguments, dict) or set(arguments) not in (required, required | {"dn_readout"}):
        raise ValueError("neural frame event has an invalid schema")
    if (not arguments["event_id"] or not arguments["episode_id"]
            or arguments["source_component"] != "neural_activity_aggregator"
            or arguments["event_type"] != "NEURAL_FRAME_OBSERVED"):
        raise ValueError("only provenance-bound neural frame observations are accepted")
    if isinstance(arguments["sequence"], bool) or not isinstance(arguments["sequence"], int) or arguments["sequence"] < 0:
        raise ValueError("neural frame sequence must be a non-negative integer")
    simulation_time = arguments["simulation_time_ms"]
    if isinstance(simulation_time, bool) or not isinstance(simulation_time, (int, float)) or simulation_time < 0:
        raise ValueError("neural simulation time must be non-negative")
    timestamp = arguments["occurred_at_utc"]
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise ValueError("occurred_at_utc must be an ISO-8601 UTC timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError("occurred_at_utc must be UTC")
    provenance = arguments["provenance_sha256"]
    if not isinstance(provenance, str) or len(provenance) != 64 or any(ch not in "0123456789abcdef" for ch in provenance):
        raise ValueError("provenance must be a lowercase SHA-256 digest")

    identity_prefix = f"{arguments['episode_id']}:generation:"
    identity_suffix = f":frame:{arguments['sequence']}"
    event_id = arguments["event_id"]
    if not event_id.startswith(identity_prefix) or not event_id.endswith(identity_suffix):
        raise ValueError("transient PicoClaw event identity does not encode its generation and sequence")
    generation_id = event_id[len(identity_prefix):-len(identity_suffix)]
    if not generation_id or ":generation:" in generation_id or ":frame:" in generation_id:
        raise ValueError("transient PicoClaw event identity has an invalid causal generation")

    payload = arguments["payload"]
    motor_readout = arguments.get("dn_readout")
    homeostasis_state = None
    if isinstance(motor_readout, dict) and "homeostasis_state" in motor_readout:
        motor_readout = dict(motor_readout)
        homeostasis_state = motor_readout.pop("homeostasis_state")
    source = {key: payload.get(key) for key in (
        "dataset_version", "mapping_sha256", "manifest_sha256", "core_id", "model_sha256",
        "config_sha256", "connectome_sha256", "start_tick", "end_tick", "dt_ms",
        "active_neuron_count", "total_spikes", "input_sha256", "mapped_spikes",
    )}
    if homeostasis_state is not None:
        source["homeostasis_state"] = homeostasis_state
    source.update({"episode_id": arguments["episode_id"], "sequence": arguments["sequence"],
                   "neural_time_ms": simulation_time})
    if not all(source.get(key) is not None for key in (
            "core_id", "model_sha256", "config_sha256", "connectome_sha256",
            "start_tick", "end_tick", "dt_ms", "mapped_spikes")):
        raise ValueError("transient frame lacks complete LIF provenance")
    expected_payload = {key: source[key] for key in (
        "dataset_version", "mapping_sha256", "manifest_sha256", "core_id", "model_sha256",
        "config_sha256", "connectome_sha256", "start_tick", "end_tick", "dt_ms",
        "active_neuron_count", "total_spikes", "input_sha256", "mapped_spikes",
    )}
    if "causal_generation_id" in payload:
        if payload["causal_generation_id"] != generation_id:
            raise ValueError("PicoClaw payload generation differs from its event identity")
        expected_payload["causal_generation_id"] = generation_id
    if "delivery_epoch" in payload:
        expected_payload["delivery_epoch"] = payload["delivery_epoch"]
    if homeostasis_state is not None:
        homeostasis = homeostasis_state
        if not isinstance(homeostasis, dict):
            raise ValueError("resident frame homeostasis state must be an object")
        if (homeostasis.get("model_epoch") != "homeostasis-v2-measured-cpu-budget-1"
                or homeostasis.get("energy_units") != "normalized_cpu_budget_fraction"
                or float(homeostasis.get("cpu_seconds_per_full_reserve", 0)) <= 0
                or homeostasis.get("episode_id") != arguments["episode_id"]
                or homeostasis.get("causal_generation_id") != generation_id
                or abs(float(homeostasis.get("neural_time_ms", -1)) - simulation_time) > 1e-9
                or not 0.0 <= float(homeostasis.get("energy_reserve", -1)) <= 1.0):
            raise ValueError("homeostasis state differs from the frame's episode/generation/time or range")
    elif os.environ.get("FLYNN_RESIDENT_SINGLE_WRITER") == "1":
        raise ValueError("resident frame is missing its causal Homeostasis V2 state")
    if payload != expected_payload:
        missing = sorted(set(expected_payload) - set(payload))
        extra = sorted(set(payload) - set(expected_payload))
        mismatched = sorted(key for key in set(payload) & set(expected_payload)
                            if payload[key] != expected_payload[key])
        raise ValueError("PicoClaw transient payload differs from its frame descriptor "
                         f"(missing={missing}, extra={extra}, mismatched={mismatched})")
    if source.get("input_sha256") != provenance:
        raise ValueError("transient frame provenance differs from its input SHA-256")
    if (source["dataset_version"] != "fafb-v783"
            or source["end_tick"] <= source["start_tick"]
            or abs(float(source["end_tick"]) * float(source["dt_ms"]) - simulation_time) > max(1e-9, float(source["dt_ms"]) * 1e-9)
            or int(source["active_neuron_count"]) != len(source["mapped_spikes"])
            or int(source["total_spikes"]) != sum(int(item["count"]) for item in source["mapped_spikes"])):
        raise ValueError("transient frame time or sparse spike counts violate the LIF contract")
    # The deployed PicoClaw v0.2.9 bridge forwards the legacy envelope fields
    # only. Recover the generation from its deterministic event identity and
    # derive the idempotency key and digest from the validated frame below.
    # This keeps retries tied to the same durable receipt without a bridge ABI
    # change or another binary dependency.
    active_generation = store.active_causal_generation()
    if (active_generation is None or active_generation["episode_id"] != source["episode_id"]
            or active_generation["generation_id"] != generation_id):
        raise ValueError("transient frame differs from the active episode/generation")
    episode_id, sequence = source["episode_id"], int(source["sequence"])
    idempotency_key = f"{episode_id}|{generation_id}|{sequence}"
    if event_id != f"{episode_id}:generation:{generation_id}:frame:{sequence}":
        raise ValueError("transient PicoClaw identity does not match episode/generation/sequence")
    _validate_transient_dn_readout(source, motor_readout)
    digest_frame = {**source, "causal_generation_id": generation_id}
    actual_digest = picoclaw_frame_digest(digest_frame, motor_readout)
    receipt = store.read_picoclaw_frame_receipt(
        episode_id=episode_id, generation_id=generation_id, frame_seq=sequence,
    )
    if receipt is None or receipt["prepared"].get("frame_digest") != actual_digest:
        prepared_id, _ = store._frame_receipt_ids(episode_id, generation_id, sequence)
        direct = store.connection.execute(
            "SELECT event_id FROM events WHERE event_id=?", (prepared_id,),
        ).fetchone()
        raise RuntimeError(
            "PicoClaw has no matching durable coordinator receipt "
            f"(db={store.path}, active={store.causal_generation_id}, requested={generation_id}/{sequence}, "
            f"prepared_id_present={direct is not None}, digest_matches="
            f"{receipt is not None and receipt['prepared'].get('frame_digest') == actual_digest})"
        )
    if receipt["status"] == "CONFIRMED":
        cache = _NEURAL_FRAME_CACHE.setdefault(episode_id, [])
        cached = next((item for item in cache if item.get("sequence") == sequence), None)
        if cached is None:
            cache.append({"sequence": sequence, "neural_time_ms": simulation_time,
                          "source_frame_sha256": provenance, "dn_readout": motor_readout})
        elif (cached.get("source_frame_sha256") != provenance
                or cached.get("dn_readout") != motor_readout):
            raise ValueError("confirmed frame retry conflicts with the MCP transient aggregation cache")
        previous = _NEURAL_FRAME_CURSOR.get(episode_id)
        if previous is None or previous == (sequence - 1, float(receipt["confirmed"]["start_neural_time_ms"])):
            _NEURAL_FRAME_CURSOR[episode_id] = (sequence, simulation_time)
        elif previous != (sequence, simulation_time):
            raise ValueError("confirmed PicoClaw retry is out of order for this MCP process")
        confirmed = receipt["confirmed"]
        return {
            "episode_id": episode_id, "causal_generation_id": generation_id,
            "sequence": sequence, "neural_time_ms": simulation_time,
            "source_event_id": arguments["event_id"],
            "source_provenance_sha256": provenance,
            "pico_component": "github.com/sipeed/picoclaw/pkg/mcp.Manager.CallTool",
            "pico_version": "v0.2.9", "provider_used": False,
            "coordination": "DURABLE_FRAME_RECEIPT_REPLAY",
            "receipt_key": idempotency_key,
            "frame_digest": actual_digest,
            "receipt_result_sha256": confirmed.get("result_sha256"),
            "output_state_id": confirmed.get("output_state_id"),
            "body_checkpoint_state_id": confirmed.get("body_checkpoint_state_id"),
            "status": "IDEMPOTENT_RETRY",
            "effect": "PRIOR_CONFIRMED_RESULT_RETURNED_NO_REDISPATCH",
            "pinocchio_timing": None, "pinocchio_result": None,
        }
    receipt_epoch = receipt["prepared"].get("delivery_epoch")
    request_epoch = payload.get("delivery_epoch")
    if not receipt_epoch or (request_epoch is not None and request_epoch != receipt_epoch):
        raise RuntimeError(
            "prepared PicoClaw operation is indeterminate after a delivery-epoch change; "
            "automatic redispatch is blocked pending reconciliation"
        )
    orphan_output = store.connection.execute(
        "SELECT 1 FROM component_states WHERE component='pinocchio_body_checkpoint' "
        "AND json_extract(state_json,'$.frame_receipt_key')=? LIMIT 1", (idempotency_key,),
    ).fetchone()
    if orphan_output is not None:
        raise RuntimeError("prepared frame has durable Pinocchio output but no confirmation; refusing blind replay")

    previous_cursor = _NEURAL_FRAME_CURSOR.get(episode_id)
    if previous_cursor is None:
        checkpoint = store.active_checkpoint()
        expected_sequence = int(checkpoint["state"].get("next_sequence", 0)) if checkpoint else 0
        if sequence != expected_sequence:
            raise ValueError("first transient frame sequence does not continue the confirmed checkpoint")
    elif sequence != previous_cursor[0] + 1 or simulation_time <= previous_cursor[1]:
        raise ValueError("transient PicoClaw frame sequence or neural time is not contiguous")

    component = "picoclaw_cerebellar_coordinator"
    state_id = f"picoclaw-frame:{episode_id}:{generation_id}:{sequence}"
    state = {
        "episode_id": episode_id,
        "causal_generation_id": active_generation["generation_id"] if active_generation else None,
        "sequence": sequence,
        "neural_time_ms": simulation_time,
        "source_event_id": arguments["event_id"],
        "source_provenance_sha256": provenance,
        "pico_component": "github.com/sipeed/picoclaw/pkg/mcp.Manager.CallTool",
        "pico_version": "v0.2.9",
        "provider_used": False,
        "coordination": "DETERMINISTIC_FRAME_VALIDATION_AND_ORDERING",
        "dn_readout": motor_readout,
        "motor_dispatch_status": (
            "ZERO_DN_FRAME_NO_NEURAL_COMMAND"
            if motor_readout is not None and motor_readout.get("total_spikes") == 0
            else "MEASURED_DN_COUNTS_AWAITING_20MS_BODY_BOUNDARY"
            if motor_readout is not None
            else "BLOCKED_NO_APPROVED_DN_MAPPING"
        ),
        "physical_actuation": "WAITING_FOR_20MS_BODY_BOUNDARY" if motor_readout is not None else "NOT_REQUESTED",
        "effect": "FRAME_COORDINATED_OBSERVATION_ONLY",
        "receipt_key": idempotency_key,
        "frame_digest": actual_digest,
        "receipt_status": "PREPARED",
    }
    cache = _NEURAL_FRAME_CACHE.setdefault(episode_id, [])
    cache.append({"sequence": sequence, "neural_time_ms": simulation_time,
                  "source_frame_sha256": provenance, "dn_readout": motor_readout})
    is_physical_boundary = abs((simulation_time / 20.0) - round(simulation_time / 20.0)) < 1e-8
    pinocchio_timing = None
    if motor_readout is not None and is_physical_boundary:
        physical_input = _aggregate_neural_dn_boundary(
            store, episode_id=episode_id, boundary_ms=simulation_time,
            current_sequence=arguments["sequence"], current_readout=motor_readout,
            cached_frames=cache,
        )
        mode = "NEURAL_ZERO_CONTROL" if physical_input["total_spikes"] == 0 else "NEURAL_DN_READOUT"
        physical = _run_pinocchio_packet(store, {
            "mode": mode, "sequence": arguments["sequence"],
            "stream_id": f"neural:{episode_id}",
            "episode_id": episode_id,
            "neural_time_ms": simulation_time, "occurred_at_utc": timestamp,
            "frame_receipt_key": idempotency_key,
            "frame_digest": actual_digest,
            "manifest_sha256": physical_input["manifest_sha256"],
            "mapping_sha256": physical_input["mapping_sha256"],
            "connectome_sha256": physical_input["connectome_sha256"],
            "compact_indices": physical_input["compact_indices"],
            "spike_counts": physical_input["spike_counts"], "chunk_ms": 20.0,
            "homeostasis_state": source.get("homeostasis_state"),
        })
        physical["homeostasis_state"] = source.get("homeostasis_state")
        pinocchio_timing = {
            "worker_ms": physical.get("worker_elapsed_ms"),
            "worker_cpu_ms": physical.get("worker_cpu_ms"),
            "worker_phase_ms": physical.get("worker_phase_ms"),
            "worker_transfer_timing": physical.get("worker_transfer_timing"),
        }
        physical_state_id = f"pinocchio-neural:{episode_id}:{sequence}"
        physical["source_event_id"] = state_id
        physical["source_frame_sequences"] = physical_input["source_frame_sequences"]
        physical["source_frame_hashes"] = physical_input["source_frame_hashes"]
        cache[:] = [item for item in cache if item["neural_time_ms"] > simulation_time]
    _NEURAL_FRAME_CURSOR[episode_id] = (sequence, simulation_time)
    return {**state, "status": "FRAME_COORDINATED_OBSERVATION_ONLY",
            "pinocchio_timing": pinocchio_timing,
            "pinocchio_result": physical if motor_readout is not None and is_physical_boundary else None}


def _validate_transient_dn_readout(source: dict[str, Any], readout: dict[str, Any] | None) -> None:
    if not isinstance(readout, dict):
        raise ValueError("transient frame is missing the official DN readout")
    manifest_path = os.environ.get("FLYNN_PINOCCHIO_POPULATION_MANIFEST")
    if not manifest_path:
        raise RuntimeError("official DN manifest is required to validate the transient readout")
    manifest_path = str(Path(manifest_path).resolve())
    manifest = _DN_MANIFEST_CACHE.get(manifest_path)
    if manifest is None:
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
        _DN_MANIFEST_CACHE[manifest_path] = manifest
    compact = [int(value) for value in manifest.get("compact_indices", [])]
    roots = [int(value) for value in manifest.get("root_ids", [])]
    if len(compact) != 1303 or len(roots) != 1303:
        raise ValueError("official DN manifest does not contain 1,303 root mappings")
    by_index = {index: position for position, index in enumerate(compact)}
    counts = [0] * 1303
    seen: set[int] = set()
    for item in source["mapped_spikes"]:
        index, root, count = int(item["compact_index"]), int(item["root_id"]), int(item["count"])
        if index in seen or count <= 0:
            raise ValueError("transient mapped spikes contain duplicate indices or non-positive counts")
        seen.add(index)
        position = by_index.get(index)
        if position is not None:
            if roots[position] != root:
                raise ValueError("transient DN root ID does not match its canonical compact index")
            counts[position] = count
    expected = {
        "population": "flywire-v2.1.0-descending-1303",
        "annotation_sha256": manifest.get("annotation_file_sha256"),
        "mapping_sha256": manifest.get("population_mapping_sha256"),
        "manifest_sha256": hashlib.sha256(Path(manifest_path).read_bytes()).hexdigest(),
        "connectome_sha256": manifest.get("connectome_sha256"),
        "active_neurons": sum(value > 0 for value in counts), "total_spikes": sum(counts),
        "compact_indices": compact, "spike_counts": counts, "effect": "MEASURED_DN_READOUT_ONLY",
    }
    if readout != expected:
        raise ValueError("transient DN readout differs from the official root map and measured LIF spikes")


def _aggregate_neural_dn_boundary(store: FlynnStore, *, episode_id: str, boundary_ms: float,
                                  current_sequence: int, current_readout: dict[str, Any],
                                  cached_frames: list[dict[str, Any]]) -> dict[str, Any]:
    """Sum transient, validated frame readouts since the last paired body checkpoint."""
    stream_id = f"neural:{episode_id}"
    checkpoint = store.active_checkpoint()
    body_ref = (checkpoint or {}).get("state", {}).get("body_checkpoint")
    if isinstance(body_ref, dict):
        body_record = store.component_state_by_id(str(body_ref.get("component_state_id", "")))
        prior_physical = body_record["state"] if body_record is not None else None
        if prior_physical is None:
            raise RuntimeError("active causal checkpoint body state is missing from the physical readout")
    else:
        row = store.connection.execute(
            "SELECT state_json FROM component_states WHERE component='pinocchio_body_checkpoint' ORDER BY rowid DESC LIMIT 1"
        ).fetchone()
        prior_physical = json.loads(row[0]) if row else None
    if prior_physical is not None and prior_physical.get("stream_id") != stream_id:
        prior_physical = None
    start_ms = float(prior_physical["physical_time_ms"]) if prior_physical else boundary_ms - 20.0
    if not math.isclose(boundary_ms - start_ms, 20.0, rel_tol=0, abs_tol=1e-8):
        raise ValueError("neural-to-body dispatch must cover exactly one 20 ms physical interval")
    frames = [frame for frame in cached_frames
              if float(frame["neural_time_ms"]) > start_ms and float(frame["neural_time_ms"]) <= boundary_ms]
    if not frames or frames[-1].get("sequence") != current_sequence:
        raise ValueError("20 ms body interval lacks its transient official DN readouts")
    expected_sequences = list(range(int(frames[0]["sequence"]), current_sequence + 1))
    if [int(frame["sequence"]) for frame in frames] != expected_sequences:
        raise ValueError("neural DN frames in physical interval are discontinuous")
    for frame in frames:
        readout = frame["dn_readout"]
        for key in ("manifest_sha256", "mapping_sha256", "connectome_sha256", "compact_indices"):
            if readout.get(key) != current_readout.get(key):
                raise ValueError(f"DN physical interval changed population provenance: {key}")
    counts = [sum(int(frame["dn_readout"]["spike_counts"][index]) for frame in frames)
              for index in range(1303)]
    if max(counts, default=0) > 2**32 - 1:
        raise OverflowError("aggregated 20 ms DN count exceeds uint32")
    return {
        "manifest_sha256": current_readout["manifest_sha256"],
        "mapping_sha256": current_readout["mapping_sha256"],
        "connectome_sha256": current_readout["connectome_sha256"],
        "compact_indices": current_readout["compact_indices"],
        "spike_counts": counts,
        "total_spikes": sum(counts),
        "source_frame_sequences": expected_sequences,
        "source_frame_hashes": [frame["source_frame_sha256"] for frame in frames],
    }


def _dispatch_motor_calibration(store: FlynnStore, arguments: dict[str, Any]) -> dict[str, Any]:
    if store.readonly:
        raise RuntimeError("instrumental motor calibration is unavailable through the resident read-only PicoClaw path")
    required = {
        "calibration_id", "sequence", "neural_time_ms", "occurred_at_utc", "manifest_sha256",
        "mapping_sha256", "connectome_sha256", "compact_indices", "root_ids", "spike_counts", "chunk_ms",
    }
    optional = {"body_episode_id", "body_stream_id"}
    if not isinstance(arguments, dict) or set(arguments) not in (required, required | optional):
        raise ValueError("motor calibration packet schema mismatch")
    if not arguments["calibration_id"].startswith("instrumental-motor-calibration:"):
        raise ValueError("calibration ID must identify an external instrumental stimulus")
    if len(arguments["compact_indices"]) != 1303 or len(arguments["root_ids"]) != 1303 or len(arguments["spike_counts"]) != 1303:
        raise ValueError("motor calibration must use exactly the official 1,303 DN slots")
    spike_sum = sum(arguments["spike_counts"])
    if spike_sum <= 0 and arguments["sequence"] == 0:
        raise ValueError("the first calibration step must contain a non-zero external packet")
    if set(arguments) == required | optional and (
            not arguments["body_episode_id"] or not arguments["body_stream_id"]):
        raise ValueError("body episode and stream IDs must both be non-empty")
    physical = _run_pinocchio_packet(store, {**arguments, "mode": "ARTIFICIAL_CALIBRATION_ONLY",
                                             "stream_id": arguments.get("body_stream_id", arguments["calibration_id"]),
                                             "episode_id": arguments.get("body_episode_id", arguments["calibration_id"])})
    if physical["dn_spike_sum"] != spike_sum:
        raise RuntimeError("Pinocchio result does not match the calibrated DN packet")
    if spike_sum > 0 and (physical["torque_max_abs"] <= 0 or physical["q_delta_max_abs"] <= 0):
        raise RuntimeError("Pinocchio did not produce a calculated physical response to the calibrated DN packet")
    event_id = f"{arguments['calibration_id']}:pinocchio:{arguments['sequence']}"
    physical["calibration_id"] = arguments["calibration_id"]
    store.record_state(state_id=event_id, event_id=f"{event_id}:state", component="pinocchio_motor_calibration",
                       occurred_at_utc=arguments["occurred_at_utc"], neural_time_ms=arguments["neural_time_ms"], state=physical)
    store.record_event(event_id=f"{event_id}:applied", event_type="INSTRUMENTAL_PINOCCHIO_MOTOR_CALIBRATION",
                       source="external_calibration_equipment", occurred_at_utc=arguments["occurred_at_utc"],
                       neural_time_ms=arguments["neural_time_ms"], provenance_sha256=arguments["manifest_sha256"], payload=physical)
    return {**physical, "status": "MOTOR_CALIBRATION_APPLIED_NOT_FLYNN_ACTIVITY"}


def _run_pinocchio_packet(store: FlynnStore, packet: dict[str, Any]) -> dict[str, Any]:
    project_root = Path(os.environ.get("FLYNN_PROJECT_ROOT", Path.cwd())).resolve()
    python = os.environ.get("FLYNN_PINOCCHIO_PYTHON")
    manifest = os.environ.get("FLYNN_PINOCCHIO_POPULATION_MANIFEST")
    if not python or not manifest:
        raise RuntimeError("Pinocchio worker is not configured with its isolated Python and official population manifest")
    manifest_path = Path(manifest).resolve()
    manifest_obj = json.loads(manifest_path.read_text(encoding="utf-8"))
    if packet.get("root_ids") is None:
        packet["root_ids"] = manifest_obj["root_ids"]
    homeostasis = packet.get("homeostasis_state")
    if packet.get("mode") == "ARTIFICIAL_CALIBRATION_ONLY":
        packet["actuation_scale"] = 1.0
    else:
        if not isinstance(homeostasis, dict):
            raise ValueError("neural Pinocchio packet requires a Homeostasis V2 sample")
        if (abs(float(homeostasis.get("neural_time_ms", -1)) - float(packet["neural_time_ms"])) > 1e-9
                or not 0.0 <= float(homeostasis.get("energy_reserve", -1)) <= 1.0):
            raise ValueError("Pinocchio energy sample is not aligned with the causal body boundary")
        packet["actuation_scale"] = float(homeostasis["energy_reserve"])
        packet["homeostasis_state_sha256"] = hashlib.sha256(json.dumps(
            homeostasis, sort_keys=True, separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")).hexdigest()
    stream_id = str(packet["stream_id"])
    previous = None
    checkpoint = store.active_checkpoint()
    body_ref = (checkpoint or {}).get("state", {}).get("body_checkpoint")
    if isinstance(body_ref, dict):
        body_record = store.component_state_by_id(str(body_ref.get("component_state_id", "")))
        if body_record is None:
            raise RuntimeError("active causal checkpoint body state is missing from Pinocchio input")
        candidate = body_record["state"]
        if candidate.get("stream_id") == stream_id:
            previous = candidate
    else:
        row = store.connection.execute(
            "SELECT state_json FROM component_states WHERE component='pinocchio_body_checkpoint' ORDER BY rowid DESC LIMIT 1"
        ).fetchone()
        if row:
            candidate = json.loads(row[0])
            if candidate.get("stream_id") == stream_id:
                previous = candidate
    stream_sequence = int(previous["stream_sequence"]) + 1 if previous else 0
    if packet["mode"] == "ARTIFICIAL_CALIBRATION_ONLY" and int(packet["sequence"]) != stream_sequence:
        raise ValueError("calibration stream sequence must be contiguous; no body-state reset is allowed")
    current_time = float(packet["neural_time_ms"])
    if not math.isfinite(current_time) or current_time < 0:
        raise ValueError("physical timestamp must be finite and non-negative")
    if previous and not math.isclose(
            current_time - float(previous["physical_time_ms"]), float(packet["chunk_ms"]),
            rel_tol=0, abs_tol=1e-8):
        raise ValueError("body stream time must advance by exactly one physical integration interval")
    if previous and any(previous.get(key) != packet.get(key) for key in
                        ("manifest_sha256", "mapping_sha256", "connectome_sha256")):
        raise ValueError("body checkpoint provenance differs from the current DN stream")
    request_id = uuid.uuid4().hex
    worker_request = {**packet, "request_id": request_id, "population_manifest": str(manifest_path)}
    if previous:
        worker_request["initial_body_state"] = previous["body_state"]
        worker_request["initial_body_model_sha256"] = previous["body_model_sha256"]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root)
    worker_script = project_root / "app" / "neuro_synthetic" / "pinocchio_motor_worker.py"
    serialization_started = time.perf_counter()
    request_line = json.dumps(worker_request, separators=(",", ":"), allow_nan=False) + "\n"
    request_serialization_ms = (time.perf_counter() - serialization_started) * 1000.0
    global _PINOCCHIO_WORKER
    worker_was_started = False
    with _PINOCCHIO_WORKER_LOCK:
        if _PINOCCHIO_WORKER is None or _PINOCCHIO_WORKER.poll() is not None:
            if _PINOCCHIO_WORKER is not None:
                _stop_pinocchio_worker()
            worker_start_started = time.perf_counter()
            _PINOCCHIO_WORKER = subprocess.Popen(
                [python, str(worker_script)], cwd=project_root, env=env,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, encoding="utf-8", bufsize=1,
            )
            worker_process_start_ms = (time.perf_counter() - worker_start_started) * 1000.0
            worker_was_started = True
        else:
            worker_process_start_ms = 0.0
        process = _PINOCCHIO_WORKER
        if process.stdin is None or process.stdout is None:
            raise RuntimeError("persistent Pinocchio worker stdio is unavailable")
        process_started = time.perf_counter()
        try:
            process.stdin.write(request_line)
            process.stdin.flush()
            selector = selectors.DefaultSelector()
            try:
                selector.register(process.stdout, selectors.EVENT_READ)
                if not selector.select(45.0):
                    raise TimeoutError("persistent Pinocchio worker exceeded its 45-second deadline")
                response_line = process.stdout.readline()
            finally:
                selector.close()
            if not response_line:
                raise RuntimeError(f"persistent Pinocchio worker exited with status {process.poll()}")
        except Exception:
            _stop_pinocchio_worker()
            raise
        worker_process_elapsed_ms = (time.perf_counter() - process_started) * 1000.0
    response_parse_started = time.perf_counter()
    try:
        response = json.loads(response_line)
    except ValueError as exc:
        _stop_pinocchio_worker()
        raise RuntimeError("persistent Pinocchio worker returned invalid JSON") from exc
    if response.get("request_id") != request_id or response.get("error"):
        raise RuntimeError(f"isolated Pinocchio worker rejected packet: {response.get('error')}")
    physical = response["result"]
    physical["worker_transfer_timing"] = {
        "request_serialization_ms": request_serialization_ms,
        "persistent_worker_roundtrip_ms": worker_process_elapsed_ms,
        "worker_process_start_ms": worker_process_start_ms,
        "worker_process_restarted": worker_was_started,
        "response_parse_ms": (time.perf_counter() - response_parse_started) * 1000.0,
        "request_bytes": len(request_line.encode("utf-8")),
        "response_bytes": len(response_line.encode("utf-8")),
        "worker_python_and_jsonl_overhead_ms": max(
            0.0, worker_process_elapsed_ms - float(physical.get("worker_elapsed_ms", 0.0)),
        ),
    }
    physical["stream_id"] = stream_id
    physical["episode_id"] = packet.get("episode_id")
    physical["episode_id"] = packet.get("episode_id")
    physical["stream_sequence"] = stream_sequence
    checkpoint_hash = __import__("hashlib").sha256(stream_id.encode("utf-8")).hexdigest()[:20]
    checkpoint_id = f"pinocchio-body:{checkpoint_hash}:{stream_sequence}"
    checkpoint = {
        "schema": "flynn.pinocchio_body_checkpoint.v1",
        "episode_id": packet.get("episode_id"),
        "stream_id": stream_id,
        "stream_sequence": stream_sequence,
        "source_sequence": int(packet["sequence"]),
        "neural_time_ms": float(packet["neural_time_ms"]),
        "occurred_at_utc": packet["occurred_at_utc"],
        "manifest_sha256": packet["manifest_sha256"],
        "mapping_sha256": packet["mapping_sha256"],
        "connectome_sha256": packet["connectome_sha256"],
        "homeostasis_state": homeostasis,
        "homeostasis_state_sha256": packet.get("homeostasis_state_sha256"),
        "body_model_sha256": physical["body_model_sha256"],
        "body_state": physical["checkpoint_state_exact"],
        "node_identities": list(physical["body_state"]["nodes"]),
        "edge_identities": [
            {"source": edge["source"], "target": edge["target"],
             "dynamic_joint_link": edge["dynamic_joint_link"]}
            for edge in physical["proprioceptive_readout"]["edges"]
        ],
        "canonical_node_count": physical["body_state"]["topology_nodes"],
        "canonical_edge_count": physical["proprioceptive_readout"]["body_model"]["canonical_edge_count"],
        "physical_time_ms": float(packet["neural_time_ms"]),
            "checkpoint_precision": "float64_roundtrip_json",
            "frame_receipt_key": packet.get("frame_receipt_key"),
            "frame_digest": packet.get("frame_digest"),
        }
    sqlite_persist_started = time.perf_counter()
    proprio_id = f"pinocchio-proprio:{checkpoint_hash}:{stream_sequence}"
    proprio = physical["proprioceptive_readout"]
    proprio.update({"stream_id": stream_id, "stream_sequence": stream_sequence,
                    "episode_id": packet.get("episode_id"),
                    "body_model_sha256": physical["body_model_sha256"],
                    "body_checkpoint_id": checkpoint_id})
    if not store.readonly:
        store.record_state(state_id=checkpoint_id, event_id=f"{checkpoint_id}:state",
                           component="pinocchio_body_checkpoint", occurred_at_utc=packet["occurred_at_utc"],
                           neural_time_ms=packet["neural_time_ms"], state=checkpoint)
        store.record_event(event_id=f"{checkpoint_id}:recorded", event_type="PINOCCHIO_BODY_CHECKPOINT_RECORDED",
                           source="isolated_pinocchio_worker", occurred_at_utc=packet["occurred_at_utc"],
                           neural_time_ms=packet["neural_time_ms"], provenance_sha256=packet["manifest_sha256"],
                           payload={"stream_id": stream_id, "stream_sequence": stream_sequence,
                                    "body_model_sha256": physical["body_model_sha256"]})
        store.record_state(state_id=proprio_id, event_id=f"{proprio_id}:state",
                           component="synthetic_proprioceptive_readout",
                           occurred_at_utc=packet["occurred_at_utc"],
                           neural_time_ms=packet["neural_time_ms"], state=proprio)
        store.record_event(event_id=f"{proprio_id}:sampled", event_type="SYNTHETIC_PROPRIOCEPTION_MEASURED",
                           source="pinocchio_body_state_transducer",
                           occurred_at_utc=packet["occurred_at_utc"],
                           neural_time_ms=packet["neural_time_ms"],
                           provenance_sha256=packet["manifest_sha256"],
                           payload={"stream_id": stream_id, "stream_sequence": stream_sequence,
                                    "body_checkpoint_id": checkpoint_id,
                                    "neural_projection": proprio["neural_projection"]})
    if store.readonly:
        physical["worker_transfer_timing"]["sqlite_persistence"] = "DEFERRED_TO_RESIDENT_COORDINATOR"
    else:
        physical["worker_transfer_timing"]["sqlite_body_state_and_readout_persist_ms"] = (
            time.perf_counter() - sqlite_persist_started
        ) * 1000.0
    physical["worker_transfer_timing"]["physical_boundary_total_ms"] = (
        physical["worker_transfer_timing"]["persistent_worker_roundtrip_ms"]
        + float(physical["worker_transfer_timing"].get("sqlite_body_state_and_readout_persist_ms", 0.0))
    )
    physical["proprioceptive_readout"] = proprio
    physical["body_checkpoint"] = checkpoint
    physical["body_checkpoint_state_id"] = checkpoint_id
    physical["proprioceptive_state_id"] = proprio_id
    physical["frame_receipt_key"] = packet.get("frame_receipt_key")
    physical["frame_digest"] = packet.get("frame_digest")
    return physical


def _handle(message: dict[str, Any]) -> dict[str, Any] | None:
    method = message.get("method")
    request_id = message.get("id")
    params = message.get("params") or {}
    if method == "notifications/initialized" or method == "notifications/cancelled":
        return None
    try:
        if method == "initialize":
            result = {
                "protocolVersion": params.get("protocolVersion", "2024-11-05"),
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": SERVER_INFO,
            }
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {"tools": TOOLS}
        elif method == "tools/call":
            result = _call(params.get("name", ""), params.get("arguments", {}))
        else:
            if request_id is None:
                return None
            return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": "method not found"}}
        if request_id is None:
            return None
        return {"jsonrpc": "2.0", "id": request_id, "result": result}
    except Exception as exc:
        if request_id is None:
            return None
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32000, "message": str(exc)}}


def serve() -> None:
    """Run the MCP stdio transport used by PicoClaw."""
    for line in sys.stdin:
        try:
            request = json.loads(line)
            if not isinstance(request, dict):
                continue
            response = _handle(request)
        except Exception as exc:
            response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(exc)}}
        if response is not None:
            sys.stdout.write(json.dumps(response, separators=(",", ":")) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    serve()
