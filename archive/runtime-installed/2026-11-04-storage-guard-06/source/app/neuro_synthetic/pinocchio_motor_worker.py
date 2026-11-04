"""One-shot isolated Pinocchio worker for an authorized 1,303-DN packet.

This process uses the dedicated robotics Python environment. It applies the
existing PinocchioSigilBody DN-to-torque map; it does not implement a second
mapping or create a graphical substitute.
"""

from __future__ import annotations

import hashlib
import json
import resource
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

import numpy as np

from app.body.pinocchio_sigil import SIGIL_EDGES, SIGIL_MODULES, SIGIL_PARENT, PinocchioSigilBody
from app.body.proprioceptive_readout import SyntheticProprioceptiveReadout


_CACHED_BODY: PinocchioSigilBody | None = None
_CACHED_DN_INDICES: np.ndarray | None = None
_CACHED_BODY_MODEL_SHA256: str | None = None
_CACHED_INITIAL_STATE: dict | None = None


def run(request: dict) -> dict:
    global _CACHED_BODY, _CACHED_DN_INDICES, _CACHED_BODY_MODEL_SHA256, _CACHED_INITIAL_STATE
    started = time.perf_counter()
    cpu_started = time.process_time()
    validation_started = time.perf_counter()
    manifest_path = Path(request["population_manifest"])
    manifest_bytes = manifest_path.read_bytes()
    manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
    manifest = json.loads(manifest_bytes)
    if manifest_sha != request["manifest_sha256"]:
        raise ValueError("DN population manifest hash mismatch")
    if manifest.get("connectome_sha256") != request["connectome_sha256"]:
        raise ValueError("DN packet belongs to another signed CSR")
    if manifest.get("population_mapping_sha256") != request["mapping_sha256"]:
        raise ValueError("DN packet mapping hash differs from official population")
    indices = np.asarray(manifest["compact_indices"], dtype=np.int64)
    roots = np.asarray(manifest["root_ids"], dtype=np.uint64)
    if len(indices) != 1303 or len(roots) != 1303 or len(set(map(int, roots))) != 1303:
        raise ValueError("official motor population must contain 1,303 unique root IDs")
    if request.get("compact_indices") != indices.tolist() or request.get("root_ids") != roots.tolist():
        raise ValueError("DN packet order or root-ID correspondence mismatch")
    counts = np.asarray(request["spike_counts"], dtype=np.int64)
    if counts.shape != (1303,) or np.any(counts < 0):
        raise ValueError("DN packet must contain 1,303 non-negative counts")
    if request["mode"] not in {"NEURAL_ZERO_CONTROL", "NEURAL_DN_READOUT", "ARTIFICIAL_CALIBRATION_ONLY"}:
        raise ValueError("unsupported motor packet origin")
    if request["mode"] == "NEURAL_ZERO_CONTROL" and np.any(counts):
        raise ValueError("zero control cannot contain DN spikes")
    # The physical model's approved integration interval is 20 ms.
    if request["chunk_ms"] != PinocchioSigilBody.DT_SEC * 1000:
        raise ValueError("motor packet must align to Pinocchio's 20 ms integration interval")

    validation_ms = (time.perf_counter() - validation_started) * 1000.0
    model_started = time.perf_counter()
    if _CACHED_BODY is None:
        body = PinocchioSigilBody(dn_idx=indices, chunk_ms=request["chunk_ms"])
        _CACHED_BODY_MODEL_SHA256 = hashlib.sha256(
            (Path(__file__).resolve().parents[1] / "body" / "pinocchio_sigil.py").read_bytes()
            + json.dumps({"modules": SIGIL_MODULES, "edges": SIGIL_EDGES,
                          "parents": SIGIL_PARENT, "dt_sec": body.DT_SEC,
                          "max_torque": body.MAX_TORQUE, "max_speed": body.MAX_SPEED,
                          "root_joint": "PINOCCHIO_PLANAR_XY_YAW_SYNTHETIC"},
                         sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        _CACHED_BODY = body
        _CACHED_DN_INDICES = indices.copy()
        _CACHED_INITIAL_STATE = body.state_snapshot()
    else:
        if (_CACHED_DN_INDICES is None or not np.array_equal(indices, _CACHED_DN_INDICES)
                or request["chunk_ms"] != _CACHED_BODY.DT_SEC * 1000):
            raise ValueError("persistent Pinocchio worker cannot change motor population or integration interval")
        body = _CACHED_BODY
    body_model_sha = str(_CACHED_BODY_MODEL_SHA256)
    initial_body_state = request.get("initial_body_state")
    restore_ms = 0.0
    restore_started = time.perf_counter()
    if initial_body_state is not None:
        if request.get("initial_body_model_sha256") != body_model_sha:
            raise ValueError("body checkpoint belongs to another Pinocchio model")
        body.restore_snapshot(initial_body_state)
    else:
        if _CACHED_INITIAL_STATE is None:
            raise RuntimeError("persistent Pinocchio initial state cache is missing")
        body.restore_snapshot(_CACHED_INITIAL_STATE)
    restore_ms = (time.perf_counter() - restore_started) * 1000.0
    model_init_ms = (time.perf_counter() - model_started) * 1000.0 - restore_ms
    before = body.state_snapshot()
    before_exact = {
        "q": [float(value) for value in body.q],
        "qdot": [float(value) for value in body.qdot],
        "requested_actuation": [float(value) for value in body.requested_actuation],
        "executed_actuation": [float(value) for value in body.executed_actuation],
        "motor_vector": [float(value) for value in body.motor_vector],
        "torque": [float(value) for value in body.torque],
        "body_capacity": float(body.body_capacity),
        "state_seq": int(body.state_seq),
        "dn_spike_sum": int(body.last_dn_spike_sum),
        "dn_active_neurons": int(body.last_dn_active),
    }
    dense = np.zeros(int(manifest["canonical_neuron_count"]), dtype=np.int64)
    dense[indices] = counts
    dynamics_started = time.perf_counter()
    body.step(
        dense,
        neural_time_ms=request["neural_time_ms"],
        actuation_scale=float(request.get("actuation_scale", 1.0)),
    )
    dynamics_ms = (time.perf_counter() - dynamics_started) * 1000.0
    after = body.state_snapshot()
    timestamp = request["occurred_at_utc"]
    readout_started = time.perf_counter()
    proprioception = SyntheticProprioceptiveReadout(body).sample(
        sequence=int(request["sequence"]), time_ms=float(request["neural_time_ms"]),
        timestamp_utc=timestamp,
    )
    readout_ms = (time.perf_counter() - readout_started) * 1000.0
    q_before = np.asarray(before["q"], dtype=float)
    q_after = np.asarray(after["q"], dtype=float)
    q_delta = q_after - q_before
    torque = np.asarray(after["torque"], dtype=float)
    qdot = np.asarray(after["qdot"], dtype=float)
    qlim = np.asarray(body.model.upperPositionLimit, dtype=float)
    lowlim = np.asarray(body.model.lowerPositionLimit, dtype=float)
    if not (np.isfinite(q_after).all() and np.isfinite(torque).all() and np.isfinite(qdot).all()):
        raise RuntimeError("Pinocchio returned a non-finite physical state")
    if np.any(q_after < lowlim - 1e-9) or np.any(q_after > qlim + 1e-9):
        raise RuntimeError("Pinocchio state exceeded mechanical position limits")
    if np.max(np.abs(torque)) > PinocchioSigilBody.MAX_TORQUE + 1e-12:
        raise RuntimeError("Pinocchio torque exceeded mechanical cap")
    base_state = after.get("base_state")
    if not isinstance(base_state, dict) or not all(
        np.isfinite(float(base_state[key])) for key in ("x", "y", "yaw_rad", "vx", "vy", "yaw_rate_rad_per_second")
    ):
        raise RuntimeError("Pinocchio planar base state is missing or non-finite")
    return {
        "status": "PINOCCHIO_STEP_APPLIED",
        "mode": request["mode"],
        "origin": "ARTIFICIAL_CALIBRATION_ONLY_NOT_FLYNN_ACTIVITY"
        if request["mode"] == "ARTIFICIAL_CALIBRATION_ONLY" else
        "REAL_LIF_ZERO_DN_READOUT" if request["mode"] == "NEURAL_ZERO_CONTROL" else "REAL_LIF_DN_READOUT",
        "sequence": request["sequence"],
        "neural_time_ms": request["neural_time_ms"],
        "occurred_at_utc": request["occurred_at_utc"],
        "manifest_sha256": manifest_sha,
        "mapping_sha256": request["mapping_sha256"],
        "connectome_sha256": request["connectome_sha256"],
        "dn_root_count": 1303,
        "dn_spike_sum": int(counts.sum()),
        "dn_active_neurons": int(np.count_nonzero(counts)),
        "torque_max_abs": float(np.max(np.abs(torque))),
        "body_capacity": float(after["body_capacity"]),
        "actuation_scale_origin": "HOMEOSTASIS_V2_ENERGY_RESERVE"
        if request.get("mode") != "ARTIFICIAL_CALIBRATION_ONLY" else "INSTRUMENTAL_CALIBRATION_DEFAULT",
        "torque": after["torque"],
        "q_before": before["q"],
        "checkpoint_state_before": before_exact,
        "q_after": after["q"],
        "q_delta_max_abs": float(np.max(np.abs(q_delta))),
        "qdot_after": after["qdot"],
        "fixed_root": {"q": after["q"][0], "qdot": after["qdot"][0]},
        "within_mechanical_limits": True,
        "base_translation_observed": any(abs(float(base_state[key])) > 1e-12 for key in ("x", "y")),
        "base_state": base_state,
        "body_state": after,
        "body_model_sha256": body_model_sha,
        "checkpoint_state_exact": {
            "q": [float(value) for value in body.q],
            "qdot": [float(value) for value in body.qdot],
            "base_state": after["base_state"],
            "physical_centroid": after["physical_centroid"],
            "requested_actuation": [float(value) for value in body.requested_actuation],
            "executed_actuation": [float(value) for value in body.executed_actuation],
            "motor_vector": [float(value) for value in body.motor_vector],
            "torque": [float(value) for value in body.torque],
            "body_capacity": float(body.body_capacity),
            "state_seq": int(body.state_seq),
            "dn_spike_sum": int(body.last_dn_spike_sum),
            "dn_active_neurons": int(body.last_dn_active),
        },
        "proprioceptive_readout": proprioception,
        "worker_elapsed_ms": (time.perf_counter() - started) * 1000.0,
        "worker_cpu_ms": (time.process_time() - cpu_started) * 1000.0,
        "worker_peak_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0,
        "worker_phase_ms": {
            "validation": validation_ms,
            "model_construction_and_identity": model_init_ms,
            "checkpoint_restore": restore_ms,
            "physical_dynamics": dynamics_ms,
            "proprioceptive_readout": readout_ms,
        },
    }


def main() -> None:
    for line in sys.stdin:
        try:
            request = json.loads(line)
            response = {"request_id": request["request_id"], "result": run(request)}
        except Exception as exc:  # return the concrete failure to the caller
            response = {"request_id": locals().get("request", {}).get("request_id"), "error": str(exc)}
        print(json.dumps(response, separators=(",", ":"), allow_nan=False), flush=True)


if __name__ == "__main__":
    main()
