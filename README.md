# Flynn — open research archive and rehosting initiative

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
PROJECT_STATUS=RESEARCH_REOPENING
RESEARCH_STATUS=ACTIVE_REHOSTING_PREPARATION
CURRENT_RUNTIME_STATUS=OFFLINE_PENDING_REHOST

FORMER_AUTHORITATIVE_HOST=MAX
FORMER_PROVIDER=ORACLE_CLOUD
RESIDENT_CONTINUITY_INTERRUPTED_EXTERNALLY=YES

NON_COMMERCIAL=YES
PUBLIC_REPOSITORY=YES
OPEN_KNOWLEDGE_COMMITMENT=YES
HOSTING_SPONSORSHIP=SEEKING
```

The original resident runtime became unavailable after the Oracle Cloud tenancy that hosted MAX was suspended. That interruption broke the resident's temporal continuity.

**A future rehost will not be presented as uninterrupted continuation of the former resident.** It will be a new research runtime reconstructed from the public code and preserved evidence.

The previous `RETIRED_FROZEN` state remains part of the historical record. On **2026-09-21**, the project was reopened specifically as a non-commercial research and open-knowledge initiative seeking suitable persistent infrastructure.

## Research purpose

Flynn exists for academic and technical inquiry, not commercial exploitation.

The research questions include:

- what persistent spiking-neural dynamics look like when coupled to an embodied closed loop;
- how a biologically anchored neural core interacts with synthetic sensory and motor boundaries;
- how temporal continuity, homeostasis, memory mechanisms and persistent state affect observed behavior;
- what can and cannot legitimately be inferred from recurrent LIF activity and connectome-derived structure;
- how to make experiments of this kind reproducible, inspectable and useful to other researchers, students and independent builders.

The project deliberately distinguishes observed results from interpretation. No claim of consciousness, sentience, associative learning or biological equivalence is made without evidence.

## Open knowledge commitment

Flynn is being reopened with a simple principle: **if the infrastructure enables the experiment, the resulting technical knowledge should be shared back.**

The repository is public. We intend to preserve and publish:

- source code and architecture;
- reproducible experimental runbooks;
- infrastructure notes where they are safe to publish;
- technical failures and negative results;
- validation evidence;
- research notes and limitations;
- improvements required to reproduce the system independently.

The goal is not only to run Flynn again, but to make the work useful as a shared technical research object.

See [Research rehosting and infrastructure](docs/RESEARCH_REHOSTING.md).

## Why persistent infrastructure matters

This is not a static website. The experimental object depends on **continuous runtime and persistent state**.

A suitable research host allows us to maintain:

- continuous neural time rather than isolated batch replays;
- persistent world/body/homeostatic state;
- append-only causal history;
- controlled restart and persistence experiments;
- long-running observations;
- reproducible public demonstrations and technical validation.

A modest Linux VPS is sufficient for the first rehosting stage. Our baseline request is:

```text
OS=Linux x86_64
CPU=2 vCPU
RAM=4 GB
DISK=40 GB SSD
NETWORK=stable public connectivity
UPTIME=continuous research runtime
```

More resources are useful but not required to begin.

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

The English documentation is intended to make the project directly reviewable by hosting sponsors, researchers, students and independent developers:

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

The repository is both an archive and a basis for renewed research.

The isolated E01 experiment has its own preserved kit and runbook. The original resident databases, canonical ledger and checkpoints that existed only on MAX are **not** represented as recovered.

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
