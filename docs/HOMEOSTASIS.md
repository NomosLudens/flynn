# Homeostasis V2

The resident installed `homeostasis-v2-measured-cpu-budget-1`. It is an operational compute-accounting model, not biological energy metabolism.

## State and rule

The checkpointed reserve is normalized to `[0,1]`. Configuration set a full reserve to 3,600 measured CPU seconds and the episode began with reserve `1.0`. For a measured cycle cost `C` CPU seconds, the next causal boundary debits:

```text
loss = min(reserve, C / 3600)
reserve_next = reserve - loss
```

Per-stage cumulative cost, pending cost event, last charged event, neural time and reserve are serialized. CPU cost is measured at one cycle and applied once at the next boundary, aligning the budget state for subsequent actuation and proprioception. Advancing neural time does not itself debit reserve.

`feeding_drive = 1 - reserve` and `body_capacity = reserve` are deterministic normalized fields. `modulation_factor` is fixed at `1.0`; this model does not modulate neural activity. `assimilate()` raises an error because no verifiable energy source or conversion is configured.

## What was and was not calibrated

The resident recorded stage CPU counters, including neural core/aggregation, PicoClaw process, Python bridge, world/persistence and descending readout. At the observed run, measured CPU exceeded the configured budget and reserve reached zero. A measured CPU budget does not represent food, ATP, metabolic rate, biological fatigue or energy transfer from the synthetic world. No assimilation, biological calibration or validated energy-to-body law was implemented.

No change to this model is proposed in the final archive. Further calibration would be new research and is outside the ended project.
