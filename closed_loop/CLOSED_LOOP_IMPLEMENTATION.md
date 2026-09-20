# PROJECT FLYNN — CLOSE THE REAL EMBODIED LOOP

Host: `max`  
Authoritative runtime: `/home/ubuntu/Portifolio/flynn-max/runtime`  
Implementation mode: resident runtime, no new body, no connectome mutation.

## Implemented causal owners

- `ContinuousBrainClock._run_loop` remains the sole owner of the continuous
  `Session.advance()` call.
- `PinocchioSigilBody.physical_centroid()` measures the arithmetic mean of the
  23 live Pinocchio physical frame positions.
- `world_delta = physical_centroid_after - physical_centroid_before` with the
  fixed `WORLD_SCALE = 1.0`.
- `CavernaVirtualBody.apply_physical_displacement()` applies that measured
  delta to the bounded canonical Caverna position and reports clamping.
- `ContinuousWorldEngine.observe_body()` owns distance, contact, and
  nutritive consumption. Contact is `distance <= contact_radius`; consumption
  is not a proximity or HTTP side effect.

The local Pinocchio articulation (`q/qdot`) and organism locomotion are stored
and reported separately. Energy continues to limit only executed actuation via
`requested_actuation * clip(energy_reserve, 0, 1)`; it is not an action selector
and is not part of the motor vector.

## Resource contract

Sweet and bitter retain their fixed positions (`[3, 0]` and `[-3, 0]`) and now
expose `resource_id`, `resource_type`, `contact_radius`, `offered_at`,
`available`, and `consumed_at`. Human offer/fulfill routes no longer inject a
brain stimulus or replenish energy. The resident world receives the queued
offer; a future physical contact is the only nutritive transition.

## Sensory boundary

The body emits `SYNTHETIC_FACTUAL_RUNTIME_SIGNAL` proprioception containing
displacement and position, with `neural_injection=NONE`, because the loaded
FlyWire modality registry has no registered proprioceptive modality. Existing
world modalities such as taste and `touch_head` continue through the normal
`Session.add_modality` boundary only when their physical exposure exists.
This is explicitly not a claim of biological proprioception reconstruction.

## Persistence and presentation

Body position, world resource metadata/contact/consumption state, body motion
telemetry, and the existing Pinocchio checkpoint are included in the resident
checkpoint path. The canonical ledger now treats world position as the world
trajectory and keeps the local Pinocchio centroid under `geometry_summary`.
The Caverna UI displays Flynn position, resource position, distance, contact,
energy, drive, and body capacity; Lethe is rendered as world transform times
local live Pinocchio geometry. Existing 23 modules and 30 edges are preserved.

## Explicit non-goals

No seeking, attraction, pathfinding, planner, reward, random walk, LLM,
ZeroClaw change, plasticity, DN remap, PCA, connectome edit, browser clock, or
GET-driven advancement was introduced.
