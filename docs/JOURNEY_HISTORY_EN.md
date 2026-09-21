# Flynn — Complete Journey History

History and provenance document

- Consolidation date: 2026-09-20
- Repository: `NomosLudens/flynn`
- State at consolidation: replication kit prepared; resident runtime blocked

This document records Flynn's technical journey, from the conception of the brain–body–world loop to recovery of the local material and publication of the kit on GitHub. It distinguishes:

- historical experience observed on host MAX;
- implementation recovered in the local checkout;
- isolated reproduction that can be executed again;
- claims about the current resident state.

These categories are not equivalent.

## 1. Idea and boundaries

Flynn began as a simulation of a neural core derived from *Drosophila* and conceptually evolved into a neuro-synthetic organism with:

- neural core;
- synthetic internal organs;
- articulated body;
- continuous world;
- persistent causal history.

The recorded architectural chain was:

```text
world
  → sensory transduction
  → LIF brain
  → descending readout
  → Pinocchio body
  → world
```

The central principle separated behavior selection from motor execution:

- Flynn or the neural output determines what to do;
- a motor layer may coordinate how to execute it;
- Pinocchio computes body dynamics;
- `CavernaVirtualBody` remains owner of canonical body state.

In experiments E01 and E01-R, the following were prohibited: policy, planner, reward, reinforcement learning, LLM, agent loop, autonomous goal selection, pathfinding, attraction, random walk, connectome modification, plasticity, or replacement of the canonical body.

## 2. Resident state before loss of the VM

The historical authoritative environment was host MAX, accessed over SSH, with the runtime at:

- `/home/ubuntu/Portifolio/flynn-max/fruit-fly-lab`
- `/home/ubuntu/Portifolio/flynn-max/data/flywire-v783`
- `/home/ubuntu/Portifolio/flynn-max/runtime`

Recorded services were:

- `flynn-brain.service`
- `flynn-web.service`
- `zeroclaw.service`
- `lethe-tunnel.service`
- `kallistis.service`

The resident organism had identifier:

```text
759f27b3-84a9-4071-b29e-20adc1d4fc50
```

The canonical state recorded before the experiments was:

- continuous brain, world, and body;
- plasticity inactive;
- zero learned deltas;
- base connectome unmodified;
- associative learning not proven;
- ZeroClaw as `EXECUTION_INTERLOCK`;
- `CavernaVirtualBody` as owner of body mutation.

These records were safety boundaries, not authorization to experimentally promote ZeroClaw or alter the resident.

## 3. E01 — Embodiment E01, 2026-09-14

### 3.1 Question

E01 investigated whether ZeroClaw could evolve from `EXECUTION_INTERLOCK` into a cerebellar-like motor coordination layer, using Pinocchio as a kinematic and dynamic model, without acquiring behavioral agency.

Intended pipeline:

```text
frozen external MotorIntent
  → execution coordination
  → Pinocchio
  → articulated movement
```

The experiment was not supposed to connect to the resident, train Flynn, or alter the canonical body.

### 3.2 Historical preflight

On MAX, the preflight recorded ARM64, Ubuntu 24.04, Python 3.12.3, canonical services active, KALLISTIS responding HTTP 200, and the resident checkout clean in detached state.

That preflight was specific to that moment and does not prove that MAX or the services are available today.

### 3.3 Pinocchio and synthetic body

Pinocchio was installed in isolation as distribution `pin 4.1.0`, imported as `pinocchio`, using a `manylinux_2_28_aarch64 cp312` wheel.

A synthetic URDF body was created, without biological claims:

- thorax;
- two legs;
- four effective degrees of freedom;
- engineered mass and inertia parameters;
- explicit joint limits.

The body is preserved at `research/e01/flynn_e01_minimal_body.xml`.

### 3.4 Executed cases

| Case | Situation | Historical result |
| --- | --- | --- |
| A | ZeroClaw and Pinocchio available | 40 ticks, coordinated articulation |
| B | ZeroClaw unavailable | FAILED/NO_EFFECT |
| C | Pinocchio unavailable | FAILED/NO_EFFECT |
| D | command outside limits | DENIED/NO_EFFECT |

Case A produced:

```text
q_delta_norm=0.1395588487606979
```

