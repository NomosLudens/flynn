# Caverna Food UI — Validation

## Runtime episode

- Host: `max`
- Resident: instance `759f27b3-84a9-4071-b29e-20adc1d4fc50`
- `flynn-brain.service`: active after code reload; instance ID and world state were preserved from checkpoint.
- SWEET remained a resident-world object at `[3.0, 0.0]` with `resource_id=sweet`, `available=true`, `offered=true`, `contact_radius=0.5`.
- The resident body position and Euclidean distance were read from the daemon, not inferred from the canvas.
- Passive samples over roughly 10 seconds advanced neural time from `5191213.4 ms` to `5192013.4 ms`.
- Distance changed `3.036028 u -> 3.036252 u`; `CONTACT=false` throughout. The resource was not reached, so no consumption or replenishment is claimed.
- The observed energy/drive change was ordinary neural-time homeostasis decay (`0.15819 -> 0.15779`, `0.84181 -> 0.84221`), not food consumption.

## Contact/idempotency check

The resident contact owner was checked with an isolated local engine fixture at the canonical resource position. One contact applied one nutritive update, set `available=false` and `consumed_at`, and a repeated observation did not call replenishment again. This is a code-path check, not a claim that the production resident reached SWEET during the episode.

## UI validation

- `390x844`: PASS. No horizontal overflow; Flynn body and situation card visible; initial technical drawer and replay HUD hidden; menu opens `DETALHES TÉCNICOS`; drawer opens with position, `q/qdot`, resource, distance/radius, event IDs and provenance.
- `320x568`: PASS. No horizontal overflow; Flynn body and situation card visible; technical drawer remains closed on initial load.
- Diary entries show Brasília local date and time, for example `16/09/2026 12:03:18`, with expandable technical payloads.
- JavaScript syntax check: PASS.

## Required final block

```text
HOST=max

# RECURSO / ALIMENTAÇÃO

SWEET_OFFER_CREATES_REAL_RESOURCE=YES
SWEET_AVAILABLE_AFTER_OFFER=YES
SWEET_WORLD_POSITION_PRESENT=YES
SAME_COORDINATE_SYSTEM_BODY_RESOURCE=YES

DISTANCE_TO_SWEET_REAL=YES
CONTACT_RADIUS_REAL=YES
PHYSICAL_CONTACT_DETECTED=NO

CONSUMPTION_REQUIRES_CONTACT=YES
SWEET_CONSUMED=NOT_REACHED
RESOURCE_CONSUMPTION_IDEMPOTENT=YES

ENERGY_INCREASED_AFTER_CONSUMPTION=NOT_REACHED
FEEDING_DRIVE_DECREASED_AFTER_CONSUMPTION=NOT_REACHED
BODY_CAPACITY_RECOVERED_AFTER_CONSUMPTION=NOT_REACHED

# INTERFACE

CAVERNA_HAS_HUMAN_SITUATION_LAYER=YES
CAVERNA_HAS_COLLAPSIBLE_TECHNICAL_DETAILS=YES
CURRENT_STATE_READABLE_WITHOUT_TELEMETRY_KNOWLEDGE=YES
RESOURCE_STATE_CLEAR=YES
DISTANCE_VISIBLE=YES
CONTACT_STATE_VISIBLE=YES
CONSUMPTION_STATE_VISIBLE=YES
CAUSAL_DIARY_HUMAN_READABLE=YES
CAUSAL_DIARY_RETAINS_TECHNICAL_DETAIL=YES
FLYNN_BODY_REMAINS_VISIBLE=YES
MOBILE_390x844=PASS
MOBILE_320x568=PASS

# INTEGRIDADE

BODY_STATE_RESET=NO
TRAJECTORY_RESET=NO
CONNECTOME_MODIFIED=NO
PLASTICITY_ACTIVE=NO
RESIDENT_TRAINED=NO
ZEROCLAW_MODIFIED=NO
FOOD_TARGETING_POLICY=NO
PATHFINDING=NO
TARGET_ATTRACTION=NO
REWARD=NO
LLM_CALLS=0
AGENT_TURNS=0
PRODUCT_REAL=YES

VERDICT=PARTIAL
```
