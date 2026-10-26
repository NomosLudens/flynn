# Final architecture record

**Project status:** `ENDED`  
**Full causal loop:** `NOT_DEMONSTRATED`  
**Source of truth for deployed behavior:** VM `flynn-1gb`, captured 2026-10-26. The VM runtime had no Git metadata tying it to a commit.

## Implemented system

The installed Flynn V2 was a Python research runtime with this intended path:

```text
continuous synthetic world
  → visual-light / body-derived proprioceptive transducers
  → signed FlyWire v783 CSR and LIF state machine
  → descending-neuron population readout
  → deterministic PicoClaw frame coordinator
  → Pinocchio sigil body step
  → body-state proprioception
  → next neural frame
```

The path was only partially demonstrated. Scalar illumination reached the visual roots and generated persisted LIF spikes. The descending population remained silent; the motor adapter consequently issued zero torque, and no body displacement or effective proprioceptive return was observed. See [experimental results](EXPERIMENTAL_RESULTS.md).

## Components and responsibilities

| Component | Installed responsibility | Observed limit |
|---|---|---|
| `app/world/continuous_world.py` and `app/neuro_synthetic/world_runtime.py` | Persist synthetic world time/state and expose illumination commands | Only a scalar global light input was used in the resident proof |
| `visual_light_transducer.py` | Map normalized light to 11,118 annotated visual roots | Instrumental synthetic drive, not a calibrated optical sensor model |
| `signed_connectome.py`, `lif_engine.py`, `neural_core.py` | Load signed outgoing CSR; advance float64 LIF state; checkpoint network arrays | Experimental model, not a biological neuron simulation |
| `aggregator.py`, `descending_readout.py` | Aggregate frames and read the 1,303-root descending population | Correct mapping was observed; zero descendant spikes were found |
| `picoclaw_port.py` and the PicoClaw bridge | Coordinate acknowledged frames and pass motor data | Sampled receipts were confirmed, but were observation-only/zero torque |
| `pinocchio_sigil.py`, `pinocchio_motor_worker.py` | Step a 23-node synthetic sigil model | The body stayed static; eight graph edges were not mechanics |
| `proprioceptive_transducer.py`, `proprioceptive_readout.py` | Derive sensor values from body state and map them to mechanosensory roots | No physical deviation meant zero effective neural targets |
| `homeostasis_v2.py` | Account for measured CPU use against a normalized compute budget | Not biological metabolism; assimilation was disabled |
| `sqlite_store.py` | Store events, component states, mappings, generations and checkpoint cursor | SQLite was in `DELETE` journal mode; long readers could block the writer |
| `server.py` / `app/web/server.py` | Serve LETHE and the public observer | Viewer was inactive after the resident reached its systemd start limit; a public GET returned HTTP 502 during capture |

## Services and storage

- Resident: `flynn-v2-resident.service`, running `python -m app.neuro_synthetic.resident_runtime` from `/home/tonyus-dev/flynn-v2-vm-validation-20261019/resident-app`.
- Viewer: `flynn-lethe-viewer.service`, Uvicorn on `127.0.0.1:8201`, configured as a public-observer surface.
- Archive timer: `flynn-history-archive.timer`, nominally every 30 minutes. Its service attempted pressure rotation and failed for insufficient staging space; see [incident history](INCIDENT_HISTORY.md).
- Current episode database at capture: `/var/lib/flynn-v2/resident-episode-5/episode-v2.sqlite3`.
- The service command and unit drop-ins identify `resident-episode-5` as the configured root. `episode.json` does not hold the generation; the SQLite causal-generation control does.

## Planned versus realized

The design documents described a continuous sensorimotor loop and energy-aware embodied behavior. The installed system had causal record types and real component calls for several boundaries, but the accepted evidence does not close the loop. Global illumination did not encode spatial patterns or motion; no Desc spikes were recorded; no nonzero actuation or body consequence was recorded; no proprioceptive signal entered a later LIF frame. The runtime was slow, stopped with a checkpoint/confirmed-cycle inconsistency, and is not to be restarted under this archive mission.

The repository's historical files described earlier offline/rehosting states. This final record supersedes their status for 2026-10-26 while retaining their historical content.