There was no policy, reward, LLM, agent turn, resident stimulus, or consumption of resident motor output.

### 3.5 Harness corrections

Two failures in the harness itself were found and corrected:

1. Pinocchio 4.1.0 does not provide `Model.nj`; the number of joints was obtained with `len(model.names) - 1`.
2. The first client opened separate connections for `initialize` and `health`. ZeroClaw required both methods on the same IPC connection.

The current runner at `research/e01/run_e01.py` incorporates these corrections and removes VM-specific fixed paths.

### 3.6 Result

The correct result was not PASS:

```text
E01=PARTIAL
ZEROCLAW_ROLE=EXECUTION_INTERLOCK
MOTOR_COORDINATION_OWNER=EXTERNAL_RESEARCH_ADAPTER
SYNTHETIC_CEREBELLAR_LAYER_IMPLEMENTED=NO
E02_READY=NO
```

The body and dynamics worked, but coordination depended on an external experimental adapter. This did not prove the existence of a motor surface belonging to the ZeroClaw process.

## 4. E01-R — ownership reconciliation

E01-R investigated whether the ZeroClaw process could own a deterministic motor-coordination surface without selecting behavior, goals, or reward.

The audit of the real ZeroClaw found:

- version 0.8.5;
- ARM64 binary;
- local Unix IPC;
- observed methods: `initialize` and `health`;
- no observed deterministic motor interface.

Inspection of the pinned upstream indicated that plugins targeted tools/WASM and ACP represented an agent session. These surfaces did not prove a deterministic motor path without an agent or LLM.

A minimal extension of the local dispatcher was studied, but the experimental patch never reached final application, build, and causal validation.

```text
E01_R=UNRESOLVED
ZEROCLAW_CEREBELLAR_CANDIDATE=UNRESOLVED
E02_READY=NO
```

No incomplete patch was promoted to product.

## 5. Hardening of the resident runtime

### 5.1 Memory growth

Unbounded growth of `Session.history` was identified despite canonical persistence in SQLite. The recorded correction was:

- `HISTORY_MAX_FRAMES=2000`;
- retention limited only in the in-memory buffer;
- historical persistence preserved in SQLite.

### 5.2 Body movement versus locomotion

The runtime could classify geometric micro-variations as locomotion. A separation based on `world_position_delta`, epsilon `0.001`, and the following classes was introduced:

- `LOCOMOTION`;
- `BODY_MOTION_WITHOUT_LOCOMOTION`;
- `REST`.

### 5.3 Low-energy body capacity

A body-capacity floor of `0.01` was recorded to allow minimal activity when energy reached zero, without creating action selection, targeting, or new behavior.

### 5.4 Validation limit

The files were historically compiled and deployed, but the ten-minute memory-stability window did not complete before the host was lost. Elimination of linear memory growth remained `UNVERIFIED`.

## 6. Closing the brain–body–world loop

The closed-loop gate recorded a historical observation lasting approximately 198.89 seconds:

- brain: 157,800 steps;
- world: 789 chunks;
- body: 789 observations;
- energy tracking neural time;
- feeding drive derived from energy;
- body displacement observed;
- body position persisted;
- Pinocchio and world state preserved after reload.

It was also recorded that position and distance came from resident state, GET did not advance the clock, offering food did not directly inject a stimulus, and consumption depended on physical contact. Contact was not reached during the passive observation window.

Historical result:

```text
BRAIN_CONTINUOUS_REAL=YES
WORLD_CONTINUOUS_REAL=YES
BODY_CONTINUOUS_REAL=YES
CONTINUITY_CLASS=MIXED
VERDICT=PARTIAL
```

The corresponding material is under `closed_loop/`.

## 7. Lethe and the Cave

Lethe was investigated as a visual laboratory surface for observing Flynn. The experience displayed quiescent state, causal network, stimuli, body, trace replay, and neural/body states.

The preserved technical interpretation was: an observation laboratory for Flynn's brain–body–world loop.

UX risks observed included:

- lack of a clear heading hierarchy;
- a select element without an obvious accessible label;
- reliance on color and animation;
- no complete proof of persistent replay versus new integration;
- terminology opaque to users outside the study.

This investigation was read-only. The UI was not treated as sufficient proof of runtime behavior.

## 8. Cave Food UI

The feeding layer was historically implemented and validated with:

