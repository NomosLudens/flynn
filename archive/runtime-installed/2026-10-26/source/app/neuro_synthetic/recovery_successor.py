"""Create a new resident episode anchored to one verified paired checkpoint.

This is an operational recovery tool, not a replay mechanism. It opens the
interrupted episode read-only, copies its exact checkpoint sidecar and the
state rows required to restore that boundary, and writes a distinct successor
root. Uncheckpointed tail records remain solely in the source episode.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from .neural_core import (
    LEGACY_NEURAL_BUNDLE_SHA256,
    LEGACY_PERSISTENCE_MODEL_SHA256,
    _legacy_neural_bundle_sha256,
    _model_sha256,
)
from .sqlite_store import FlynnStore


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _state_row(connection: sqlite3.Connection, component: str, *, state_id: str | None = None,
               predicate: str = "") -> tuple[str, str, float | None, str] | None:
    query = "SELECT state_id,event_id,neural_time_ms,state_json FROM component_states WHERE component=?"
    args: list[Any] = [component]
    if state_id is not None:
        query += " AND state_id=?"
        args.append(state_id)
    if predicate:
        query += f" AND {predicate}"
    query += " ORDER BY rowid DESC LIMIT 1"
    return connection.execute(query, args).fetchone()


def prepare_successor(source_root: str | Path, target_root: str | Path, *,
                      checkpoint_dir: str | Path | None = None,
                      source_original_database_sha256: str) -> dict[str, Any]:
    """Prepare a successor database without modifying any source artifact."""
    source = Path(source_root).resolve()
    target = Path(target_root).resolve()
    source_db = source / "episode-v2.sqlite3"
    if not source_db.is_file() or not (source / "episode.json").is_file():
        raise FileNotFoundError("source resident root lacks its database or episode identity")
    if target.exists():
        raise FileExistsError("successor root already exists; refusing to overwrite it")

    source_identity = json.loads((source / "episode.json").read_text(encoding="utf-8"))
    if source_identity.get("execution_kind") != "RESIDENT":
        raise ValueError("source episode is not explicitly RESIDENT")
    source_db_sha256 = _sha256_file(source_db)
    if (not isinstance(source_original_database_sha256, str)
            or len(source_original_database_sha256) != 64
            or any(character not in "0123456789abcdef" for character in source_original_database_sha256)):
        raise ValueError("the verified original production database SHA-256 is required")
    connection = sqlite3.connect(source_db.as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("source SQLite integrity check failed")
        checkpoint_row = _state_row(connection, "integrated_world_neural_checkpoint")
        if checkpoint_row is None:
            raise ValueError("source episode has no integrated checkpoint")
        checkpoint = json.loads(checkpoint_row[3])
        if (checkpoint.get("model_sha256") != LEGACY_PERSISTENCE_MODEL_SHA256
                or _legacy_neural_bundle_sha256() != LEGACY_NEURAL_BUNDLE_SHA256):
            raise ValueError("source checkpoint model identity is not the specifically verified legacy bundle")
        source_episode_id = checkpoint.get("episode_id")
        if source_episode_id != source_identity.get("episode_id"):
            raise ValueError("source checkpoint and episode marker identities differ")
        source_checkpoint = (
            Path(checkpoint_dir).resolve() / Path(checkpoint["checkpoint_file"]).name
            if checkpoint_dir is not None else Path(checkpoint["checkpoint_file"]).resolve()
        )
        if not source_checkpoint.is_file() or _sha256_file(source_checkpoint) != checkpoint.get("checkpoint_sha256"):
            raise ValueError("source paired checkpoint sidecar is missing or has a mismatched hash")
        # Query the exact durable frame cursor paired with the checkpoint.
        frame_row = connection.execute(
            "SELECT state_id,event_id,neural_time_ms,state_json FROM component_states "
            "WHERE component='neural_activity_aggregator' "
            "AND json_extract(state_json,'$.episode_id')=? "
            "AND CAST(json_extract(state_json,'$.sequence') AS INTEGER)=? "
            "ORDER BY rowid DESC LIMIT 1",
            (source_episode_id, int(checkpoint["next_sequence"]) - 1),
        ).fetchone()
        if frame_row is None:
            raise ValueError("source has no durable LIF frame matching the checkpoint cursor")
        source_frame = json.loads(frame_row[3])
        if (int(source_frame["end_tick"]) != int(checkpoint["neural_tick"])
                or abs(float(source_frame["neural_time_ms"]) - float(checkpoint["neural_time_ms"])) > 1e-9):
            raise ValueError("durable frame cursor does not align exactly with the checkpoint")

        body_ref = checkpoint.get("body_checkpoint")
        if not isinstance(body_ref, dict):
            raise ValueError("source checkpoint is not paired with a body state")
        body_row = _state_row(connection, "pinocchio_body_checkpoint", state_id=body_ref["component_state_id"])
        if body_row is None:
            raise ValueError("source paired Pinocchio state is missing")
        body = json.loads(body_row[3])
        body_json = json.dumps(body["body_state"], sort_keys=True, separators=(",", ":"), allow_nan=False)
        body_hash = hashlib.sha256(body_json.encode("utf-8")).hexdigest()
        if (body.get("episode_id") != source_episode_id
                or float(body.get("physical_time_ms", -1)) != float(checkpoint["world_time_ms"])
                or body_hash != body_ref.get("body_state_sha256")):
            raise ValueError("source body state does not match the verified paired checkpoint")
        readout_row = connection.execute(
            "SELECT state_id,event_id,neural_time_ms,state_json FROM component_states "
            "WHERE component='synthetic_proprioceptive_readout' "
            "AND json_extract(state_json,'$.body_checkpoint_id')=? ORDER BY rowid DESC LIMIT 1",
            (body_row[0],),
        ).fetchone()
        if readout_row is None:
            raise ValueError("source checkpoint has no matching persisted proprioceptive readout")
        readout = json.loads(readout_row[3])

        latest_frame = connection.execute(
            "SELECT state_json FROM component_states WHERE component='neural_activity_aggregator' "
            "AND json_extract(state_json,'$.episode_id')=? ORDER BY rowid DESC LIMIT 1",
            (source_episode_id,),
        ).fetchone()
        latest_frame_state = json.loads(latest_frame[0]) if latest_frame else {}
        if int(latest_frame_state.get("end_tick", -1)) > int(checkpoint["neural_tick"]):
            ambiguous_tail = {
                "latest_durable_frame_sequence": latest_frame_state.get("sequence"),
                "latest_durable_frame_tick": latest_frame_state.get("end_tick"),
                "latest_durable_frame_time_ms": latest_frame_state.get("neural_time_ms"),
            }
        else:
            ambiguous_tail = None
    finally:
        connection.close()

    if not ambiguous_tail:
        raise ValueError("source has no uncheckpointed tail; use ordinary paired-checkpoint recovery")

    successor_id = f"resident-v2:{source_identity['instance_id']}:successor-{uuid.uuid4().hex}"
    checkpoint_dir = target / "checkpoints"
    target.mkdir(mode=0o700, parents=True)
    checkpoint_dir.mkdir(mode=0o700)
    checkpoint_copy = checkpoint_dir / source_checkpoint.name
    shutil.copy2(source_checkpoint, checkpoint_copy)
    source_checkpoint_sha256 = checkpoint["checkpoint_sha256"]
    if _sha256_file(checkpoint_copy) != source_checkpoint_sha256:
        raise IOError("checkpoint copy hash differs from verified source")
    # A new episode starts its PicoClaw and frame cursors at zero. Preserve all
    # neural arrays, tick, world snapshot and body state from the parent.
    temporary_checkpoint = checkpoint_copy.with_suffix(".npz.tmp")
    with np.load(checkpoint_copy, allow_pickle=False) as source_archive:
        arrays = {key: source_archive[key] for key in source_archive.files}
    arrays["next_sequence"] = np.asarray([0], dtype=np.uint64)
    with temporary_checkpoint.open("wb") as output:
        np.savez_compressed(output, **arrays)
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary_checkpoint, checkpoint_copy)
    successor_checkpoint_sha256 = _sha256_file(checkpoint_copy)

    now = datetime.now(timezone.utc).isoformat()
    lineage = {
        "schema": "flynn.resident_recovery_lineage.v1",
        "source_episode_id": source_episode_id,
        "source_database_sha256": source_db_sha256,
        "source_original_database_sha256": source_original_database_sha256,
        "source_checkpoint_sha256": source_checkpoint_sha256,
        "successor_checkpoint_sha256": successor_checkpoint_sha256,
        "source_checkpoint_tick": int(checkpoint["neural_tick"]),
        "source_checkpoint_time_ms": float(checkpoint["neural_time_ms"]),
        "source_model_sha256": checkpoint["model_sha256"],
        "successor_model_sha256": _model_sha256(),
        "model_identity_reconciliation": "PERSISTENCE_STORE_HASH_REMOVED_FROM_MODEL_ID; MODEL_BUNDLE_IDENTICAL",
        "ambiguous_uncheckpointed_tail": ambiguous_tail,
        "historical_gap": {
            "last_recoverable_tick": int(checkpoint["neural_tick"]),
            "last_recoverable_time_ms": float(checkpoint["neural_time_ms"]),
            "latest_uncheckpointed_frame_sequence": ambiguous_tail["latest_durable_frame_sequence"],
            "latest_uncheckpointed_tick": ambiguous_tail["latest_durable_frame_tick"],
            "latest_uncheckpointed_time_ms": ambiguous_tail["latest_durable_frame_time_ms"],
            "classification": "UNRECONCILED_TAIL_PRESERVED_IN_SOURCE_EPISODE",
        },
        "prepared_at_utc": now,
        "policy": "PRESERVE_PARENT_AND_RESUME_ONLY_FROM_VERIFIED_CHECKPOINT",
    }
    marker = {
        **source_identity,
        "episode_id": successor_id,
        "created_at_utc": now,
        "recovery_lineage": lineage,
        "last_start_at_utc": None,
        "last_stop_at_utc": None,
    }
    temp_marker = target / ".episode.json.tmp"
    with temp_marker.open("x", encoding="utf-8") as stream:
        json.dump(marker, stream, sort_keys=True, separators=(",", ":"))
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp_marker, target / "episode.json")

    store = FlynnStore(target / "episode-v2.sqlite3")
    try:
        with store.connection:
            store.connection.execute(
                "INSERT OR REPLACE INTO metadata(key, value) VALUES('execution_kind', 'RESIDENT')"
            )
        new_stream_id = f"neural:{successor_id}"
        body_tag = hashlib.sha256(new_stream_id.encode("utf-8")).hexdigest()[:20]
        new_body_id = f"pinocchio-body:{body_tag}:{body['stream_sequence']}"
        body.update({"episode_id": successor_id, "stream_id": new_stream_id,
                     "body_checkpoint_id": new_body_id})
        readout.update({"episode_id": successor_id, "stream_id": new_stream_id,
                        "body_checkpoint_id": new_body_id})
        checkpoint.update({
            "episode_id": successor_id,
            "checkpoint_file": str(checkpoint_copy),
            "checkpoint_sha256": successor_checkpoint_sha256,
            "checkpoint_bytes": checkpoint_copy.stat().st_size,
            "next_sequence": 0,
            "recovery_lineage": lineage,
        })
        new_body_ref = dict(body_ref)
        new_body_ref.update({"component_state_id": new_body_id, "stream_id": new_stream_id})
        checkpoint["body_checkpoint"] = new_body_ref

        def add(state_id: str, component: str, state: dict[str, Any], neural_time: float,
                event_type: str = "RECOVERY_STATE_IMPORTED") -> None:
            store.record_state(
                state_id=state_id, event_id=f"{state_id}:event", component=component,
                occurred_at_utc=now, neural_time_ms=neural_time, state=state,
            )

        add(new_body_id, "pinocchio_body_checkpoint", body, float(checkpoint["world_time_ms"]))
        readout_id = f"pinocchio-proprio:{body_tag}:{body['stream_sequence']}"
        add(readout_id, "synthetic_proprioceptive_readout", readout, float(checkpoint["world_time_ms"]))
        checkpoint_id = (
            f"integrated-checkpoint:{successor_id}:{checkpoint['neural_tick']}:"
            f"{checkpoint['checkpoint_sha256'][:16]}"
        )
        checkpoint["recovery_anchor_state_id"] = checkpoint_id
        add(checkpoint_id, "integrated_world_neural_checkpoint", checkpoint,
            float(checkpoint["neural_time_ms"]))
        cycle = {
            "episode_id": successor_id,
            "execution_kind": "RESIDENT",
            "cycle_sequence": max(0, int(checkpoint.get("next_sequence", 1)) // 2 - 1),
            "cycle_status": "RECOVERY_ANCHOR",
            "start_world_time_ms": float(checkpoint["world_time_ms"]),
            "end_world_time_ms": float(checkpoint["world_time_ms"]),
            "start_neural_time_ms": float(checkpoint["neural_time_ms"]),
            "end_neural_time_ms": float(checkpoint["neural_time_ms"]),
            "start_tick": int(checkpoint["neural_tick"]),
            "end_tick": int(checkpoint["neural_tick"]),
            "checkpoint_tick": int(checkpoint["neural_tick"]),
            "checkpoint_sha256": successor_checkpoint_sha256,
            "recovery_source_episode_id": source_episode_id,
            "recovery_lineage": lineage,
            "timestamp_utc": now,
            "effect": "VERIFIED_CHECKPOINT_RECOVERY_ANCHOR_NO_REPLAY",
        }
        add(f"neuro-world:{successor_id}:recovery-anchor", "neuro_world_coordinator",
            cycle, float(checkpoint["neural_time_ms"]))
        store.connection.commit()
        if store.connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise IOError("successor SQLite integrity check failed")
    finally:
        store.close()

    directory_fd = os.open(target, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    return {
        "source_episode_id": source_episode_id,
        "successor_episode_id": successor_id,
        "source_database_sha256": source_db_sha256,
        "source_checkpoint_sha256": source_checkpoint_sha256,
        "successor_checkpoint_sha256": successor_checkpoint_sha256,
        "source_checkpoint_tick": int(checkpoint["neural_tick"]),
        "source_checkpoint_time_ms": float(checkpoint["neural_time_ms"]),
        "ambiguous_uncheckpointed_tail": ambiguous_tail,
        "successor_root": str(target),
    }
