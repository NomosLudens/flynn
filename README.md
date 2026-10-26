# Flynn — final research archive

> **Non-commercial research project · public repository · open knowledge**

Flynn is an experimental neuro-synthetic research project that studies what can be learned from running a biologically anchored neural core inside a persistent sensorimotor loop.

The preserved architecture links:

```text
world → sensory transduction → continuous LIF brain → descending readout
→ Pinocchio body dynamics → Lethe synthetic morphology → world
```

The neural substrate is derived from the **FlyWire FAFB v783** adult female *Drosophila melanogaster* connectome. The historical runtime used a continuous LIF implementation, a persistent world, homeostatic state, an append-only causal ledger and a synthetic body represented by the Lethe sigil.

## Current status

```text
PROJECT=FLYNN
PROJECT_STATUS=ENDED
RESEARCH_STATUS=ENDED_ARCHIVE_ONLY
CURRENT_RUNTIME_STATUS=FAILED_AFTER_RESTART_LIMIT
FULL_CAUSAL_LOOP=NOT_DEMONSTRATED
ARCHIVE_STATUS=PARTIAL_PENDING_DATA_DECISION

FORMER_AUTHORITATIVE_HOST=MAX
FORMER_PROVIDER=ORACLE_CLOUD
RESIDENT_CONTINUITY_INTERRUPTED_EXTERNALLY=YES

NON_COMMERCIAL=YES
PUBLIC_REPOSITORY=YES
OPEN_KNOWLEDGE_COMMITMENT=YES
```

Development ended on **2026-10-26**. The former Oracle-hosted MAX runtime and the later Flynn V2 runtime on `flynn-1gb` are distinct episodes. The later installation ran, but a complete neural-to-body causal loop was not demonstrated. At final inventory, `flynn-v2-resident.service` was failed after automatic restart attempts; it was not restarted during archival.

The historical reopening on **2026-09-21** remains part of the record. This repository preserves code and research documentation, while essential resident databases, checkpoints and connectome arrays remain unpreserved outside the VM. Do not delete the VM or its disks before those data are preserved at a separately verified destination or their disposition is explicitly decided.

## Research purpose

Flynn was conducted as a non-commercial academic and technical inquiry.

The research questions include:

- what persistent spiking-neural dynamics look like when coupled to an embodied closed loop;
- how a biologically anchored neural core interacts with synthetic sensory and motor boundaries;
- how temporal continuity, homeostasis, memory mechanisms and persistent state affect observed behavior;
- what can and cannot legitimately be inferred from recurrent LIF activity and connectome-derived structure;
- how to make experiments of this kind reproducible, inspectable and useful to other researchers, students and independent builders.

The project deliberately distinguishes observed results from interpretation. No claim of consciousness, sentience, associative learning or biological equivalence is made without evidence.

## Open knowledge commitment

The final archive follows a simple principle: **share the technical knowledge, failures and negative results produced by the experiment.**

The public repository preserves:

- source code and architecture;
- reproducible experimental runbooks;
- infrastructure notes where they are safe to publish;
- technical failures and negative results;
- validation evidence;
- research notes and limitations;
- improvements required to reproduce the system independently.

The goal is to make the historical work reviewable without overstating what the runtime demonstrated.

See [Research rehosting and infrastructure](docs/RESEARCH_REHOSTING.md).

## Final archive — 2026-10-26

`FULL_CAUSAL_LOOP=NOT_DEMONSTRATED`: visual LIF activity was persisted, while descending activity, nonzero actuation, body displacement and effective proprioceptive return were not demonstrated. The installed source snapshot is preserved with per-file SHA-256 hashes and an explicit comparison against the public repository revision. Episode databases and checkpoints are inventoried but not published; they remain on the VM. This is a partial archive, not a complete preservation of resident state.

- [Final research report](docs/FINAL_RESEARCH_REPORT.md)
- [Final architecture](docs/FINAL_ARCHITECTURE.md)
- [Neural model](docs/NEURAL_MODEL.md)
- [Embodiment](docs/EMBODIMENT.md)
- [Homeostasis V2](docs/HOMEOSTASIS.md)
- [Persistence and episodes](docs/PERSISTENCE_AND_EPISODES.md)
- [Experimental results](docs/EXPERIMENTAL_RESULTS.md)
- [Incident history](docs/INCIDENT_HISTORY.md)
- [Scientific limitations](docs/SCIENTIFIC_LIMITATIONS.md)
- [Installed runtime source snapshot and data inventory](archive/runtime-installed/2026-10-26/README.md)

## Historical infrastructure requirements

The experiment depended on continuous runtime and persistent state. The following requirements describe the historical rehosting plan; they are not an active request:

- continuous neural time rather than isolated batch replays;
- persistent world/body/homeostatic state;
- append-only causal history;
- controlled restart and persistence experiments;
- long-running observations;
- reproducible public demonstrations and technical validation.

The historical baseline proposal for a first rehosting stage was:

```text
OS=Linux x86_64
CPU=2 vCPU
RAM=4 GB
DISK=40 GB SSD
NETWORK=stable public connectivity
UPTIME=continuous research runtime
```

