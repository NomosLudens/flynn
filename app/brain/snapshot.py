"""
LIF Engine State Snapshot & Restoration Engine (Gate 013).
Serializes mutable neural simulation state to disk with versioned checkpoints,
SHA256 integrity verification, and software provenance manifests.

Gate 013 Extends checkpointing to include:
- Body state (position, orientation, current_action, body_status)
- World synchronization state (entities, conditions, event timers, world_time_ms)
- Plasticity state (epoch, active status, learned deltas, bounds, config_hash)
- Homeostasis v2 state
- Neural state and RNG state
"""
import os
import sys
import json
import hashlib
import pickle
import numpy as np
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any

os.environ.setdefault("FLYWIRE_V783_DIR", "/home/ubuntu/Portifolio/flynn-max/data/flywire-v783")
sys.path.insert(0, "/home/ubuntu/Portifolio/flynn-max/fruit-fly-lab")
from brain.neurons.registry import load_connectome
from simulation.engine.session import Session

SNAPSHOT_DIR = Path("/home/ubuntu/Portifolio/flynn-max/runtime/data/snapshots")
RUNTIME_ROOT = Path("/home/ubuntu/Portifolio/flynn-max/runtime")


def _compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def _get_software_hashes() -> Dict[str, str]:
    files = [
        RUNTIME_ROOT / "app/daemon.py",
        RUNTIME_ROOT / "app/brain/clock.py",
        RUNTIME_ROOT / "app/brain/snapshot.py",
        RUNTIME_ROOT / "app/brain/plasticity.py",
        RUNTIME_ROOT / "app/body/adapter.py",
        RUNTIME_ROOT / "app/body/contract.py",
        RUNTIME_ROOT / "app/world/continuous_world.py"
    ]
    hashes = {}
    for f in files:
        if f.exists():
            hashes[f.name] = _compute_sha256(f)
    return hashes


def save_versioned_checkpoint(session: Session, organism_id: str, snapshot_dir: Path = SNAPSHOT_DIR) -> Dict[str, Any]:
    """
    Serializes mutable LIFEngine, Session, Body, World, and Plasticity state to disk into a versioned checkpoint.
    Creates .pkl file, computes SHA256, generates companion .manifest.json,
    and atomically updates latest.json pointer.
    """
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    engine = session.engine

    now_utc = datetime.now(timezone.utc)
    ts_str = now_utc.strftime("%Y%m%d_%H%M%S")
    checkpoint_id = f"snapshot_{organism_id}_{ts_str}"
    pkl_filename = f"{checkpoint_id}.pkl"
    pkl_path = snapshot_dir / pkl_filename
    manifest_path = snapshot_dir / f"{checkpoint_id}.manifest.json"

    state = {
        "v": engine.v.copy(),
        "g": engine.g.copy(),
        "rfc_left": engine.rfc_left.copy(),
        "rfc_len": engine.rfc_len.copy(),
        "_ring": engine._ring.copy(),
        "_slot": engine._slot,
        "_n_refractory": engine._n_refractory,
        "step_count": engine.step_count,
        "t_ms": engine.t_ms,
        "spike_counts": engine.spike_counts.copy(),
        "_poi_idx": engine._poi_idx.copy(),
        "_poi_p": engine._poi_p.copy(),
        "_silenced": engine._silenced.copy(),
        "rng_state": engine.rng.bit_generator.state,
        "window_sum": session.recorder.window_sum.copy() if hasattr(session.recorder, 'window_sum') else None,
    }

    # Homeostasis v2
    homeo_engine = None
    if hasattr(session, "clock") and hasattr(session.clock, "homeostasis"):
        homeo_engine = session.clock.homeostasis
    elif hasattr(session, "homeostasis"):
        homeo_engine = session.homeostasis
    if homeo_engine is not None:
        state["homeostasis_v2"] = homeo_engine.serialize_checkpoint()

    # Body State (Gate 013)
    body_adapter = None
    if hasattr(session, "clock") and hasattr(session.clock, "body"):
        body_adapter = session.clock.body
    elif hasattr(session, "body"):
        body_adapter = session.body
    if body_adapter is not None and hasattr(body_adapter, "snapshot"):
        state["body_state"] = body_adapter.snapshot().to_dict()

    # Live Pinocchio embodiment state. The clock is recreated after this
    # loader during daemon startup, so retain it as a pending session state.
    sigil_body = getattr(getattr(session, "clock", None), "sigil_body", None)
    if sigil_body is not None and hasattr(sigil_body, "state_snapshot"):
        state["sigil_body_state"] = sigil_body.state_snapshot()

    # World State (Gate 013)
    world_engine = None
    if hasattr(session, "clock") and hasattr(session.clock, "world"):
        world_engine = session.clock.world
    elif hasattr(session, "world"):
        world_engine = session.world
    if world_engine is not None:
        state["world_state"] = world_engine.snapshot()

    # Plasticity State (Gate 013)
    plasticity_engine = None
    if hasattr(session, "clock") and hasattr(session.clock, "plasticity"):
        plasticity_engine = session.clock.plasticity
    elif hasattr(session, "plasticity"):
        plasticity_engine = session.plasticity
    if plasticity_engine is not None:
        state["plasticity_state"] = plasticity_engine.snapshot()

    # Atomic write of .pkl
    tmp_pkl = pkl_path.with_suffix(".tmp")
    with open(tmp_pkl, "wb") as f:
        pickle.dump(state, f, protocol=pickle.HIGHEST_PROTOCOL)
    tmp_pkl.replace(pkl_path)

    sha256_hash = _compute_sha256(pkl_path)

    manifest = {
        "checkpoint_id": checkpoint_id,
        "organism_id": organism_id,
        "filename": pkl_filename,
        "filepath": str(pkl_path),
        "sha256": sha256_hash,
        "neural_time_ms": float(engine.t_ms),
        "step_count": int(engine.step_count),
        "created_at_utc": now_utc.isoformat(),
        "engine_version": "fruit-fly-lab-v1.0",
        "connectome_version": "FlyWire-v783",
        "homeostasis_epoch": homeo_engine.epoch if homeo_engine else None,
        "homeostasis_config_hash": homeo_engine.config_hash if homeo_engine else None,
        "body_status": body_adapter.status() if hasattr(body_adapter, "status") else None,
        "world_time_ms": world_engine.world_time_ms if world_engine else None,
        "plasticity_config_hash": plasticity_engine.config_hash if plasticity_engine else None,
        "plasticity_active": plasticity_engine.active if plasticity_engine else False,
        "plasticity_deltas_count": len(plasticity_engine.learned_deltas) if plasticity_engine else 0,
        "software_hashes": _get_software_hashes()
    }

    tmp_manifest = manifest_path.with_suffix(".tmp")
    with open(tmp_manifest, "w") as f:
        json.dump(manifest, f, indent=2)
    tmp_manifest.replace(manifest_path)

    # Atomically update latest.json
    latest_path = snapshot_dir / f"latest_{organism_id}.json"
    tmp_latest = latest_path.with_suffix(".tmp")
    with open(tmp_latest, "w") as f:
        json.dump({
            "latest_checkpoint_id": checkpoint_id,
            "filepath": str(pkl_path),
            "manifest_filepath": str(manifest_path),
            "sha256": sha256_hash,
            "neural_time_ms": float(engine.t_ms),
            "updated_at_utc": now_utc.isoformat()
        }, f, indent=2)
    tmp_latest.replace(latest_path)

    # Maintain backward compatibility link
    compat_path = snapshot_dir / f"snapshot_{organism_id}.pkl"
    try:
        if compat_path.exists() or compat_path.is_symlink():
            compat_path.unlink()
        compat_path.symlink_to(pkl_path.name)
    except Exception:
        pass

    return manifest


