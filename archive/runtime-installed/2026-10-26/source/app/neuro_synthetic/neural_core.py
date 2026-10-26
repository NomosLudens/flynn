"""Bind the real LIF engine to Flynn's existing frame pipeline and SQLite."""

from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from .aggregator import NeuralActivityFrame, SpikeCount
from .lif_engine import LIFEngine, LIFParameters, MODEL_ID, PARAMETERS
from .pipeline import NeuralActivityPipeline
from .signed_connectome import SignedConnectome


CORE_ID = "flynn-neural-core-python-v1"
CHECKPOINT_COMPONENT = "lif_core_checkpoint"
# The 2026-10-19 first-residence checkpoint fingerprint included sqlite_store.py
# even though that module is persistence plumbing, not model behavior. This
# exact legacy digest is accepted only while the neural-source bundle remains
# byte-identical to the verified packaged baseline below.
LEGACY_PERSISTENCE_MODEL_SHA256 = "e2c1a52274acee4c6959aec6c1befd982ac5cfbcb0df8e87e6a928dbdf791779"
# Attested successor checkpoint made with the same neural dynamics but a
# different observation-pipeline fingerprint.
LEGACY_OBSERVATION_MODEL_SHA256 = "82be39f3c81ff33248418ae97946a3c13de0972d7e75f9c7bf00c5e70a52766f"
LEGACY_NEURAL_DYNAMICS_SHA256 = "ca078196b52dd2504e4e4faeb283ac32519bdc5caed6fee61050a406bd8590f2"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _model_sha256() -> str:
    # The approved sampling change modifies persistence only. Preserve the
    # installed model identity while the dynamics/transducer bundle remains
    # byte-identical, so existing checkpoints and code rollback stay valid.
    if _legacy_neural_dynamics_sha256() == LEGACY_NEURAL_DYNAMICS_SHA256:
        return LEGACY_OBSERVATION_MODEL_SHA256
    digest = hashlib.sha256()
    package_dir = Path(__file__).parent
    for filename in (
        "lif_engine.py", "signed_connectome.py",
        "aggregator.py", "pipeline.py",
        "visual_light_transducer.py", "proprioceptive_transducer.py", "descending_readout.py",
    ):
        path = package_dir / filename
        digest.update(path.name.encode("utf-8") + b"\0")
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _legacy_neural_dynamics_sha256() -> str:
    """Fingerprint dynamics and transducers for the attested legacy checkpoint.

    The old checkpoint's model hash also included pipeline.py. That file is
    persistence/observation plumbing, so a lossless sampling change must not
    invalidate the neural state when every dynamics-bearing module is byte
    identical to the installed baseline.
    """
    digest = hashlib.sha256()
    package_dir = Path(__file__).parent
    for filename in (
        "lif_engine.py", "signed_connectome.py", "aggregator.py",
        "visual_light_transducer.py",
        "proprioceptive_transducer.py", "descending_readout.py",
    ):
        path = package_dir / filename
        digest.update(path.name.encode("utf-8") + b"\0")
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _config_sha256(parameters: LIFParameters) -> str:
    payload = {"model_id": MODEL_ID, **parameters.__dict__, "delay_slots": parameters.delay_steps + 1,
               "method": "brian2-linear-equivalent", "dtype": "float64", "schedule": [
                   "groups", "thresholds", "synapses", "resets",
               ]}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class NeuralCore:
    """Produce provenance-bound frames from the complete approved CSR graph."""

    def __init__(
        self,
        *,
        connectome: SignedConnectome,
        pipeline: NeuralActivityPipeline,
        parameters: LIFParameters = LIFParameters(),
        episode_id: str,
    ):
        if not episode_id:
            raise ValueError("episode_id is required")
        if parameters != PARAMETERS:
            raise ValueError("NeuralCore runs only the approved Gate 02 LIF parameters")
        if (pipeline.aggregator.dataset_version != "fafb-v783"
                or pipeline.aggregator.mapping_sha256 != connectome.mapping_sha256
                or pipeline.aggregator.manifest_sha256 != connectome.manifest_sha256):
            raise ValueError("pipeline provenance must exactly match the loaded approved connectome")
        if len(pipeline.aggregator._root_to_index) != len(connectome.root_ids):
            raise ValueError("pipeline root map size differs from the connectome")
        if any(int(connectome.root_ids[index]) != root for root, index in pipeline.aggregator._root_to_index.items()):
            raise ValueError("pipeline root map order differs from the canonical connectome map")

        self.connectome = connectome
        self.pipeline = pipeline
        self.episode_id = episode_id
        self.parameters = parameters
        self.engine = LIFEngine(connectome, parameters)
        self.model_sha256 = _model_sha256()
        self._legacy_model_compatible = (
            _legacy_neural_dynamics_sha256() == LEGACY_NEURAL_DYNAMICS_SHA256
        )
        self.config_sha256 = _config_sha256(parameters)
        latest = pipeline.store.latest_component_state(NeuralActivityPipeline.COMPONENT)
        if latest and latest["state"].get("episode_id") == episode_id:
            state = latest["state"]
            if state.get("dataset_version") != "fafb-v783":
                raise ValueError("persisted neural frames use another dataset")
            self._next_sequence = int(state["sequence"]) + 1
        else:
            self._next_sequence = 0
        self._faulted = False
        self.last_frame_metrics: dict[str, float | int] = {}

    def advance_frame(self, *, steps: int = 100,
                      external_input: dict[str, Any] | None = None) -> Any:
        """Advance a fixed frame window and persist its computed spike deltas.

        An empty spike list is a valid, persisted observation. No stimulus or
        artificial activity is introduced by this method.
        """
        if isinstance(steps, bool) or not isinstance(steps, int) or steps <= 0:
            raise ValueError("a neural frame must contain a positive integer number of ticks")
        if self._faulted:
            raise RuntimeError("core is faulted after a persistence error; restore a durable checkpoint before continuing")
        external_indices = None
        external_g_increment: float | np.ndarray = 0.0
        stimulus = None
        if external_input is not None:
            stimulus = {
                key: value for key, value in external_input.items()
                if key not in {"compact_indices", "root_ids", "g_increment_by_target"}
            }
            external_indices = np.asarray(external_input.get("compact_indices"), dtype=np.int64)
            external_roots = np.asarray(external_input.get("root_ids"), dtype=np.uint64)
            if "g_increment_by_target" in external_input:
                external_g_increment = np.asarray(external_input["g_increment_by_target"], dtype=np.float64)
            else:
                external_g_increment = float(external_input.get("g_increment_per_tick", 0.0))
            if stimulus.get("connectome_sha256") != self.connectome.matrix_sha256:
                raise ValueError("sensory transducer is bound to another signed connectome")
            if external_indices.shape != (int(stimulus.get("target_count", -1)),):
                raise ValueError("sensory transducer target count differs from its index list")
            if (np.any(external_indices < 0) or np.any(external_indices >= len(self.connectome.root_ids))
                    or len(np.unique(external_indices)) != external_indices.size):
                raise ValueError("sensory compact indices must be unique and in the canonical CSR population")
            if external_roots.shape != external_indices.shape or not np.array_equal(
                self.connectome.root_ids[external_indices], external_roots
            ):
                raise ValueError("sensory root IDs do not match the active canonical CSR mapping")
            increments = np.asarray(external_g_increment, dtype=np.float64)
            if increments.ndim not in (0, 1) or (increments.ndim == 1 and increments.shape != external_indices.shape):
                raise ValueError("sensory conductance values must be scalar or aligned to the target indices")
            if not np.isfinite(increments).all() or np.any(increments < 0):
                raise ValueError("sensory conductance values must be finite and non-negative")
            if stimulus.get("calibration_status") != "INSTRUMENTAL_SYNTHETIC_NOT_BIOPHYSICAL":
                raise ValueError("external environmental input must declare its synthetic provenance")
            supplied_hash = stimulus.get("input_sha256")
            unsigned_descriptor = {key: value for key, value in stimulus.items() if key != "input_sha256"}
            expected_hash = hashlib.sha256(
                json.dumps(unsigned_descriptor, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
            ).hexdigest()
            if supplied_hash != expected_hash:
                raise ValueError("sensory descriptor SHA-256 does not match its declared input")
        frame_wall_start = time.perf_counter()
        start_tick = self.engine.tick
        engine_start = time.perf_counter()
        self.engine.advance(
            steps,
            external_indices=external_indices,
            external_g_increment=external_g_increment,
        )
        engine_elapsed_ms = (time.perf_counter() - engine_start) * 1000.0
        end_tick = self.engine.tick
        frame_build_start = time.perf_counter()
        sparse_counts = tuple(
            SpikeCount(compact_index=index, root_id=int(self.connectome.root_ids[index]), count=count)
            for index, count in self.engine.sparse_frame_counts()
        )
        frame = NeuralActivityFrame(
            episode_id=self.episode_id,
            dataset_version="fafb-v783",
            manifest_sha256=self.connectome.manifest_sha256,
            mapping_sha256=self.connectome.mapping_sha256,
            sequence=self._next_sequence,
            neural_time_ms=end_tick * self.parameters.dt_ms,
            spikes=sparse_counts,
            core_id=CORE_ID,
            model_sha256=self.model_sha256,
            config_sha256=self.config_sha256,
            connectome_sha256=self.connectome.matrix_sha256,
            start_tick=start_tick,
            end_tick=end_tick,
            dt_ms=self.parameters.dt_ms,
            stimulus=stimulus,
        )
        frame_build_elapsed_ms = (time.perf_counter() - frame_build_start) * 1000.0
        persistence_start = time.perf_counter()
        try:
            observation = self.pipeline.process(
                frame,
                occurred_at_utc=datetime.now(timezone.utc).isoformat(),
            )
        except Exception:
            self._faulted = True
            raise
        persistence_elapsed_ms = (time.perf_counter() - persistence_start) * 1000.0
        drain_start = time.perf_counter()
        self.engine.drain_frame_counts()
        self._next_sequence += 1
        drain_elapsed_ms = (time.perf_counter() - drain_start) * 1000.0
        self.last_frame_metrics = {
            "steps": steps,
            "lif_engine_ms": engine_elapsed_ms,
            "frame_build_ms": frame_build_elapsed_ms,
            "aggregator_sqlite_ms": persistence_elapsed_ms,
            "frame_drain_ms": drain_elapsed_ms,
            "total_ms": (time.perf_counter() - frame_wall_start) * 1000.0,
        }
        return observation

    def save_checkpoint(self, checkpoint_dir: str | Path) -> dict[str, Any]:
        """Atomically write numerical arrays and append their hash to SQLite."""
        state = self.engine.export_state()
        checkpoint_dir = Path(checkpoint_dir).resolve()
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        episode_tag = hashlib.sha256(self.episode_id.encode("utf-8")).hexdigest()[:12]
        filename = f"lif-{episode_tag}-tick-{self.engine.tick}-{uuid.uuid4().hex}.npz"
        destination = checkpoint_dir / filename
        temporary = checkpoint_dir / f".{filename}.tmp"
        try:
            with temporary.open("wb") as output:
                np.savez(
                    output,
                    state_version=np.asarray([state["state_version"]], dtype=np.uint32),
                    tick=np.asarray([state["tick"]], dtype=np.uint64),
                    v=state["v"],
                    g=state["g"],
                    refractory_until_tick=state["refractory_until_tick"],
                    delay_buffer=state["delay_buffer"],
                    frame_spike_counts=state["frame_spike_counts"],
                )
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, destination)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise

        checkpoint_sha256 = _sha256_file(destination)
        persisted = {
            "episode_id": self.episode_id,
            "dataset_version": "fafb-v783",
            "mapping_sha256": self.connectome.mapping_sha256,
            "manifest_sha256": self.connectome.manifest_sha256,
            "connectome_sha256": self.connectome.matrix_sha256,
            "model_sha256": self.model_sha256,
            "config_sha256": self.config_sha256,
            "core_id": CORE_ID,
            "tick": self.engine.tick,
            "neural_time_ms": self.engine.neural_time_ms,
            "next_sequence": self._next_sequence,
            "checkpoint_file": str(destination),
            "checkpoint_sha256": checkpoint_sha256,
            "checkpoint_bytes": destination.stat().st_size,
            "state_version": self.engine.STATE_VERSION,
            "dtype": "float64/int64/uint32",
        }
        event_id = f"{self.episode_id}:lif-checkpoint:{self.engine.tick}:{checkpoint_sha256[:16]}"
        self.pipeline.store.record_state(
            state_id=event_id,
            event_id=event_id,
            component=CHECKPOINT_COMPONENT,
            occurred_at_utc=datetime.now(timezone.utc).isoformat(),
            state=persisted,
            neural_time_ms=self.engine.neural_time_ms,
        )
        return persisted

    def export_runtime_state(self) -> dict[str, Any]:
        """Return a drained, provenance-bound state for an atomic outer checkpoint."""
        if self._faulted:
            raise RuntimeError("cannot checkpoint a faulted neural core")
        return {
            "episode_id": self.episode_id,
            "dataset_version": "fafb-v783",
            "mapping_sha256": self.connectome.mapping_sha256,
            "manifest_sha256": self.connectome.manifest_sha256,
            "connectome_sha256": self.connectome.matrix_sha256,
            "model_sha256": self.model_sha256,
            "config_sha256": self.config_sha256,
            "core_id": CORE_ID,
            "next_sequence": self._next_sequence,
            "observability_state": self.pipeline.export_observability_state(),
            "engine_state": self.engine.export_state(),
        }

    def restore_runtime_state(self, runtime_state: dict[str, Any], *, validate_latest_frame: bool = True) -> None:
        """Restore state from a verified enclosing checkpoint at the frame cursor."""
        expected = {
            "episode_id": self.episode_id,
            "dataset_version": "fafb-v783",
            "mapping_sha256": self.connectome.mapping_sha256,
            "manifest_sha256": self.connectome.manifest_sha256,
            "connectome_sha256": self.connectome.matrix_sha256,
            "config_sha256": self.config_sha256,
            "core_id": CORE_ID,
        }
        saved_model_sha = runtime_state.get("model_sha256")
        model_matches = self.accepts_model_sha256(saved_model_sha)
        if any(runtime_state.get(key) != value for key, value in expected.items()) or not model_matches:
            raise ValueError("integrated checkpoint neural provenance does not match the active core")
        next_sequence = runtime_state.get("next_sequence")
        if isinstance(next_sequence, bool) or not isinstance(next_sequence, int) or next_sequence < 0:
            raise ValueError("integrated checkpoint sequence cursor is invalid")
        engine_state = runtime_state.get("engine_state")
        if not isinstance(engine_state, dict):
            raise ValueError("integrated checkpoint has no neural engine state")

        if validate_latest_frame:
            frame_state = self.pipeline.store.latest_component_state(NeuralActivityPipeline.COMPONENT)
            if frame_state and frame_state["state"].get("episode_id") == self.episode_id:
                saved = frame_state["state"]
                if saved.get("observation_kind") == "NEURAL_ACTIVITY_WINDOW":
                    if (int(saved.get("end_tick", -1)) > int(engine_state.get("tick", -2))
                            or int(saved.get("end_sequence", saved.get("sequence", -1))) >= next_sequence):
                        raise ValueError("integrated checkpoint precedes its durable neural observation window")
                elif (saved.get("end_tick") != engine_state.get("tick")
                        or int(saved.get("sequence", -1)) + 1 != next_sequence):
                    observation_state = runtime_state.get("observability_state")
                    window = (observation_state.get("pending_window")
                              if isinstance(observation_state, dict) else None)
                    frame_sequence = int(saved.get("sequence", -1))
                    frame_end_tick = int(saved.get("end_tick", -1))
                    window_covers_gap = (
                        isinstance(observation_state, dict)
                        and observation_state.get("policy") == "flynn.significant-observation.v2"
                        and isinstance(window, dict)
                        and int(window.get("start_sequence", -1)) == frame_sequence + 1
                        and int(window.get("end_sequence", -1)) + 1 == next_sequence
                        and int(window.get("start_tick", -1)) == frame_end_tick
                        and int(window.get("end_tick", -1)) == int(engine_state.get("tick", -2))
                        and int(window.get("frame_count", -1))
                            == int(window.get("end_sequence", -1)) - int(window.get("start_sequence", 0)) + 1
                        and abs(float(window.get("start_neural_time_ms", -1))
                                - float(saved.get("neural_time_ms", -2))) <= 1e-8
                        and abs(float(window.get("end_neural_time_ms", -1))
                                - int(engine_state.get("tick", -2)) * float(window.get("dt_ms", 0))) <= 1e-8
                        and all(window.get(key) == runtime_state.get(key) for key in (
                            "dataset_version", "manifest_sha256", "mapping_sha256", "core_id",
                            "model_sha256", "config_sha256", "connectome_sha256",
                        ))
                        and len(str(window.get("input_hash_chain_sha256", ""))) == 64
                    )
                    if not window_covers_gap:
                        raise ValueError("integrated checkpoint does not match the durable neural frame cursor")
            elif next_sequence != 0:
                # A recovery generation can begin at a checkpoint whose last
                # durable neural observation belongs to its parent generation.
                # In sampled mode, the checkpoint's hashed pending window is
                # the durable cursor for frames since the last aggregate; use
                # it only when it terminates exactly at the paired checkpoint.
                observation_state = runtime_state.get("observability_state")
                window = (observation_state.get("pending_window")
                          if isinstance(observation_state, dict) else None)
                if (not isinstance(observation_state, dict)
                        or observation_state.get("policy") != "flynn.significant-observation.v2"
                        or not isinstance(window, dict)
                        or int(window.get("end_tick", -1)) != int(engine_state.get("tick", -2))
                        or int(window.get("end_sequence", -1)) + 1 != next_sequence
                        or abs(float(window.get("end_neural_time_ms", -1))
                               - int(engine_state.get("tick", -2)) * float(window.get("dt_ms", 0))) > 1e-8):
                    raise ValueError("integrated checkpoint has no same-generation frame cursor or exact sampled parent cursor")

        self.engine.restore_state(engine_state)
        self._next_sequence = next_sequence
        self.pipeline.restore_observability_state(runtime_state.get("observability_state"))
        self.pipeline.restore_checkpoint_cursor(
            next_sequence, int(engine_state["tick"]), float(self.parameters.dt_ms),
        )
        self._faulted = False

    def accepts_model_sha256(self, value: Any) -> bool:
        """Accept current identity or attested pre-sampling persistence fingerprints."""
        return value == self.model_sha256 or (
            value in {LEGACY_PERSISTENCE_MODEL_SHA256, LEGACY_OBSERVATION_MODEL_SHA256}
            and self._legacy_model_compatible
        )

    def restore_latest_checkpoint(self) -> dict[str, Any] | None:
        """Verify checkpoint file, source/config identity and frame cursor before restore."""
        latest = self.pipeline.store.latest_component_state(CHECKPOINT_COMPONENT)
        if latest is None:
            return None
        metadata = latest["state"]
        expected = {
            "episode_id": self.episode_id,
            "dataset_version": "fafb-v783",
            "mapping_sha256": self.connectome.mapping_sha256,
            "manifest_sha256": self.connectome.manifest_sha256,
            "connectome_sha256": self.connectome.matrix_sha256,
            "model_sha256": self.model_sha256,
            "config_sha256": self.config_sha256,
            "core_id": CORE_ID,
            "state_version": self.engine.STATE_VERSION,
        }
        if any(metadata.get(key) != value for key, value in expected.items()):
            raise ValueError("latest SQLite checkpoint provenance does not match the active neural core")
        path = Path(metadata["checkpoint_file"]).resolve()
        if not path.is_file() or _sha256_file(path) != metadata.get("checkpoint_sha256"):
            raise ValueError("checkpoint artifact is missing or its SHA-256 does not match SQLite")
        pipeline_state = self.pipeline.store.latest_component_state(NeuralActivityPipeline.COMPONENT)
        persisted_sequence = -1
        if pipeline_state and pipeline_state["state"].get("episode_id") == self.episode_id:
            persisted_sequence = int(pipeline_state["state"]["sequence"])
            if (pipeline_state["state"].get("end_tick") != metadata["tick"]
                    or persisted_sequence + 1 != metadata["next_sequence"]):
                raise ValueError("neural frame cursor and checkpoint tick/sequence do not agree")
        elif metadata["next_sequence"] != 0:
            raise ValueError("checkpoint has frames but SQLite has no matching durable frame cursor")

        with np.load(path, allow_pickle=False) as archive:
            state = {
                "state_version": int(archive["state_version"][0]),
                "tick": int(archive["tick"][0]),
                "v": archive["v"],
                "g": archive["g"],
                "refractory_until_tick": archive["refractory_until_tick"],
                "delay_buffer": archive["delay_buffer"],
                "frame_spike_counts": archive["frame_spike_counts"],
            }
            if state["tick"] != metadata["tick"]:
                raise ValueError("checkpoint file tick differs from its SQLite record")
            self.engine.restore_state(state)
        self._next_sequence = int(metadata["next_sequence"])
        self._faulted = False
        return metadata
