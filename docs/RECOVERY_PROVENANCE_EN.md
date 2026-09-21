# Flynn — Recovery Provenance

## Checkout

- Directory: `/home/tonyus-dev/Documents/ChatGPT/FLYNN`
- State found: `master` branch with no commits and no remote.
- Preserved local files: Cave/Lethe code, closed-loop artifacts, JSON traces, and web surface.
- Residue excluded from the package: Python bytecode, SQLite databases, and runtime state.

## Recovery of records

The local Git object database still contained orphan trees even though there were no commits:

- tree `8359c852a9d88fe10b45fa9f870834586990fb7b`: broad snapshot of code and validation artifacts;
- tree `293b7dd06bc1bde071fcdfc643b14f3d2ffbaa3d`: E01 runner and URDF;
- tree `68365af490e3d8b804c16084f7f8049bba789526`: auxiliary R01 analysis.

The E01 runner and URDF were recovered from that tree and rewritten into the parameterized kit under `research/e01/`. The current version removes VM-specific fixed paths, keeps `initialize` and `health` on the same IPC connection, and fails explicitly when the host or Pinocchio are unavailable.

## Operational records used

- E01 rollout: `01a0a259-efb3-73e0-a759-a5821e6ce2d4`.
- Lethe/Cave investigation: `01a0aaa9-51a2-7201-b99d-c7978f0dc112`.
- E01 protocol: 2026-09-14 reference.
- E01-R protocol: later reconciliation, without promotion to E02.

## Recovery result

```text
REPLICABLE_KIT=READY
PINOCCHIO_BODY=PASS
FAIL_CLOSED_CASES=PASS
REAL_ZEROCLAW_SESSION=BLOCKED_HOST_UNREACHABLE
RESIDENT_REPLICATION=BLOCKED
E01=PARTIAL
E01_R=UNRESOLVED
E02=NOT_READY
```

No historical MAX result was converted into current proof. Reconstructing a new research runtime requires a suitable host and renewed validation of the actual process, persistence, code SHA, and manual flow. The original resident's uninterrupted continuity cannot be recreated after the infrastructure gap.