def load_versioned_checkpoint(session: Session, checkpoint_path: Optional[Path] = None, organism_id: Optional[str] = None, snapshot_dir: Path = SNAPSHOT_DIR) -> Dict[str, Any]:
    """
    Loads engine state from versioned checkpoint with SHA256 integrity verification.
    """
    if checkpoint_path is None:
        if organism_id is None:
            raise ValueError("Must specify either checkpoint_path or organism_id")
        latest_path = snapshot_dir / f"latest_{organism_id}.json"
        if not latest_path.exists():
            legacy_path = snapshot_dir / f"snapshot_{organism_id}.pkl"
            if legacy_path.exists():
                load_engine_snapshot(session, legacy_path)
                return {"status": "restored_legacy", "filepath": str(legacy_path)}
            raise FileNotFoundError(f"No checkpoint found for organism {organism_id}")

        with open(latest_path, "r") as f:
            latest_info = json.load(f)
        checkpoint_path = Path(latest_info["filepath"])

    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Checkpoint file does not exist: {checkpoint_path}")

    # Check manifest if present
    manifest_path = checkpoint_path.with_suffix(".manifest.json")
    if manifest_path.exists():
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
        expected_sha = manifest.get("sha256")
        actual_sha = _compute_sha256(checkpoint_path)
        if expected_sha and expected_sha != actual_sha:
            raise ValueError(f"Checkpoint SHA256 mismatch! Expected {expected_sha}, got {actual_sha}")

    load_engine_snapshot(session, checkpoint_path)
    return {
        "status": "restored",
        "filepath": str(checkpoint_path),
        "neural_time_ms": float(session.engine.t_ms),
        "step_count": int(session.engine.step_count)
    }


