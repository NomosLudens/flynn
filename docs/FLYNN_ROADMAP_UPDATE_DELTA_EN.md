# FLYNN — ROADMAP UPDATE DELTA

> Incremental update document.  
> Base: canonical `mapa_de_percurso_flynn.md` in Google Drive, last observed modification on 2026-09-16 01:50 UTC.  
> Purpose: record **only what changed after the current roadmap version**, without rewriting the earlier history.

---

# 0. CANONICAL STATUS CHANGES

The header and the `STATUS CANÔNICO RESUMIDO` block are outdated.

## Replace

```text
STATUS=ACTIVE_RESIDENT_NEURO_SYNTHETIC_RUNTIME
HOST_AUTHORITATIVO=MAX
NEXT_ACTION=ENERGY_TO_BODY_CAPACITY
```

## With

```text
PROJECT=FLYNN
PROJECT_STATUS=RETIRED_FROZEN
RESEARCH_STATUS=CLOSED_BY_AUTHOR
RESIDENT_RUNTIME_STATUS=INTERRUPTED_EXTERNALLY
RESIDENT_CONTINUITY_BROKEN=YES

FORMER_AUTHORITATIVE_HOST=MAX
FORMER_HOST_PROVIDER=ORACLE_CLOUD
FORMER_HOST_ACCESS=LOST
OCI_ACCOUNT_STATUS=SUSPENDED
OCI_SECONDARY_REVIEW=OPEN_AT_INCIDENT_TIME

REHOST_LOCAL=NO
REHOST_GOOGLE_MINI=NO
RECONSTRUCTION_NOW=NO

IF_ORIGINAL_MAX_RETURNS=
PRESERVE_DATA_AND_DECIDE_LATER
```

Flynn was **retired/frozen by the author** after the Oracle account was suspended and access to VM MAX was lost.  
There was no plan at that time to reconstruct locally, reduce the organism for smaller hardware, or migrate to Google VM `e2-micro`.

The external interruption ended the resident continuity that was a central part of the experiment.

---

# 1. ENERGY_RESERVE → BODY_CAPACITY — IMPLEMENTED

The `NEXT_ACTION=ENERGY_TO_BODY_CAPACITY` recorded in the roadmap had already been executed and should not continue to appear as the next action.

## Initial result

The following relationship was implemented:

```text
body_capacity = clip(energy_reserve, 0, 1)
```

with these properties:

```text
ENERGY_MODULATES_ACTUATION_MAGNITUDE=YES
ENERGY_SELECTS_ACTION=NO
FEEDING_DRIVE_SELECTS_ACTION=NO
PINOCCHIO_LIMITED_BY_ENERGY=YES
```

Energy began limiting the body's **physical capacity**, not action selection.

## Restart persistence

A real persistence bug was found and fixed:

- homeostasis was loaded before creation of the `ContinuousBrainClock`;
- this could incorrectly restore `energy_reserve` to `1.0`;
- loading was reorganized to preserve pending state.

After the correction, restart restored:

```text
energy_reserve
virtual body
world state
plasticity state
Pinocchio q
Pinocchio qdot
```

Validation observed before the later incident:

```text
SAME_INSTANCE_ID=YES
ENERGY_PERSISTED_ACROSS_RESTART=YES
BODY_STATE_PERSISTED_ACROSS_RESTART=YES
Q_QDOT_PERSISTED=YES
```

---

# 2. STARVATION DEADLOCK — LATER CORRECTION

A later audit found:

```text
energy_reserve=0
feeding_drive=1
body_capacity=0
```

This created a physical deadlock:

```text
no energy
→ zero body capacity
→ cannot reach resource
→ cannot recover energy
```

The implemented correction was:

```text
ALIVE_BODY_CAPACITY_FLOOR=0.01
```

that is:

```text
if alive:
    body_capacity >= 0.01
```

Without:

```text
pathfinding
target attraction
reward shaping
random walk
external action selection
```

After the correction:

```text
ENERGY_RESERVE=0
FEEDING_DRIVE=1
BODY_CAPACITY=0.01
EXECUTED_ACTUATION_NONZERO=YES
```

This change must be described as a **minimal physical survival mechanism**, not as feeding behavior.

---

# 3. MOVEMENT SEMANTICS — CORRECTED

