# CLOSED LOOP VALIDATION

## Required result fields

HOST=`max`  
AUDIT_MODE=`IMPLEMENTATION + OBSERVATIONAL VALIDATION`  
SERVICES_RESTARTED=`YES — controlled reload required to load code`  
STATE_MUTATED=`YES — runtime code/config state changed; no synthetic body movement or forced consumption`  
RESIDENT_TRAINED=`NO`  

WALL_ELAPSED_SEC=`198.890528`  
NEURAL_ELAPSED_SEC=`15.78`  

BRAIN_TICKS_DELTA=`157800` neural engine steps  
WORLD_TICKS_DELTA=`789` continuous chunks  
BODY_TICKS_DELTA=`789` physical-loop observations  

ENERGY_T0=`0.28384`  
ENERGY_T1=`0.27595`  
ENERGY_T2=`0.27136` (precise follow-up window)  

FEEDING_DRIVE_T0=`0.71616`  
FEEDING_DRIVE_T1=`0.72405`  
FEEDING_DRIVE_T2=`0.72864`  

EXPECTED_ENERGY_DELTA_FROM_NEURAL_TIME=`-0.00789`  
ACTUAL_ENERGY_DELTA=`-0.00789`  

## Classification

BRAIN_CONTINUOUS_REAL=`YES`  
WORLD_CONTINUOUS_REAL=`YES`  
BODY_CONTINUOUS_REAL=`YES`  
HOMEOSTASIS_CONTINUOUS_REAL=`YES`  

ENERGY_CLOCK_ACTUAL=`NEURAL_TIME`  
ENERGY_CHANGED_WITHOUT_HUMAN_REQUEST=`YES — decreased by neural-time bookkeeping`  
FEEDING_DRIVE_CHANGED_WITHOUT_HUMAN_REQUEST=`YES — derived from energy`  
UI_MATCHES_BACKEND=`YES — position/distance/energy read from resident state in tested UI`  
MOCKED_STATE_FOUND=`NO`  

CONTINUITY_CLASS=`MIXED`  
VERDICT=`PARTIAL`  

The movement loop is real and observed: Pinocchio physical centroid deltas
produced nonzero canonical Caverna displacement; the position changed during
passive observation; q/qdot, body capacity, DN aggregates, and homeostasis
continued. Energy change matched the neural-time formula exactly.

The resource/contact half is implemented in the resident owner but is not yet
validated end-to-end because the pre-existing browser offer was a legacy
`offered=true, available=false` state. A new offer through the authenticated
human UI was intentionally not clicked without direct confirmation. Therefore
`offered → available`, physical contact, one-time consumption, and the
corresponding replenishment remain `UNVERIFIED`, not failures and not mocked.

The proprioceptive return is factual runtime telemetry with explicit synthetic
provenance. It is not injected into an arbitrary connectome population. Existing
physical contact/taste inputs use the registered sensory transduction path, but
no contact occurred in the passive window, so that causal branch is also
`UNVERIFIED` in product observation.

## Persistence and request checks

The controlled reload preserved instance ID
`759f27b3-84a9-4071-b29e-20adc1d4fc50`, Pinocchio state, body position state,
world state, and homeostasis state. The browser UI was tested at 390×844 and
320×568 with no horizontal overflow, visible `FLYNN · CORPO VIVO`, zero console
errors, and HTTP 200 for the manifest, service worker, and icon.

Read-only GET requests did not advance the resident. `Session.advance()` has one
live call site in `ContinuousBrainClock._run_loop`. Food fulfill no longer
directly stimulates or replenishes; the resident world owns contact consumption.

The user-owned browser tab was not closed/reopened automatically, preserving the
active session. That mission substep remains `NOT_EXECUTED`.