- body state;
- energy, drive, and capacity;
- resource position;
- canonical distance;
- contact;
- consumption;
- causal diary;
- collapsible technical details;
- mobile validation at `390x844` and `320x568`.

The preserved contract was:

```text
distance <= contact_radius
  → CONTACT
  → single consumption
  → homeostatic replenishment
```

Idempotency was added to prevent double replenishment. The real observation did not reach the SWEET resource; consumption, energy increase, and drive reduction remained `NOT_REACHED`.

Artifacts are under `caverna_food_ui/`.

## 9. Loss of MAX

After resident changes, host MAX stopped responding:

- Cloudflare returned 530/Error 1033;
- SSH timed out;
- ping did not respond;
- Tailscale showed the host offline.

The evidence classified the failure as host-wide rather than as a defect proven to belong only to Flynn.

Memory use near `MemoryMax=4G` was recorded as an OOM/pressure hypothesis, but not as a proven cause. There was no kernel or provider-console evidence to close the diagnosis.

```text
HOST_MAX=UNREACHABLE
FLYNN_SERVICE=UNKNOWN
EXACT_CAUSE=UNRESOLVED
OOM_PROVEN=NO
```

No blind restart or destructive recovery was performed.

## 10. Local recovery on 2026-09-20

The local checkout was reassessed:

- there were no commits;
- there was no remote;
- recovered code was present as unversioned files;
- Python bytecode was mixed into the directory;
- the complete runtime was not present.

The local Git object database still contained orphan trees. One preserved the E01 runner and URDF. These artifacts were recovered and transformed into a reproducible version:

- VM paths removed from the runner;
- binary and socket supplied through arguments;
- artifact output parameterized;
- IPC session corrected;
- fail-closed report;
- SHA-256 manifest;
- no resident import.

The following were also created:

- `docs/REPLICATION_RUNBOOK.md`;
- `docs/EVIDENCE_INDEX.md`;
- `docs/RECOVERY_PROVENANCE.md`;
- `research/e01/requirements.txt`;
- `research/e01/flynn_e01_minimal_body.xml`;
- `research/e01/run_e01.py`.

## 11. Validation of the local recovery

In the temporary local environment:

- Python compiled the recovered code;
- the XML passed the parser;
- Pinocchio 4.1.0 was installed outside the project;
- the body executed 40 steps;
- `N_DOF=4`;
- `q_norm=0.13955884876069757`;
- an invalid limit was rejected;
- execution without real ZeroClaw produced a report and exited with code 2.

Exit code 2 is intentional: without real ZeroClaw, complete replication cannot be considered successful. The runner does not use a mock to mask that absence.

## 12. Publication on GitHub

The local commit created was:

```text
3e29d21c566e0520a81393b45dcd428fb1d33e86
```

The supplied remote was configured as:

```text
https://github.com/NomosLudens/flynn.git
```

The commit was published to `master`. Final verification confirmed:

```text
LOCAL_HEAD=3e29d21c566e0520a81393b45dcd428fb1d33e86
REMOTE_HEAD=3e29d21c566e0520a81393b45dcd428fb1d33e86
WORKTREE=CLEAN
```

## 13. Consolidated state at that point

| Component | State |
| --- | --- |
| Local checkout | PASS |
| GitHub repository | PASS |
| E01 kit | READY |
| Synthetic Pinocchio body | PASS in temporary environment |
| Fail-closed cases | PASS |
| Current real ZeroClaw | BLOCKED |
| VM MAX | UNREACHABLE |
| Resident runtime | BLOCKED |
| Memory stability | UNVERIFIED |
| Real food contact/consumption | NOT_REACHED |
| E01 | PARTIAL |
| E01-R | UNRESOLVED |
| E02 | NOT_READY |

## 14. Correct next path at that point

The next step was not to create another parallel runtime. It was to recover the original authority:

1. obtain console, volume, or backup access to MAX;
2. positively identify directories, services, and databases;
3. copy the runtime without secrets;
4. compare SHA, processes, ports, and database;
5. recover modules missing from the checkout;
6. repeat the manual proof of the resident flow;
7. only then update resident status.

Until that chain was proven, the GitHub repository had to be read as:

> recovered code + isolated reproduction kit + historical evidence, not as a currently operational Flynn resident.