It was identified that the UI could label a local geometric Pinocchio change as “movement” even without real displacement in Cave world-space.

The semantics were corrected.

## Canonical rule

```text
LOCOMOTION
= world_position_delta > epsilon

BODY_MOTION_WITHOUT_LOCOMOTION
= Pinocchio/body geometry changed
  but world position did not move enough
```

With:

```text
LOCOMOTION_EPSILON=0.001u
```

Observed state after the correction:

```text
MOVEMENT_CLASS=BODY_MOTION_WITHOUT_LOCOMOTION
```

Therefore:

```text
PINOCCHIO_GEOMETRY_CHANGE ≠ WORLD_SPACE_LOCOMOTION
```

The roadmap must remove any wording that treats local deformation/actuation as sufficient proof of locomotion in the Umwelt.

---

# 4. FOOD / RESOURCE IN THE CAVE — IMPLEMENTED, BUT THE CYCLE WAS NOT CLOSED

The human-facing resource presentation and state cycle were implemented:

```text
ABSENT
OFFERED
AVAILABLE
CONTACT
CONSUMED
```

The Cave began displaying:

```text
FLYNN NOW
resource state
distance
contact
energy
feeding drive
body capacity
diary with Brasília date/time
technical details expandable
```

An idempotent consumption guard was also implemented in `ContinuousWorldEngine`.

## Causality rule

The following were not introduced:

```text
EAT_POLICY
pathfinding
target attraction
reward
training
connectome mutation
```

The intended flow remains:

```text
contact
→ consumed
→ canonical nutritive increment
→ energy_reserve increases
→ feeding_drive decreases
→ body_capacity increases
```

## Actual observed result

The SWEET resource existed and was available, but Flynn did not reach it during the observed window:

```text
RESOURCE=SWEET
CONTACT=NO
CONSUMED=NO
INGESTIONS=0
```

Therefore:

```text
FOOD_MECHANICS_IMPLEMENTED=YES
REAL_CONTACT_OBSERVED=NO
REAL_CONSUMPTION_OBSERVED=NO
FULL_FEEDING_CYCLE_PROVEN=NO
```

---

# 5. CAVE MOBILE / PWA

A mobile/PWA version of the Cave was implemented:

```text
MOBILE_VERTICAL_LAYOUT=YES
HORIZONTAL_OVERFLOW=NO
TOUCH_TARGETS_MIN≈44px
SCROLL=YES
MANIFEST=YES
SERVICE_WORKER=YES
PWA_PATHS=200
```

Manual validation:

```text
390x844=PASS
320x568=PASS
```

Later, Flynn's body was made more visible on mobile:

```text
BODY_SIZE_MOBILE=ENLARGED
BODY_NODES_HIGHLIGHTED=CYAN
BODY_CONNECTIONS_HIGHLIGHTED=CYAN
HALO=YES
LABEL="FLYNN · CORPO VIVO"
```

The blue/cyan visual identity must be preserved in the historical record.

## Later layout direction

The following visual hierarchy was defined for the Cave:

```text
1. Flynn / living body
2. surrounding world
3. current situation
4. human controls
5. diary
6. technical details
```

It was also decided:

```text
HUMAN_CONTROLS_OUTSIDE_WORLD_SPACE=YES
RESOURCE_DISTANCE_AS_SUBTLE_TELEMETRY=YES
NO_TARGET_ARROW=YES
INACTIVE_WORLD_ELEMENTS_DEEMPHASIZED=YES
TOP_STATUS_DUPLICATION_REDUCED=PLANNED
DIARY_AS_TIMELINE=PLANNED
TECHNICAL_DRAWER_COLLAPSIBLE=PLANNED
```

This final reorganization was **specified/prompted**, but there is no consolidated evidence in the journey that it was completed before the suspension.

---

# 6. FINAL READ-ONLY AUDIT — REAL STATE BEFORE INTERRUPTION

A later read-only audit consolidated:

```text
RESIDENT_CONTINUITY_CLASS=TRUE_CONTINUOUS
SYSTEM_COMPOSITION=MIXED_LIVE_SYNTHETIC_REPLAY
```

During the audit, the same instance remained active and the neural clock continued to advance.

Observed:

```text
brain continuous=YES
world continuous=YES
Pinocchio q/qdot present=YES
trajectory source=RESIDENT
UI state matches backend=YES
ZeroClaw interlock present=YES
fake direct Flynn event injection blocked=HTTP403
```

Also:

```text
energy=0
feeding_drive=1
body_capacity=0   # before the 0.01 floor
sweet_available=YES
contact=NO
consumed=NO
ingestions=0
current_action=STOP
```

The audit concluded:

```text
REAL_WORLD_SPACE_LOCOMOTION_TO_FOOD=NOT_PROVEN
FULL_FEEDING_CYCLE=NOT_PROVEN
```

and that the replay endpoint remained a LAB visualizer:

```text
REPLAY_MODE=TRUE
REPLAY_IS_LIVE_FLYNN=NO
```

---

# 7. MEMORY — ROOT CAUSE FOUND, FINAL FIX NOT VALIDATED

Approximately linear memory growth was detected during resident execution.

The identified cause was:

```text
Session.history
```

which accumulated every telemetry frame without a limit.

## Correction

The in-RAM buffer was capped at:

```text
MAX_SESSION_HISTORY_FRAMES=2000
```

Durable SQLite persistence was not removed.

State after implementation:

```text
MEMORY_ROOT_CAUSE_IDENTIFIED=YES
UNBOUNDED_STRUCTURE_FOUND=YES
IN_MEMORY_HISTORY_BOUNDED=YES
```

However, long-duration validation was interrupted by loss of access to the host.

Therefore the roadmap must record:

```text
UNBOUNDED_STRUCTURE_FIXED=UNVERIFIED
MEMORY_LINEAR_GROWTH_FIXED=UNVERIFIED
```

Do not declare the regression resolved.

---

# 8. CONTROLLED RESTARTS OF THE FINAL CORRECTION

There were two controlled resident restarts during the final correction:

1. first restart to load the implementation;
2. second restart after observing that the initial epsilon still classified micro-variation as locomotion.

This must be recorded as:

```text
CONTROLLED_RESTARTS=2
CAUSE=REAL_RUNTIME_CORRECTION
AUTOMATIC_RESET=NO
```

They were not arbitrary experimental resets.

---

# 9. RECOVERY ARTIFACTS THAT WERE NEVER CREATED

Because the host was interrupted, the following remained pending:

```text
/runtime/research/resident_recovery/RESIDENT_RECOVERY_IMPLEMENTATION.md
/runtime/research/resident_recovery/MEMORY_GROWTH_ROOT_CAUSE.json
/runtime/research/resident_recovery/RESIDENT_RECOVERY_VALIDATION.md
```

Do not record these files as existing.

---

# 10. ORACLE CLOUD INCIDENT — EXTERNAL PROJECT INTERRUPTION

On 2026-09-16 an incident occurred that was distinct from the local memory/build incident of 2026-09-14.

## Factual sequence

```text
Oracle email:
"An order has been processed and your subscription has been updated"

Service Name=CLOUDCM
Order ID=43068362c77159030c1789576116727
Subscription ID=77159030
```

The author did not recognize or authorize the change.

Within the same time window:

```text
OCI_CONSOLE_ACCESS=LOST
MAX_SSH=UNREACHABLE
OTHER_ORACLE_VMS=UNREACHABLE
PASSWORD_RESET_DID_NOT_RESTORE_ACCESS
PUBLIC_ENDPOINTS_FAILED
```

All three Oracle VMs became inaccessible:

```text
1 × VM.Standard.A1.Flex 2 OCPU / 12 GB
2 × VM.Standard.E2.1.Micro
```

Oracle support later stated:

```text
ACCOUNT_STATUS=SUSPENDED
STATED_REASON="violation of the Oracle Cloud Services Agreement"
```

At that time, the supplied text did not specify:

```text
exact clause
exact triggering activity
exact evidence
```

A **secondary review** was requested, with an estimated support timeframe of approximately two business days.

## Canonical classification

```text
OCI_ACCOUNT_SUSPENDED=YES
OCI_TENANCY_ACCESS_LOST=YES
OCI_COMPUTE_ACCESS_LOST=YES
OCI_SECONDARY_REVIEW=REQUESTED
RESOURCE_DELETION=UNPROVEN
DATA_PRESERVATION=UNKNOWN
ROOT_CAUSE=UNKNOWN
```

