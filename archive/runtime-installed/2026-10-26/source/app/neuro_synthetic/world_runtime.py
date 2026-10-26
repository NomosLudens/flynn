"""Connect the existing continuous world to V2 observation and persistence.

This adapter records world state as world state. It does not turn legacy sensory
rates into neural activity and it does not produce body commands.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from app.world.continuous_world import ContinuousWorldEngine
from app.brain.homeostasis_v2 import HomeostasisEngineV2

from .aggregator import NeuralActivityFrame
from .pipeline import NeuralActivityPipeline
from .sqlite_store import FlynnStore


class FlynnWorldRuntime:
    """Compose the existing world, optional real LIF core, and V2 SQLite store.

    The coordinated path advances the neural clock first against the world's
    current committed state, then advances the world to the same boundary. No
    legacy firing-rate fields are converted into neural input, and no body
    output is produced without an approved sensory/motor contract. Synthetic
    proprioception is read only from a real body sample at the same boundary.
    """

    WORLD_COMPONENT = "continuous_world"
    COORDINATOR_COMPONENT = "neuro_world_coordinator"
    CHECKPOINT_COMPONENT = "integrated_world_neural_checkpoint"
    WORLD_CHUNK_MS = 20.0
    FRAME_MS = 10.0

    def __init__(
        self,
        *,
        world: ContinuousWorldEngine,
        pipeline: NeuralActivityPipeline,
        neural_core: Any | None = None,
        picoclaw_port: Any | None = None,
        visual_light_transducer: Any | None = None,
        proprioceptive_transducer: Any | None = None,
        descending_readout: Any | None = None,
        homeostasis: HomeostasisEngineV2 | None = None,
        homeostasis_seeded_from_operator: bool = False,
        execution_kind: str = "INSTRUMENTAL_LOCAL_ONLY",
    ):
        if world is None or pipeline is None:
            raise ValueError("world and neural activity pipeline are required")
        if neural_core is not None and neural_core.pipeline is not pipeline:
            raise ValueError("coordinated neural core must use this exact Flynn pipeline")
        if execution_kind not in {"INSTRUMENTAL_LOCAL_ONLY", "RESIDENT"}:
            raise ValueError("execution_kind must explicitly identify an instrumental or resident run")
        if execution_kind == "RESIDENT":
            episode_id = pipeline.aggregator.episode_id
            if not episode_id.startswith("resident-v2:"):
                raise ValueError("resident execution requires a new resident-v2 episode identity")
            if not str(pipeline.store.path).endswith("/episode-v2.sqlite3"):
                raise ValueError("resident execution requires its dedicated episode SQLite path")
            if homeostasis is None:
                raise ValueError("resident execution requires an explicit HomeostasisEngineV2 state")
        self.world = world
        self.pipeline = pipeline
        self.neural_core = neural_core
        self.picoclaw_port = picoclaw_port
        self.visual_light_transducer = visual_light_transducer
        self.proprioceptive_transducer = proprioceptive_transducer
        self.descending_readout = descending_readout
        self.homeostasis = homeostasis
        self._homeostasis_seeded_from_operator = bool(homeostasis_seeded_from_operator)
        self._homeostasis_initialization_source = (
            "OPERATOR_CONFIGURED_AT_CONFIRMED_BOUNDARY"
            if self._homeostasis_seeded_from_operator else "CHECKPOINT_RESTORED"
        )
        self.execution_kind = execution_kind
        self.store: FlynnStore = pipeline.store
        with self.store.connection:
            current_kind = self.store.connection.execute(
                "SELECT value FROM metadata WHERE key='execution_kind'"
            ).fetchone()
            if current_kind and current_kind[0] != execution_kind:
                raise ValueError("SQLite execution kind differs from the active runtime mode")
            self.store.connection.execute(
                "INSERT OR IGNORE INTO metadata(key, value) VALUES('execution_kind', ?)",
                (execution_kind,),
            )
        self._cycle_lock = threading.RLock()
        latest = self.store.latest_component_state(self.WORLD_COMPONENT)
        prior = latest["state"].get("snapshot_sequence", -1) if latest else -1
        self._snapshot_sequence = int(prior) + 1
        self._last_world_signature = self._world_signature(latest["state"].get("world")) if latest else None
        self._last_world_persist_wall = time.monotonic()
        self._last_world_persist_time_ms = (
            float(latest["state"].get("world_time_ms", 0.0)) if latest else 0.0
        )
        self._observation_signatures: dict[str, str] = {}
        self._observation_last_wall: dict[str, float] = {}
        latest_cycle = self.store.latest_component_state(self.COORDINATOR_COMPONENT)
        if latest_cycle and latest_cycle["state"].get("episode_id") == pipeline.aggregator.episode_id:
            self._cycle_sequence = int(latest_cycle["state"].get("cycle_sequence", -1)) + 1
        else:
            self._cycle_sequence = 0
        self._restored_checkpoint_sha256: str | None = None

    def tick(self, chunk_ms: float, neural_time_ms: float) -> dict[str, Any]:
        """Advance the existing world and durably publish its actual snapshot."""
        self.world.tick(chunk_ms, neural_time_ms)
        return self.publish_world_snapshot()

    def publish_world_snapshot(self) -> dict[str, Any]:
        world = self.world.get_world_dict()
        state = {
            "episode_id": self.pipeline.aggregator.episode_id,
            "execution_kind": self.execution_kind,
            "dataset_version": self.pipeline.aggregator.dataset_version,
            "manifest_sha256": self.pipeline.aggregator.manifest_sha256,
            "mapping_sha256": self.pipeline.aggregator.mapping_sha256,
            "snapshot_sequence": self._snapshot_sequence,
            "world_time_ms": world["world_time_ms"],
            "neural_time_ms": world["neural_time_ms"],
            "timestamp_utc": world["timestamps"]["updated_at"],
            "world": world,
            "effect": "WORLD_OBSERVATION_ONLY",
        }
        signature = self._world_signature(world)
        now_wall = time.monotonic()
        changed = signature != self._last_world_signature
        if changed or now_wall - self._last_world_persist_wall >= 60.0:
            kind = "WORLD_STATE_CHANGE" if changed else "WORLD_STABILITY_INTERVAL"
            state["observation_kind"] = kind
            state["observation_interval_start_world_time_ms"] = self._last_world_persist_time_ms
            state["observation_interval_end_world_time_ms"] = float(world["world_time_ms"])
            event_id = f"world:{self.pipeline.aggregator.episode_id}:{self._snapshot_sequence}"
            self.store.record_state(
                state_id=event_id, event_id=event_id, component=self.WORLD_COMPONENT,
                occurred_at_utc=state["timestamp_utc"], neural_time_ms=state["neural_time_ms"], state=state,
            )
            self._last_world_signature = signature
            self._last_world_persist_wall = now_wall
            self._last_world_persist_time_ms = float(world["world_time_ms"])
        self._snapshot_sequence += 1
        return state

    @staticmethod
    def _world_signature(world: dict[str, Any] | None) -> str | None:
        if not isinstance(world, dict):
            return None
        stable = {key: value for key, value in world.items()
                  if key not in {"world_time_ms", "neural_time_ms", "timestamps", "updated_at_utc"}}
        encoded = json.dumps(stable, sort_keys=True, separators=(",", ":"), allow_nan=False)
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    def _should_persist_observation(self, component: str, signature: str, *, force: bool = False) -> bool:
        now = time.monotonic()
        changed = self._observation_signatures.get(component) != signature
        due = now - self._observation_last_wall.get(component, 0.0) >= 60.0
        if force or changed or due:
            self._observation_signatures[component] = signature
            self._observation_last_wall[component] = now
            return True
        return False

    def process_neural_frame(self, frame: NeuralActivityFrame):
        """Persist a frame supplied by a real, provenance-compatible core."""
        return self.pipeline.process(
            frame,
            occurred_at_utc=datetime.now(timezone.utc).isoformat(),
        )

    def _assert_aligned(self) -> tuple[float, float]:
        if self.neural_core is None:
            raise RuntimeError("no real neural core is attached to this world runtime")
        neural_time_ms = float(self.neural_core.engine.neural_time_ms)
        world_time_ms = float(self.world.world_time_ms)
        world_neural_time_ms = float(self.world.current_neural_t_ms)
        tolerance = max(1e-9, self.neural_core.parameters.dt_ms * 1e-8)
        if abs(world_time_ms - neural_time_ms) > tolerance:
            raise RuntimeError("world and LIF clocks differ; refusing to advance across a temporal gap")
        if abs(world_neural_time_ms - neural_time_ms) > tolerance:
            raise RuntimeError("world snapshot neural time differs from the LIF clock")
        return world_time_ms, neural_time_ms

    def _command_receipts(
        self,
        commands: list[dict[str, Any]],
        *,
        delivered_world_time_ms: float,
        delivered_neural_time_ms: float,
    ) -> list[dict[str, Any]]:
        now_monotonic_ns = time.perf_counter_ns()
        receipts = []
        for command in commands:
            age_ms = max(
                0.0,
                (now_monotonic_ns - int(command["received_monotonic_ns"])) / 1_000_000.0,
            )
            receipts.append({
                "command_id": command["command_id"],
                "cmd_type": command["cmd_type"],
                "variable": command["variable"],
                "received_at_utc": command["received_at_utc"],
                "arrival_to_boundary_ms": age_ms,
                "delivered_at_world_time_ms": delivered_world_time_ms,
                "delivered_at_neural_time_ms": delivered_neural_time_ms,
            })
        return receipts

    def _record_command_deliveries(self, receipts: list[dict[str, Any]], *, snapshot_sequence: int) -> None:
        for receipt in receipts:
            self.store.record_event(
                event_id=f"world-command:{receipt['command_id']}",
                event_type="WORLD_COMMAND_DELIVERED_AT_CAUSAL_BOUNDARY",
                source="continuous_world_command_queue",
                occurred_at_utc=datetime.now(timezone.utc).isoformat(),
                neural_time_ms=receipt["delivered_at_neural_time_ms"],
                payload={**receipt, "world_snapshot_sequence": snapshot_sequence},
            )

    def _body_readout_at_boundary(self, boundary_ms: float) -> dict[str, Any] | None:
        checkpoint = self.store.active_checkpoint()
        body_ref = (checkpoint or {}).get("state", {}).get("body_checkpoint")
        if isinstance(body_ref, dict):
            body_record = self.store.component_state_by_id(str(body_ref.get("component_state_id", "")))
            if body_record is None or body_record.get("state", {}).get("episode_id") != self.pipeline.aggregator.episode_id:
                raise RuntimeError("active causal checkpoint body reference is missing or belongs to another episode")
            body_state = body_record["state"]
            if body_state.get("episode_id") == self.pipeline.aggregator.episode_id:
                body_time = float(body_state.get("physical_time_ms", float("nan")))
                if abs(body_time - boundary_ms) > 1e-8:
                    raise RuntimeError("checkpoint-referenced Pinocchio state does not match the active causal boundary")
                compact = body_state.get("proprioceptive_readout")
                if isinstance(compact, dict):
                    if compact.get("episode_id") not in (None, body_state["episode_id"]):
                        raise RuntimeError("checkpoint-referenced Pinocchio readout belongs to another episode")
                    return {**compact, "episode_id": body_state["episode_id"]}
                raise RuntimeError("checkpoint-referenced Pinocchio state has no proprioceptive readout")
        else:
            body_row = self.store.connection.execute(
                "SELECT state_json FROM component_states WHERE component='pinocchio_body_checkpoint' ORDER BY rowid DESC LIMIT 1"
            ).fetchone()
            if body_row is not None:
                body_state = json.loads(body_row[0])
                if body_state.get("episode_id") == self.pipeline.aggregator.episode_id:
                    body_time = float(body_state.get("physical_time_ms", float("nan")))
                    if body_time > boundary_ms + 1e-8:
                        raise RuntimeError("future Pinocchio checkpoint cannot be delivered to the current LIF boundary")
                    if abs(body_time - boundary_ms) <= 1e-8:
                        compact = body_state.get("proprioceptive_readout")
                        if isinstance(compact, dict):
                            if compact.get("episode_id") not in (None, body_state["episode_id"]):
                                raise RuntimeError("Pinocchio readout belongs to another episode")
                            return {**compact, "episode_id": body_state["episode_id"]}
        rows = self.store.connection.execute(
            "SELECT state_json FROM component_states WHERE component='synthetic_proprioceptive_readout' ORDER BY rowid DESC"
        ).fetchall()
        for (raw_state,) in rows:
            state = json.loads(raw_state)
            if state.get("episode_id") != self.pipeline.aggregator.episode_id:
                continue
            sample_time = float(state.get("time_ms", float("nan")))
            if sample_time > boundary_ms + 1e-8:
                raise RuntimeError("future Pinocchio state cannot be delivered to the current LIF boundary")
            if sample_time < boundary_ms - 1e-8:
                raise RuntimeError("proprioceptive input has no Pinocchio sample at the current causal boundary")
            return state
        return None

    @staticmethod
    def _input_descriptor(packet: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in packet.items()
                if key not in {"compact_indices", "root_ids", "g_increment_by_target"}}

    @staticmethod
    def _sensor_signature(record: dict[str, Any]) -> str:
        semantic = {key: value for key, value in record.items() if key not in {
            "input_sha256", "body_checkpoint_id", "body_stream_sequence", "body_sample_sequence",
            "body_sample_time_ms", "neural_boundary_time_ms", "sequence", "time_ms",
        }}
        return hashlib.sha256(json.dumps(semantic, sort_keys=True, separators=(",", ":"),
                                      allow_nan=False).encode("utf-8")).hexdigest()

    def _combine_sensory_inputs(self, packets: list[dict[str, Any]]) -> dict[str, Any] | None:
        if not packets:
            return None
        if len(packets) == 1:
            return packets[0]
        indices_parts = []
        roots_parts = []
        increment_parts = []
        descriptors = []
        for packet in packets:
            indexes = np.asarray(packet["compact_indices"], dtype=np.int64)
            roots = np.asarray(packet["root_ids"], dtype=np.uint64)
            if "g_increment_by_target" in packet:
                increments = np.asarray(packet["g_increment_by_target"], dtype=np.float64)
            else:
                increments = np.full(indexes.shape, float(packet.get("g_increment_per_tick", 0.0)), dtype=np.float64)
            if roots.shape != indexes.shape or increments.shape != indexes.shape:
                raise ValueError("sensory packet indices, root IDs and conductance values are misaligned")
            indices_parts.append(indexes)
            roots_parts.append(roots)
            increment_parts.append(increments)
            descriptors.append(self._input_descriptor(packet))
        indices = np.concatenate(indices_parts)
        roots = np.concatenate(roots_parts)
        increments = np.concatenate(increment_parts)
        if len(np.unique(indices)) != len(indices):
            raise ValueError("sensory modalities overlap canonical neuron targets; refusing implicit double injection")
        order = np.argsort(indices, kind="stable")
        indices, roots, increments = indices[order], roots[order], increments[order]
        mapping_digest = hashlib.sha256("".join(
            f"{int(index)}\t{int(root)}\n" for index, root in zip(indices, roots)
        ).encode("ascii")).hexdigest()
        descriptor = {
            "schema": "flynn.synthetic_external_lif_input.v1",
            "modality": "composite_synthetic_sensory_input",
            "components": descriptors,
            "target_count": int(indices.size),
            "target_mapping_sha256": mapping_digest,
            "connectome_sha256": self.neural_core.connectome.matrix_sha256,
            "calibration_status": "INSTRUMENTAL_SYNTHETIC_NOT_BIOPHYSICAL",
        }
        descriptor["input_sha256"] = hashlib.sha256(
            json.dumps(descriptor, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        ).hexdigest()
        return {**descriptor, "compact_indices": indices, "root_ids": roots,
                "g_increment_by_target": increments}

    def _paired_body_checkpoint(self, boundary_ms: float) -> dict[str, Any] | None:
        rows = self.store.connection.execute(
            "SELECT state_id, state_json FROM component_states WHERE component='pinocchio_body_checkpoint' ORDER BY rowid DESC"
        ).fetchall()
        for state_id, raw_state in rows:
            state = json.loads(raw_state)
            if state.get("episode_id") != self.pipeline.aggregator.episode_id:
                continue
            physical_time = float(state.get("physical_time_ms", float("nan")))
            if physical_time > boundary_ms + 1e-8:
                raise RuntimeError("future body checkpoint cannot be paired with the current world/LIF checkpoint")
            if physical_time < boundary_ms - 1e-8:
                raise RuntimeError("world/LIF checkpoint has no body checkpoint at the same causal boundary")
            body_json = json.dumps(state["body_state"], sort_keys=True, separators=(",", ":"), allow_nan=False)
            return {
                "component_state_id": state_id,
                "stream_id": state["stream_id"],
                "stream_sequence": state["stream_sequence"],
                "physical_time_ms": physical_time,
                "body_model_sha256": state["body_model_sha256"],
                "body_state_sha256": hashlib.sha256(body_json.encode("utf-8")).hexdigest(),
            }
        return None

    def advance_synchronized(self, chunk_ms: float = WORLD_CHUNK_MS) -> dict[str, Any]:
        """Advance the real LIF core and existing world to one shared boundary.

        Commands already queued in the world are applied at the start boundary.
        Commands arriving while the synchronous neural chunk is running are
        applied at its end boundary, so no future world state reaches the LIF.
        Configured synthetic sensors are applied only from measurements at this
        causal boundary; stale or future body samples fail closed.
        """
        if isinstance(chunk_ms, bool) or not isinstance(chunk_ms, (int, float)) or not math.isfinite(chunk_ms) or chunk_ms <= 0:
            raise ValueError("chunk_ms must be a finite positive duration")
        with self._cycle_lock:
            start_world_ms, start_neural_ms = self._assert_aligned()
            latest_cycle = self.store.latest_component_state(self.COORDINATOR_COMPONENT)
            if (latest_cycle and latest_cycle["state"].get("episode_id") == self.pipeline.aggregator.episode_id
                    and latest_cycle["state"].get("cycle_status") not in {"CYCLE_COMPLETE", "CYCLE_CONFIRMED"}):
                checkpoint = self.store.latest_component_state(self.CHECKPOINT_COMPONENT)
                checkpoint_state = checkpoint["state"] if checkpoint else {}
                restored_checkpoint_is_current = (
                    self._restored_checkpoint_sha256 is not None
                    and checkpoint_state.get("episode_id") == self.pipeline.aggregator.episode_id
                    and checkpoint_state.get("checkpoint_sha256") == self._restored_checkpoint_sha256
                    and abs(float(checkpoint_state.get("neural_time_ms", -1)) - start_neural_ms) <= 1e-9
                    and abs(float(checkpoint_state.get("world_time_ms", -1)) - start_world_ms) <= 1e-9
                )
                if not restored_checkpoint_is_current:
                    raise RuntimeError("an incomplete coordinated cycle exists; restore a valid paired checkpoint or start a new episode")
            charged_cpu_event_id = None
            charged_cpu_costs = {}
            if self.homeostasis is not None:
                homeostasis_checkpoint = self.homeostasis.serialize_checkpoint()
                charged_cpu_event_id = homeostasis_checkpoint.get("pending_cpu_event_id")
                charged_cpu_costs = homeostasis_checkpoint.get("pending_cpu_seconds_by_stage", {})
                self.homeostasis.apply_pending_cpu_costs()
            dt_ms = float(self.neural_core.parameters.dt_ms)
            tick_count_float = float(chunk_ms) / dt_ms
            tick_count = round(tick_count_float)
            if tick_count <= 0 or abs(tick_count_float - tick_count) > 1e-9:
                raise ValueError("world chunk must be an exact positive number of neural dt ticks")

            wall_start = time.perf_counter()
            cpu_start = time.process_time()
            tolerance = max(1e-9, dt_ms * 1e-8)
            started_at_utc = datetime.now(timezone.utc).isoformat()
            start_state_id = f"neuro-world-cycle-start:{self.pipeline.aggregator.episode_id}:{self._cycle_sequence}"
            self.store.record_state(
                state_id=start_state_id,
                event_id=start_state_id,
                component=self.COORDINATOR_COMPONENT,
                occurred_at_utc=started_at_utc,
                neural_time_ms=start_neural_ms,
                state={
                    "episode_id": self.pipeline.aggregator.episode_id,
                    "cycle_sequence": self._cycle_sequence,
                    "cycle_status": "CYCLE_ADVANCING",
                    "execution_kind": self.execution_kind,
                    "start_world_time_ms": start_world_ms,
                    "start_neural_time_ms": start_neural_ms,
                    "target_world_time_ms": start_world_ms + float(chunk_ms),
                    "target_neural_time_ms": start_neural_ms + float(chunk_ms),
                    "start_tick": self.neural_core.engine.tick,
                    "homeostasis_state": self._homeostasis_payload() if self.homeostasis is not None else None,
                    "homeostasis_cpu_event_charged": charged_cpu_event_id,
                    "timestamp_utc": started_at_utc,
                },
            )
            if charged_cpu_event_id is not None:
                self.store.record_event(
                    event_id=f"{charged_cpu_event_id}:charged",
                    event_type="HOMEOSTASIS_CPU_COST_CHARGED",
                    source="resident_homeostasis_v2",
                    occurred_at_utc=started_at_utc,
                    neural_time_ms=start_neural_ms,
                    provenance_sha256=self.homeostasis.config_hash,
                    payload={
                        "episode_id": self.pipeline.aggregator.episode_id,
                        "causal_generation_id": (
                            self.store.active_causal_generation() or {}
                        ).get("generation_id"),
                        "measured_cpu_seconds_by_stage": charged_cpu_costs,
                        "energy_reserve_after_charge": self.homeostasis.energy_reserve,
                        "neural_time_ms": start_neural_ms,
                        "energy_units": "normalized_cpu_budget_fraction",
                    },
                )
            # Drain operator/world commands at the current causal boundary.
            world_start_phase = time.perf_counter()
            applied_at_start = self.world.tick(0.0, start_neural_ms)
            start_snapshot = self.publish_world_snapshot()
            start_receipts = self._command_receipts(
                applied_at_start,
                delivered_world_time_ms=start_world_ms,
                delivered_neural_time_ms=start_neural_ms,
            )
            self._record_command_deliveries(start_receipts, snapshot_sequence=start_snapshot["snapshot_sequence"])
            sensory_packets: list[dict[str, Any]] = []
            sensory_records: list[dict[str, Any]] = []
            sensory_timing_ms = {"visual_transducer_ms": 0.0, "proprioceptive_transducer_ms": 0.0}
            if self.visual_light_transducer is not None:
                transducer_started = time.perf_counter()
                visual_input = self.visual_light_transducer.transduce(float(self.world.illumination))
                sensory_timing_ms["visual_transducer_ms"] = (time.perf_counter() - transducer_started) * 1000.0
                sensory_packets.append(visual_input)
                sensory_record = self._input_descriptor(visual_input)
                sensory_records.append(sensory_record)
                sensory_state_id = (
                    f"visual-transduction:{self.pipeline.aggregator.episode_id}:"
                    f"{self._cycle_sequence}:{sensory_record['input_sha256']}"
                )
                if self._should_persist_observation("visual_light_transducer", sensory_record["input_sha256"]):
                    self.store.record_state(
                        state_id=sensory_state_id, event_id=sensory_state_id,
                        component="visual_light_transducer",
                        occurred_at_utc=datetime.now(timezone.utc).isoformat(),
                        neural_time_ms=start_neural_ms,
                        state={"episode_id": self.pipeline.aggregator.episode_id,
                               "execution_kind": self.execution_kind,
                               "cycle_sequence": self._cycle_sequence,
                               "world_snapshot_sequence": start_snapshot["snapshot_sequence"],
                               "world_time_ms": start_world_ms, **sensory_record,
                               "effect": "INSTRUMENTAL_SYNTHETIC_SENSORY_INPUT"},
                    )
            proprioception_status = "NOT_CONFIGURED"
            proprioception_record = None
            if self.proprioceptive_transducer is not None:
                body_readout = self._body_readout_at_boundary(start_world_ms)
                if body_readout is None:
                    proprioception_status = "NO_BODY_SAMPLE_AT_INITIAL_BOUNDARY"
                else:
                    transducer_started = time.perf_counter()
                    proprio_input = self.proprioceptive_transducer.transduce(
                        body_readout, neural_boundary_ms=start_neural_ms,
                    )
                    sensory_timing_ms["proprioceptive_transducer_ms"] = (time.perf_counter() - transducer_started) * 1000.0
                    sensory_packets.append(proprio_input)
                    proprioception_record = self._input_descriptor(proprio_input)
                    sensory_records.append(proprioception_record)
                    proprioception_status = proprioception_record["effect"]
                    proprio_id = (
                        f"proprioceptive-transduction:{self.pipeline.aggregator.episode_id}:"
                        f"{self._cycle_sequence}:{proprioception_record['input_sha256']}"
                    )
                    proprio_signature = self._sensor_signature(proprioception_record)
                    proprio_changed = self._observation_signatures.get("proprioceptive_neural_transduction") != proprio_signature
                    if self._should_persist_observation("proprioceptive_neural_transduction", proprio_signature):
                        self.store.record_state(
                            state_id=proprio_id, event_id=proprio_id,
                            component="proprioceptive_neural_transduction",
                            occurred_at_utc=datetime.now(timezone.utc).isoformat(),
                            neural_time_ms=start_neural_ms,
                            state={"episode_id": self.pipeline.aggregator.episode_id,
                                   "execution_kind": self.execution_kind,
                                   "cycle_sequence": self._cycle_sequence,
                                   "world_snapshot_sequence": start_snapshot["snapshot_sequence"],
                                   **proprioception_record, "effect": proprioception_record["effect"]},
                        )
                    if proprio_changed and proprioception_record["target_count"]:
                        self.store.record_event(
                            event_id=f"{proprio_id}:applied",
                            event_type="SYNTHETIC_PROPRIOCEPTIVE_LIF_INPUT_PREPARED",
                            source="synthetic_proprioceptive_transducer",
                            occurred_at_utc=datetime.now(timezone.utc).isoformat(),
                            neural_time_ms=start_neural_ms,
                            provenance_sha256=proprioception_record["input_sha256"],
                            payload={"body_checkpoint_id": body_readout.get("body_checkpoint_id"),
                                     "body_model_sha256": body_readout.get("body_model_sha256"),
                                     "target_mapping_sha256": proprioception_record["target_mapping_sha256"],
                                     "target_count": proprioception_record["target_count"],
                                     "effect": proprioception_record["effect"]},
                        )
            sensory_input = self._combine_sensory_inputs(sensory_packets)
            sensory_record = None
            if sensory_input is not None:
                sensory_record = self._input_descriptor(sensory_input)
            world_start_elapsed_ms = (time.perf_counter() - world_start_phase) * 1000.0

            frames: list[dict[str, Any]] = []
            picoclaw_acks: list[dict[str, Any]] = []
            frame_execution_metrics: list[dict[str, Any]] = []
            remaining = tick_count
            frame_ticks = max(1, round(self.FRAME_MS / dt_ms))
            neural_phase_start = time.perf_counter()
            while remaining:
                steps = min(frame_ticks, remaining)
                frame_metric: dict[str, Any] = {"steps": steps}
                frame_started = time.perf_counter()
                if self.homeostasis is not None:
                    if abs(self.homeostasis.neural_time_ms - float(self.neural_core.engine.neural_time_ms)) > tolerance:
                        raise RuntimeError("homeostasis and LIF clocks differ before the neural frame")
                    self.homeostasis.tick_neural(steps * dt_ms)
                neural_cpu_started = time.process_time()
                observation = self.neural_core.advance_frame(steps=steps, external_input=sensory_input)
                frame_metric["neural_core_cpu_ms"] = (time.process_time() - neural_cpu_started) * 1000.0
                if self.homeostasis is not None and abs(
                        self.homeostasis.neural_time_ms - float(observation.neural_time_ms)) > tolerance:
                    raise RuntimeError("homeostasis and LIF clocks differ after the neural frame")
                transient_frame = self.pipeline.observation_state(observation)
                if self.homeostasis is not None:
                    transient_frame["homeostasis_state"] = self._homeostasis_payload()
                frame_metric["neural_core"] = dict(self.neural_core.last_frame_metrics)
                frame_state = {
                    "sequence": observation.sequence,
                    "start_tick": observation.start_tick,
                    "end_tick": observation.end_tick,
                    "neural_time_ms": observation.neural_time_ms,
                    "spikes": observation.total_spikes,
                "stimulus_sha256": sensory_record["input_sha256"] if sensory_record else None,
                }
                frames.append(frame_state)
                motor_readout = None
                if self.descending_readout is not None:
                    readout_started = time.perf_counter()
                    readout_cpu_started = time.process_time()
                    motor_readout = self.descending_readout.extract(transient_frame["mapped_spikes"])
                    frame_state["dn_active_neurons"] = motor_readout["active_neurons"]
                    frame_state["dn_spikes"] = motor_readout["total_spikes"]
                    frame_state["dn_readout_sha256"] = motor_readout["manifest_sha256"]
                    frame_metric["dn_readout_ms"] = (time.perf_counter() - readout_started) * 1000.0
                    frame_metric["dn_readout_cpu_ms"] = (time.process_time() - readout_cpu_started) * 1000.0
                if self.picoclaw_port is not None:
                    receipt = self.store.prepare_picoclaw_frame_receipt(
                        frame=transient_frame, dn_readout=motor_readout,
                        occurred_at_utc=datetime.now(timezone.utc).isoformat(),
                        delivery_epoch=self.picoclaw_port.delivery_epoch,
                    )
                    picoclaw_cpu_started = time.process_time()
                    ack = self.picoclaw_port.coordinate_persisted_frame(
                        transient_frame, dn_readout=motor_readout, receipt=receipt,
                    )
                    frame_metric["picoclaw_python_bridge_cpu_ms"] = (
                        time.process_time() - picoclaw_cpu_started
                    ) * 1000.0
                    frame_metric["python_picoclaw_roundtrip_ms"] = ack["pico_bridge_elapsed_ms"]
                    frame_metric["picoclaw_process_tree_cpu_ms"] = ack.get("picoclaw_process_tree_cpu_ms")
                    frame_metric["picoclaw_manager_call_ms"] = ack.get("upstream_call_elapsed_ms")
                    frame_metric["pinocchio"] = ack.get("pinocchio_timing")
                    frame_state["picoclaw_status"] = ack["status"]
                    frame_state["picoclaw_bridge_elapsed_ms"] = ack["pico_bridge_elapsed_ms"]
                    frame_state["picoclaw_version"] = ack.get("pico_version")
                    frame_state["picoclaw_effect"] = ack.get("effect")
                    frame_state["picoclaw_source_provenance_sha256"] = ack.get("source_provenance_sha256")
                    if ack.get("status") != "IDEMPOTENT_RETRY":
                        if self.execution_kind == "RESIDENT" and ack.get("pinocchio_result") is not None:
                            self._persist_picoclaw_result(
                                ack, frame_state, observation.neural_time_ms, receipt=receipt,
                            )
                        else:
                            stable_result = {
                                "status": ack.get("status"), "receipt_key": receipt["idempotency_key"],
                                "frame_digest": receipt["frame_digest"], "sequence": frame_state["sequence"],
                                "neural_time_ms": float(observation.neural_time_ms),
                                "provider_used": ack.get("provider_used"),
                                "effect": ack.get("effect"),
                            }
                            result_sha256 = hashlib.sha256(json.dumps(
                                stable_result, sort_keys=True, separators=(",", ":"), allow_nan=False,
                            ).encode("utf-8")).hexdigest()
                            self.store.confirm_picoclaw_frame_receipt(
                                receipt=receipt, occurred_at_utc=datetime.now(timezone.utc).isoformat(),
                                result_sha256=result_sha256, result_status=str(ack.get("status")),
                                output_state_id=None, body_checkpoint_state_id=None,
                            )
                    picoclaw_acks.append(ack)
                frame_metric["coordinator_frame_ms"] = (time.perf_counter() - frame_started) * 1000.0
                frame_execution_metrics.append(frame_metric)
                remaining -= steps
            neural_pipeline_elapsed_ms = (time.perf_counter() - neural_phase_start) * 1000.0

            end_neural_ms = float(self.neural_core.engine.neural_time_ms)
            if abs(end_neural_ms - (start_neural_ms + float(chunk_ms))) > tolerance:
                raise RuntimeError("LIF tick count did not land on the requested world boundary")
            world_end_phase = time.perf_counter()
            # World changes queued during the neural advance take effect here,
            # never retroactively during the just-completed neural interval.
            applied_at_end = self.world.tick(float(chunk_ms), end_neural_ms)
            body_world_observation = None
            if self.proprioceptive_transducer is not None:
                latest_body = self.store.latest_component_state("pinocchio_body_checkpoint")
                if (latest_body is None
                        or latest_body["state"].get("episode_id") != self.pipeline.aggregator.episode_id
                        or abs(float(latest_body["state"].get("physical_time_ms", -1)) - end_neural_ms) > 1e-8):
                    raise RuntimeError("planar world observation requires the Pinocchio body sample at this causal boundary")
                body_state = latest_body["state"].get("body_state")
                centroid = body_state.get("physical_centroid") if isinstance(body_state, dict) else None
                if not isinstance(centroid, list) or len(centroid) < 2:
                    raise RuntimeError("Pinocchio body checkpoint lacks its measured world-coordinate centroid")
                body_world_observation = self.world.observe_body(
                    (float(centroid[0]), float(centroid[1])),
                    neural_time_ms=end_neural_ms,
                    homeostasis=None,
                    consume_on_contact=False,
                )
            end_snapshot = self.publish_world_snapshot()
            end_receipts = self._command_receipts(
                applied_at_end,
                delivered_world_time_ms=start_world_ms + float(chunk_ms),
                delivered_neural_time_ms=end_neural_ms,
            )
            self._record_command_deliveries(end_receipts, snapshot_sequence=end_snapshot["snapshot_sequence"])
            world_end_elapsed_ms = (time.perf_counter() - world_end_phase) * 1000.0
            wall_seconds = time.perf_counter() - wall_start
            cpu_seconds = time.process_time() - cpu_start
            pinocchio_cpu_seconds = sum(
                max(0.0, float(metric.get("pinocchio_worker_cpu_ms") or 0.0)) / 1000.0
                for metric in frame_execution_metrics
            )
            picoclaw_tree_cpu_seconds = sum(
                max(0.0, float(metric.get("picoclaw_process_tree_cpu_ms") or 0.0)) / 1000.0
                for metric in frame_execution_metrics
            )
            picoclaw_non_pinocchio_cpu_seconds = max(
                0.0, picoclaw_tree_cpu_seconds - pinocchio_cpu_seconds,
            )
            neural_cpu_seconds = sum(float(metric.get("neural_core_cpu_ms", 0.0)) / 1000.0
                                     for metric in frame_execution_metrics)
            readout_cpu_seconds = sum(float(metric.get("dn_readout_cpu_ms", 0.0)) / 1000.0
                                      for metric in frame_execution_metrics)
            bridge_cpu_seconds = sum(float(metric.get("picoclaw_python_bridge_cpu_ms", 0.0)) / 1000.0
                                     for metric in frame_execution_metrics)
            baseline_cpu_seconds = max(
                0.0, cpu_seconds - neural_cpu_seconds - readout_cpu_seconds - bridge_cpu_seconds,
            )
            cpu_event_id = None
            if self.homeostasis is not None:
                active_generation = self.store.active_causal_generation()
                if self.execution_kind == "RESIDENT" and active_generation is None:
                    raise RuntimeError("resident CPU accounting requires an active causal generation")
                generation_id = active_generation["generation_id"] if active_generation else "instrumental"
                cpu_event_id = (
                    f"homeostasis-cpu:{self.pipeline.aggregator.episode_id}:"
                    f"{generation_id}:{self._cycle_sequence}"
                )
                self.homeostasis.record_cpu_costs(
                    event_id=cpu_event_id,
                    costs_by_stage={
                        "resident_base_world_and_persistence": baseline_cpu_seconds,
                        "neural_core_and_aggregation": neural_cpu_seconds,
                        "descending_readout": readout_cpu_seconds,
                        "picoclaw_python_bridge": bridge_cpu_seconds,
                        "picoclaw_mcp_process_tree_excluding_pinocchio": picoclaw_non_pinocchio_cpu_seconds,
                        "pinocchio_worker_process": pinocchio_cpu_seconds,
                    },
                )
                self.store.record_event(
                    event_id=f"{cpu_event_id}:measured",
                    event_type="HOMEOSTASIS_CPU_COST_MEASURED",
                    source="resident_process_and_pinocchio_worker_cpu_counters",
                    occurred_at_utc=datetime.now(timezone.utc).isoformat(),
                    neural_time_ms=end_neural_ms,
                    provenance_sha256=self.homeostasis.config_hash,
                    payload={
                        "episode_id": self.pipeline.aggregator.episode_id,
                        "causal_generation_id": generation_id,
                        "cycle_sequence": self._cycle_sequence,
                        "cpu_seconds_by_stage": {
                            "resident_base_world_and_persistence": baseline_cpu_seconds,
                            "neural_core_and_aggregation": neural_cpu_seconds,
                            "descending_readout": readout_cpu_seconds,
                            "picoclaw_python_bridge": bridge_cpu_seconds,
                            "picoclaw_mcp_process_tree_excluding_pinocchio": picoclaw_non_pinocchio_cpu_seconds,
                            "pinocchio_worker_process": pinocchio_cpu_seconds,
                        },
                        "budget_cpu_seconds": self.homeostasis.config.cpu_seconds_per_full_reserve,
                        "energy_units": "normalized_cpu_budget_fraction",
                        "debit_status": "PENDING_NEXT_CAUSAL_BOUNDARY",
                    },
                )
            elapsed_real_ms = wall_seconds * 1000.0
            state = {
                "episode_id": self.pipeline.aggregator.episode_id,
                "dataset_version": self.pipeline.aggregator.dataset_version,
                "mapping_sha256": self.pipeline.aggregator.mapping_sha256,
                "cycle_sequence": self._cycle_sequence,
                # RESIDENT cycles become recoverable only when the paired
                # neural/world/body checkpoint marker is committed below.
                "cycle_status": "CYCLE_PREPARED" if self.execution_kind == "RESIDENT" else "CYCLE_COMPLETE",
                "execution_kind": self.execution_kind,
                "start_world_time_ms": start_world_ms,
                "end_world_time_ms": float(self.world.world_time_ms),
                "start_neural_time_ms": start_neural_ms,
                "end_neural_time_ms": end_neural_ms,
                "start_tick": frames[0]["start_tick"],
                "end_tick": self.neural_core.engine.tick,
                "dt_ms": dt_ms,
                "world_chunk_ms": float(chunk_ms),
                "frames": frames,
                "world_start_snapshot_sequence": start_snapshot["snapshot_sequence"],
                "world_end_snapshot_sequence": end_snapshot["snapshot_sequence"],
                "body_world_observation": body_world_observation,
                "synchronization_error_ms": float(self.world.world_time_ms - end_neural_ms),
                "elapsed_real_ms": elapsed_real_ms,
                "cpu_ms": cpu_seconds * 1000.0,
                "measured_cpu_cost_seconds_by_stage": {
                    "resident_base_world_and_persistence": baseline_cpu_seconds,
                    "neural_core_and_aggregation": neural_cpu_seconds,
                    "descending_readout": readout_cpu_seconds,
                    "picoclaw_python_bridge": bridge_cpu_seconds,
                    "picoclaw_mcp_process_tree_excluding_pinocchio": picoclaw_non_pinocchio_cpu_seconds,
                    "pinocchio_worker_process": pinocchio_cpu_seconds,
                },
                "homeostasis_cpu_cost_event_id": cpu_event_id,
                "homeostasis_cpu_cost_status": (
                    "MEASURED_PENDING_NEXT_CAUSAL_BOUNDARY" if cpu_event_id else "NOT_CONFIGURED"
                ),
                "homeostasis_state": self._homeostasis_payload() if self.homeostasis is not None else None,
                "world_start_boundary_elapsed_ms": world_start_elapsed_ms,
                "sensory_transduction_timing_ms": sensory_timing_ms,
                "neural_pipeline_elapsed_ms": neural_pipeline_elapsed_ms,
                "observability_policy_id": "flynn.significant-observation.v1",
                "neural_observation": {
                    "frame_count": len(frames),
                    "observed_spike_count": sum(int(frame.get("spikes", 0)) for frame in frames),
                    "frames_with_spikes": sum(int(frame.get("spikes", 0)) > 0 for frame in frames),
                    "silence_observed": all(int(frame.get("spikes", 0)) == 0 for frame in frames),
                    "silence_scope": "LIF_FRAME_SPIKE_COUNTS_ONLY",
                },
                "frame_execution_metrics": [{
                    "steps": metric.get("steps"),
                    "neural_core_total_ms": metric.get("neural_core", {}).get("total_ms"),
                    "lif_engine_ms": metric.get("neural_core", {}).get("lif_engine_ms"),
                    "aggregator_sqlite_ms": metric.get("neural_core", {}).get("aggregator_sqlite_ms"),
                    "dn_readout_and_sqlite_ms": metric.get("dn_readout_and_sqlite_ms"),
                    "picoclaw_roundtrip_ms": metric.get("python_picoclaw_roundtrip_ms"),
                    "picoclaw_manager_call_ms": metric.get("picoclaw_manager_call_ms"),
                    "coordinator_frame_ms": metric.get("coordinator_frame_ms"),
                    "pinocchio_worker_ms": (metric.get("pinocchio") or {}).get("worker_ms"),
                    "pinocchio_worker_cpu_ms": (metric.get("pinocchio") or {}).get("worker_cpu_ms"),
                } for metric in frame_execution_metrics],
                "world_end_boundary_elapsed_ms": world_end_elapsed_ms,
                "coordination_pre_journal_elapsed_ms": max(
                    0.0, elapsed_real_ms - world_start_elapsed_ms - neural_pipeline_elapsed_ms - world_end_elapsed_ms
                ),
                "neural_simulation_speed": float(chunk_ms) / elapsed_real_ms if elapsed_real_ms else 0.0,
                "world_commands_at_start_boundary": len(start_receipts),
                "oldest_world_command_start_latency_ms": max((item["arrival_to_boundary_ms"] for item in start_receipts), default=0.0),
                "start_boundary_command_receipts": start_receipts,
                "world_commands_at_end_boundary": len(end_receipts),
                "oldest_world_command_end_latency_ms": max((item["arrival_to_boundary_ms"] for item in end_receipts), default=0.0),
                "end_boundary_command_receipts": end_receipts,
                "world_command_backlog_after_boundary": self.world._command_queue.qsize(),
                "environment_event_status": "WORLD_STATE_ONLY",
                "body_exposure_status": (
                    "SYNTHETIC_PROPRIOCEPTION_READ_BY_LIF"
                    if proprioception_status == "PROPRIOCEPTIVE_INPUT_APPLIED_TO_LIF"
                    else "BODY_READOUT_PRESENT_WITH_ZERO_DEVIATION"
                    if proprioception_status == "NO_PHYSICAL_DEVIATION_NO_NEURAL_INPUT"
                    else "NO_CURRENT_BODY_SAMPLE"
                    if self.proprioceptive_transducer is not None
                    else "NOT_CONNECTED_TO_V2_BODY"
                ),
                "sensory_transduction_status": (
                    "+".join(record["modality"] for record in sensory_records)
                    if sensory_records else "BLOCKED_NO_APPROVED_TRANSDUCER"
                    if self.visual_light_transducer is None and self.proprioceptive_transducer is None
                    else "NO_CURRENT_SENSORY_INPUT"
                ),
                "lif_input_status": (
                    "SYNTHETIC_PROPRIOCEPTIVE_CONDUCTANCE_DELIVERED"
                    if proprioception_status == "PROPRIOCEPTIVE_INPUT_APPLIED_TO_LIF"
                    else "SYNTHETIC_VISUAL_CONDUCTANCE_DELIVERED"
                    if any(record.get("modality") == "visible_light_calibration" for record in sensory_records)
                    else "NO_ENVIRONMENTAL_INPUT_DELIVERED"
                    if not sensory_records
                    else "NO_SENSORY_CONDUCTANCE_THIS_BOUNDARY"
                ),
                "visual_illumination_normalized": float(self.world.illumination),
                "visual_transducer_sha256": next(
                    (record["input_sha256"] for record in sensory_records
                     if record.get("modality") == "visible_light_calibration"), None
                ),
                "visual_target_count": next(
                    (record["target_count"] for record in sensory_records
                     if record.get("modality") == "visible_light_calibration"), 0
                ),
                "proprioceptive_input_status": proprioception_status,
                "proprioceptive_transducer_sha256": (
                    proprioception_record["input_sha256"] if proprioception_record else None
                ),
                "proprioceptive_target_count": (
                    proprioception_record["target_count"] if proprioception_record else 0
                ),
                "motor_mapping_status": (
                    "OFFICIAL_DN_READOUT_ZERO_NO_TORQUE"
                    if self.descending_readout is not None and all(frame.get("dn_spikes", 0) == 0 for frame in frames)
                    else "OFFICIAL_DN_READOUT_NONZERO_AWAITING_BODY_DISPATCH"
                    if self.descending_readout is not None
                    else "BLOCKED_NO_APPROVED_DN_MAPPING"
                ),
                "pinocchio_status": (
                    "REAL_PINOCCHIO_STEP_DISPATCHED_VIA_PICOCLAW"
                    if (self.picoclaw_port is not None and self.descending_readout is not None
                        and len(picoclaw_acks) == len(frames)
                        and abs((end_neural_ms / 20.0) - round(end_neural_ms / 20.0)) < 1e-8)
                    else "NOT_CONNECTED"
                ),
                "picoclaw_status": (
                    "FRAME_COORDINATION_OBSERVED_MOTOR_BLOCKED"
                    if self.picoclaw_port is not None and len(picoclaw_acks) == len(frames)
                    else "PICOCLAW_BRIDGE_NOT_CONFIGURED"
                ),
                "picoclaw_frame_ack_count": len(picoclaw_acks),
                "picoclaw_mean_bridge_elapsed_ms": (
                    sum(float(item["pico_bridge_elapsed_ms"]) for item in picoclaw_acks) / len(picoclaw_acks)
                    if picoclaw_acks else None
                ),
                "picoclaw_provider_used": False if picoclaw_acks else None,
                "effect": (
                    "SYNCHRONIZED_INSTRUMENTAL_WORLD_LIF_AND_SYNTHETIC_PROPRIOCEPTION"
                    if proprioception_status == "PROPRIOCEPTIVE_INPUT_APPLIED_TO_LIF"
                    else "SYNCHRONIZED_INSTRUMENTAL_WORLD_AND_LIF_ONLY"
                ),
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            }
            state_id = f"neuro-world:{self.pipeline.aggregator.episode_id}:{self._cycle_sequence}"
            durable_cycle_state = dict(state)
            durable_cycle_state["neural_observation"] = {
                "sampling_policy": "flynn.significant-observation.v2",
                "sample_resolution_ms": self.pipeline.sampling_window_ms,
                "frame_resolution_ms": self.FRAME_MS,
                "frames_processed_this_cycle": len(frames),
            }
            for transient_key in (
                "frames", "frame_execution_metrics", "start_boundary_command_receipts",
                "end_boundary_command_receipts", "elapsed_real_ms", "cpu_ms",
                "measured_cpu_cost_seconds_by_stage", "homeostasis_cpu_cost_event_id",
                "homeostasis_cpu_cost_status",
                "world_start_boundary_elapsed_ms", "sensory_transduction_timing_ms",
                "neural_pipeline_elapsed_ms", "world_end_boundary_elapsed_ms",
                "coordination_pre_journal_elapsed_ms", "neural_simulation_speed",
                "picoclaw_mean_bridge_elapsed_ms",
            ):
                durable_cycle_state.pop(transient_key, None)
            self.store.record_state(
                state_id=state_id,
                event_id=state_id,
                component=self.COORDINATOR_COMPONENT,
                occurred_at_utc=state["timestamp_utc"],
                neural_time_ms=end_neural_ms,
                state=durable_cycle_state,
            )
            self._cycle_sequence += 1
            self._restored_checkpoint_sha256 = None
            return state

    def _persist_picoclaw_result(self, ack: dict[str, Any], frame: dict[str, Any],
                                  neural_time_ms: float, *, receipt: dict[str, Any]) -> None:
        """Atomically persist body result and confirmation of its durable frame receipt."""
        timestamp = datetime.now(timezone.utc).isoformat()
        episode_id = self.pipeline.aggregator.episode_id
        sequence = int(frame["sequence"])
        ack_id = f"picoclaw-frame:{episode_id}:{sequence}"
        physical = ack.get("pinocchio_result")
        if not isinstance(physical, dict):
            raise RuntimeError("PicoClaw frame receipt cannot be confirmed without its expected physical result")
        physical_id = f"pinocchio-neural:{episode_id}:{sequence}"
        physical["source_event_id"] = ack_id
        physical["source_frame_sequences"] = physical.get("source_frame_sequences", [sequence])
        mode = physical.get("mode")
        dn_spikes = int(physical.get("dn_spike_sum", 0))
        torque_max = float(physical.get("torque_max_abs", 0.0))
        records = []
        if dn_spikes or torque_max:
            physical_state = {
                key: physical.get(key) for key in (
                    "episode_id", "mode", "origin", "sequence", "neural_time_ms", "status",
                    "manifest_sha256", "mapping_sha256", "connectome_sha256", "dn_root_count",
                    "dn_spike_sum", "dn_active_neurons", "torque_max_abs", "q_delta_max_abs",
                    "within_mechanical_limits", "source_frame_sequences", "source_frame_hashes",
                )
            }
            physical_state["source_event_id"] = ack_id
            physical_state["frame_receipt_key"] = receipt["idempotency_key"]
            physical_state["frame_digest"] = receipt["frame_digest"]
            records.append({
                "state_id": physical_id, "event_id": f"{physical_id}:state",
                "component": "pinocchio_motor_actuation", "occurred_at_utc": timestamp,
                "neural_time_ms": neural_time_ms, "state": physical_state,
            })
        body = physical.get("body_checkpoint")
        if not isinstance(body, dict):
            raise RuntimeError("Pinocchio result lacks the body checkpoint required for receipt confirmation")
        body_id = str(physical["body_checkpoint_state_id"])
        body["frame_receipt_key"] = receipt["idempotency_key"]
        body["frame_digest"] = receipt["frame_digest"]
        proprio = physical.get("proprioceptive_readout")
        if isinstance(proprio, dict):
            joint = proprio.get("joint_state_by_name", {}).get("AUDITORY_L")
            if not isinstance(joint, dict):
                raise RuntimeError("Pinocchio proprioceptive readout lacks the calibrated joint")
            body["proprioceptive_readout"] = {
                "schema": proprio.get("schema"), "source": proprio.get("source"),
                "body_model_sha256": proprio.get("body_model_sha256"),
                "body_checkpoint_id": body_id, "stream_id": proprio.get("stream_id"),
                "stream_sequence": proprio.get("stream_sequence"),
                "sequence": proprio.get("sequence"), "time_ms": proprio.get("time_ms"),
                "q": proprio.get("q"), "qdot": proprio.get("qdot"),
                "joint_state_by_name": {"AUDITORY_L": joint},
                "provenance": proprio.get("provenance"),
                "body_model": proprio.get("body_model"),
            }
        body_state = {
            "state_id": body_id, "event_id": f"{body_id}:state",
            "component": "pinocchio_body_checkpoint", "occurred_at_utc": timestamp,
            "neural_time_ms": neural_time_ms, "state": body,
        }
        result_payload = {
            "frame_digest": receipt["frame_digest"],
            "dn_spike_sum": int(physical.get("dn_spike_sum", 0)),
            "torque": physical.get("torque"),
            "body_state": body.get("body_state"),
            "body_model_sha256": body.get("body_model_sha256"),
            "source_frame_hashes": physical.get("source_frame_hashes"),
        }
        result_sha256 = hashlib.sha256(json.dumps(
            result_payload, sort_keys=True, separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")).hexdigest()
        receipt_record = self.store.picoclaw_frame_confirmation_record(
            receipt=receipt, occurred_at_utc=timestamp, result_sha256=result_sha256,
            result_status=str(ack.get("status")),
            output_state_id=physical_id if dn_spikes or torque_max else body_id,
            body_checkpoint_state_id=body_id,
        )
        records.extend((body_state, receipt_record))
        self.store.record_states_atomically(records)
        if dn_spikes or torque_max:
            self.store.record_event(
                event_id=f"{physical_id}:applied",
                event_type="PINOCCHIO_NEURAL_DN_READOUT_APPLIED",
                source="picoclaw_motor_coordinator", occurred_at_utc=timestamp,
                neural_time_ms=neural_time_ms,
                provenance_sha256=physical.get("manifest_sha256"),
                payload=physical_state,
            )

    def save_integrated_checkpoint(self, checkpoint_dir: str | Path) -> dict[str, Any]:
        """Commit one atomic world+LIF sidecar and a single SQLite recovery marker."""
        with self._cycle_lock:
            world_time_ms, neural_time_ms = self._assert_aligned()
            latest_cycle = self.store.latest_component_state(self.COORDINATOR_COMPONENT)
            if (latest_cycle is None
                    or latest_cycle["state"].get("episode_id") != self.pipeline.aggregator.episode_id
                    or latest_cycle["state"].get("cycle_status") not in {"CYCLE_COMPLETE", "CYCLE_PREPARED"}
                    or abs(float(latest_cycle["state"].get("end_neural_time_ms", -1)) - neural_time_ms) > 1e-9):
                raise RuntimeError("integrated checkpoint requires a completed, aligned world+LIF cycle")
            if self.world._command_queue.qsize():
                raise RuntimeError("integrated checkpoint requires an empty world command queue")

            runtime_state = self.neural_core.export_runtime_state()
            world_snapshot = self.world.snapshot()
            snapshot_json = json.dumps(world_snapshot, sort_keys=True, separators=(",", ":"), allow_nan=False)
            world_snapshot_sha256 = hashlib.sha256(snapshot_json.encode("utf-8")).hexdigest()
            body_checkpoint = self._paired_body_checkpoint(world_time_ms)
            if self.proprioceptive_transducer is not None and body_checkpoint is None:
                raise RuntimeError("paired world/LIF checkpoint requires the real Pinocchio checkpoint at the same boundary")
            checkpoint_dir = Path(checkpoint_dir).resolve()
            checkpoint_dir.mkdir(parents=True, exist_ok=True)
            episode_tag = hashlib.sha256(self.pipeline.aggregator.episode_id.encode("utf-8")).hexdigest()[:12]
            tick = int(runtime_state["engine_state"]["tick"])
            filename = f"flynn-world-lif-{episode_tag}-tick-{tick}-{uuid.uuid4().hex}.npz"
            destination = checkpoint_dir / filename
            temporary = checkpoint_dir / f".{filename}.tmp"
            engine_state = runtime_state["engine_state"]
            observability_state = runtime_state.get("observability_state")
            observability_state_json = json.dumps(
                observability_state, sort_keys=True, separators=(",", ":"), allow_nan=False,
            ) if observability_state is not None else "null"
            observability_state_sha256 = hashlib.sha256(observability_state_json.encode("utf-8")).hexdigest()
            ready_windows = self.pipeline.completed_observation_windows()
            checkpoint_started = time.perf_counter()
            try:
                with temporary.open("wb") as output:
                    save_archive = np.savez_compressed if self.execution_kind == "RESIDENT" else np.savez
                    save_archive(
                        output,
                        checkpoint_version=np.asarray([1], dtype=np.uint32),
                        neural_tick=np.asarray([tick], dtype=np.uint64),
                        next_sequence=np.asarray([runtime_state["next_sequence"]], dtype=np.uint64),
                        world_snapshot_json=np.asarray(snapshot_json),
                        observability_state_json=np.asarray(observability_state_json),
                        state_version=np.asarray([engine_state["state_version"]], dtype=np.uint32),
                        v=engine_state["v"],
                        g=engine_state["g"],
                        refractory_until_tick=engine_state["refractory_until_tick"],
                        delay_buffer=engine_state["delay_buffer"],
                        frame_spike_counts=engine_state["frame_spike_counts"],
                    )
                    output.flush()
                    os.fsync(output.fileno())
                os.replace(temporary, destination)
            except Exception:
                temporary.unlink(missing_ok=True)
                raise

            checkpoint_sha256 = self._sha256_file(destination)
            metadata = {
                "checkpoint_version": 1,
                "execution_kind": self.execution_kind,
                "episode_id": self.pipeline.aggregator.episode_id,
                "dataset_version": self.pipeline.aggregator.dataset_version,
                "manifest_sha256": self.pipeline.aggregator.manifest_sha256,
                "mapping_sha256": self.pipeline.aggregator.mapping_sha256,
                "connectome_sha256": self.neural_core.connectome.matrix_sha256,
                "core_id": runtime_state["core_id"],
                "model_sha256": runtime_state["model_sha256"],
                "config_sha256": runtime_state["config_sha256"],
                "neural_tick": tick,
                "next_sequence": runtime_state["next_sequence"],
                "neural_time_ms": neural_time_ms,
                "world_time_ms": world_time_ms,
                "world_snapshot_sha256": world_snapshot_sha256,
                "observability_state_sha256": observability_state_sha256,
                "homeostasis_state": self._homeostasis_payload() if self.homeostasis is not None else None,
                "checkpoint_file": str(destination),
                "checkpoint_sha256": checkpoint_sha256,
                "checkpoint_bytes": destination.stat().st_size,
                "checkpoint_write_elapsed_ms": (time.perf_counter() - checkpoint_started) * 1000.0,
                "body_checkpoint": body_checkpoint,
                "proprioceptive_population_manifest_sha256": (
                    self.proprioceptive_transducer.manifest_sha256
                    if self.proprioceptive_transducer is not None else None
                ),
                "sensory_event_queue": "DERIVED_FROM_PERSISTED_BODY_SAMPLE_AT_NEXT_CAUSAL_BOUNDARY",
                "saved_at_utc": datetime.now(timezone.utc).isoformat(),
            }
            state_id = self.store.qualify_id(
                f"integrated-checkpoint:{self.pipeline.aggregator.episode_id}:{tick}:{checkpoint_sha256[:16]}"
            )
            if self.execution_kind == "RESIDENT":
                cycle_state = dict(latest_cycle["state"])
                if cycle_state.get("cycle_status") != "CYCLE_PREPARED":
                    raise RuntimeError("resident checkpoint requires an unconfirmed prepared cycle")
                cycle_state.update({
                    "cycle_status": "CYCLE_CONFIRMED",
                    "checkpoint_state_id": state_id,
                    "checkpoint_sha256": checkpoint_sha256,
                    "checkpoint_tick": tick,
                })
                cycle_id = self.store.qualify_id(
                    f"neuro-world:{self.pipeline.aggregator.episode_id}:{cycle_state['cycle_sequence']}:confirmed"
                )
                active_generation = self.store.active_causal_generation()
                if active_generation is None:
                    raise RuntimeError("resident checkpoint cannot be confirmed without an active causal generation")
                cycle_state["checkpoint_state_id"] = state_id
                records = [*ready_windows,
                    {"state_id": state_id, "event_id": state_id,
                     "component": self.CHECKPOINT_COMPONENT,
                     "occurred_at_utc": metadata["saved_at_utc"],
                     "neural_time_ms": neural_time_ms, "state": metadata},
                    {"state_id": cycle_id, "event_id": cycle_id,
                     "component": self.COORDINATOR_COMPONENT,
                     "occurred_at_utc": metadata["saved_at_utc"],
                     "neural_time_ms": neural_time_ms, "state": cycle_state},
                ]
                self.store.record_states_atomically(records, causal_cursor={
                    "episode_id": self.pipeline.aggregator.episode_id,
                    "generation_id": active_generation["generation_id"],
                    "checkpoint_state_id": state_id,
                    "checkpoint_sha256": checkpoint_sha256,
                    "checkpoint_tick": tick,
                    "updated_at_utc": metadata["saved_at_utc"],
                })
            else:
                records = [*ready_windows, {
                    "state_id": state_id, "event_id": state_id,
                    "component": self.CHECKPOINT_COMPONENT,
                    "occurred_at_utc": metadata["saved_at_utc"],
                    "neural_time_ms": neural_time_ms, "state": metadata,
                }]
                self.store.record_states_atomically(records)
            if ready_windows:
                self.pipeline.acknowledge_persisted_observation_windows(ready_windows)
            metadata["cycle_status"] = "CYCLE_CONFIRMED" if self.execution_kind == "RESIDENT" else "CYCLE_COMPLETE"
            return metadata

    def restore_integrated_checkpoint(self) -> dict[str, Any] | None:
        """Validate one paired checkpoint, then restore its LIF and world states."""
        with self._cycle_lock:
            latest = self.store.latest_component_state(self.CHECKPOINT_COMPONENT)
            if latest is None:
                return None
            metadata = latest["state"]
            expected = {
                "checkpoint_version": 1,
                "execution_kind": self.execution_kind,
                "episode_id": self.pipeline.aggregator.episode_id,
                "dataset_version": self.pipeline.aggregator.dataset_version,
                "manifest_sha256": self.pipeline.aggregator.manifest_sha256,
                "mapping_sha256": self.pipeline.aggregator.mapping_sha256,
                "connectome_sha256": self.neural_core.connectome.matrix_sha256,
                "core_id": self.neural_core.export_runtime_state()["core_id"],
                "config_sha256": self.neural_core.config_sha256,
                "proprioceptive_population_manifest_sha256": (
                    self.proprioceptive_transducer.manifest_sha256
                    if self.proprioceptive_transducer is not None else None
                ),
            }
            saved_model_sha = metadata.get("model_sha256")
            model_matches = self.neural_core.accepts_model_sha256(saved_model_sha)
            if any(metadata.get(key) != value for key, value in expected.items()) or not model_matches:
                raise ValueError("integrated checkpoint provenance does not match the active world+LIF runtime")
            saved_homeostasis = metadata.get("homeostasis_state")
            if self.homeostasis is not None:
                if not isinstance(saved_homeostasis, dict):
                    if (not self._homeostasis_seeded_from_operator
                            or abs(self.homeostasis.neural_time_ms
                                   - float(metadata["neural_time_ms"])) > 1e-9):
                        raise ValueError(
                            "integrated checkpoint has no homeostasis state; an explicit seed at this confirmed boundary is required"
                        )
                else:
                    if (saved_homeostasis.get("episode_id") != metadata["episode_id"]
                            or saved_homeostasis.get("causal_generation_id") != self.pipeline.causal_generation_id
                            or abs(float(saved_homeostasis.get("neural_time_ms", -1))
                                   - float(metadata["neural_time_ms"])) > 1e-9):
                        raise ValueError("integrated checkpoint homeostasis identity or clock differs")
            saved_body = metadata.get("body_checkpoint")
            if self.proprioceptive_transducer is not None and not isinstance(saved_body, dict):
                raise ValueError("integrated checkpoint does not reference its Pinocchio body checkpoint")
            if isinstance(saved_body, dict):
                row = self.store.connection.execute(
                    "SELECT state_json FROM component_states WHERE state_id=? AND component='pinocchio_body_checkpoint'",
                    (saved_body.get("component_state_id"),),
                ).fetchone()
                if row is None:
                    raise ValueError("integrated checkpoint Pinocchio body state is missing")
                body_state = json.loads(row[0])
                body_json = json.dumps(body_state.get("body_state"), sort_keys=True,
                                       separators=(",", ":"), allow_nan=False)
                if (body_state.get("episode_id") != metadata["episode_id"]
                        or abs(float(body_state.get("physical_time_ms", -1)) - float(metadata["world_time_ms"])) > 1e-8
                        or body_state.get("body_model_sha256") != saved_body.get("body_model_sha256")
                        or hashlib.sha256(body_json.encode("utf-8")).hexdigest() != saved_body.get("body_state_sha256")):
                    raise ValueError("integrated checkpoint body identity/state hash differs from SQLite readback")
            latest_frame = self.store.latest_component_state(NeuralActivityPipeline.COMPONENT)
            if latest_frame is not None and latest_frame["state"].get("episode_id") == metadata["episode_id"]:
                frame_state = latest_frame["state"]
                if (int(frame_state.get("sequence", -1)) >= int(metadata["next_sequence"])
                        or int(frame_state.get("end_tick", -1)) > int(metadata["neural_tick"])):
                    raise RuntimeError(
                        "an uncheckpointed durable LIF frame exists; "
                        "refusing ambiguous replay after restart"
                    )
            if self.execution_kind == "RESIDENT":
                latest_cycle = self.store.latest_component_state(self.COORDINATOR_COMPONENT)
                cycle_state = latest_cycle["state"] if latest_cycle else {}
                confirmed = (
                    cycle_state.get("cycle_status") == "CYCLE_CONFIRMED"
                    and cycle_state.get("checkpoint_sha256") == metadata.get("checkpoint_sha256")
                    and cycle_state.get("checkpoint_tick") == metadata.get("neural_tick")
                )
                # Existing resident episodes predate the explicit confirmation
                # marker. Their checkpoint row is accepted only when its tick
                # and both clocks exactly match the last completed cycle.
                legacy_paired = (
                    cycle_state.get("cycle_status") == "CYCLE_COMPLETE"
                    and int(cycle_state.get("end_tick", -1)) == int(metadata.get("neural_tick", -2))
                    and abs(float(cycle_state.get("end_neural_time_ms", -1))
                            - float(metadata.get("neural_time_ms", -2))) <= 1e-9
                    and abs(float(cycle_state.get("end_world_time_ms", -1))
                            - float(metadata.get("world_time_ms", -2))) <= 1e-9
                )
                lineage = metadata.get("recovery_lineage")
                recovery_anchor = (
                    cycle_state.get("cycle_status") == "RECOVERY_ANCHOR"
                    and isinstance(lineage, dict)
                    and lineage.get("successor_checkpoint_sha256") == metadata.get("checkpoint_sha256")
                    and lineage.get("source_episode_id")
                    and cycle_state.get("recovery_source_episode_id") == lineage.get("source_episode_id")
                    and cycle_state.get("checkpoint_sha256") == metadata.get("checkpoint_sha256")
                    and int(cycle_state.get("checkpoint_tick", -1)) == int(metadata.get("neural_tick", -2))
                    and abs(float(cycle_state.get("end_neural_time_ms", -1))
                            - float(metadata.get("neural_time_ms", -2))) <= 1e-9
                    and abs(float(cycle_state.get("end_world_time_ms", -1))
                            - float(metadata.get("world_time_ms", -2))) <= 1e-9
                )
                if not (confirmed or legacy_paired or recovery_anchor):
                    raise RuntimeError("resident checkpoint lacks its atomic confirmed-cycle record")
            path = Path(metadata["checkpoint_file"]).resolve()
            if not path.is_file() or self._sha256_file(path) != metadata.get("checkpoint_sha256"):
                raise ValueError("integrated checkpoint file is missing or its SHA-256 differs from SQLite")
            with np.load(path, allow_pickle=False) as archive:
                if int(archive["checkpoint_version"][0]) != metadata["checkpoint_version"]:
                    raise ValueError("integrated checkpoint file version differs from SQLite")
                tick = int(archive["neural_tick"][0])
                next_sequence = int(archive["next_sequence"][0])
                snapshot_json = str(archive["world_snapshot_json"].item())
                world_snapshot = json.loads(snapshot_json)
                observability_state = (
                    json.loads(str(archive["observability_state_json"].item()))
                    if "observability_state_json" in archive.files else None
                )
                if observability_state is not None and hashlib.sha256(
                        json.dumps(observability_state, sort_keys=True, separators=(",", ":"),
                                   allow_nan=False).encode("utf-8")).hexdigest() != metadata.get("observability_state_sha256"):
                    raise ValueError("integrated checkpoint observation window hash mismatch")
                state = {
                    "state_version": int(archive["state_version"][0]),
                    "tick": tick,
                    "v": archive["v"],
                    "g": archive["g"],
                    "refractory_until_tick": archive["refractory_until_tick"],
                    "delay_buffer": archive["delay_buffer"],
                    "frame_spike_counts": archive["frame_spike_counts"],
                }
                if tick != metadata["neural_tick"] or next_sequence != metadata["next_sequence"]:
                    raise ValueError("integrated checkpoint arrays disagree with SQLite cursor")
                if hashlib.sha256(snapshot_json.encode("utf-8")).hexdigest() != metadata["world_snapshot_sha256"]:
                    raise ValueError("integrated checkpoint world snapshot hash mismatch")
                dt_ms = self.neural_core.parameters.dt_ms
                expected_time = tick * dt_ms
                if (abs(float(world_snapshot.get("world_time_ms", -1)) - expected_time) > 1e-8
                        or abs(float(world_snapshot.get("current_neural_t_ms", -1)) - expected_time) > 1e-8
                        or abs(float(metadata["world_time_ms"]) - expected_time) > 1e-8
                        or abs(float(metadata["neural_time_ms"]) - expected_time) > 1e-8):
                    raise ValueError("integrated checkpoint world and neural clocks do not align")
                runtime_state = {
                    "episode_id": metadata["episode_id"],
                    "dataset_version": metadata["dataset_version"],
                    "mapping_sha256": metadata["mapping_sha256"],
                    "manifest_sha256": metadata["manifest_sha256"],
                    "connectome_sha256": metadata["connectome_sha256"],
                    "model_sha256": metadata["model_sha256"],
                    "config_sha256": metadata["config_sha256"],
                    "core_id": metadata["core_id"],
                    "next_sequence": next_sequence,
                    "observability_state": observability_state,
                    "engine_state": state,
                }
                # Validate the durable frame cursor and arrays before mutating
                # either component. Both restores are fail-closed on mismatch.
                self.neural_core.restore_runtime_state(runtime_state)
                self.world.restore(world_snapshot)
                if self.homeostasis is not None and isinstance(saved_homeostasis, dict):
                    self.homeostasis.restore_checkpoint(saved_homeostasis)
                    self._homeostasis_initialization_source = str(
                        saved_homeostasis.get("initialization_source", "CHECKPOINT_RESTORED")
                    )

            restored_world_time, restored_neural_time = self._assert_aligned()
            if abs(restored_world_time - float(metadata["world_time_ms"])) > 1e-8:
                raise RuntimeError("restored world time differs from the integrated checkpoint marker")
            self.publish_world_snapshot()
            self.store.record_event(
                event_id=f"integrated-restore:{self.pipeline.aggregator.episode_id}:{uuid.uuid4().hex}",
                event_type="INTEGRATED_WORLD_NEURAL_RESTORE",
                source="flynn_world_runtime",
                occurred_at_utc=datetime.now(timezone.utc).isoformat(),
                neural_time_ms=restored_neural_time,
                payload={"checkpoint_sha256": metadata["checkpoint_sha256"],
                         "body_state": "RESTORED_FROM_PINOCCHIO_CHECKPOINT_IN_SQLITE"
                         if metadata.get("body_checkpoint") else "NO_BODY_CHECKPOINT_BOUND"},
                provenance_sha256=metadata["checkpoint_sha256"],
            )
            self._restored_checkpoint_sha256 = metadata["checkpoint_sha256"]
            return metadata

    def _homeostasis_payload(self) -> dict[str, Any]:
        if self.homeostasis is None:
            raise RuntimeError("homeostasis state is not attached to this runtime")
        active = self.store.active_causal_generation()
        if self.execution_kind == "RESIDENT" and active is None:
            raise RuntimeError("resident homeostasis state requires an active causal generation")
        payload = self.homeostasis.serialize_checkpoint()
        payload.update({
            "episode_id": self.pipeline.aggregator.episode_id,
            "causal_generation_id": active["generation_id"] if active else None,
            "execution_kind": self.execution_kind,
            "initialization_source": self._homeostasis_initialization_source,
        })
        return payload

    @staticmethod
    def _sha256_file(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()
