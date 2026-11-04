"""Load and build the approved, root-ID-mapped Shiu FAFB v783 CSR graph.

The CSR builder is an offline preparation step. It streams the pinned parquet,
retains every signed pair, and writes local binary arrays plus a hash manifest.
It never downloads or redistributes connectome data.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import resource
import shutil
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from .sqlite_store import mapping_digest


DATASET_VERSION = "fafb-v783"
CANONICAL_NEURON_COUNT = 139_255
SHIU_NEURON_COUNT = 138_639
EXPECTED_PAIR_COUNT = 15_091_983
EXPECTED_SYNAPSE_COUNT = 54_492_922
EXPECTED_MAPPING_SHA256 = "23de4f221e330dc5b298ee9ade27ec2a15555db9e3f8af4436652c8301def3cf"
EXPECTED_ROOTS_SHA256 = "7c7b7e818e9232e5ab64793d52ba20574dbe9da3a6509fbc74193b0f259a01be"
EXPECTED_MATRIX_SHA256 = "efeb23fb99098e9c390f6869969b2a121a2ee92c833cfc45ecb2c1d8e1af0347"
EXPECTED_COMPLETENESS_SHA256 = "bbb847a4cc2caaa7a16349722d220c087317b946d148d4d592d94d250617a311"
CSR_FORMAT_VERSION = 1
_BATCH_SIZE = 262_144
_PARQUET_COLUMNS = (
    "Presynaptic_ID",
    "Postsynaptic_ID",
    "Presynaptic_Index",
    "Postsynaptic_Index",
    "Connectivity",
    "Excitatory",
    "Excitatory x Connectivity",
)


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_completeness(path: Path) -> tuple[np.ndarray, str]:
    digest = sha256_file(path)
    if digest != EXPECTED_COMPLETENESS_SHA256:
        raise ValueError(f"Shiu Completeness_783.csv SHA-256 mismatch: {digest}")
    roots: list[int] = []
    with path.open("r", encoding="utf-8", newline="") as source:
        reader = csv.reader(source)
        header = next(reader, None)
        if header != ["", "Completed"]:
            raise ValueError(f"unexpected Completeness_783.csv header: {header!r}")
        for row_number, row in enumerate(reader, start=2):
            if len(row) != 2 or row[1].strip().lower() != "true":
                raise ValueError(f"unexpected Shiu completeness row at line {row_number}")
            roots.append(int(row[0]))
    if len(roots) != SHIU_NEURON_COUNT or len(set(roots)) != SHIU_NEURON_COUNT:
        raise ValueError("Shiu complete root list has an unexpected size or duplicate IDs")
    return np.asarray(roots, dtype=np.uint64), digest


def _read_canonical_roots(path: Path) -> tuple[np.ndarray, str]:
    digest = sha256_file(path)
    if digest != EXPECTED_ROOTS_SHA256:
        raise ValueError(f"canonical root-ID SHA-256 mismatch: {digest}")
    roots = np.load(path, allow_pickle=False, mmap_mode="r")
    if roots.dtype != np.dtype("<u8") or roots.shape != (CANONICAL_NEURON_COUNT,):
        raise ValueError("canonical roots must be the verified 139255-element little-endian uint64 array")
    return roots, digest


def _batch_arrays(batch: Any) -> tuple[np.ndarray, ...]:
    arrays = tuple(
        batch.column(batch.schema.get_field_index(name)).to_numpy(zero_copy_only=False)
        for name in _PARQUET_COLUMNS
    )
    if any(array.ndim != 1 for array in arrays):
        raise ValueError("Shiu parquet columns must be one-dimensional")
    return arrays


def build_signed_csr(
    *,
    parquet_path: str | Path,
    completeness_path: str | Path,
    canonical_roots_path: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    """Build a new CSR directory from the exact approved inputs; never overwrite."""
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:  # pragma: no cover - exercised by missing-dependency check
        raise RuntimeError("PyArrow is required to build the v783 CSR; install requirements-neuro.txt") from exc

    started_wall = time.perf_counter()
    started_cpu = time.process_time()
    parquet_path = Path(parquet_path).resolve()
    completeness_path = Path(completeness_path).resolve()
    canonical_roots_path = Path(canonical_roots_path).resolve()
    output_dir = Path(output_dir).resolve()
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing CSR directory: {output_dir}")
    output_dir.parent.mkdir(parents=True, exist_ok=True)

    matrix_sha256 = sha256_file(parquet_path)
    if matrix_sha256 != EXPECTED_MATRIX_SHA256:
        raise ValueError(f"Shiu matrix SHA-256 mismatch: {matrix_sha256}")
    canonical_roots, roots_sha256 = _read_canonical_roots(canonical_roots_path)
    shiu_roots, completeness_sha256 = _read_completeness(completeness_path)
    root_to_compact = {int(root): index for index, root in enumerate(canonical_roots)}
    if len(root_to_compact) != CANONICAL_NEURON_COUNT:
        raise ValueError("canonical root list contains duplicate IDs")
    try:
        shiu_to_compact = np.fromiter(
            (root_to_compact[int(root)] for root in shiu_roots),
            dtype=np.uint32,
            count=SHIU_NEURON_COUNT,
        )
    except KeyError as exc:
        raise ValueError(f"Shiu root ID is absent from the canonical map: {exc.args[0]}") from exc
    computed_mapping_sha256 = mapping_digest(DATASET_VERSION, (int(root) for root in canonical_roots))
    if computed_mapping_sha256 != EXPECTED_MAPPING_SHA256:
        raise ValueError(f"canonical mapping hash mismatch: {computed_mapping_sha256}")

    parquet = pq.ParquetFile(parquet_path)
    absent = sorted(set(_PARQUET_COLUMNS) - set(parquet.schema_arrow.names))
    if absent:
        raise ValueError(f"Shiu parquet is missing required fields: {absent}")
    if parquet.metadata.num_rows != EXPECTED_PAIR_COUNT:
        raise ValueError(f"Shiu parquet row count mismatch: {parquet.metadata.num_rows}")

    # Pass one validates every source row and counts canonical outgoing degrees.
    degrees = np.zeros(CANONICAL_NEURON_COUNT, dtype=np.uint64)
    total_synapses = 0
    previous_pre_index: int | None = None
    for batch in parquet.iter_batches(batch_size=_BATCH_SIZE, columns=list(_PARQUET_COLUMNS)):
        pre_id, post_id, pre_index, post_index, connectivity, excitatory, signed_product = _batch_arrays(batch)
        if any(array.size and (array.min() < 0) for array in (pre_index, post_index)):
            raise ValueError("Shiu positional indices must be non-negative")
        pre_idx = pre_index.astype(np.int64, copy=False)
        post_idx = post_index.astype(np.int64, copy=False)
        if (pre_idx.size and (pre_idx.max() >= SHIU_NEURON_COUNT or post_idx.max() >= SHIU_NEURON_COUNT)):
            raise ValueError("Shiu endpoint index is outside its complete root list")
        if (not np.array_equal(pre_id, shiu_roots[pre_idx])
                or not np.array_equal(post_id, shiu_roots[post_idx])):
            raise ValueError("Shiu endpoint IDs do not match the positional complete-root index")
        if np.any(connectivity <= 0) or np.any(~np.isin(excitatory, (-1, 1))):
            raise ValueError("connectivity must be positive and presynaptic signs must be +/-1")
        if np.any(signed_product < np.iinfo(np.int32).min) or np.any(signed_product > np.iinfo(np.int32).max):
            raise ValueError("signed connection count exceeds the approved int32 CSR range")
        if not np.array_equal(excitatory * connectivity, signed_product):
            raise ValueError("Shiu signed product differs from Excitatory * Connectivity")

        if pre_idx.size:
            if previous_pre_index is not None and int(pre_idx[0]) < previous_pre_index:
                raise ValueError("Shiu edges are not sorted by presynaptic source index")
            if np.any(pre_idx[1:] < pre_idx[:-1]):
                raise ValueError("Shiu edges are not sorted by presynaptic source index")
            previous_pre_index = int(pre_idx[-1])

        compact_pre = shiu_to_compact[pre_idx]
        degrees += np.bincount(compact_pre, minlength=CANONICAL_NEURON_COUNT).astype(np.uint64)
        total_synapses += int(np.sum(connectivity, dtype=np.uint64))

    if total_synapses != EXPECTED_SYNAPSE_COUNT or int(degrees.sum()) != EXPECTED_PAIR_COUNT:
        raise ValueError("validated matrix totals differ from the approved v783 contract")
    if np.any(degrees > np.iinfo(np.uint32).max):
        raise ValueError("out-degree exceeds uint32 CSR pointer capacity")

    indptr = np.empty(CANONICAL_NEURON_COUNT + 1, dtype=np.uint32)
    indptr[0] = 0
    indptr[1:] = np.cumsum(degrees, dtype=np.uint64).astype(np.uint32)
    if int(indptr[-1]) != EXPECTED_PAIR_COUNT:
        raise ValueError("CSR index pointer total differs from approved pair count")

    temporary_dir = Path(tempfile.mkdtemp(prefix=".shiu-v783-csr-", dir=output_dir.parent))
    try:
        np.save(temporary_dir / "indptr.npy", indptr, allow_pickle=False)
        indices = np.lib.format.open_memmap(
            temporary_dir / "indices.npy", mode="w+", dtype=np.uint32,
            shape=(EXPECTED_PAIR_COUNT,),
        )
        signed_counts = np.lib.format.open_memmap(
            temporary_dir / "signed_count.npy", mode="w+", dtype=np.int32,
            shape=(EXPECTED_PAIR_COUNT,),
        )
        cursor = indptr[:-1].astype(np.uint64, copy=True)

        # Pass two streams the already source-sorted parquet and stable-sorts only
        # each bounded batch into canonical outgoing-row order.
        for batch in parquet.iter_batches(batch_size=_BATCH_SIZE, columns=list(_PARQUET_COLUMNS)):
            _pre_id, post_id, pre_index, post_index, _connectivity, _excitatory, signed_product = _batch_arrays(batch)
            pre_idx = pre_index.astype(np.int64, copy=False)
            post_idx = post_index.astype(np.int64, copy=False)
            compact_pre = shiu_to_compact[pre_idx]
            compact_post = shiu_to_compact[post_idx]
            order = np.argsort(compact_pre, kind="stable")
            sorted_pre = compact_pre[order]
            if sorted_pre.size == 0:
                continue
            starts = np.r_[0, np.flatnonzero(sorted_pre[1:] != sorted_pre[:-1]) + 1]
            group_pre = sorted_pre[starts]
            group_counts = np.diff(np.r_[starts, sorted_pre.size])
            rank_in_group = np.arange(sorted_pre.size, dtype=np.uint64) - np.repeat(starts.astype(np.uint64), group_counts)
            positions = np.repeat(cursor[group_pre], group_counts) + rank_in_group
            if np.any(positions >= np.repeat(indptr[group_pre + 1], group_counts)):
                raise ValueError("CSR source bucket overflow during batch scatter")
            indices[positions] = compact_post[order]
            signed_counts[positions] = signed_product[order].astype(np.int32, copy=False)
            cursor[group_pre] += group_counts.astype(np.uint64)

        indices.flush()
        signed_counts.flush()
        if not np.array_equal(cursor, indptr[1:].astype(np.uint64)):
            raise ValueError("CSR construction did not fill every declared source row")

        # Sort each completed source row by canonical target and reject duplicate
        # endpoint pairs. The upstream parquet is source-sorted, not target-sorted.
        for row in range(CANONICAL_NEURON_COUNT):
            start, end = int(indptr[row]), int(indptr[row + 1])
            if end - start > 1:
                local_order = np.argsort(indices[start:end], kind="stable")
                sorted_targets = indices[start:end][local_order]
                if np.any(sorted_targets[1:] == sorted_targets[:-1]):
                    raise ValueError(f"duplicate directed root-ID pair found in CSR row {row}")
                indices[start:end] = sorted_targets
                signed_counts[start:end] = signed_counts[start:end][local_order]
        indices.flush()
        signed_counts.flush()
        del indices, signed_counts

        # Every root is retained; roots absent from Shiu remain isolated rows.
        additional_roots = np.setdiff1d(canonical_roots, shiu_roots, assume_unique=False)
        if additional_roots.size != CANONICAL_NEURON_COUNT - SHIU_NEURON_COUNT:
            raise ValueError("the canonical/Shiu root population difference is not 616")
        for root_id in additional_roots:
            row = root_to_compact[int(root_id)]
            if indptr[row] != indptr[row + 1]:
                raise ValueError("an additional canonical root unexpectedly has outgoing edges")

        arrays = {name: sha256_file(temporary_dir / f"{name}.npy") for name in ("indptr", "indices", "signed_count")}
        manifest = {
            "format_version": CSR_FORMAT_VERSION,
            "dataset_version": DATASET_VERSION,
            "source": {
                "repository": "philshiu/Drosophila_brain_model",
                "commit": "91bdd1e7dcf193f3e7ca5a8933497fcef63b7960",
                "matrix_sha256": matrix_sha256,
                "completeness_sha256": completeness_sha256,
                "license_note": "FlyWire-derived; local non-commercial use only; do not redistribute matrix without clarifying file-level license",
            },
            "canonical_population": {
                "count": CANONICAL_NEURON_COUNT,
                "root_ids_sha256": roots_sha256,
                "mapping_sha256": computed_mapping_sha256,
                "additional_isolated_roots": int(additional_roots.size),
            },
            "connectivity": {
                "pairs": EXPECTED_PAIR_COUNT,
                "synapses": total_synapses,
                "sign_rule": "Excitatory * Connectivity",
                "direction": "presynaptic root ID to postsynaptic root ID",
                "storage": "CSR outgoing: uint32 indptr/indices; int32 signed_count",
            },
            "arrays": {
                f"{name}.npy": {
                    "sha256": arrays[name],
                    "bytes": (temporary_dir / f"{name}.npy").stat().st_size,
                }
                for name in arrays
            },
            "builder": {
                "batch_size": _BATCH_SIZE,
                "peak_rss_bytes": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1024 if sys.platform.startswith("linux") else 1)),
                "wall_seconds": round(time.perf_counter() - started_wall, 3),
                "cpu_seconds": round(time.process_time() - started_cpu, 3),
            },
        }
        manifest_path = temporary_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        with manifest_path.open("rb") as handle:
            os.fsync(handle.fileno())
        temporary_dir.rename(output_dir)
        return manifest
    except Exception:
        shutil.rmtree(temporary_dir, ignore_errors=True)
        raise


@dataclass(frozen=True)
class SignedConnectome:
    """Memory-mapped CSR arrays with provenance verified on every load."""

    root_ids: np.ndarray
    indptr: np.ndarray
    indices: np.ndarray
    signed_count: np.ndarray
    mapping_sha256: str
    matrix_sha256: str
    manifest_sha256: str
    manifest: dict[str, Any]

    @classmethod
    def load(
        cls,
        *,
        csr_dir: str | Path,
        canonical_roots_path: str | Path,
        verify_array_hashes: bool = True,
    ) -> "SignedConnectome":
        csr_dir = Path(csr_dir).resolve()
        roots, roots_hash = _read_canonical_roots(Path(canonical_roots_path).resolve())
        manifest_path = csr_dir / "manifest.json"
        manifest_bytes = manifest_path.read_bytes()
        manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
        manifest = json.loads(manifest_bytes)
        source = manifest.get("source", {})
        population = manifest.get("canonical_population", {})
        connectivity = manifest.get("connectivity", {})
        if manifest.get("format_version") != CSR_FORMAT_VERSION or manifest.get("dataset_version") != DATASET_VERSION:
            raise ValueError("unsupported signed CSR format or dataset version")
        if (source.get("commit") != "91bdd1e7dcf193f3e7ca5a8933497fcef63b7960"
                or source.get("matrix_sha256") != EXPECTED_MATRIX_SHA256
                or source.get("completeness_sha256") != EXPECTED_COMPLETENESS_SHA256):
            raise ValueError("CSR manifest does not identify the approved Shiu source")
        if (population.get("count") != CANONICAL_NEURON_COUNT
                or population.get("root_ids_sha256") != roots_hash
                or population.get("mapping_sha256") != EXPECTED_MAPPING_SHA256
                or connectivity.get("pairs") != EXPECTED_PAIR_COUNT
                or connectivity.get("synapses") != EXPECTED_SYNAPSE_COUNT):
            raise ValueError("CSR manifest differs from the approved population or connectivity contract")

        if verify_array_hashes:
            for filename, expected in manifest.get("arrays", {}).items():
                actual = sha256_file(csr_dir / filename)
                if actual != expected.get("sha256"):
                    raise ValueError(f"CSR array hash mismatch for {filename}: {actual}")
        indptr = np.load(csr_dir / "indptr.npy", mmap_mode="r", allow_pickle=False)
        indices = np.load(csr_dir / "indices.npy", mmap_mode="r", allow_pickle=False)
        signed_count = np.load(csr_dir / "signed_count.npy", mmap_mode="r", allow_pickle=False)
        if (indptr.dtype != np.dtype("uint32") or indptr.shape != (CANONICAL_NEURON_COUNT + 1,)
                or indices.dtype != np.dtype("uint32") or indices.shape != (EXPECTED_PAIR_COUNT,)
                or signed_count.dtype != np.dtype("int32") or signed_count.shape != (EXPECTED_PAIR_COUNT,)):
            raise ValueError("CSR array shape or dtype differs from the approved compact representation")
        if int(indptr[0]) != 0 or int(indptr[-1]) != EXPECTED_PAIR_COUNT or np.any(indptr[1:] < indptr[:-1]):
            raise ValueError("CSR indptr is malformed")
        if np.any(indices >= CANONICAL_NEURON_COUNT) or np.any(signed_count == 0):
            raise ValueError("CSR target index or signed weight count is invalid")
        synapse_total = 0
        for start in range(0, EXPECTED_PAIR_COUNT, 1_000_000):
            counts = signed_count[start:start + 1_000_000].astype(np.int64)
            synapse_total += int(np.abs(counts).sum())
        if synapse_total != EXPECTED_SYNAPSE_COUNT:
            raise ValueError("CSR signed counts do not conserve the approved synapse total")
        computed_mapping = mapping_digest(DATASET_VERSION, (int(root) for root in roots))
        if computed_mapping != EXPECTED_MAPPING_SHA256:
            raise ValueError("loaded root map does not match the approved mapping digest")
        return cls(
            root_ids=roots,
            indptr=indptr,
            indices=indices,
            signed_count=signed_count,
            mapping_sha256=computed_mapping,
            matrix_sha256=EXPECTED_MATRIX_SHA256,
            manifest_sha256=manifest_sha256,
            manifest=manifest,
        )