## 15. Update introduced by the roadmap

The file `docs/MAPA_DE_PERCURSO_FLYNN.md`, supplied after the first consolidation of this history, is a more recent operational record, updated on 2026-09-15. It adds a later phase of the journey that was not available in the recovered local checkout.

### 15.1 Refined scientific state

The roadmap confirms and details:

- neural core anchored in FlyWire FAFB v783;
- 139,255 neurons and 1,305 descending neurons;
- Foundation closed through Gate 014;
- functional plasticity and persistent synaptic change;
- associative learning still not proven;
- Gate 014 protocol incident recorded;
- resident restored to the pre-training checkpoint;
- plasticity OFF, zero learned deltas, and base connectome intact.

The learning result remains:

```text
PLASTICITY_MECHANISM_FUNCTIONAL=YES
PERSISTENT_SYNAPTIC_CHANGE=YES
ASSOCIATIVE_LEARNING_PROVEN=NO
LEARNING_PROVEN=NO
```

### 15.2 Embodiment after E01

The roadmap distinguishes experiments that previously appeared only under E01:

- E01: articulated-body feasibility, PARTIAL;
- E01-R: coordination inside ZeroClaw, BLOCKED/UNPROVEN;
- E01-R2: build-surface audit, no completed causal runtime;
- E01-D: direct motor transduction, PASS;
- E01-N: real temporal DN activity, PARTIAL;
- E03: resident integration Flynn → Pinocchio → Lethe, PASS.

E01-D showed that a minimal synthetic motor boundary was sufficient for the body test, without making a cerebellar-like ZeroClaw layer necessary. Coordination remained free of policy, reward, LLM, or agent loop.

E01-N found real temporal activity in the 1,305 DNs, but no sufficiently reproducible motor dimension to declare a neural `MotorVector`. The VNC boundary remained explicitly limited:

```text
BIOLOGICAL_VNC_PRESENT=NO
BIOLOGICAL_VNC_RECONSTRUCTED=NO
SYNTHETIC_MOTOR_BOUNDARY=YES
```

### 15.3 Documented resident integration

According to the roadmap, E03 integration was completed on MAX:

```text
FLYNN_CONNECTED_TO_PINOCCHIO=YES
PINOCCHIO_CONTROLS_EXISTING_LETHE_SIGIL=YES
LETHE_LIVE_BODY=YES
BODY_STATE_PERSISTENT=YES
LIVE_BODY_DRIVEN_BY_REPLAY=NO
LIVE_BODY_DRIVEN_BY_HTTP_REQUEST=NO
REAL_CAUSAL_TRACE_CAPTURED=YES
PRODUCT_REAL=YES
```

The documented body was not a separate demo: it was Lethe's canonical sigil, with 23 modules and 30 connections.

These claims are valid as historical records from 2026-09-15. Because VM MAX later became inaccessible, they are not proof of runtime availability on 2026-09-20 or today.

### 15.4 H00/H01 and living trajectory

The roadmap records real continuity over a 866.9976-second window, with:

- continuous brain, world, body, and homeostasis;
- energy evolving in `NEURAL_TIME`;
- no regression to request-driven advancement;
- fail-closed homeostasis UI;
- no fallback converting missing data into 100% or 0.00.

It also records a persistent server-side trajectory on the same temporal axis, containing position, Pinocchio geometry, `q`, distance, direction, aggregated DN activity, `energy_reserve`, `feeding_drive`, and Umwelt state.

The preserved limit is important: aggregated DN activity was recorded, but sufficient individual identities for `TOP_DNS` were not available. No neuronal name should be invented.

### 15.5 Next action recorded by the roadmap

The roadmap identified the next product task as:

```text
energy_reserve → body_capacity → physical degradation/recovery
```

Energy should limit physical actuation capacity, not select actions or goals. Future validation also needed to verify exact persistence of `energy_reserve`, `feeding_drive`, `q`, position, and `body_capacity` after restart.

That item was incorporated into this history as context and was not executed in the first local recovery. Access to the VM remained the blocker at that point.

## 16. Later addendum: project closure and freeze

The file `docs/FLYNN_DELTA_ATUALIZACAO_MAPA_DE_PERCURSO.md` records an update after the 2026-09-15 roadmap. It should be read as a historical delta: it does not rewrite earlier measurements and was not, at that time, an instruction to reactivate the resident.

