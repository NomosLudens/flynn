"""Minimal append-only SQLite records for a new Flynn runtime episode.

This module stores provenance, mappings, stimuli, component states, and events.
It does not simulate neurons, interpret stimuli, or choose body actions.
"""

from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS neuron_mapping (
    dataset_version TEXT NOT NULL,
    compact_index INTEGER NOT NULL CHECK (compact_index >= 0),
    root_id INTEGER NOT NULL CHECK (root_id > 0),
    source_sha256 TEXT NOT NULL,
    mapping_sha256 TEXT NOT NULL,
    PRIMARY KEY (dataset_version, compact_index),
    UNIQUE (dataset_version, root_id)
);
CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    source TEXT NOT NULL,
    neural_time_ms REAL,
    occurred_at_utc TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    provenance_sha256 TEXT
);
CREATE TABLE IF NOT EXISTS stimuli (
    event_id TEXT PRIMARY KEY REFERENCES events(event_id),
    modality TEXT NOT NULL,
    origin TEXT NOT NULL,
    parameters_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS component_states (
    state_id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL REFERENCES events(event_id),
    component TEXT NOT NULL,
    neural_time_ms REAL,
    schema_version INTEGER NOT NULL,
    state_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS coordinator_control (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    ingestion_paused INTEGER NOT NULL CHECK (ingestion_paused IN (0, 1)),
    revision INTEGER NOT NULL CHECK (revision >= 0),
    updated_at_utc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS causal_generations (
    generation_id TEXT PRIMARY KEY,
    episode_id TEXT NOT NULL,
    parent_generation_id TEXT,
    origin_checkpoint_state_id TEXT,
    origin_checkpoint_sha256 TEXT,
    origin_tick INTEGER NOT NULL CHECK (origin_tick >= 0),
    created_at_utc TEXT NOT NULL,
    recovery_event_id TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS causal_generation_control (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    episode_id TEXT NOT NULL,
    active_generation_id TEXT NOT NULL REFERENCES causal_generations(generation_id),
    checkpoint_state_id TEXT,
    checkpoint_sha256 TEXT,
    checkpoint_tick INTEGER NOT NULL CHECK (checkpoint_tick >= 0),
    revision INTEGER NOT NULL CHECK (revision >= 0),
    updated_at_utc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS events_time_idx ON events(neural_time_ms, occurred_at_utc);
CREATE INDEX IF NOT EXISTS states_component_time_idx
    ON component_states(component, neural_time_ms);
CREATE TRIGGER IF NOT EXISTS events_no_update
BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT, 'events are append-only'); END;
CREATE TRIGGER IF NOT EXISTS events_no_delete
BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT, 'events are append-only'); END;
CREATE TRIGGER IF NOT EXISTS mappings_no_update
BEFORE UPDATE ON neuron_mapping BEGIN SELECT RAISE(ABORT, 'mappings are immutable'); END;
CREATE TRIGGER IF NOT EXISTS mappings_no_delete
BEFORE DELETE ON neuron_mapping BEGIN SELECT RAISE(ABORT, 'mappings are immutable'); END;
CREATE TRIGGER IF NOT EXISTS states_no_update
BEFORE UPDATE ON component_states BEGIN SELECT RAISE(ABORT, 'states are append-only'); END;
CREATE TRIGGER IF NOT EXISTS states_no_delete
BEFORE DELETE ON component_states BEGIN SELECT RAISE(ABORT, 'states are append-only'); END;
CREATE TRIGGER IF NOT EXISTS causal_generations_no_update
BEFORE UPDATE ON causal_generations BEGIN SELECT RAISE(ABORT, 'causal generations are append-only'); END;
CREATE TRIGGER IF NOT EXISTS causal_generations_no_delete
BEFORE DELETE ON causal_generations BEGIN SELECT RAISE(ABORT, 'causal generations are append-only'); END;
"""


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def picoclaw_frame_digest(frame: Mapping[str, Any], dn_readout: Mapping[str, Any] | None) -> str:
    """Digest the identity, exact LIF frame and official DN readout sent to PicoClaw."""
    def canonical_number(value: Any) -> Any:
        # The deployed Go bridge decodes generic DN JSON numbers as float64.
        # Normalize integral values back to integers so the same readout has
        # one digest before and after the JSON-RPC hop.
        if isinstance(value, float) and math.isfinite(value) and value.is_integer():
            return int(value)
        if isinstance(value, dict):
            return {key: canonical_number(item) for key, item in value.items()}
        if isinstance(value, list):
            return [canonical_number(item) for item in value]
        return value

    fields = (
        "episode_id", "causal_generation_id", "sequence", "dataset_version",
        "manifest_sha256", "mapping_sha256", "core_id", "model_sha256",
        "config_sha256", "connectome_sha256", "start_tick", "end_tick", "dt_ms",
        "neural_time_ms", "active_neuron_count", "total_spikes", "input_sha256",
        "mapped_spikes", "homeostasis_state",
    )
    canonical = canonical_number({key: frame.get(key) for key in fields})
    canonical["dn_readout"] = canonical_number(dict(dn_readout)) if dn_readout is not None else None
    return hashlib.sha256(_json(canonical).encode("utf-8")).hexdigest()


def _compact_component_state(component: str, state: Mapping[str, Any]) -> dict[str, Any]:
    """Losslessly sparse-encode DN counts when that is smaller than the dense JSON."""
    value = dict(state)
    if component != "descending_motor_readout_v2":
        return value
    indices = value.get("compact_indices")
    counts = value.get("spike_counts")
    if not isinstance(indices, list) or not isinstance(counts, list) or len(indices) != len(counts):
        return value
    if any(isinstance(count, bool) or not isinstance(count, int) or count < 0 for count in counts):
        raise ValueError("DN spike counts must be non-negative integers")
    if (sum(counts) != state.get("total_spikes")
            or sum(count > 0 for count in counts) != state.get("active_neurons")):
        raise ValueError("DN spike count vector disagrees with the readout totals")
    sparse = [[index, count] for index, count in enumerate(counts) if count]
    if len(_json(sparse).encode("utf-8")) >= len(_json(counts).encode("utf-8")):
        return value
    value.pop("spike_counts")
    value["_flynn_observation_encoding"] = "dn_sparse_counts_v1"
    value["spike_counts_sparse"] = sparse
    return value


def _expand_component_state(component: str, state: Mapping[str, Any]) -> dict[str, Any]:
    """Read losslessly compacted states through the historical dense interface."""
    value = dict(state)
    encoding = value.pop("_flynn_observation_encoding", None)
    if encoding is None:
        return value
    if component != "descending_motor_readout_v2" or encoding != "dn_sparse_counts_v1":
        raise RuntimeError(f"unsupported persisted observation encoding: {encoding}")
    sparse = value.pop("spike_counts_sparse", None)
    indices = value.get("compact_indices")
    if not isinstance(indices, list) or not isinstance(sparse, list):
        raise RuntimeError("sparse DN observation is missing its canonical index map or counts")
    counts = [0] * len(indices)
    previous = -1
    for pair in sparse:
        if not isinstance(pair, list) or len(pair) != 2:
            raise RuntimeError("invalid sparse DN count entry")
        index, count = pair
        if (isinstance(index, bool) or not isinstance(index, int) or index <= previous
                or index < 0 or index >= len(counts) or isinstance(count, bool)
                or not isinstance(count, int) or count <= 0):
            raise RuntimeError("sparse DN counts violate ordered index or value constraints")
        counts[index] = count
        previous = index
    if sum(counts) != value.get("total_spikes") or sum(count > 0 for count in counts) != value.get("active_neurons"):
        raise RuntimeError("sparse DN counts disagree with their persisted totals")
    value["spike_counts"] = counts
    return value


def _validate_event_time(occurred_at_utc: str, neural_time_ms: float | None) -> None:
    try:
        parsed = datetime.fromisoformat(occurred_at_utc.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise ValueError("occurred_at_utc must be an ISO-8601 UTC timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError("occurred_at_utc must include the UTC timezone")
    if neural_time_ms is not None and (
        isinstance(neural_time_ms, bool)
        or not isinstance(neural_time_ms, (int, float))
        or not math.isfinite(neural_time_ms)
        or neural_time_ms < 0
    ):
        raise ValueError("neural_time_ms must be finite and non-negative")


def mapping_digest(dataset_version: str, root_ids: Iterable[int]) -> str:
    """Hash the exact ordered root-ID/index mapping, without inventing edges."""
    digest = hashlib.sha256()
    digest.update((dataset_version + "\n").encode("ascii"))
    for index, root_id in enumerate(root_ids):
        if isinstance(root_id, bool) or not isinstance(root_id, int) or root_id <= 0:
            raise ValueError("root IDs must be positive integers")
        digest.update(f"{index}\t{root_id}\n".encode("ascii"))
    return digest.hexdigest()


class FlynnStore:
    """SQLite event and state store; caller owns the database location."""

    def __init__(self, path: str | Path, *, readonly: bool = False):
        self.path = str(path)
        self.readonly = readonly
        if readonly:
            database_uri = Path(self.path).resolve().as_uri() + "?mode=ro"
            self.connection = sqlite3.connect(database_uri, uri=True)
        else:
            self.connection = sqlite3.connect(self.path)
        self.connection.execute("PRAGMA foreign_keys = ON")
        if not readonly:
            self.connection.executescript(_SCHEMA)
            self.connection.execute(
                "INSERT OR IGNORE INTO metadata(key, value) VALUES('schema_version', ?)",
                (str(SCHEMA_VERSION),),
            )
        version = self.connection.execute(
            "SELECT value FROM metadata WHERE key='schema_version'"
        ).fetchone()[0]
        if version != str(SCHEMA_VERSION):
            self.connection.close()
            raise RuntimeError(f"unsupported FlynnStore schema version: {version}")
        if not readonly:
            self.connection.commit()
        self._active_generation_id = None
        self._active_episode_id = None
        active = self.active_causal_generation()
        if active is not None:
            self._active_generation_id = active["generation_id"]
            self._active_episode_id = active["episode_id"]

    def close(self) -> None:
        self.connection.close()

    def _require_writer(self) -> None:
        if self.readonly:
            raise RuntimeError("this SQLite connection is read-only; writes belong to the resident coordinator")

    def latest_component_state(self, component: str) -> dict[str, Any] | None:
        """Read the most recently committed snapshot for one component."""
        if self._active_generation_id is None:
            row = self.connection.execute(
                "SELECT state_id, event_id, neural_time_ms, schema_version, state_json "
                "FROM component_states WHERE component=? ORDER BY rowid DESC LIMIT 1", (component,),
            ).fetchone()
        else:
            row = self.connection.execute(
                "SELECT state_id, event_id, neural_time_ms, schema_version, state_json "
                "FROM component_states WHERE component=? "
                "AND json_extract(state_json,'$.causal_generation_id')=? ORDER BY rowid DESC LIMIT 1",
                (component, self._active_generation_id),
            ).fetchone()
        if row is None and component == "integrated_world_neural_checkpoint":
            return self.active_checkpoint()
        if row is None and component == "neuro_world_coordinator":
            active = self.active_causal_generation()
            if active is not None:
                row = self.connection.execute(
                    "SELECT state_id,event_id,neural_time_ms,schema_version,state_json FROM component_states "
                    "WHERE component=? AND json_extract(state_json,'$.checkpoint_sha256')=? "
                    "AND json_extract(state_json,'$.checkpoint_tick')=? ORDER BY rowid DESC LIMIT 1",
                    (component, active["checkpoint_sha256"], active["checkpoint_tick"]),
                ).fetchone()
        if row is None and component == "pinocchio_body_checkpoint":
            checkpoint = self.active_checkpoint()
            body_ref = (checkpoint or {}).get("state", {}).get("body_checkpoint")
            if isinstance(body_ref, dict):
                body = self.component_state_by_id(str(body_ref.get("component_state_id", "")))
                if body is not None:
                    return body
        if row is None:
            return None
        return {
            "state_id": row[0], "event_id": row[1], "neural_time_ms": row[2],
            "schema_version": row[3], "state": self.decode_component_state(component, json.loads(row[4])),
        }

    @staticmethod
    def decode_component_state(component: str, state: Mapping[str, Any]) -> dict[str, Any]:
        """Return the historical full shape for losslessly compacted observations."""
        return _expand_component_state(component, state)

    def event_payload(self, event_id: str) -> dict[str, Any] | None:
        """Resolve both legacy inline event payloads and compact state references."""
        row = self.connection.execute(
            "SELECT event_type, payload_json FROM events WHERE event_id=?", (event_id,)
        ).fetchone()
        if row is None:
            return None
        payload = json.loads(row[1])
        ref = payload.get("_component_state_ref") if isinstance(payload, dict) else None
        if ref is None:
            return payload
        if row[0] != "COMPONENT_STATE_RECORDED" or not isinstance(ref, dict):
            raise RuntimeError("invalid component-state event reference")
        state = self.connection.execute(
            "SELECT state_json FROM component_states WHERE state_id=? AND event_id=? AND component=?",
            (ref.get("state_id"), event_id, ref.get("component")),
        ).fetchone()
        if state is None:
            raise RuntimeError(f"component-state event reference is unresolved: {event_id}")
        return self.decode_component_state(str(ref.get("component")), json.loads(state[0]))

    def _state_event_reference(
        self, *, state_id: str, event_id: str, component: str,
        neural_time_ms: float | None, state: Mapping[str, Any],
    ) -> str:
        """Build a compact event payload while retaining indexed causal identity."""
        causal = self.active_causal_generation()
        generation_id = state.get("causal_generation_id")
        episode_id = state.get("episode_id")
        if causal is not None:
            generation_id = generation_id or causal["generation_id"]
            episode_id = episode_id or causal["episode_id"]
        reference = {
            "_component_state_ref": {
                "schema_version": SCHEMA_VERSION,
                "state_id": state_id,
                "component": component,
            },
            "episode_id": episode_id,
            "causal_generation_id": generation_id,
            "neural_time_ms": neural_time_ms,
        }
        for key in ("tick", "end_tick", "sequence"):
            if key in state:
                reference[key] = state[key]
        return _json(reference)

    def coordinator_status(self) -> dict[str, Any]:
        row = self.connection.execute(
            "SELECT ingestion_paused, revision, updated_at_utc FROM coordinator_control WHERE singleton=1"
        ).fetchone()
        if row is None:
            return {"ingestion_paused": False, "revision": 0, "updated_at_utc": None}
        return {"ingestion_paused": bool(row[0]), "revision": row[1], "updated_at_utc": row[2]}

    def active_causal_generation(self) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT c.episode_id, c.active_generation_id, c.checkpoint_state_id, c.checkpoint_sha256, "
            "c.checkpoint_tick, c.revision, c.updated_at_utc, g.parent_generation_id, "
            "g.origin_checkpoint_state_id, g.origin_checkpoint_sha256, g.origin_tick "
            "FROM causal_generation_control AS c JOIN causal_generations AS g "
            "ON g.generation_id=c.active_generation_id WHERE c.singleton=1"
        ).fetchone()
        if row is None:
            return None
        return {
            "episode_id": row[0], "generation_id": row[1], "checkpoint_state_id": row[2],
            "checkpoint_sha256": row[3], "checkpoint_tick": int(row[4]),
            "revision": int(row[5]), "updated_at_utc": row[6],
            "parent_generation_id": row[7], "origin_checkpoint_state_id": row[8],
            "origin_checkpoint_sha256": row[9], "origin_tick": int(row[10]),
        }

    @property
    def causal_generation_id(self) -> str | None:
        return self._active_generation_id

    def qualify_id(self, identifier: str) -> str:
        """Qualify persistence IDs by generation without changing legacy IDs."""
        generation_id = self._active_generation_id
        if generation_id is None or f":generation:{generation_id}" in identifier:
            return identifier
        return f"{identifier}:generation:{generation_id}"

    def component_state_by_id(self, state_id: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT state_id, event_id, component, neural_time_ms, schema_version, state_json "
            "FROM component_states WHERE state_id=?", (state_id,)
        ).fetchone()
        if row is None:
            return None
        return {
            "state_id": row[0], "event_id": row[1], "neural_time_ms": row[3],
            "schema_version": row[4], "state": self.decode_component_state(row[2], json.loads(row[5])),
        }

    def active_checkpoint(self) -> dict[str, Any] | None:
        """Resolve only the checkpoint named by the active causal cursor."""
        active = self.active_causal_generation()
        if active is None:
            return None
        if active["checkpoint_state_id"] is None:
            if (active["checkpoint_sha256"] is None
                    and active["checkpoint_tick"] == 0
                    and active["parent_generation_id"] is None
                    and active["origin_checkpoint_state_id"] is None
                    and active["origin_checkpoint_sha256"] is None
                    and active["origin_tick"] == 0):
                # A newly initialized generation has a valid causal cursor at
                # tick zero before its first paired neural/world checkpoint.
                return None
            raise RuntimeError("active causal cursor has an incomplete checkpoint reference")
        checkpoint = self.component_state_by_id(active["checkpoint_state_id"])
        if checkpoint is None or checkpoint["state"].get("checkpoint_sha256") != active["checkpoint_sha256"]:
            raise RuntimeError("active causal cursor does not reference its exact confirmed checkpoint")
        metadata = checkpoint["state"]
        if (metadata.get("episode_id") != active["episode_id"]
                or int(metadata.get("neural_tick", -1)) != active["checkpoint_tick"]):
            raise RuntimeError("active causal cursor identity or tick differs from its referenced checkpoint")
        return checkpoint

    def generation_has_unconfirmed_tail(self) -> bool:
        active = self.active_causal_generation()
        if active is None:
            return False
        checkpoint = self.active_checkpoint()
        checkpoint_time = float(checkpoint["state"]["neural_time_ms"])
        generation_id = active["generation_id"]
        row = self.connection.execute(
            "SELECT state_json FROM component_states WHERE component='neuro_world_coordinator' "
            "AND json_extract(state_json,'$.causal_generation_id')=? ORDER BY rowid DESC LIMIT 1",
            (generation_id,),
        ).fetchone()
        if row is not None:
            cycle = json.loads(row[0])
            if (cycle.get("cycle_status") != "CYCLE_CONFIRMED"
                    and int(cycle.get("end_tick", cycle.get("start_tick", -1))) >= active["checkpoint_tick"]):
                return True
        if self.connection.execute(
            "SELECT 1 FROM component_states WHERE json_extract(state_json,'$.causal_generation_id')=? "
            "AND neural_time_ms>? LIMIT 1", (generation_id, checkpoint_time + 1e-9),
        ).fetchone() is not None:
            return True
        return self.connection.execute(
            "SELECT 1 FROM events WHERE json_extract(payload_json,'$.causal_generation_id')=? "
            "AND neural_time_ms>? LIMIT 1", (generation_id, checkpoint_time + 1e-9),
        ).fetchone() is not None

    def activate_causal_generation(
        self, *, episode_id: str, generation_id: str, parent_generation_id: str | None,
        checkpoint_state_id: str | None, checkpoint_sha256: str | None, checkpoint_tick: int,
        event_payload: Mapping[str, Any], occurred_at_utc: str | None = None,
        created_at_utc: str | None = None, event_id: str | None = None,
    ) -> dict[str, Any]:
        """Append a generation transition and move its active cursor in one SQLite commit."""
        self._require_writer()
        timestamp = occurred_at_utc or created_at_utc
        if timestamp is None:
            raise ValueError("generation activation requires a UTC timestamp")
        _validate_event_time(timestamp, None)
        if not episode_id or not generation_id or checkpoint_tick < 0:
            raise ValueError("episode, causal generation, and non-negative origin tick are required")
        if checkpoint_sha256 is not None and (
            len(checkpoint_sha256) != 64
            or any(char not in "0123456789abcdef" for char in checkpoint_sha256.lower())
        ):
            raise ValueError("checkpoint hash must be a SHA-256 digest")
        with self.connection:
            self.connection.execute("BEGIN IMMEDIATE")
            active = self.active_causal_generation()
            if active and active["episode_id"] != episode_id:
                raise ValueError("active causal generation belongs to a different resident episode")
            if active and active["generation_id"] == generation_id:
                self._active_generation_id = generation_id
                self._active_episode_id = episode_id
                return active
            if active and (
                parent_generation_id != active["generation_id"]
                or checkpoint_state_id != active["checkpoint_state_id"]
                or checkpoint_sha256 != active["checkpoint_sha256"]
                or checkpoint_tick != active["checkpoint_tick"]
            ):
                raise RuntimeError("new causal generation must descend from the current exact confirmed cursor")
            if parent_generation_id:
                parent = self.connection.execute(
                    "SELECT episode_id FROM causal_generations WHERE generation_id=?", (parent_generation_id,)
                ).fetchone()
                if parent is None or parent[0] != episode_id:
                    raise ValueError("causal generation parent is missing or belongs to another episode")
            if checkpoint_state_id is not None:
                checkpoint = self.component_state_by_id(checkpoint_state_id)
                if checkpoint is None:
                    raise RuntimeError("authorized causal origin checkpoint is missing")
                metadata = checkpoint["state"]
                if (metadata.get("episode_id") != episode_id
                        or metadata.get("checkpoint_sha256") != checkpoint_sha256
                        or int(metadata.get("neural_tick", -1)) != checkpoint_tick):
                    raise RuntimeError("authorized causal origin checkpoint identity, hash, or tick differs")
            elif checkpoint_sha256 is not None or checkpoint_tick != 0 or parent_generation_id is not None:
                raise ValueError("only an initial generation may omit its checkpoint origin")
            event_id = event_id or f"causal-generation:{episode_id}:{generation_id}:activated:generation:{generation_id}"
            payload_json = _json({**event_payload, "causal_generation_id": generation_id})
            self.connection.execute(
                "INSERT INTO events VALUES (?, 'CAUSAL_GENERATION_RECOVERY', 'resident_t2', ?, ?, ?, ?)",
                (event_id, (checkpoint["neural_time_ms"] if checkpoint_state_id is not None else None),
                 timestamp, payload_json, checkpoint_sha256),
            )
            self.connection.execute(
                "INSERT INTO causal_generations VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (generation_id, episode_id, parent_generation_id, checkpoint_state_id,
                 checkpoint_sha256, checkpoint_tick, event_id, timestamp),
            )
            revision = (active["revision"] if active else 0) + 1
            self.connection.execute(
                "INSERT INTO causal_generation_control(singleton, episode_id, active_generation_id, "
                "checkpoint_state_id, checkpoint_sha256, checkpoint_tick, revision, updated_at_utc) "
                "VALUES (1, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(singleton) DO UPDATE SET "
                "episode_id=excluded.episode_id, active_generation_id=excluded.active_generation_id, "
                "checkpoint_state_id=excluded.checkpoint_state_id, checkpoint_sha256=excluded.checkpoint_sha256, "
                "checkpoint_tick=excluded.checkpoint_tick, revision=excluded.revision, "
                "updated_at_utc=excluded.updated_at_utc",
                (episode_id, generation_id, checkpoint_state_id, checkpoint_sha256,
                 checkpoint_tick, revision, timestamp),
            )
        self._active_generation_id = generation_id
        self._active_episode_id = episode_id
        return self.active_causal_generation() or {}

    def set_ingestion_paused(self, paused: bool, *, occurred_at_utc: str) -> dict[str, Any]:
        """Persist an audited administrative gate for incoming neural frames."""
        self._require_writer()
        if not isinstance(paused, bool):
            raise ValueError("paused must be a boolean")
        _validate_event_time(occurred_at_utc, None)
        with self.connection:
            self.connection.execute("BEGIN IMMEDIATE")
            current = self.connection.execute(
                "SELECT revision FROM coordinator_control WHERE singleton=1"
            ).fetchone()
            revision = (current[0] if current else 0) + 1
            event_id = f"coordinator:ingestion:{revision}"
            payload = {"ingestion_paused": paused, "revision": revision}
            self.connection.execute(
                "INSERT INTO events VALUES (?, 'COORDINATOR_CONTROL', 'picoclaw_mcp', NULL, ?, ?, NULL)",
                (event_id, occurred_at_utc, _json(payload)),
            )
            self.connection.execute(
                "INSERT INTO coordinator_control(singleton, ingestion_paused, revision, updated_at_utc) "
                "VALUES (1, ?, ?, ?) ON CONFLICT(singleton) DO UPDATE SET "
                "ingestion_paused=excluded.ingestion_paused, revision=excluded.revision, "
                "updated_at_utc=excluded.updated_at_utc",
                (int(paused), revision, occurred_at_utc),
            )
        return self.coordinator_status()

    def register_mapping(
        self,
        dataset_version: str,
        root_ids: Iterable[int],
        source_sha256: str,
    ) -> str:
        """Persist an immutable compact-index mapping from an ordered root list."""
        self._require_writer()
        ids = list(root_ids)
        if not dataset_version or len(ids) == 0:
            raise ValueError("dataset version and a non-empty root-ID list are required")
        if len(set(ids)) != len(ids):
            raise ValueError("root IDs must be unique")
        if not all(isinstance(value, int) and not isinstance(value, bool) and 0 < value < 2**63 for value in ids):
            raise ValueError("root IDs must fit positive SQLite signed 64-bit integers")
        if len(source_sha256) != 64 or any(char not in "0123456789abcdef" for char in source_sha256.lower()):
            raise ValueError("source_sha256 must be a 64-character SHA-256 hex digest")
        map_hash = mapping_digest(dataset_version, ids)
        rows = [
            (dataset_version, index, root_id, source_sha256, map_hash)
            for index, root_id in enumerate(ids)
        ]
        try:
            with self.connection:
                existing = self.connection.execute(
                    "SELECT COUNT(*), MIN(mapping_sha256), MAX(mapping_sha256), "
                    "MIN(source_sha256), MAX(source_sha256) "
                    "FROM neuron_mapping WHERE dataset_version=?",
                    (dataset_version,),
                ).fetchone()
                if existing[0]:
                    if (existing[1] == existing[2] == map_hash
                            and existing[3] == existing[4] == source_sha256
                            and existing[0] == len(rows)):
                        return map_hash
                    raise ValueError("dataset version already has a different immutable mapping")
                self.connection.executemany(
                    "INSERT INTO neuron_mapping VALUES (?, ?, ?, ?, ?)", rows
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError("mapping violates uniqueness or index constraints") from exc
        return map_hash

    def record_event(
        self,
        *,
        event_id: str,
        event_type: str,
        source: str,
        occurred_at_utc: str,
        payload: Mapping[str, Any],
        neural_time_ms: float | None = None,
        provenance_sha256: str | None = None,
    ) -> bool:
        """Insert an event; an identical retry is idempotent, a collision fails."""
        self._require_writer()
        if not all((event_id, event_type, source, occurred_at_utc)):
            raise ValueError("event ID, type, source, and UTC timestamp are required")
        _validate_event_time(occurred_at_utc, neural_time_ms)
        event_id = self.qualify_id(event_id)
        if provenance_sha256 is not None and (
            len(provenance_sha256) != 64
            or any(char not in "0123456789abcdef" for char in provenance_sha256.lower())
        ):
            raise ValueError("provenance_sha256 must be a SHA-256 hex digest")
        payload_value = dict(payload)
        if self._active_generation_id is not None:
            payload_value.setdefault("causal_generation_id", self._active_generation_id)
        payload_json = _json(payload_value)
        row = (event_type, source, neural_time_ms, occurred_at_utc, payload_json, provenance_sha256)
        with self.connection:
            current = self.connection.execute(
                "SELECT event_type, source, neural_time_ms, occurred_at_utc, payload_json, provenance_sha256 "
                "FROM events WHERE event_id=?", (event_id,),
            ).fetchone()
            if current is not None:
                if current == row:
                    return False
                raise ValueError("event ID already exists with different content")
            self.connection.execute(
                "INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?)", (event_id, *row)
            )
        return True

    @staticmethod
    def _frame_receipt_ids(episode_id: str, generation_id: str, frame_seq: int) -> tuple[str, str]:
        key_json = _json([episode_id, generation_id, frame_seq])
        key_hash = hashlib.sha256(key_json.encode("utf-8")).hexdigest()
        generation_marker = f":generation:{generation_id}"
        prefix = f"picoclaw-frame-receipt:{key_hash}{generation_marker}"
        return f"{prefix}:prepared", f"{prefix}:confirmed"

    def read_picoclaw_frame_receipt(
        self, *, episode_id: str, generation_id: str, frame_seq: int,
    ) -> dict[str, Any] | None:
        """Read the durable prepared/confirmed receipt; this never moves the causal cursor."""
        prepared_id, confirmed_id = self._frame_receipt_ids(episode_id, generation_id, frame_seq)
        prepared_id = self.qualify_id(prepared_id)
        confirmed_id = self.qualify_id(confirmed_id)
        event = self.connection.execute(
            "SELECT event_type,source,neural_time_ms,occurred_at_utc,payload_json,provenance_sha256 "
            "FROM events WHERE event_id=?", (prepared_id,),
        ).fetchone()
        if event is None:
            return None
        prepared = json.loads(event[4])
        if (prepared.get("episode_id") != episode_id
                or prepared.get("causal_generation_id") != generation_id
                or int(prepared.get("frame_seq", -1)) != int(frame_seq)):
            raise RuntimeError("frame receipt key resolves to different causal identity")
        confirmed = self.component_state_by_id(confirmed_id)
        if confirmed is not None:
            state = confirmed["state"]
            for key in ("episode_id", "causal_generation_id", "frame_seq", "frame_digest"):
                if state.get(key) != prepared.get(key):
                    raise RuntimeError("confirmed frame receipt conflicts with its prepared identity")
            return {**prepared, "status": "CONFIRMED", "prepared": prepared,
                    "confirmed": state, "state_id": confirmed_id}
        return {**prepared, "status": "PREPARED", "prepared": prepared,
                "confirmed": None, "state_id": confirmed_id}

    def prepare_picoclaw_frame_receipt(
        self, *, frame: Mapping[str, Any], dn_readout: Mapping[str, Any] | None,
        occurred_at_utc: str, delivery_epoch: str,
    ) -> dict[str, Any]:
        """Durably record minimal frame identity before calling the MCP/PicoClaw path."""
        self._require_writer()
        active = self.active_causal_generation()
        episode_id = str(frame.get("episode_id", ""))
        generation_id = str(frame.get("causal_generation_id") or (active or {}).get("generation_id") or "")
        sequence = frame.get("sequence")
        if (not episode_id or not generation_id or not isinstance(delivery_epoch, str)
                or not delivery_epoch or isinstance(sequence, bool)
                or not isinstance(sequence, int) or sequence < 0):
            raise ValueError("resident frame receipt requires episode, generation, and non-negative sequence")
        if active is not None and (active["episode_id"] != episode_id or active["generation_id"] != generation_id):
            raise ValueError("frame receipt identity differs from the active causal generation")
        digest = picoclaw_frame_digest(frame, dn_readout)
        receipt = {
            "schema": "flynn.picoclaw_frame_receipt.v1",
            "episode_id": episode_id,
            "causal_generation_id": generation_id,
            "frame_seq": sequence,
            "start_tick": int(frame["start_tick"]),
            "end_tick": int(frame["end_tick"]),
            "start_neural_time_ms": float(frame["start_tick"]) * float(frame["dt_ms"]),
            "end_neural_time_ms": float(frame["neural_time_ms"]),
            "input_provenance_sha256": str(frame["input_sha256"]),
            "mapping_sha256": str(frame["mapping_sha256"]),
            "manifest_sha256": str(frame["manifest_sha256"]),
            "model_sha256": str(frame["model_sha256"]),
            "config_sha256": str(frame["config_sha256"]),
            "connectome_sha256": str(frame["connectome_sha256"]),
            "dn_readout_sha256": hashlib.sha256(_json(dn_readout).encode("utf-8")).hexdigest()
                if dn_readout is not None else None,
            "frame_digest": digest,
            "idempotency_key": f"{episode_id}|{generation_id}|{sequence}",
            "delivery_epoch": delivery_epoch,
            "status": "PREPARED",
            "replay_policy": "PENDING_FROM_ANOTHER_DELIVERY_EPOCH_REQUIRES_RECONCILIATION",
        }
        current = self.read_picoclaw_frame_receipt(
            episode_id=episode_id, generation_id=generation_id, frame_seq=sequence,
        )
        if current is not None:
            if current["prepared"].get("frame_digest") != digest:
                raise ValueError("frame idempotency conflict: same episode/generation/sequence has different content")
            return {**current["prepared"], "created": False,
                    "status": current["status"],
                    "confirmed": current["confirmed"]}
        prepared_id, _ = self._frame_receipt_ids(episode_id, generation_id, sequence)
        inserted = self.record_event(
            event_id=prepared_id,
            event_type="PICOCLAW_FRAME_RECEIPT_PREPARED",
            source="resident_t2_coordinator",
            occurred_at_utc=occurred_at_utc,
            neural_time_ms=float(frame["neural_time_ms"]),
            provenance_sha256=str(frame["input_sha256"]),
            payload=receipt,
        )
        if not inserted:
            current = self.read_picoclaw_frame_receipt(
                episode_id=episode_id, generation_id=generation_id, frame_seq=sequence,
            )
            if current is None or current["prepared"].get("frame_digest") != digest:
                raise ValueError("concurrent frame receipt preparation conflicts with this frame")
            return {**receipt, "status": current["status"], "created": False,
                    "confirmed": current["confirmed"]}
        return {**receipt, "created": True, "confirmed": None}

    def picoclaw_frame_confirmation_record(
        self, *, receipt: Mapping[str, Any], occurred_at_utc: str,
        result_sha256: str, result_status: str, output_state_id: str | None,
        body_checkpoint_state_id: str | None,
    ) -> dict[str, Any]:
        """Prepare an append-only confirmation row for an atomic state transaction."""
        self._require_writer()
        if receipt.get("status") != "PREPARED":
            raise ValueError("only a prepared PicoClaw receipt can be confirmed")
        if len(result_sha256) != 64 or any(c not in "0123456789abcdef" for c in result_sha256):
            raise ValueError("PicoClaw receipt result must have a lowercase SHA-256 digest")
        episode_id = str(receipt["episode_id"])
        generation_id = str(receipt["causal_generation_id"])
        sequence = int(receipt["frame_seq"])
        _, state_id = self._frame_receipt_ids(episode_id, generation_id, sequence)
        return {
            "state_id": state_id,
            "event_id": f"{state_id}:state",
            "component": "picoclaw_frame_receipt",
            "occurred_at_utc": occurred_at_utc,
            "neural_time_ms": float(receipt["end_neural_time_ms"]),
            "state": {
                **{key: receipt[key] for key in (
                    "schema", "episode_id", "causal_generation_id", "frame_seq",
                    "start_tick", "end_tick", "start_neural_time_ms", "end_neural_time_ms",
                    "input_provenance_sha256", "mapping_sha256", "manifest_sha256",
                    "model_sha256", "config_sha256", "connectome_sha256",
                    "dn_readout_sha256", "frame_digest", "idempotency_key",
                )},
                "status": "CONFIRMED",
                "pico_version": "v0.2.9",
                "provider_used": False,
                "result_sha256": result_sha256,
                "result_status": result_status,
                "output_state_id": output_state_id,
                "body_checkpoint_state_id": body_checkpoint_state_id,
            },
        }

    def confirm_picoclaw_frame_receipt(self, **kwargs: Any) -> dict[str, Any]:
        """Append the confirmation when no body state must join the same transaction."""
        record = self.picoclaw_frame_confirmation_record(**kwargs)
        receipt = kwargs["receipt"]
        current = self.read_picoclaw_frame_receipt(
            episode_id=str(receipt["episode_id"]),
            generation_id=str(receipt["causal_generation_id"]),
            frame_seq=int(receipt["frame_seq"]),
        )
        if current is None or current["prepared"].get("frame_digest") != receipt.get("frame_digest"):
            raise RuntimeError("PicoClaw receipt confirmation has no matching durable preparation")
        if current["status"] == "CONFIRMED":
            existing = current["confirmed"]
            if (existing.get("result_sha256") != record["state"].get("result_sha256")
                    or existing.get("output_state_id") != record["state"].get("output_state_id")):
                raise RuntimeError("PicoClaw confirmation retry conflicts with the durable result")
            return existing
        self.record_state(**record)
        return record["state"]

    def record_stimulus(
        self,
        *,
        event_id: str,
        modality: str,
        origin: str,
        occurred_at_utc: str,
        parameters: Mapping[str, Any],
        neural_time_ms: float | None = None,
    ) -> None:
        """Record an offered stimulus; this does not imply neural or energy effect."""
        self._require_writer()
        if not modality or not origin:
            raise ValueError("stimulus modality and origin are required")
        _validate_event_time(occurred_at_utc, neural_time_ms)
        event_id = self.qualify_id(event_id)
        parameters_value = dict(parameters)
        if self._active_generation_id is not None:
            parameters_value.setdefault("causal_generation_id", self._active_generation_id)
        parameters_json = _json(parameters_value)
        with self.connection:
            self.connection.execute(
                "INSERT INTO events VALUES (?, 'STIMULUS_RECORDED', ?, ?, ?, ?, NULL)",
                (event_id, origin, neural_time_ms, occurred_at_utc, parameters_json),
            )
            self.connection.execute(
                "INSERT INTO stimuli VALUES (?, ?, ?, ?)",
                (event_id, modality, origin, parameters_json),
            )

    def record_state(
        self,
        *,
        state_id: str,
        event_id: str,
        component: str,
        occurred_at_utc: str,
        state: Mapping[str, Any],
        neural_time_ms: float | None = None,
    ) -> None:
        """Append a component snapshot without interpreting its scientific meaning."""
        self._require_writer()
        if not all((state_id, event_id, component, occurred_at_utc)):
            raise ValueError("state ID, event ID, component, and UTC timestamp are required")
        _validate_event_time(occurred_at_utc, neural_time_ms)
        state_value = dict(state)
        if self._active_generation_id is not None:
            state_value.setdefault("causal_generation_id", self._active_generation_id)
            if state_value["causal_generation_id"] != self._active_generation_id:
                raise ValueError("component state belongs to a non-active causal generation")
            if component == "neural_activity_aggregator":
                episode_id = state_value.get("episode_id")
                end_tick = state_value.get("end_tick")
                if not episode_id or isinstance(end_tick, bool) or not isinstance(end_tick, int):
                    raise ValueError("generation-scoped neural state requires episode_id and integer end_tick")
                state_id = event_id = f"{episode_id}:generation:{self._active_generation_id}:tick:{end_tick}"
        state_id = self.qualify_id(state_id)
        event_id = self.qualify_id(event_id)
        state_json = _json(_compact_component_state(component, state_value))
        event_payload_json = self._state_event_reference(
            state_id=state_id, event_id=event_id, component=component,
            neural_time_ms=neural_time_ms, state=state_value,
        )
        with self.connection:
            self.connection.execute(
                "INSERT INTO events VALUES (?, 'COMPONENT_STATE_RECORDED', ?, ?, ?, ?, NULL)",
                (event_id, component, neural_time_ms, occurred_at_utc, event_payload_json),
            )
            self.connection.execute(
                "INSERT INTO component_states VALUES (?, ?, ?, ?, ?, ?)",
                (state_id, event_id, component, neural_time_ms, SCHEMA_VERSION, state_json),
            )

    def record_states_atomically(
        self, records: Iterable[Mapping[str, Any]], *,
        causal_cursor: Mapping[str, Any] | None = None,
    ) -> None:
        """Append related component states as one SQLite commit boundary."""
        self._require_writer()
        prepared = []
        for record in records:
            state_id = self.qualify_id(record["state_id"])
            event_id = self.qualify_id(record["event_id"])
            component = record["component"]
            occurred_at_utc = record["occurred_at_utc"]
            neural_time_ms = record.get("neural_time_ms")
            state_value = dict(record["state"])
            if self._active_generation_id is not None:
                state_value.setdefault("causal_generation_id", self._active_generation_id)
                if state_value["causal_generation_id"] != self._active_generation_id:
                    raise ValueError("atomic component state belongs to a non-active causal generation")
            state_json = _json(_compact_component_state(component, state_value))
            if not all((state_id, event_id, component, occurred_at_utc)):
                raise ValueError("state ID, event ID, component, and UTC timestamp are required")
            _validate_event_time(occurred_at_utc, neural_time_ms)
            event_payload_json = self._state_event_reference(
                state_id=state_id, event_id=event_id, component=component,
                neural_time_ms=neural_time_ms, state=state_value,
            )
            prepared.append((state_id, event_id, component, occurred_at_utc,
                             neural_time_ms, state_json, event_payload_json))
        if not prepared:
            raise ValueError("atomic state batch cannot be empty")
        with self.connection:
            self.connection.execute("BEGIN IMMEDIATE")
            for state_id, event_id, component, occurred_at_utc, neural_time_ms, state_json, event_payload_json in prepared:
                self.connection.execute(
                    "INSERT INTO events VALUES (?, 'COMPONENT_STATE_RECORDED', ?, ?, ?, ?, NULL)",
                    (event_id, component, neural_time_ms, occurred_at_utc, event_payload_json),
                )
                self.connection.execute(
                    "INSERT INTO component_states VALUES (?, ?, ?, ?, ?, ?)",
                    (state_id, event_id, component, neural_time_ms, SCHEMA_VERSION, state_json),
                )
            if causal_cursor is not None:
                current = self.active_causal_generation()
                if (current is None
                        or current["episode_id"] != causal_cursor.get("episode_id")
                        or current["generation_id"] != causal_cursor.get("generation_id")):
                    raise ValueError("checkpoint confirmation does not belong to the active causal generation")
                checkpoint_tick = int(causal_cursor["checkpoint_tick"])
                if checkpoint_tick < current["checkpoint_tick"]:
                    raise ValueError("confirmed causal checkpoint cannot move its cursor backwards")
                checkpoint_state_id = self.qualify_id(str(causal_cursor["checkpoint_state_id"]))
                checkpoint_record = next((item for item in prepared if item[0] == checkpoint_state_id), None)
                if checkpoint_record is None or checkpoint_record[2] != "integrated_world_neural_checkpoint":
                    raise RuntimeError("causal cursor update must commit with its integrated checkpoint state")
                checkpoint_state = json.loads(checkpoint_record[5])
                if (checkpoint_state.get("episode_id") != causal_cursor.get("episode_id")
                        or checkpoint_state.get("checkpoint_sha256") != causal_cursor.get("checkpoint_sha256")
                        or int(checkpoint_state.get("neural_tick", -1)) != checkpoint_tick
                        or checkpoint_state.get("execution_kind") != "RESIDENT"):
                    raise RuntimeError("causal cursor metadata differs from the checkpoint committed in this transaction")
                confirmed_cycle = False
                for item in prepared:
                    if item[2] != "neuro_world_coordinator":
                        continue
                    cycle_state = json.loads(item[5])
                    if (cycle_state.get("cycle_status") == "CYCLE_CONFIRMED"
                            and cycle_state.get("checkpoint_sha256") == causal_cursor.get("checkpoint_sha256")
                            and int(cycle_state.get("checkpoint_tick", -1)) == checkpoint_tick
                            and cycle_state.get("checkpoint_state_id") == checkpoint_state_id):
                        confirmed_cycle = True
                        break
                if not confirmed_cycle:
                    raise RuntimeError("causal cursor update requires its matching confirmed cycle in the same transaction")
                self.connection.execute(
                    "UPDATE causal_generation_control SET checkpoint_state_id=?, checkpoint_sha256=?, "
                    "checkpoint_tick=?, revision=revision+1, updated_at_utc=? WHERE singleton=1",
                    (checkpoint_state_id, causal_cursor["checkpoint_sha256"],
                     checkpoint_tick, causal_cursor["updated_at_utc"]),
                )
