"""Dimensionless calibration adapter for the official visual sensory roots."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np


class VisualLightTransducer:
    """Map world illumination [0,1] to synthetic LIF conductance increments.

    ``g_increment_at_full_light`` is an instrumental calibration value in the
    LIF engine's internal conductance units per neural tick. It is not a
    biological photoreceptor current or an SI light measurement.
    """

    CALIBRATION_ID = "visual-light-g-increment-per-tick-v1"

    def __init__(self, manifest_path: str | Path, *, expected_connectome_sha256: str,
                 g_increment_at_full_light: float = 0.5):
        raw = Path(manifest_path).read_bytes()
        self.manifest_sha256 = hashlib.sha256(raw).hexdigest()
        manifest = json.loads(raw)
        if manifest.get("schema") != "flynn.descending_population.v2":
            raise ValueError("unsupported population manifest")
        if manifest.get("dataset_version") != "fafb-v783" or manifest.get("annotation_release") != "v2.1.0":
            raise ValueError("visual map must use FlyWire v2.1.0 annotations for FAFB v783")
        if manifest.get("connectome_sha256") != expected_connectome_sha256:
            raise ValueError("visual map belongs to another connectome")
        indices = np.asarray(manifest.get("visual_sensory_compact_indices", []), dtype=np.int64)
        roots = np.asarray(manifest.get("visual_sensory_root_ids", []), dtype=np.uint64)
        if indices.shape != (11118,) or roots.shape != (11118,) or len(np.unique(indices)) != 11118:
            raise ValueError("expected 11118 unique official R1-6/R7/R8 visual sensory roots")
        if np.any(indices < 0) or np.any(np.diff(indices) <= 0):
            raise ValueError("visual sensory roots must be ordered by canonical compact index")
        expected_mapping = hashlib.sha256(
            "".join(f"{int(index)}\t{int(root)}\n" for index, root in zip(indices, roots)).encode("ascii")
        ).hexdigest()
        if expected_mapping != manifest.get("visual_sensory_mapping_sha256"):
            raise ValueError("visual root-ID/index manifest hash mismatch")
        if np.any(indices >= int(manifest.get("canonical_neuron_count", 0))):
            raise ValueError("visual compact index exceeds canonical population")
        if not np.isfinite(g_increment_at_full_light) or g_increment_at_full_light <= 0:
            raise ValueError("full-light conductance calibration must be finite and positive")
        self.compact_indices = indices
        self.root_ids = roots
        self.g_increment_at_full_light = float(g_increment_at_full_light)
        self.annotation_sha256 = str(manifest["annotation_file_sha256"])
        self.population_mapping_sha256 = str(manifest["visual_sensory_mapping_sha256"])
        self.connectome_sha256 = str(manifest["connectome_sha256"])

    def transduce(self, illumination: float) -> dict[str, Any]:
        if isinstance(illumination, bool) or not isinstance(illumination, (int, float)):
            raise ValueError("world illumination must be numeric")
        value = float(illumination)
        if not np.isfinite(value) or not 0.0 <= value <= 1.0:
            raise ValueError("world illumination must be finite and normalized to [0, 1]")
        increment = value * self.g_increment_at_full_light
        descriptor = {
            "modality": "visible_light_calibration",
            "illumination_normalized": value,
            "input_units": "dimensionless_normalized_world_value",
            "transducer": self.CALIBRATION_ID,
            "g_increment_per_tick": increment,
            "output_units": "synthetic_LIF_g_units_per_tick",
            "target_population": "FlyWire-v2.1.0-sensory-visual-R1-6-R7-R8",
            "target_count": int(self.compact_indices.size),
            "target_mapping_sha256": self.population_mapping_sha256,
            "annotation_sha256": self.annotation_sha256,
            "manifest_sha256": self.manifest_sha256,
            "connectome_sha256": self.connectome_sha256,
            "calibration_status": "INSTRUMENTAL_SYNTHETIC_NOT_BIOPHYSICAL",
        }
        descriptor["input_sha256"] = hashlib.sha256(
            json.dumps(descriptor, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        ).hexdigest()
        return {
            **descriptor,
            "compact_indices": self.compact_indices,
            "root_ids": self.root_ids,
        }
