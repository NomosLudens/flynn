"""Deterministic V2 readout for the official FlyWire v2.1.0 DN population.

The manifest is built from the pinned annotation table and the canonical
FAFB-v783 root map.  This module only selects measured DN spike counts; it
does not create activity or choose an action.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np


class DescendingReadoutV2:
    def __init__(self, manifest_path: str | Path, *, expected_connectome_sha256: str):
        path = Path(manifest_path)
        raw = path.read_bytes()
        self.manifest_sha256 = hashlib.sha256(raw).hexdigest()
        manifest = json.loads(raw)
        if manifest.get("schema") != "flynn.descending_population.v2":
            raise ValueError("unsupported descending population manifest")
        if manifest.get("dataset_version") != "fafb-v783":
            raise ValueError("descending population is not bound to FAFB v783")
        if manifest.get("annotation_release") != "v2.1.0":
            raise ValueError("descending population is not bound to FlyWire annotations v2.1.0")
        if manifest.get("connectome_sha256") != expected_connectome_sha256:
            raise ValueError("descending population manifest belongs to another connectome")

        root_ids = np.asarray(manifest.get("root_ids", []), dtype=np.uint64)
        compact = np.asarray(manifest.get("compact_indices", []), dtype=np.int64)
        if root_ids.shape != (1303,) or compact.shape != (1303,):
            raise ValueError("official V2 motor population must contain exactly 1303 roots")
        if len(np.unique(root_ids)) != 1303 or len(np.unique(compact)) != 1303:
            raise ValueError("descending root IDs and compact indices must be unique")
        if np.any(compact < 0) or np.any(np.diff(compact) <= 0):
            raise ValueError("descending population must be ordered by canonical compact index")
        expected_mapping = hashlib.sha256(
            "".join(f"{int(index)}\t{int(root)}\n" for index, root in zip(compact, root_ids)).encode("ascii")
        ).hexdigest()
        if expected_mapping != manifest.get("population_mapping_sha256"):
            raise ValueError("descending root-ID/index manifest hash mismatch")
        self.root_ids = root_ids
        self.compact_indices = compact
        self.source_sha256 = str(manifest["annotation_file_sha256"])
        self.mapping_sha256 = str(manifest["population_mapping_sha256"])
        self.connectome_sha256 = str(manifest["connectome_sha256"])
        self.neuron_count = int(manifest["canonical_neuron_count"])

    def extract(self, mapped_spikes: list[dict[str, Any]] | tuple[Any, ...]) -> dict[str, Any]:
        """Select actual frame deltas and return a sparse, provenance-bound DN vector."""
        by_index = {int(index): pos for pos, index in enumerate(self.compact_indices)}
        counts = np.zeros(1303, dtype=np.uint32)
        seen: set[int] = set()
        for item in mapped_spikes:
            index = int(item["compact_index"])
            root_id = int(item["root_id"])
            count = int(item["count"])
            if index in seen or count <= 0:
                raise ValueError("frame has duplicate or invalid spike deltas")
            seen.add(index)
            pos = by_index.get(index)
            if pos is not None:
                if int(self.root_ids[pos]) != root_id:
                    raise ValueError("DN root ID does not match its canonical CSR index")
                if count > np.iinfo(np.uint32).max:
                    raise OverflowError("DN frame count exceeds uint32")
                counts[pos] = count
        return {
            "population": "flywire-v2.1.0-descending-1303",
            "annotation_sha256": self.source_sha256,
            "mapping_sha256": self.mapping_sha256,
            "manifest_sha256": self.manifest_sha256,
            "connectome_sha256": self.connectome_sha256,
            "active_neurons": int(np.count_nonzero(counts)),
            "total_spikes": int(counts.sum(dtype=np.uint64)),
            "compact_indices": self.compact_indices.tolist(),
            "spike_counts": counts.tolist(),
            "effect": "MEASURED_DN_READOUT_ONLY",
        }

    def full_population_delta(self, readout: dict[str, Any]) -> np.ndarray:
        """Return body adapter input, with all non-DN neurons fixed at zero."""
        if readout.get("manifest_sha256") != self.manifest_sha256:
            raise ValueError("readout manifest hash differs from active mapping")
        counts = np.asarray(readout.get("spike_counts"), dtype=np.uint32)
        if counts.shape != (1303,):
            raise ValueError("readout has an invalid DN vector length")
        result = np.zeros(self.neuron_count, dtype=np.int64)
        result[self.compact_indices] = counts
        return result

    def calibration_readout(self, artificial_counts: list[int] | np.ndarray, *, calibration_id: str) -> dict[str, Any]:
        """Build an explicitly external calibration packet, never a LIF frame."""
        if not calibration_id.startswith("instrumental-motor-calibration:"):
            raise ValueError("artificial DN counts require an explicit instrumental calibration ID")
        counts = np.asarray(artificial_counts, dtype=np.int64)
        if counts.shape != (1303,) or np.any(counts < 0) or np.any(counts > np.iinfo(np.uint32).max):
            raise ValueError("calibration counts must be 1,303 non-negative uint32 values")
        return {
            "population": "flywire-v2.1.0-descending-1303",
            "annotation_sha256": self.source_sha256,
            "mapping_sha256": self.mapping_sha256,
            "manifest_sha256": self.manifest_sha256,
            "connectome_sha256": self.connectome_sha256,
            "active_neurons": int(np.count_nonzero(counts)),
            "total_spikes": int(counts.sum(dtype=np.uint64)),
            "compact_indices": self.compact_indices.tolist(),
            "spike_counts": counts.astype(np.uint32).tolist(),
            "effect": "ARTIFICIAL_CALIBRATION_ONLY_NOT_FLYNN_ACTIVITY",
            "calibration_id": calibration_id,
        }
