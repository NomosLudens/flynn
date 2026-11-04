"""Instrumental synthetic body-state input for the existing LIF V2 core.

FlyWire annotation identifies a sensory/mechanosensory endpoint pool. It does
not claim those cells biologically encode LETHE proprioception. The channel
split and conductance rule here are explicit synthetic engineering choices.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np


class SyntheticProprioceptiveTransducer:
    """Encode one measured LETHE revolute joint's position and velocity."""

    TRANSDUCER_ID = "lethe-joint-position-velocity-g-to-lif-v1"
    JOINT_NAME = "AUDITORY_L"
    ANNOTATION_FILE_SHA256 = "30be6c73975a70c56d930e27911f36455d3886e15abf383b78edd2a5d679e0b6"
    GAIN_G_UNITS_PER_TICK_AT_FULL_SCALE = 0.01
    MAX_SPEED_RAD_PER_SECOND = 1.0

    def __init__(self, manifest_path: str | Path, *, expected_connectome_sha256: str,
                 gain_g_units_per_tick_at_full_scale: float = GAIN_G_UNITS_PER_TICK_AT_FULL_SCALE):
        path = Path(manifest_path)
        raw = path.read_bytes()
        self.manifest_sha256 = hashlib.sha256(raw).hexdigest()
        manifest = json.loads(raw)
        if manifest.get("schema") != "flynn.synthetic_proprioceptive_population.v1":
            raise ValueError("unsupported synthetic proprioceptive population manifest")
        if manifest.get("dataset_version") != "fafb-v783" or manifest.get("annotation_release") != "v2.1.0":
            raise ValueError("synthetic input endpoint map must use the pinned FlyWire v2.1.0 FAFB v783 annotations")
        if (manifest.get("annotation_commit") != "ebd66db2596fcc39c6950fb54ea3efa00f7fe8a0"
                or manifest.get("annotation_file_sha256") != self.ANNOTATION_FILE_SHA256):
            raise ValueError("synthetic input endpoint map annotation provenance differs from the pinned v2.1.0 source")
        if manifest.get("connectome_sha256") != expected_connectome_sha256:
            raise ValueError("synthetic input endpoint map belongs to another signed connectome")
        indices = np.asarray(manifest.get("compact_indices", []), dtype=np.int64)
        roots = np.asarray(manifest.get("root_ids", []), dtype=np.uint64)
        count = int(manifest.get("population_count", -1))
        if count != 2646 or indices.shape != (count,) or roots.shape != (count,):
            raise ValueError("expected 2,646 sensory mechanosensory endpoints excluding 2 explicitly descending cells")
        if np.any(indices < 0) or np.any(np.diff(indices) <= 0) or len(np.unique(roots)) != count:
            raise ValueError("synthetic input endpoints must be unique and canonically ordered")
        digest = hashlib.sha256("".join(
            f"{int(index)}\t{int(root)}\n" for index, root in zip(indices, roots)
        ).encode("ascii")).hexdigest()
        if digest != manifest.get("population_mapping_sha256"):
            raise ValueError("synthetic proprioceptive root-ID/index map hash mismatch")
        channels: dict[str, dict[str, np.ndarray]] = {}
        for name in ("position_positive", "position_negative", "velocity_positive", "velocity_negative"):
            source = manifest.get("channels", {}).get(name, {})
            channel_indices = np.asarray(source.get("compact_indices", []), dtype=np.int64)
            channel_roots = np.asarray(source.get("root_ids", []), dtype=np.uint64)
            if channel_indices.shape != channel_roots.shape or len(channel_indices) != int(source.get("count", -1)):
                raise ValueError(f"invalid synthetic channel map: {name}")
            channels[name] = {"indices": channel_indices, "roots": channel_roots}
        assigned = np.concatenate([value["indices"] for value in channels.values()])
        if len(assigned) != count or len(np.unique(assigned)) != count or not np.array_equal(np.sort(assigned), indices):
            raise ValueError("synthetic channel groups must partition the official annotated endpoint set")
        channel_payload = {
            name: [[int(index), int(root)] for index, root in zip(value["indices"], value["roots"])]
            for name, value in channels.items()
        }
        channel_hash = hashlib.sha256(
            json.dumps(channel_payload, sort_keys=True, separators=(",", ":")).encode("ascii")
        ).hexdigest()
        if channel_hash != manifest.get("channel_mapping_sha256"):
            raise ValueError("synthetic channel assignment hash mismatch")
        gain = float(gain_g_units_per_tick_at_full_scale)
        if not math.isfinite(gain) or gain <= 0 or gain > 0.01:
            raise ValueError("full-scale synthetic LIF conductance gain must be in (0, 0.01]")
        self.compact_indices = indices
        self.root_ids = roots
        self.channels = channels
        self.population_mapping_sha256 = digest
        self.channel_mapping_sha256 = str(manifest["channel_mapping_sha256"])
        self.annotation_sha256 = str(manifest["annotation_file_sha256"])
        self.connectome_sha256 = str(manifest["connectome_sha256"])
        self.canonical_roots_sha256 = str(manifest["canonical_roots_sha256"])
        self.gain = gain

    def transduce(self, body_readout: dict[str, Any], *, neural_boundary_ms: float) -> dict[str, Any]:
        if not isinstance(body_readout, dict):
            raise ValueError("proprioception requires a measured Pinocchio readout")
        if body_readout.get("schema") != "flynn.synthetic_proprioceptive_readout.v1":
            raise ValueError("unsupported physical readout schema")
        if body_readout.get("source") != "PinocchioSigilBody" or not str(body_readout.get("body_model_sha256", "")):
            raise ValueError("proprioceptive input requires a provenance-bound Pinocchio body sample")
        sample_time = float(body_readout.get("time_ms", float("nan")))
        if not math.isfinite(neural_boundary_ms) or abs(sample_time - neural_boundary_ms) > 1e-8:
            raise ValueError("body sample must be from the current neural/world boundary; future or stale state is rejected")
        joint = body_readout.get("joint_state_by_name", {}).get(self.JOINT_NAME)
        if not isinstance(joint, dict):
            raise ValueError(f"Pinocchio readout lacks the configured joint {self.JOINT_NAME}")
        q = float(joint.get("position_rad", float("nan")))
        qdot = float(joint.get("velocity_rad_per_second", float("nan")))
        if not math.isfinite(q) or not math.isfinite(qdot):
            raise ValueError("measured joint state must contain finite radians and radians/second")

        # A continuous revolute joint has no finite position stop in this body
        # model. Use the principal angular displacement from neutral, [-pi,pi].
        q_normalized = math.atan2(math.sin(q), math.cos(q)) / math.pi
        qdot_normalized = float(np.clip(qdot / self.MAX_SPEED_RAD_PER_SECOND, -1.0, 1.0))
        amplitudes = {
            "position_positive": max(q_normalized, 0.0),
            "position_negative": max(-q_normalized, 0.0),
            "velocity_positive": max(qdot_normalized, 0.0),
            "velocity_negative": max(-qdot_normalized, 0.0),
        }
        selected_indices: list[np.ndarray] = []
        selected_roots: list[np.ndarray] = []
        increments: list[np.ndarray] = []
        active_channels: dict[str, dict[str, float | int]] = {}
        for name, amplitude in amplitudes.items():
            if amplitude <= 0:
                continue
            target_indices = self.channels[name]["indices"]
            target_roots = self.channels[name]["roots"]
            selected_indices.append(target_indices)
            selected_roots.append(target_roots)
            increments.append(np.full(target_indices.shape, self.gain * amplitude, dtype=np.float64))
            active_channels[name] = {
                "normalized_magnitude": float(amplitude),
                "target_count": int(target_indices.size),
                "g_increment_per_tick": float(self.gain * amplitude),
            }

        if selected_indices:
            indices = np.concatenate(selected_indices)
            roots = np.concatenate(selected_roots)
            gain_vector = np.concatenate(increments)
            order = np.argsort(indices, kind="stable")
            indices, roots, gain_vector = indices[order], roots[order], gain_vector[order]
        else:
            indices = np.empty(0, dtype=np.int64)
            roots = np.empty(0, dtype=np.uint64)
            gain_vector = np.empty(0, dtype=np.float64)

        if np.any(gain_vector < 0) or not np.isfinite(gain_vector).all() or np.any(gain_vector > self.gain):
            raise ValueError("transducer produced an invalid or out-of-range conductance increment")
        descriptor = {
            "schema": "flynn.synthetic_proprioceptive_lif_input.v1",
            "modality": "synthetic_proprioception",
            "transducer": self.TRANSDUCER_ID,
            "calibration_status": "INSTRUMENTAL_SYNTHETIC_NOT_BIOPHYSICAL",
            "body_readout_schema": body_readout["schema"],
            "body_model_sha256": body_readout["body_model_sha256"],
            "body_checkpoint_id": body_readout.get("body_checkpoint_id"),
            "body_stream_id": body_readout.get("stream_id"),
            "body_stream_sequence": body_readout.get("stream_sequence"),
            "body_sample_sequence": int(body_readout["sequence"]),
            "body_sample_time_ms": sample_time,
            "neural_boundary_time_ms": float(neural_boundary_ms),
            "joint_name": self.JOINT_NAME,
            "joint_q_index": int(joint["q_index"]),
            "joint_qdot_index": int(joint["qdot_index"]),
            "position_reference_rad": 0.0,
            "position_value_rad": q,
            "position_normalized_principal_angle": q_normalized,
            "velocity_value_rad_per_second": qdot,
            "velocity_normalization_limit_rad_per_second": self.MAX_SPEED_RAD_PER_SECOND,
            "velocity_normalized": qdot_normalized,
            "input_units": {"position": "radian", "velocity": "radian_per_second"},
            "referential": "Pinocchio generalized joint coordinates; CENTRAL_EB anchored",
            "normalization": "atan2(sin(q-q_ref),cos(q-q_ref))/pi; clip(qdot/1_rad_s,-1,1)",
            "channel_allocation": "position/velocity sign channels over deterministic official annotated pool; synthetic only",
            "gain_g_units_per_tick_at_full_scale": self.gain,
            "output_units": "nonnegative synthetic LIF conductance units per 0.1 ms tick",
            "target_population": "official sensory/mechanosensory annotation endpoints; no proprioceptive biological function claim",
            "target_population_count": int(self.compact_indices.size),
            "target_count": int(indices.size),
            "target_mapping_sha256": self.population_mapping_sha256,
            "channel_mapping_sha256": self.channel_mapping_sha256,
            "annotation_sha256": self.annotation_sha256,
            "population_manifest_sha256": self.manifest_sha256,
            "connectome_sha256": self.connectome_sha256,
            "canonical_roots_sha256": self.canonical_roots_sha256,
            "active_channels": active_channels,
            "effect": "PROPRIOCEPTIVE_INPUT_APPLIED_TO_LIF" if indices.size else "NO_PHYSICAL_DEVIATION_NO_NEURAL_INPUT",
        }
        descriptor["input_sha256"] = hashlib.sha256(
            json.dumps(descriptor, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        ).hexdigest()
        return {
            **descriptor,
            "compact_indices": indices,
            "root_ids": roots,
            "g_increment_by_target": gain_vector,
        }
