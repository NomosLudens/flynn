# Installed runtime source snapshot — 2026-10-26

This is a verbatim archive of 31 Python source files copied from the VM's installed runtime after the resident unit had failed and no resident/viewer/archiver process held the database. The files preserve the paths relative to `/home/tonyus-dev/flynn-v2-vm-validation-20261019/resident-app/`. They are **not** assigned a Git commit: the runtime tree did not expose Git provenance. Per-file installed SHA-256 values are in [`source.sha256`](source.sha256); the copied source tree is under [`source/`](source/).

## Comparison with public GitHub `master`

Comparison base: `f69f6c0d2193e128df97ca58cabca75c06636172`, fetched from `origin/master` on 2026-10-26.

- 8 installed files matched byte-for-byte.
- 4 installed files existed on GitHub but differed: `app/body/pinocchio_sigil.py`, `app/world/continuous_world.py`, `ops/flynn_history_archiver.py`, `server.py`.
- 19 installed files were not present on GitHub, including the resident core, LIF engine, signed-connectome loader, visual/proprioceptive transducers, SQLite store, and Homeostasis V2.

The exact 31 comparison rows appear below. `ABSENT_ON_GITHUB` means there was no file at that path on the comparison ref; it does not imply that an earlier implementation never existed.

```text
MATCH       app/body/adapter.py
MATCH       app/body/contract.py
DIFF        app/body/pinocchio_sigil.py
ABSENT      app/body/proprioceptive_readout.py
MATCH       app/brain/clock.py
ABSENT      app/brain/homeostasis_v2.py
MATCH       app/brain/snapshot.py
MATCH       app/experiment_ledger.py
ABSENT      app/local_operator_auth.py
ABSENT      app/neuro_synthetic/__init__.py
ABSENT      app/neuro_synthetic/aggregator.py
ABSENT      app/neuro_synthetic/descending_readout.py
ABSENT      app/neuro_synthetic/lif_engine.py
ABSENT      app/neuro_synthetic/mcp_server.py
ABSENT      app/neuro_synthetic/neural_core.py
ABSENT      app/neuro_synthetic/picoclaw_port.py
ABSENT      app/neuro_synthetic/pinocchio_motor_worker.py
ABSENT      app/neuro_synthetic/pipeline.py
ABSENT      app/neuro_synthetic/proprioceptive_transducer.py
ABSENT      app/neuro_synthetic/recovery_successor.py
ABSENT      app/neuro_synthetic/resident_runtime.py
ABSENT      app/neuro_synthetic/signed_connectome.py
ABSENT      app/neuro_synthetic/sqlite_store.py
ABSENT      app/neuro_synthetic/visual_light_transducer.py
ABSENT      app/neuro_synthetic/world_runtime.py
MATCH       app/web/caverna.py
MATCH       app/web/server.py
DIFF        app/world/continuous_world.py
MATCH       app/world/geometry.py
DIFF        ops/flynn_history_archiver.py
DIFF        server.py
```

The snapshot was scanned for common token, private-key and embedded-password patterns; no matches were found. It contains source code only, not `.env`, operator credential files, private keys, Python environments, connectome arrays, database files or checkpoints. The project license in the repository is CPAL 1.0; upstream dataset and dependency licenses remain their own.

## Installed environment and deployment

- Service: `flynn-v2-resident.service`; Python 3.10 environment under the dated VM package tree.
- Work directory: `/home/tonyus-dev/flynn-v2-vm-validation-20261019/resident-app`.
- LIF environment package inventory: NumPy 1.22.3. The corresponding checked-in requirements also pin PyArrow 11.0.0; installed PyArrow was not independently confirmed in the final inventory.
- Pinocchio environment: `pin==4.1.0`, `cmeel==0.61.0`, NumPy 2.2.6. Unit `LD_LIBRARY_PATH` points to its packaged `libgomp` runtime.
- Resident root at capture: `/var/lib/flynn-v2/resident-episode-5`.
- Service was `failed` at start-limit after five attempts at 15:43:26 UTC. No process restart was issued during this archive mission.

## Data and publication status

The paired `data-preservation/data.sha256` manifest inventories SQLite databases, episode markers, checkpoint NPZs and archive manifests/catalogs under `/var/lib/flynn-v2`. It records hashes and VM paths, not data contents. [`data-preservation/STATUS.md`](data-preservation/STATUS.md) lists the known preservation boundary, the existing historical Cloud Storage coverage, and the access failure that prevented a new copy in the final closure mission. These databases/checkpoints were not uploaded to the public repository because the remaining payloads were inaccessible from the closure client and require licensing/privacy review.

Historical episode-3 segments are readable in the existing Cloud Storage archive through tick 3,786,800. The local episode-3 database/checkpoint at tick 4,468,400 and current episode 5 through its last durable tick 87,800 (plus an unconfirmed 88,000 state) remain on the VM. They are unpreserved outside the VM. **Do not delete the VM or its disks until the owner chooses an additional durable location and verifies the copy.**

## Related record

- [Final research report](../../../docs/FINAL_RESEARCH_REPORT.md)
- [Persistence and episode identity](../../../docs/PERSISTENCE_AND_EPISODES.md)
- [Incident history](../../../docs/INCIDENT_HISTORY.md)
- [Scientific limitations](../../../docs/SCIENTIFIC_LIMITATIONS.md)
