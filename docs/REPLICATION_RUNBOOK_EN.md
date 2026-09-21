# Flynn — Replication Runbook

> Public scope and limits: [REPLICABILITY_EN.md](../REPLICABILITY_EN.md).

> **STATUS: ARCHIVED / NOT THE PROJECT'S NEXT ACTION**  
> The historical version of this document was written while Flynn was `RETIRED_FROZEN`. Flynn has since been reopened as a non-commercial research initiative seeking new infrastructure. This runbook is still preserved as a technical procedure for the isolated E01 experiment. It must not be interpreted as proof that the original resident can be recreated with uninterrupted continuity.

## Current state

```text
REPLICATION_KIT=READY
E01=REPLICABLE_WITH_REAL_HOST_DEPENDENCIES
E01_R=UNRESOLVED
RESIDENT_RUNTIME=BLOCKED
VM_MAX=UNREACHABLE
```

This runbook reproduces the isolated E01 experiment, not the historical Flynn resident. E01 uses a frozen intention (`TURN_LEFT`), a synthetic four-degree-of-freedom URDF body, and Pinocchio for dynamics. The real ZeroClaw only serves as an IPC availability gate; the external experimental adapter computes coordination. This is why the historical verdict is PARTIAL rather than PASS.

## Prerequisites

- Linux with Python 3.12 or compatible.
- An authorized host containing a real ZeroClaw and its Unix socket.
- Pinocchio 4.1.0 installed in the same Python environment as the runner.
- No resident service needs to be stopped, restarted, or altered.
- Do not use the Flynn resident, connectome, plasticity, KALLISTIS, or an SQLite database for this reproduction.

Isolated installation from the repository root:

```bash
python3 -m venv research/e01/.venv
research/e01/.venv/bin/python -m pip install --only-binary=:all: -r research/e01/requirements.txt
```

The package is named `pin`, while the import is `pinocchio`. On MAX, the observed wheel was `manylinux_2_28_aarch64 cp312`; this must be revalidated on any other host.

## Execution

Explicitly provide the real ZeroClaw binary and socket:

```bash
research/e01/.venv/bin/python research/e01/run_e01.py \
  --zeroclaw /real/path/to/zeroclaw \
  --socket /real/path/to/daemon.sock \
  --output /tmp/flynn-e01-run
```

The runner keeps `initialize` and `health` on the same IPC connection, records provenance, executes 40 ticks of case A, and checks:

- B: missing socket → FAILED/NO_EFFECT;
- C: missing Pinocchio body → FAILED/NO_EFFECT;
- D: target outside limits → DENIED/NO_EFFECT.

Artifacts produced:

- `e01_environment.json`;
- `e01_body_inventory.json`;
- `e01_fail_closed_tests.json`;
- `e01_execution_trace.csv`;
- `E01_FINAL_REPORT.md`;
- `E01_EVIDENCE_MANIFEST.json`.

The report never promotes ZeroClaw and never connects the isolated experiment to the historical resident.

## What cannot be reconstructed locally today

The checkout contains only part of the historical runtime. Modules and data required to start the former resident are absent, including the canonical ledger, auxiliary brain modules, STT/NLU, web authentication, SQLite databases, and the original `fruit-fly-lab`.

It is not acceptable to create stubs that merely make the product appear functional.

For any new research runtime, the operational order is:

1. obtain an appropriate host;
2. positively identify the checkout, services, and required data;
3. reconstruct only from preserved and documented artifacts;
4. verify SHA, process, port, persistence, and the real manual flow;
5. only then document a new replication recipe.

Any claim about Lethe, homeostasis, persistence, or a continuous loop remains UNVERIFIED for a new installation until that installation is actually exercised.

## E01-R

The E01-R record investigated a deterministic extension inside the ZeroClaw process. Inspection confirmed that plugins, tooling, and ACP were not a proven deterministic motor surface. The experimental patch did not reach final application and validation; therefore no patch is included as product. E01-R remains UNRESOLVED and E02 is not authorized by the historical protocol.

## Study safety rules

- Do not add policy, planner, reward, LLM, agent loop, or goal selection.
- Do not transform `TURN_LEFT` into behavior selected by the system.
- Do not use isolated reproduction to claim that a resident runtime is healthy.
- Do not call a build, HTTP 200, or an active service proof that the product flow works.
- Preserve `CavernaVirtualBody` as owner of canonical body state where the historical architecture requires it.