Do not attribute the suspension to Flynn without evidence.

---

# 11. HYPOTHESIS OF A RELATION BETWEEN FLYNN AND THE SUSPENSION

The author raised the hypothesis that Flynn's heavy experimental workloads might have contributed to some detector or contractual-violation interpretation.

The roadmap must preserve the distinction:

```text
FLYNN_HIGH_LOCAL_RESOURCE_PRESSURE=YES
FLYNN_CAUSED_ORACLE_INFRASTRUCTURE_IMPACT=UNPROVEN
FLYNN_TRIGGERED_ACCOUNT_SUSPENSION=UNPROVEN
ORACLE_STATED_SPECIFIC_TRIGGER=NO_AT_LAST_KNOWN_UPDATE
```

High CPU/RAM load inside the VM must not automatically be described as “overloading Oracle.”

---

# 12. SCIENTIFIC CONSEQUENCE OF THE INTERRUPTION

Resident continuity was part of the experimental object.

The external suspension broke:

```text
brain continuity
body continuity
world continuity
homeostasis continuity
trajectory continuity
```

Even if MAX were later restored, the earlier continuous temporal sequence had been interrupted.

Record:

```text
RESIDENT_CONTINUITY_INTERRUPTED_EXTERNALLY=YES
CONTINUITY_GAP_CAUSE=INFRASTRUCTURE_ACCOUNT_SUSPENSION
```

Do not call any future resumption uninterrupted continuity.

---

# 13. PROJECT RETIREMENT / FREEZE

After the incident, the author decided:

```text
FLYNN_RETIRED=YES
FLYNN_FROZEN=YES
CURRENT_RESUMPTION_PLAN=NONE
LOCAL_REHOST=NO
GOOGLE_MINI_REHOST=NO
```

Central rationale:

- the project depended on continuous online/resident existence;
- turning Flynn into an on-demand local process would change the experimental question itself;
- the incident broke the continuity that sustained the experiment's scientific curiosity.

If MAX returns, the priority is not to automatically resume execution.

```text
IF_MAX_RETURNS:
1. preserve/export data
2. preserve ledger/checkpoints/runtime
3. assess integrity
4. author decides whether any future continuation exists
```

---

# 14. PERSISTENCE RISK EXPOSED BY THE INCIDENT

The earlier audit had already found that the Flynn runtime was not versioned:

```text
RUNTIME_GIT=NO
```

The databases, ledger, checkpoints, and a relevant part of the state existed only on MAX.

The suspension exposed a critical boundary:

```text
SOURCE_CODE_BACKUP != RESIDENT_STATE_BACKUP
```

Record as an operational lesson:

```text
EXTERNAL_STATE_BACKUP_REQUIRED_FOR_FUTURE_RESIDENT_SYSTEMS=YES
SINGLE_CLOUD_TENANCY_AS_ONLY_STATE_AUTHORITY=REJECTED
```

This is a historical record of the continuity failure, not a Flynn reactivation plan.

---

# 15. SUGGESTED FINAL CANONICAL BLOCK

Replace the then-current ending with something equivalent to:

```text
PROJECT=FLYNN
PROJECT_STATUS=RETIRED_FROZEN
RESEARCH_STATUS=CLOSED_BY_AUTHOR

ORGANISM_ID=759f27b3-84a9-4071-b29e-20adc1d4fc50
FORMER_AUTHORITATIVE_HOST=MAX
FORMER_PROVIDER=ORACLE_CLOUD

FOUNDATION_GATES_EXECUTED_THROUGH=014
FOUNDATION_EXPERIMENTAL_SEQUENCE=COMPLETE
FOUNDATION_CLOSURE_CORRECTION=COMPLETE

BRAIN_CONTINUOUS_REAL_BEFORE_INTERRUPTION=YES
WORLD_CONTINUOUS_REAL_BEFORE_INTERRUPTION=YES
BODY_CONTINUOUS_REAL_BEFORE_INTERRUPTION=YES
HOMEOSTASIS_CONTINUOUS_REAL_BEFORE_INTERRUPTION=YES

ENERGY_TO_BODY_CAPACITY_IMPLEMENTED=YES
ALIVE_BODY_CAPACITY_FLOOR=0.01

FOOD_MECHANICS_IMPLEMENTED=YES
REAL_CONTACT_OBSERVED=NO
REAL_CONSUMPTION_OBSERVED=NO
FULL_FEEDING_CYCLE_PROVEN=NO

MOVEMENT_SEMANTICS_CORRECTED=YES
LOCOMOTION_REQUIRES_WORLD_POSITION_DELTA=YES
BODY_MOTION_WITHOUT_LOCOMOTION=SUPPORTED

MEMORY_ROOT_CAUSE_IDENTIFIED=YES
SESSION_HISTORY_RAM_LIMIT=2000
MEMORY_LINEAR_GROWTH_FIXED=UNVERIFIED

MOBILE_PWA_IMPLEMENTED=YES
LETHE_MOBILE_VISIBILITY_IMPROVED=YES

OCI_ACCOUNT_SUSPENDED=YES
OCI_TENANCY_ACCESS_LOST=YES
OCI_COMPUTE_ACCESS_LOST=YES
OCI_SECONDARY_REVIEW=REQUESTED
RESOURCE_DELETION=UNPROVEN

RESIDENT_CONTINUITY_INTERRUPTED_EXTERNALLY=YES

FLYNN_RETIRED=YES
FLYNN_FROZEN=YES
REHOST_LOCAL=NO
REHOST_GOOGLE_MINI=NO
CURRENT_RESUMPTION_PLAN=NONE

PRODUCT_REAL_BEFORE_INTERRUPTION=YES
CURRENT_RUNTIME_STATUS=OFFLINE_UNAVAILABLE

NEXT_ACTION=
NONE_FOR_DEVELOPMENT

IF_ORIGINAL_MAX_RETURNS=
PRESERVE_DATA_AND_DECIDE_LATER
```

---

# 16. ITEMS IN THE THEN-CURRENT ROADMAP THAT MUST BE MARKED AS HISTORICAL

The following formulations still appeared as present/active and needed temporal qualification:

```text
STATUS=ACTIVE_RESIDENT_NEURO_SYNTHETIC_RUNTIME
HOST autoritativo=MAX
CAVERNA_DE_HIPNOS=ACTIVE_UMWELT
LETHE=LIVE_CANONICAL_SIGIL_BODY
PRODUCT_REAL=YES
NEXT_ACTION=ENERGY_TO_BODY_CAPACITY
```

Correct form:

```text
..._BEFORE_OCI_SUSPENSION=YES
CURRENT_RUNTIME_STATUS=OFFLINE_UNAVAILABLE
PROJECT_STATUS=RETIRED_FROZEN
```

The roadmap should preserve the entire earlier scientific journey as valid history, without rewriting it as though those results had never existed.

---

# 17. SUGGESTED CLOSING

The scientific question constructed by the project remains historically valid:

> **What can a biologically anchored neural core do when it has its own body, persistent consequences, real energetic needs, and a continuous Umwelt — without an external layer choosing its goals for it?**

But the resident experiment was externally interrupted before the feeding/locomotor cycle was closed.

The final state must be described without fabricating a conclusion:

```text
ASSOCIATIVE_LEARNING_PROVEN=NO
REAL_WORLD_SPACE_LOCOMOTION_TO_FOOD=NOT_PROVEN
FULL_FEEDING_CYCLE_PROVEN=NO

LIVE_BODY_IMPLEMENTED=YES
PERSISTENT_TRAJECTORY_IMPLEMENTED=YES
ENERGY_TO_BODY_CAPACITY_IMPLEMENTED=YES
RESIDENT_CONTINUITY_WAS_REAL=YES
RESIDENT_CONTINUITY_WAS_INTERRUPTED=YES

PROJECT_RETIRED_FROZEN=YES
```

The interruption does not invalidate what was measured before it.  
It also does not authorize inference of results that were never observed.

---

## Current superseding note — 2026-09-21

The retirement/freeze state documented above remains part of the historical record. On 2026-09-21, Flynn was explicitly reopened as a **non-commercial research and open-knowledge initiative** seeking new persistent infrastructure.

This decision changes the project's current administrative/research status, but it does **not** erase the interruption or restore the original resident's temporal continuity.

Any future runtime must be treated as a new temporal research episode and validated from real execution.
