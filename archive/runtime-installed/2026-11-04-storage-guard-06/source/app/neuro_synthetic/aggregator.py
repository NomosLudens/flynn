"""Provenance-bound, observational activity aggregation for Flynn.

The aggregator maps real core output and summarizes counts. It cannot mutate
neural state, choose behavior, inject input, or produce body actuation.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from typing import Iterable


@dataclass(frozen=True)
class SpikeCount:
    compact_index: int
    root_id: int
    count: int


@dataclass(frozen=True)
class NeuralActivityFrame:
    episode_id: str
    dataset_version: str
    manifest_sha256: str
    mapping_sha256: str
    sequence: int
    neural_time_ms: float
    spikes: tuple[SpikeCount, ...]
    core_id: str | None = None
    model_sha256: str | None = None
    config_sha256: str | None = None
    connectome_sha256: str | None = None
    start_tick: int | None = None
    end_tick: int | None = None
    dt_ms: float | None = None
    stimulus: dict | None = None


@dataclass(frozen=True)
class ActivityObservation:
    episode_id: str
    dataset_version: str
    sequence: int
    neural_time_ms: float
    mapped_spikes: tuple[SpikeCount, ...]
    active_neuron_count: int
    total_spikes: int
    input_sha256: str
    core_id: str | None = None
    model_sha256: str | None = None
    config_sha256: str | None = None
    connectome_sha256: str | None = None
    start_tick: int | None = None
    end_tick: int | None = None
    dt_ms: float | None = None
    stimulus: dict | None = None


class NeuralActivityAggregator:
    """Validate/map sparse core frames and emit descriptive observations only."""

    def __init__(
        self,
        *,
        episode_id: str,
        dataset_version: str,
        manifest_sha256: str,
        mapping_sha256: str,
        root_ids: Iterable[int],
    ):
        roots = tuple(root_ids)
        if not episode_id or not dataset_version or not roots:
            raise ValueError("episode, dataset version, and root IDs are required")
        if len(set(roots)) != len(roots):
            raise ValueError("root IDs must be unique")
        if any(not isinstance(root, int) or isinstance(root, bool) or root <= 0 for root in roots):
            raise ValueError("root IDs must be positive integers")
        for label, value in (("manifest", manifest_sha256), ("mapping", mapping_sha256)):
            if len(value) != 64 or any(char not in "0123456789abcdef" for char in value.lower()):
                raise ValueError(f"{label} hash must be a SHA-256 hex digest")
        self.episode_id = episode_id
        self.dataset_version = dataset_version
        self.manifest_sha256 = manifest_sha256
        self.mapping_sha256 = mapping_sha256
        self._root_to_index = {root_id: index for index, root_id in enumerate(roots)}
        self._last_sequence: int | None = None
        self._last_time_ms: float | None = None

    def aggregate(self, frame: NeuralActivityFrame) -> ActivityObservation:
        if (frame.episode_id != self.episode_id
                or frame.dataset_version != self.dataset_version
                or frame.manifest_sha256 != self.manifest_sha256
                or frame.mapping_sha256 != self.mapping_sha256):
            raise ValueError("activity frame provenance does not match this aggregator")
        if (isinstance(frame.sequence, bool) or not isinstance(frame.sequence, int)
                or frame.sequence < 0 or not math.isfinite(frame.neural_time_ms)
                or frame.neural_time_ms < 0):
            raise ValueError("sequence and neural time must be finite and non-negative")
        if self._last_sequence is not None and frame.sequence != self._last_sequence + 1:
            raise ValueError("activity frame sequence is discontinuous")
        if self._last_time_ms is not None and frame.neural_time_ms < self._last_time_ms:
            raise ValueError("neural time cannot move backwards")

        core_metadata = (
            frame.core_id, frame.model_sha256, frame.config_sha256,
            frame.connectome_sha256, frame.start_tick, frame.end_tick, frame.dt_ms,
        )
        if any(value is not None for value in core_metadata):
            if not all(value is not None for value in core_metadata):
                raise ValueError("core frames must provide complete model, connectome, and tick provenance")
            if not isinstance(frame.core_id, str) or not frame.core_id:
                raise ValueError("core_id must be a non-empty string")
            for label, value in (
                ("model", frame.model_sha256),
                ("config", frame.config_sha256),
                ("connectome", frame.connectome_sha256),
            ):
                if len(value) != 64 or any(char not in "0123456789abcdef" for char in value.lower()):
                    raise ValueError(f"{label} hash must be a SHA-256 hex digest")
            for label, value in (("start_tick", frame.start_tick), ("end_tick", frame.end_tick)):
                if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                    raise ValueError(f"{label} must be a non-negative integer")
            if frame.end_tick <= frame.start_tick:
                raise ValueError("core frame end_tick must be greater than start_tick")
            if (isinstance(frame.dt_ms, bool) or not isinstance(frame.dt_ms, (int, float))
                    or not math.isfinite(frame.dt_ms) or frame.dt_ms <= 0):
                raise ValueError("core frame dt_ms must be finite and positive")
            expected_time = frame.end_tick * frame.dt_ms
            if abs(frame.neural_time_ms - expected_time) > max(1e-9, frame.dt_ms * 1e-9):
                raise ValueError("core frame neural_time_ms does not match end_tick and dt_ms")

        seen: set[int] = set()
        mapped: list[SpikeCount] = []
        for spike in frame.spikes:
            if (isinstance(spike.compact_index, bool) or not isinstance(spike.compact_index, int)
                    or spike.compact_index < 0 or spike.compact_index >= len(self._root_to_index)):
                raise ValueError("compact index is outside the verified root-ID map")
            if (isinstance(spike.root_id, bool) or not isinstance(spike.root_id, int)
                    or self._root_to_index.get(spike.root_id) != spike.compact_index):
                raise ValueError("root ID and compact index disagree with the verified map")
            if spike.compact_index in seen:
                raise ValueError("frame contains duplicate compact indices")
            if (isinstance(spike.count, bool) or not isinstance(spike.count, int)
                    or spike.count <= 0):
                raise ValueError("sparse frames may contain only positive spike deltas")
            seen.add(spike.compact_index)
            mapped.append(spike)

        payload = {
            "episode_id": frame.episode_id,
            "dataset_version": frame.dataset_version,
            "manifest_sha256": frame.manifest_sha256,
            "mapping_sha256": frame.mapping_sha256,
            "sequence": frame.sequence,
            "neural_time_ms": frame.neural_time_ms,
            "spikes": [asdict(spike) for spike in mapped],
            "stimulus": frame.stimulus,
        }
        if any(value is not None for value in core_metadata):
            payload.update({
                "core_id": frame.core_id,
                "model_sha256": frame.model_sha256,
                "config_sha256": frame.config_sha256,
                "connectome_sha256": frame.connectome_sha256,
                "start_tick": frame.start_tick,
                "end_tick": frame.end_tick,
                "dt_ms": frame.dt_ms,
            })
        input_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        ).hexdigest()
        return ActivityObservation(
            episode_id=frame.episode_id,
            dataset_version=frame.dataset_version,
            sequence=frame.sequence,
            neural_time_ms=frame.neural_time_ms,
            mapped_spikes=tuple(mapped),
            active_neuron_count=len(mapped),
            total_spikes=sum(item.count for item in mapped),
            input_sha256=input_hash,
            core_id=frame.core_id,
            model_sha256=frame.model_sha256,
            config_sha256=frame.config_sha256,
            connectome_sha256=frame.connectome_sha256,
            start_tick=frame.start_tick,
            end_tick=frame.end_tick,
            dt_ms=frame.dt_ms,
            stimulus=frame.stimulus,
        )

    def commit(self, observation: ActivityObservation) -> None:
        """Advance the in-memory cursor only after the caller persists the frame."""
        if observation.episode_id != self.episode_id or observation.dataset_version != self.dataset_version:
            raise ValueError("observation belongs to a different episode or dataset")
        if self._last_sequence is not None and observation.sequence != self._last_sequence + 1:
            raise ValueError("committed observation sequence is discontinuous")
        if self._last_time_ms is not None and observation.neural_time_ms < self._last_time_ms:
            raise ValueError("committed neural time cannot move backwards")
        self._last_sequence = observation.sequence
        self._last_time_ms = observation.neural_time_ms

    def restore_cursor(self, sequence: int, neural_time_ms: float) -> None:
        """Restore the last durable sequence from the SQLite component snapshot."""
        if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
            raise ValueError("restored sequence must be a non-negative integer")
        if not math.isfinite(neural_time_ms) or neural_time_ms < 0:
            raise ValueError("restored neural time must be finite and non-negative")
        if self._last_sequence is not None:
            raise RuntimeError("aggregator cursor is already initialized")
        self._last_sequence = sequence
        self._last_time_ms = neural_time_ms