def save_engine_snapshot(session: Session, snapshot_path: Path) -> Path:
    """
    Backward-compatible atomic snapshot serialization.
    """
    engine = session.engine
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)

    state = {
        "v": engine.v.copy(),
        "g": engine.g.copy(),
        "rfc_left": engine.rfc_left.copy(),
        "rfc_len": engine.rfc_len.copy(),
        "_ring": engine._ring.copy(),
        "_slot": engine._slot,
        "_n_refractory": engine._n_refractory,
        "step_count": engine.step_count,
        "t_ms": engine.t_ms,
        "spike_counts": engine.spike_counts.copy(),
        "_poi_idx": engine._poi_idx.copy(),
        "_poi_p": engine._poi_p.copy(),
        "_silenced": engine._silenced.copy(),
        "rng_state": engine.rng.bit_generator.state,
        "window_sum": session.recorder.window_sum.copy() if hasattr(session.recorder, 'window_sum') else None,
    }

    homeo_engine = None
    if hasattr(session, "clock") and hasattr(session.clock, "homeostasis"):
        homeo_engine = session.clock.homeostasis
    elif hasattr(session, "homeostasis"):
        homeo_engine = session.homeostasis
    if homeo_engine is not None:
        state["homeostasis_v2"] = homeo_engine.serialize_checkpoint()

    # Body State
    body_adapter = None
    if hasattr(session, "clock") and hasattr(session.clock, "body"):
        body_adapter = session.clock.body
    elif hasattr(session, "body"):
        body_adapter = session.body
    if body_adapter is not None and hasattr(body_adapter, "snapshot"):
        state["body_state"] = body_adapter.snapshot().to_dict()

    # World State
    world_engine = None
    if hasattr(session, "clock") and hasattr(session.clock, "world"):
        world_engine = session.clock.world
    elif hasattr(session, "world"):
        world_engine = session.world
    if world_engine is not None:
        state["world_state"] = world_engine.snapshot()

    # Plasticity State
    plasticity_engine = None
    if hasattr(session, "clock") and hasattr(session.clock, "plasticity"):
        plasticity_engine = session.clock.plasticity
    elif hasattr(session, "plasticity"):
        plasticity_engine = session.plasticity
    if plasticity_engine is not None:
        state["plasticity_state"] = plasticity_engine.snapshot()

    tmp_path = snapshot_path.with_suffix(".tmp")
    with open(tmp_path, "wb") as f:
        pickle.dump(state, f, protocol=pickle.HIGHEST_PROTOCOL)
    tmp_path.replace(snapshot_path)

    return snapshot_path


def load_engine_snapshot(session: Session, snapshot_path: Path) -> None:
    """
    Restores mutable LIFEngine and Session state from disk into an existing Session.
    """
    if not snapshot_path.exists():
        raise FileNotFoundError(f"Snapshot file not found: {snapshot_path}")

    with open(snapshot_path, "rb") as f:
        state = pickle.load(f)

    engine = session.engine
    engine.v = state["v"].copy()
    engine.g = state["g"].copy()
    engine.rfc_left = state["rfc_left"].copy()
    engine.rfc_len = state["rfc_len"].copy()
    engine._ring = state["_ring"].copy()
    engine._slot = state["_slot"]
    engine._n_refractory = state["_n_refractory"]
    engine.step_count = state["step_count"]
    engine.t_ms = state["t_ms"]
    engine.spike_counts = state["spike_counts"].copy()
    engine._poi_idx = state["_poi_idx"].copy()
    engine._poi_p = state["_poi_p"].copy()
    engine._silenced = state["_silenced"].copy()
    engine.rng.bit_generator.state = state["rng_state"]

    if state.get("window_sum") is not None and hasattr(session.recorder, 'window_sum'):
        session.recorder.window_sum = state["window_sum"].copy()

    if "homeostasis_v2" in state:
        homeo_engine = None
        if hasattr(session, "clock") and hasattr(session.clock, "homeostasis"):
            homeo_engine = session.clock.homeostasis
        elif hasattr(session, "homeostasis"):
            homeo_engine = session.homeostasis
        if homeo_engine is not None:
            homeo_engine.restore_checkpoint(state["homeostasis_v2"])
        else:
            session._pending_homeostasis_v2 = state["homeostasis_v2"]

    if "sigil_body_state" in state:
        sigil_body = getattr(getattr(session, "clock", None), "sigil_body", None)
        if sigil_body is not None and hasattr(sigil_body, "restore_snapshot"):
            sigil_body.restore_snapshot(state["sigil_body_state"])
        else:
            session._pending_sigil_body_state = state["sigil_body_state"]

    if "body_state" in state:
        from app.body.contract import BodyState
        body_adapter = None
        if hasattr(session, "clock") and hasattr(session.clock, "body"):
            body_adapter = session.clock.body
        elif hasattr(session, "body"):
            body_adapter = session.body
        if body_adapter is not None and hasattr(body_adapter, "snapshot"):
            body_adapter.restore(BodyState.from_dict(state["body_state"]))
        else:
            session._pending_body_state = state["body_state"]

    if "world_state" in state:
        world_engine = None
        if hasattr(session, "clock") and hasattr(session.clock, "world"):
            world_engine = session.clock.world
        elif hasattr(session, "world"):
            world_engine = session.world
        if world_engine is not None:
            world_engine.restore(state["world_state"])
        else:
            session._pending_world_state = state["world_state"]

    if "plasticity_state" in state:
        plasticity_engine = None
        if hasattr(session, "clock") and hasattr(session.clock, "plasticity"):
            plasticity_engine = session.clock.plasticity
        elif hasattr(session, "plasticity"):
            plasticity_engine = session.plasticity
        if plasticity_engine is not None:
            plasticity_engine.restore(state["plasticity_state"])
        else:
            session._pending_plasticity_state = state["plasticity_state"]