### 16.1 Corrections implemented before interruption

The addendum records the following as implemented, although not necessarily proven over a later long-duration observation window:

- `body_capacity = clip(energy_reserve, 0, 1)`, without external action selection;
- restart persistence of energy, body, world, plasticity, `q`, and `qdot`;
- survival floor `body_capacity >= 0.01` to prevent starvation deadlock, without pathfinding, attraction, or reward;
- distinction between geometric body movement and locomotion through world-space, requiring a position delta greater than `0.001u`;
- resource mechanics and presentation in the Cave, although real contact and consumption were not observed;
- mobile/PWA Cave, with recorded validation at `390x844` and `320x568`.

The complete feeding cycle remains unproven:

```text
REAL_CONTACT_OBSERVED=NO
REAL_CONSUMPTION_OBSERVED=NO
FULL_FEEDING_CYCLE_PROVEN=NO
```

### 16.2 Memory and continuity limits

The addendum identifies `Session.history` as the cause of linear memory growth and records a limit of `2000` frames in RAM. The correction was implemented, but long-duration validation was interrupted by loss of the host:

```text
MEMORY_ROOT_CAUSE_IDENTIFIED=YES
IN_MEMORY_HISTORY_BOUNDED=YES
MEMORY_LINEAR_GROWTH_FIXED=UNVERIFIED
```

Two controlled restarts occurred during the final correction; they were not arbitrary experimental resets. The external interruption, however, broke resident temporal continuity:

```text
RESIDENT_CONTINUITY_INTERRUPTED_EXTERNALLY=YES
CONTINUITY_GAP_CAUSE=INFRASTRUCTURE_ACCOUNT_SUSPENSION
```

### 16.3 Oracle incident and the author's decision

The addendum separates the Oracle suspension incident from any hypothesis about Flynn. What remains recorded is:

```text
OCI_ACCOUNT_SUSPENDED=YES
OCI_TENANCY_ACCESS_LOST=YES
OCI_COMPUTE_ACCESS_LOST=YES
OCI_SECONDARY_REVIEW=REQUESTED
FLYNN_TRIGGERED_ACCOUNT_SUSPENSION=UNPROVEN
RESOURCE_DELETION=UNPROVEN
DATA_PRESERVATION=UNKNOWN
```

The author then decided to retire and freeze the project. There was no current plan for local rehosting, Google Mini rehosting, or reconstruction. If MAX returned, the historical priority was to preserve/export data, ledger, checkpoints, and runtime, assess integrity, and only then decide whether any continuation would exist.

### 16.4 Canonical status after the addendum

The status after the addendum became:

```text
PROJECT_STATUS=RETIRED_FROZEN
RESEARCH_STATUS=CLOSED_BY_AUTHOR
RESIDENT_RUNTIME_STATUS=INTERRUPTED_EXTERNALLY
CURRENT_RUNTIME_STATUS=OFFLINE_UNAVAILABLE
REHOST_LOCAL=NO
REHOST_GOOGLE_MINI=NO
CURRENT_RESUMPTION_PLAN=NONE
NEXT_ACTION=NONE_FOR_DEVELOPMENT
```

The product and continuity were real before the interruption, but that does not authorize a claim that the runtime is available today. Associative learning, real locomotion to food, and closure of the feeding cycle also remain unproven.

## 17. Current superseding status — 2026-09-21

On 2026-09-21, the author explicitly reopened Flynn as a **non-commercial research and open-knowledge initiative**, seeking suitable persistent infrastructure.

This does not erase or reinterpret the historical freeze. It changes the project's present status:

```text
PROJECT_STATUS=RESEARCH_REOPENING
RESEARCH_STATUS=ACTIVE_REHOSTING_PREPARATION
CURRENT_RUNTIME_STATUS=OFFLINE_PENDING_REHOST
NON_COMMERCIAL=YES
PUBLIC_REPOSITORY=YES
OPEN_KNOWLEDGE_COMMITMENT=YES
```

Any future Flynn runtime must be treated as a **new temporal experimental episode**, reconstructed from preserved artifacts and validated from real execution. The original resident's uninterrupted continuity cannot be restored retroactively.
