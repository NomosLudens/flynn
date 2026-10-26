"""Persist observational aggregator output into the new episode SQLite store."""

from __future__ import annotations

import hashlib
import math
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Iterable

from .aggregator import NeuralActivityAggregator, NeuralActivityFrame
from .sqlite_store import FlynnStore


class NeuralActivityPipeline:
    """Bind the verified root map, observation aggregator, and durable SQLite."""

    COMPONENT = "neural_activity_aggregator"
    PERSISTENCE_MODE_COMPONENT = "flynn_observability_persistence_mode"
    PERSISTENCE_MODES = {"dense", "sampled"}

    def __init__(
        self,
        *,
        store: FlynnStore,
        episode_id: str,
        dataset_version: str,
        manifest_sha256: str,
        mapping_sha256: str,
        root_ids: Iterable[int],
        restore_latest_cursor: bool = True,
        sampling_window_ms: float | None = None,
        requested_persistence_mode: str | None = None,
    ):
        self.store = store
        self.aggregator = NeuralActivityAggregator(
            episode_id=episode_id,
            dataset_version=dataset_version,
            manifest_sha256=manifest_sha256,
            mapping_sha256=mapping_sha256,
            root_ids=root_ids,
        )
        latest = store.latest_component_state(self.COMPONENT) if restore_latest_cursor else None
        if latest is not None:
            state = latest["state"]
            if state.get("episode_id") == episode_id:
                if (state.get("dataset_version") != dataset_version
                        or state.get("manifest_sha256") != manifest_sha256
                        or state.get("mapping_sha256") != mapping_sha256):
                    raise ValueError("persisted episode provenance differs from the requested dataset/map")
                self.aggregator.restore_cursor(
                    state["sequence"], state["neural_time_ms"],
                )
        # FlynnStore loads the active generation from its durable cursor when
        # it opens. Reuse that authority on restore instead of requiring a
        # second, potentially divergent activation call in the pipeline.
        self.causal_generation_id: str | None = store.causal_generation_id
        if sampling_window_ms is not None and (
            isinstance(sampling_window_ms, bool) or not math.isfinite(sampling_window_ms)
            or sampling_window_ms <= 0
        ):
            raise ValueError("sampling_window_ms must be a finite positive duration")
        self.sampling_window_ms = float(sampling_window_ms) if sampling_window_ms is not None else None
        if requested_persistence_mode is None:
            requested_persistence_mode = "sampled" if self.sampling_window_ms is not None else "dense"
        if requested_persistence_mode not in self.PERSISTENCE_MODES:
            raise ValueError("requested persistence mode must be 'dense' or 'sampled'")
        self.requested_persistence_mode = requested_persistence_mode
        mode_record = store.latest_component_state(self.PERSISTENCE_MODE_COMPONENT)
        if mode_record is None:
            last_observation = store.latest_component_state(self.COMPONENT)
            last_state = last_observation["state"] if last_observation else {}
            # Older sampled candidates did not persist a mode event. A window
            # record is unambiguous evidence of their active writer; otherwise
            # legacy history remains dense by default.
            self.persistence_mode = (
                "sampled" if last_state.get("observation_kind") == "NEURAL_ACTIVITY_WINDOW"
                else "dense"
            )
            self._mode_is_explicit = False
        else:
            mode_state = mode_record["state"]
            if (mode_state.get("episode_id") != episode_id
                    or mode_state.get("causal_generation_id") != self.causal_generation_id
                    or mode_state.get("mode") not in self.PERSISTENCE_MODES):
                raise ValueError("persisted observability mode belongs to another episode or generation")
            self.persistence_mode = mode_state["mode"]
            self._mode_is_explicit = True
        if self.persistence_mode == "sampled" and self.sampling_window_ms is None:
            raise ValueError("sampled persistence requires an explicit observation window")
        self._window: dict | None = None
        self._ready_windows: list[dict] = []

    def activate_causal_generation(
        self, generation_id: str, *, last_sequence: int | None = None,
        last_neural_time_ms: float | None = None,
    ) -> None:
        if not generation_id:
            raise ValueError("causal generation identity is required")
        self.causal_generation_id = generation_id
        if last_sequence is not None:
            if last_neural_time_ms is None:
                raise ValueError("restored frame time is required with a sequence cursor")
            self.aggregator.restore_cursor(last_sequence, last_neural_time_ms)

    def process(self, frame: NeuralActivityFrame, *, occurred_at_utc: str):
        if self.store.coordinator_status()["ingestion_paused"]:
            raise RuntimeError("neural activity ingestion is paused by coordinator control")
        observation = self.aggregator.aggregate(frame)
        if self.persistence_mode == "dense":
            state = {
                "episode_id": observation.episode_id,
                "dataset_version": observation.dataset_version,
                "manifest_sha256": self.aggregator.manifest_sha256,
                "mapping_sha256": self.aggregator.mapping_sha256,
                "sequence": observation.sequence,
                "neural_time_ms": observation.neural_time_ms,
                "core_id": observation.core_id,
                "model_sha256": observation.model_sha256,
                "config_sha256": observation.config_sha256,
                "connectome_sha256": observation.connectome_sha256,
                "start_tick": observation.start_tick,
                "end_tick": observation.end_tick,
                "dt_ms": observation.dt_ms,
                "stimulus": observation.stimulus,
                "active_neuron_count": observation.active_neuron_count,
                "total_spikes": observation.total_spikes,
                "input_sha256": observation.input_sha256,
                "mapped_spikes": [asdict(item) for item in observation.mapped_spikes],
                "effect": "OBSERVATION_ONLY",
            }
            generation_id = self.causal_generation_id
            if generation_id is not None:
                state["causal_generation_id"] = generation_id
                state["tick_identity"] = observation.end_tick
                event_id = f"{observation.episode_id}:generation:{generation_id}:tick:{observation.end_tick}"
            else:
                event_id = f"{observation.episode_id}:activity:{observation.sequence}"
            self.store.record_state(
                state_id=event_id,
                event_id=event_id,
                component=self.COMPONENT,
                occurred_at_utc=occurred_at_utc,
                state=state,
                neural_time_ms=observation.neural_time_ms,
            )
        else:
            self._accumulate_window(observation, occurred_at_utc)
        self.aggregator.commit(observation)
        return observation

    def observation_state(self, observation) -> dict:
        """Build an exact transient frame for PicoClaw without a per-frame SQLite row."""
        state = {
            "episode_id": observation.episode_id, "dataset_version": observation.dataset_version,
            "manifest_sha256": self.aggregator.manifest_sha256,
            "mapping_sha256": self.aggregator.mapping_sha256,
            "sequence": observation.sequence, "neural_time_ms": observation.neural_time_ms,
            "core_id": observation.core_id, "model_sha256": observation.model_sha256,
            "config_sha256": observation.config_sha256, "connectome_sha256": observation.connectome_sha256,
            "start_tick": observation.start_tick, "end_tick": observation.end_tick,
            "dt_ms": observation.dt_ms, "stimulus": observation.stimulus,
            "active_neuron_count": observation.active_neuron_count,
            "total_spikes": observation.total_spikes, "input_sha256": observation.input_sha256,
            "mapped_spikes": [asdict(item) for item in observation.mapped_spikes],
            "effect": "OBSERVATION_ONLY_TRANSIENT_FRAME",
        }
        if self.causal_generation_id is not None:
            state["causal_generation_id"] = self.causal_generation_id
            state["tick_identity"] = observation.end_tick
        return state

    def _accumulate_window(self, observation, occurred_at_utc: str) -> None:
        if self._window is None:
            self._window = {
                "start_sequence": observation.sequence, "end_sequence": observation.sequence,
                # Before the first frame is accumulated, the previous window
                # boundary is the frame's start tick. Setting end_tick to this
                # frame's end made the continuity check reject the first frame.
                "start_tick": observation.start_tick, "end_tick": observation.start_tick,
                "start_neural_time_ms": observation.start_tick * observation.dt_ms,
                "end_neural_time_ms": observation.neural_time_ms, "dt_ms": observation.dt_ms,
                "frame_count": 0, "frame_spike_totals": [], "neuron_spike_totals": {},
                "first_input_sha256": observation.input_sha256,
                "last_input_sha256": observation.input_sha256,
                "input_hash_chain_sha256": "0" * 64,
                "dataset_version": observation.dataset_version,
                "manifest_sha256": self.aggregator.manifest_sha256,
                "mapping_sha256": self.aggregator.mapping_sha256,
                "core_id": observation.core_id, "model_sha256": observation.model_sha256,
                "config_sha256": observation.config_sha256,
                "connectome_sha256": observation.connectome_sha256,
                "started_at_utc": occurred_at_utc, "ended_at_utc": occurred_at_utc,
            }
        window = self._window
        if (observation.sequence != window["end_sequence"] + (1 if window["frame_count"] else 0)
                or observation.start_tick != window["end_tick"]):
            raise RuntimeError("neural observation window received a discontinuous frame")
        window["end_sequence"] = observation.sequence
        window["end_tick"] = observation.end_tick
        window["end_neural_time_ms"] = observation.neural_time_ms
        window["ended_at_utc"] = occurred_at_utc
        window["frame_count"] += 1
        window["frame_spike_totals"].append(int(observation.total_spikes))
        for item in observation.mapped_spikes:
            key = str(item.compact_index)
            record = window["neuron_spike_totals"].setdefault(key, [int(item.root_id), 0])
            if record[0] != int(item.root_id):
                raise RuntimeError("neural observation window root ID changed for a compact index")
            record[1] += int(item.count)
            if record[1] > 2**64 - 1:
                raise OverflowError("neural observation window count exceeds uint64")
        link = f"{window['input_hash_chain_sha256']}:{observation.sequence}:{observation.input_sha256}"
        window["input_hash_chain_sha256"] = hashlib.sha256(link.encode("ascii")).hexdigest()
        window["last_input_sha256"] = observation.input_sha256
        elapsed_ms = float(window["end_neural_time_ms"] - window["start_neural_time_ms"])
        if elapsed_ms + 1e-9 >= self.sampling_window_ms:
            self._ready_windows.append(self._window_record(window))
            self._window = None
        elif elapsed_ms > self.sampling_window_ms + 1e-9:
            raise RuntimeError("neural observation window exceeded its configured sampling interval")

    def _window_record(self, window: dict, *, partial: bool = False) -> dict:
        generation = self.causal_generation_id or "legacy"
        state_id = (f"{self.aggregator.episode_id}:generation:{generation}:neural-window:"
                    f"{window['start_tick']}-{window['end_tick']}")
        totals = [[int(index), int(value[0]), int(value[1])]
                  for index, value in sorted(window["neuron_spike_totals"].items(), key=lambda item: int(item[0]))]
        frame_rle: list[list[int]] = []
        for count in window["frame_spike_totals"]:
            if frame_rle and frame_rle[-1][0] == count:
                frame_rle[-1][1] += 1
            else:
                frame_rle.append([count, 1])
        state = {
            "episode_id": self.aggregator.episode_id, "causal_generation_id": self.causal_generation_id,
            "dataset_version": window["dataset_version"],
            "manifest_sha256": window["manifest_sha256"], "mapping_sha256": window["mapping_sha256"],
            "core_id": window["core_id"], "model_sha256": window["model_sha256"],
            "config_sha256": window["config_sha256"], "connectome_sha256": window["connectome_sha256"],
            "observation_kind": "NEURAL_ACTIVITY_WINDOW", "sampling_policy": "flynn.significant-observation.v2",
            "sample_resolution_ms": self.sampling_window_ms,
            "partial_window": bool(partial),
            "window_close_reason": "PERSISTENCE_MODE_TRANSITION" if partial else "SAMPLE_INTERVAL_REACHED",
            "start_sequence": window["start_sequence"], "end_sequence": window["end_sequence"],
            "sequence": window["end_sequence"], "start_tick": window["start_tick"],
            "end_tick": window["end_tick"], "neural_time_ms": window["end_neural_time_ms"],
            "window_start_neural_time_ms": window["start_neural_time_ms"],
            "window_end_neural_time_ms": window["end_neural_time_ms"],
            "window_duration_ms": window["end_neural_time_ms"] - window["start_neural_time_ms"],
            "dt_ms": window["dt_ms"], "frame_count": window["frame_count"],
            "frame_resolution_ms": 10.0, "frame_total_spikes_rle": frame_rle,
            "silent_frame_count": sum(run for count, run in frame_rle if count == 0),
            "total_spikes": sum(value[1] for value in window["neuron_spike_totals"].values()),
            "active_neuron_count": len(window["neuron_spike_totals"]),
            "spike_counts_by_compact_index": totals,
            "first_input_sha256": window["first_input_sha256"],
            "last_input_sha256": window["last_input_sha256"],
            "ordered_input_hash_chain_sha256": window["input_hash_chain_sha256"],
            "started_at_utc": window["started_at_utc"], "ended_at_utc": window["ended_at_utc"],
            "effect": "OBSERVATION_AGGREGATE_ONLY",
        }
        if self.causal_generation_id is not None:
            state["tick_identity"] = window["end_tick"]
        return {"state_id": state_id, "event_id": state_id, "component": self.COMPONENT,
                "occurred_at_utc": window["ended_at_utc"],
                "neural_time_ms": window["end_neural_time_ms"], "state": state}

    def completed_observation_windows(self) -> list[dict]:
        return list(self._ready_windows)

    def acknowledge_persisted_observation_windows(self, records: list[dict]) -> None:
        ids = {record["state_id"] for record in records}
        if len(ids) != len(records) or any(record not in self._ready_windows for record in records):
            raise RuntimeError("attempted to acknowledge an unknown observation window")
        self._ready_windows = [record for record in self._ready_windows if record["state_id"] not in ids]

    @staticmethod
    def _state_digest(value: dict) -> str:
        import json
        return hashlib.sha256(json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")).hexdigest()

    def transition_persistence_mode(self, target_mode: str, checkpoint: dict) -> dict | None:
        """Change only after the referenced paired checkpoint is durably active."""
        if target_mode not in self.PERSISTENCE_MODES:
            raise ValueError("persistence mode must be 'dense' or 'sampled'")
        if target_mode == "sampled" and self.sampling_window_ms is None:
            raise ValueError("sampled persistence requires a positive sampling window")
        if target_mode == self.persistence_mode:
            return None
        active = self.store.active_causal_generation()
        saved = self.store.active_checkpoint()
        if (active is None or saved is None
                or active.get("episode_id") != self.aggregator.episode_id
                or active.get("generation_id") != self.causal_generation_id
                or active.get("checkpoint_sha256") != checkpoint.get("checkpoint_sha256")
                or int(active.get("checkpoint_tick", -1)) != int(checkpoint.get("neural_tick", -2))
                or saved.get("state", {}).get("checkpoint_sha256") != checkpoint.get("checkpoint_sha256")):
            raise RuntimeError("persistence mode can change only after its paired checkpoint is the active causal cursor")
        records = []
        flushed_window_sha256 = None
        if target_mode == "dense" and self._window is not None:
            window = self._window
            if (int(window["end_tick"]) != int(checkpoint["neural_tick"])
                    or int(window["end_sequence"]) + 1 != int(checkpoint["next_sequence"])):
                raise RuntimeError("cannot close sampled history outside the confirmed checkpoint boundary")
            partial = self._window_record(window, partial=True)
            flushed_window_sha256 = self._state_digest(window)
            records.append(partial)
        timestamp = datetime.now(timezone.utc).isoformat()
        state_id = (f"observability-mode:{self.aggregator.episode_id}:"
                    f"{self.causal_generation_id}:{checkpoint['neural_tick']}:{target_mode}")
        mode_state = {
            "episode_id": self.aggregator.episode_id,
            "causal_generation_id": self.causal_generation_id,
            "mode": target_mode,
            "previous_mode": self.persistence_mode,
            "effective_after_checkpoint_state_id": active.get("checkpoint_state_id"),
            "effective_after_checkpoint_sha256": checkpoint["checkpoint_sha256"],
            "effective_after_tick": int(checkpoint["neural_tick"]),
            "effective_after_sequence": int(checkpoint["next_sequence"]),
            "flushed_window_sha256": flushed_window_sha256,
            "transitioned_at_utc": timestamp,
            "effect": "OBSERVABILITY_POLICY_ONLY",
        }
        records.append({
            "state_id": state_id, "event_id": f"{state_id}:event",
            "component": self.PERSISTENCE_MODE_COMPONENT,
            "occurred_at_utc": timestamp,
            "neural_time_ms": float(checkpoint["neural_time_ms"]), "state": mode_state,
        })
        self.store.record_states_atomically(records)
        if flushed_window_sha256 is not None:
            self._window = None
        self.persistence_mode = target_mode
        self._mode_is_explicit = True
        return mode_state

    def export_observability_state(self) -> dict:
        """Checkpoint the bounded unfinished window; completed windows commit with the checkpoint."""
        return {"policy": "flynn.significant-observation.v2",
                "sampling_window_ms": self.sampling_window_ms,
                "persistence_mode": self.persistence_mode,
                "pending_window": self._window}

    def restore_observability_state(self, state: dict | None) -> None:
        if self.sampling_window_ms is None:
            if self.persistence_mode == "sampled":
                raise ValueError("sampled persistence has no configured sampling window")
            if state is not None and state.get("persistence_mode", "dense") != "dense":
                raise ValueError("sampled checkpoint cannot be restored without its sampling window")
            return
        if state is None:
            if self.persistence_mode == "sampled":
                raise ValueError("sampled checkpoint is missing its observation cursor")
            self._window = None
            self._ready_windows.clear()
            return
        if (state.get("policy") != "flynn.significant-observation.v2"
                or float(state.get("sampling_window_ms", -1)) != self.sampling_window_ms):
            raise ValueError("checkpoint observation policy differs from the active sampled writer")
        window = state.get("pending_window")
        if window is not None:
            if (not isinstance(window, dict) or int(window.get("frame_count", -1)) < 1
                    or int(window.get("end_sequence", -1)) < int(window.get("start_sequence", 0))
                    or int(window.get("end_tick", -1)) <= int(window.get("start_tick", -1))
                    or len(window.get("input_hash_chain_sha256", "")) != 64):
                raise ValueError("checkpoint pending neural observation window is invalid")
        saved_mode = state.get(
            "persistence_mode",
            "sampled" if window is not None else self.persistence_mode,
        )
        if saved_mode not in self.PERSISTENCE_MODES:
            raise ValueError("checkpoint persistence mode is invalid")
        if not self._mode_is_explicit and saved_mode != self.persistence_mode:
            # A previous sampled checkpoint may have a pending window before
            # its first aggregate row. Its hash-bound sidecar is the evidence.
            if saved_mode == "sampled" and isinstance(window, dict):
                self.persistence_mode = "sampled"
            else:
                raise ValueError("legacy checkpoint mode cannot be inferred safely")
        if saved_mode != self.persistence_mode:
            mode_record = self.store.latest_component_state(self.PERSISTENCE_MODE_COMPONENT)
            mode_state = mode_record["state"] if mode_record else {}
            checkpoint_record = self.store.active_checkpoint()
            checkpoint_state = checkpoint_record["state"] if checkpoint_record else {}
            if (mode_state.get("mode") != self.persistence_mode
                    or mode_state.get("episode_id") != self.aggregator.episode_id
                    or mode_state.get("causal_generation_id") != self.causal_generation_id
                    or mode_state.get("effective_after_checkpoint_state_id")
                        != (self.store.active_causal_generation() or {}).get("checkpoint_state_id")
                    or mode_state.get("effective_after_checkpoint_sha256") != checkpoint_state.get("checkpoint_sha256")
                    or int(mode_state.get("effective_after_tick", -1)) != int(checkpoint_state.get("neural_tick", -2))):
                raise ValueError("checkpoint/mode difference has no matching post-checkpoint transition record")
            flushed_hash = mode_state.get("flushed_window_sha256")
            if self.persistence_mode == "dense":
                if window is not None and self._state_digest(window) != flushed_hash:
                    raise ValueError("sampled window was not atomically closed by the dense-mode transition")
                window = None
            elif window is not None or flushed_hash is not None:
                raise ValueError("dense-to-sampled transition checkpoint must not carry a closed sample window")
        self._window = window if self.persistence_mode == "sampled" else None
        self._ready_windows.clear()

    def restore_checkpoint_cursor(self, next_sequence: int, tick: int, dt_ms: float) -> None:
        if next_sequence < 0 or tick < 0 or not math.isfinite(dt_ms) or dt_ms <= 0:
            raise ValueError("checkpoint observation cursor is invalid")
        if next_sequence == 0:
            return
        checkpoint_time = tick * dt_ms
        if self.aggregator._last_sequence is None:
            self.aggregator.restore_cursor(next_sequence - 1, checkpoint_time)
        elif self.aggregator._last_sequence > next_sequence - 1:
            raise ValueError("durable observation cursor is beyond the paired checkpoint")
        else:
            self.aggregator._last_sequence = next_sequence - 1
            self.aggregator._last_time_ms = checkpoint_time