This proposal was not a validated capacity guarantee and is no longer an active deployment plan.

## Scientific substrate

Historical preserved dataset:

```text
DATASET=FlyWire FAFB v783
SEX=adult female
N_NEURONS=139255
N_CONNECTION_PAIRS=3732460
N_SYNAPSES=50666648
DESCENDING_NEURONS=1305
DESCENDING_TYPES=473
```

The project uses this biological ancestry as a neural anchor while keeping synthetic interfaces explicit. Lethe is a synthetic morphology; Pinocchio is the body-dynamics layer; the motor boundary is not presented as a biological reconstruction of the missing VNC.

## English documentation

The English documentation provides a historical record for researchers and independent developers:

- [Research rehosting and infrastructure](docs/RESEARCH_REHOSTING.md)
- [Canonical status: closure history + research reopening](docs/STATUS_FINAL_EN.md)
- [Complete Flynn roadmap](docs/FLYNN_ROADMAP_EN.md)
- [Complete journey history](docs/JOURNEY_HISTORY_EN.md)
- [Roadmap update delta](docs/FLYNN_ROADMAP_UPDATE_DELTA_EN.md)
- [Avatar / living sigil specification](docs/FLYNN_AVATAR_SIGIL_EN.md)
- [Replicability and limits](REPLICABILITY_EN.md)
- [Replication runbook](docs/REPLICATION_RUNBOOK_EN.md)
- [Recovered evidence index](docs/EVIDENCE_INDEX_EN.md)
- [Recovery provenance](docs/RECOVERY_PROVENANCE_EN.md)
- [Visual evidence and screenshot provenance](docs/PRINTS_VISUAL_EVIDENCE_EN.md)

The original Portuguese documents remain preserved alongside these mirrors as historical/source-language records.

## What was preserved

- `app/`: recovered portions of the brain, body, world and web surface;
- `closed_loop/`: implementation and historical evidence of the embodied loop;
- `caverna_food_ui/`: implementation and historical validation of the feeding interface;
- `research/e01/`: isolated E01 replication kit;
- `docs/MAPA_DE_PERCURSO_FLYNN.md`: original detailed historical operational roadmap;
- `docs/FLYNN_ROADMAP_EN.md`: English roadmap mirror;
- `docs/FLYNN_DELTA_ATUALIZACAO_MAPA_DE_PERCURSO.md`: original interruption and recovery record;
- `docs/FLYNN_ROADMAP_UPDATE_DELTA_EN.md`: English delta mirror;
- `docs/FLYNN_AVATAR_SIGILO.md`: original visual, functional and epistemological specification of Lethe;
- `docs/FLYNN_AVATAR_SIGIL_EN.md`: English sigil specification;
- `docs/STATUS_FINAL.md` and `docs/STATUS_FINAL_EN.md`: historical freeze state plus reopening record;
- `docs/PRINTS_EVIDENCIA_VISUAL.md` and `docs/PRINTS_VISUAL_EVIDENCE_EN.md`: provenance of recovered runtime screenshots and conceptual images;
- `docs/assets/screenshots/flynn/`: archived product/runtime screenshots;
- `docs/assets/concepts/`: conceptual images kept separate from runtime evidence;
- `index.html`, `manifest.webmanifest`, `sw.js`, `icon.svg`: recovered web surface.

## Replicability

The repository is a historical archive; its contents do not certify a turnkey or independently reproduced runtime.

The isolated E01 experiment has its own preserved kit and runbook. The MAX records were not recovered. Flynn V2 resident databases, checkpoints and connectome arrays are inventoried by hash but remain only on the VM; they are not preserved in this repository or verified external storage.

English: [Replicability and limits](REPLICABILITY_EN.md) · [Replication runbook](docs/REPLICATION_RUNBOOK_EN.md)  
Portuguese originals: [REPLICABILITY.md](REPLICABILITY.md) · [docs/REPLICATION_RUNBOOK.md](docs/REPLICATION_RUNBOOK.md)

The code is published under the [Common Public Attribution License 1.0](LICENSE).

## Epistemic rule

```text
IMPLEMENT -> OBSERVE_REAL_RESULT -> VALIDATE -> CLOSE_OR_FIX_REAL_BLOCKER
```

Do not fabricate learning, autonomy, intention, causality or continuity that has not been observed.

Historical results preserve these explicit limits:

```text
ASSOCIATIVE_LEARNING_PROVEN=NO
REAL_WORLD_SPACE_LOCOMOTION_TO_FOOD=NOT_PROVEN
FULL_FEEDING_CYCLE_PROVEN=NO
MEMORY_LINEAR_GROWTH_FIXED=UNVERIFIED
FLYNN_TRIGGERED_ACCOUNT_SUSPENSION=UNPROVEN
RESOURCE_DELETION=UNPROVEN
```

## Historical continuity note

The historical Flynn resident and any future rehost are scientifically distinct temporal episodes.

```text
SOURCE_CODE_BACKUP != RESIDENT_STATE_BACKUP
REHOST != UNINTERRUPTED_CONTINUATION
```

That distinction is part of the experiment, not something to hide.
