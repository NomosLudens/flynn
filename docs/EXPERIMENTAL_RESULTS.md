# Experimental results

## Scope

Results below describe the installed resident observations available for the ended project. They do not infer performance outside the named run and do not claim biological behavior.

## Visual input and LIF activity

The resident accepted a `set_illumination` command at a causal boundary in episode 5. It set normalized global light to `1.0`, applied a conductance increment of `0.5` per tick to 11,118 visual roots and recorded input hash `36b0d95c6e5546d03c0f7c65f617dd1332f8f94503a245b847d68ba2ecbbc5d0`. The event was labeled instrumental synthetic input. The target root IDs and compact indices matched the installed canonical map in sampled records.

Observed 1-second aggregate windows:

| Neural time | Total spikes | Active neurons | Descending spikes |
|---:|---:|---:|---:|
| 4,020 ms | 381,696 | 12,417 | 0 |
| 5,020 ms | 1,021,001 | 12,447 | 0 |
| 6,020 ms | 1,013,476 | 12,419 | 0 |
| 7,020 ms | 1,020,669 | 12,423 | 0 |
| 8,020 ms | 1,020,003 | 12,420 | 0 |

All 11,118 visual roots were active in these windows. The Desc manifest included 1,303 unique roots and the readout checked canonical identity. This is evidence of input-driven network activity and silent descending output for that stimulus. It does not prove that the network is incapable of Desc activity under other calibrated inputs.

## Motor, body and proprioception

Sampled cycle records reported `OFFICIAL_DN_READOUT_ZERO_NO_TORQUE`, `FRAME_COORDINATION_OBSERVED_MOTOR_BLOCKED`, and `REAL_PINOCCHIO_STEP_DISPATCHED_VIA_PICOCLAW`. PicoClaw frame receipts were confirmed but observation-only. Pinocchio received zero-torque frames. No change in joint pose or velocity was demonstrated. The proprioceptive transducer reported `NO_PHYSICAL_DEVIATION_NO_NEURAL_INPUT` and zero target count. No later LIF frame contained an effective proprioceptive return.

Thus the full chain—sensory input → Desc activity → motor command → body consequence → proprioceptive return → later LIF processing—was **not demonstrated**.

## Time and resource cost

One observation lasting 1,800 seconds of wall time advanced about 1,380 ms of neural time. This ratio applies only to that observation. The LIF step was 0.1 ms; a 20-ms neural coordinator cycle cost approximately 10.53 CPU seconds in sampled cost events. Neural core/aggregation accounted for about 7.34 CPU seconds per cycle and was the largest measured stage. The host reported 964 MiB RAM, no swap, and 1.2 GB free disk at a later incident capture. A separate 30-minute observation must not be generalized to every run.

## Restore and final state

The last causal-control cursor in episode 5 was tick 87,800 / 8,780 ms, generation `ffc7f14f56c149268e695faaf40a0451`. Records at 8,800 ms include a partially persisted cycle but lack the required atomic confirmed-cycle record. Automatic systemd retries then failed with that exact message and exhausted the start limit. No restore attempt or new experiment was performed for this archive.

The public observer returned HTTP 502 while the resident/viewer services were unavailable. No final manual LETHE session was validated after shutdown. HTTP status alone is not treated as evidence of functionality.
