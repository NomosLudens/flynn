# RackGenius installed source snapshot — 2026-11-04

Source-only copy of the 20 Python files in `/home/flynnadmin/flynn/releases/storage-guard-06-20261104`, the candidate snapshot used for `FLYNN_RACKGENIUS_SCIENTIFIC_WRITE_GUARD_06`. Every published source file was read back from the RackGenius snapshot and matched byte-for-byte with this copy before publication.

This is an additive record. It does not change the preserved `2026-10-26` historical snapshot or activate the candidate snapshot. The instrumented acceptance run created a real checkpoint and SQLite state, restored the real LIF/world state, and exercised logical-only disk-pressure refusals. Continuous residency was not started.

- [Scientific write-guard 06 report](../../../docs/FLYNN_RACKGENIUS_SCIENTIFIC_WRITE_GUARD_06.md)
- [Per-file SHA-256 manifest](source.sha256)
- [Source tree](source/)

Verify source hashes with `cd source && sha256sum -c ../source.sha256`. The snapshot contains source code only. No databases, checkpoints, CSR arrays, credentials, private keys, Python bytecode, or other scientific data are included.
