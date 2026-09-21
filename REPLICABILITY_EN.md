# Flynn — Replicability and Limits

Flynn is preserved as a **technical archive and experimental research project**. The purpose of this publication is to make the artifacts that were actually preserved reproducible without pretending that the lost resident state still exists.

## Replicability matrix

| Component | Distribution status | What can be reproduced |
| --- | --- | --- |
| Recovered code in `app/` and web surfaces | **AVAILABLE / ARCHIVAL** | inspection, study, and partial reconstruction of preserved layers |
| Closed loop and Cave Food UI | **EVIDENCE + IMPLEMENTATION PRESERVED** | implementation and historical traces preserved in the repository |
| Isolated E01 experiment | **REPLICABLE_WITH_EXTERNAL_DEPENDENCY** | runner, synthetic body, fail-closed tests, and artifact generation |
| E01 minimal body | **REPLICABLE** | `research/e01/flynn_e01_minimal_body.xml` |
| Pinocchio used in E01 | **PINNED** | distribution `pin==4.1.0` |
| ZeroClaw used in E01 | **EXTERNAL / NOT BUNDLED** | requires a compatible real binary and a functional Unix socket |
| Final Flynn resident state | **NOT RECONSTRUCTIBLE FROM THIS REPOSITORY** | do not claim full reconstruction |
| SQLite databases, canonical ledger, checkpoints, and temporal state from MAX | **NOT RECOVERED** | absent |
| Original resident temporal continuity | **IRREPRODUCIBLE BY DEFINITION** | a new execution would be a new temporal instance |
| Historical screenshots | **EVIDENCE ONLY** | document past observations; do not prove current availability |

## What is reproducible today

The artifact with an explicit technical recipe is **E01**.

From the repository root:

```bash
python3 -m venv research/e01/.venv
research/e01/.venv/bin/python -m pip install --only-binary=:all: -r research/e01/requirements.txt
```

Execution requires a real and compatible ZeroClaw. The complete procedure, arguments, and failure criteria are documented in [docs/REPLICATION_RUNBOOK_EN.md](docs/REPLICATION_RUNBOOK_EN.md).

The repository **does not provide a mock, stub, or false fallback** to replace this dependency. If a real ZeroClaw is not available, E01 must not be declared reproduced.

## What must not be claimed

Publishing the recovered code does not automatically reconstruct:

- the Flynn resident;
- the persistent state that existed on VM MAX;
- the canonical ledger;
- the SQLite databases;
- unrecovered checkpoints;
- temporal continuity prior to the interruption;
- scientific results that the archive itself records as unproven.

In particular:

```text
E01_REPLICATION != RESIDENT_FLYNN_RECONSTRUCTION
SOURCE_CODE_BACKUP != RESIDENT_STATE_BACKUP
HISTORICAL_EVIDENCE != CURRENT_RUNTIME
```

## Replicability commitment

The artifacts distributed in this repository should be **reconstructible within their declared limits**, not merely inspectable.

If a documented procedure fails because a component under Nomos Ludens' control is missing, open an issue in this repository describing:

1. the step that was executed;
2. the environment used;
3. the missing component or observed error;
4. the actual output obtained.

When the missing piece can be published safely, legally, and with technical fidelity, it will be made available or the reproduction path will be documented. A gap must not be hidden with simulation.

## Evidence rule

```text
IMPLEMENT -> OBSERVE_REAL_RESULT -> VALIDATE -> CLOSE_OR_FIX_REAL_BLOCKER
```

A successful build, import, HTTP 200 response, or rendered interface does not replace proof of the flow being claimed.

## License

The code published in this repository is made available under the [Common Public Attribution License 1.0](LICENSE), subject to third-party rights over datasets, dependencies, images, and other materials where applicable.

**Attribution:** Flynn, by Nomos Ludens — https://github.com/NomosLudens/flynn
