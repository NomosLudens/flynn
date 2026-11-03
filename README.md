# FLYNN — EM DESENVOLVIMENTO

> **Estado atual (03/11/2026): EM DESENVOLVIMENTO — nova fase experimental.**
>
> A **FLYNN V2 foi encerrada em 26/10/2026** e seus resultados permanecem preservados. A implementação demonstrou processamento de estímulos simulados, atividade neural e persistência experimental, mas **não demonstrou o ciclo causal neuromotor completo**. O encerramento daquela fase não equivale ao encerramento definitivo da pesquisa.
>
> **Retomada com apoio da [RackGenius](https://rackgenius.com/):** VPS de 2 GB concedida por um ano para a pesquisa independente, não comercial e aberta da FLYNN. O serviço foi criado em 03/11/2026; instalação do sistema operacional, acesso SSH e execução científica na nova máquina **ainda não foram validados**. Uma nova execução será um **novo episódio experimental**, jamais a continuidade fictícia da residente antiga.
>
> **Preservação dos dados identificados: `COMPLETE`.** Bancos, metadados, checkpoints, arrays CSR FAFB-v783 e todos os 23 objetos do arquivo histórico GCS foram recuperados e publicados na [Release final](https://github.com/NomosLudens/flynn/releases/tag/v2.0-research-closed). Hashes SHA-256/digests e checksums GCS conferem. O tick 88.000 do episódio 5 está preservado, mas continua não confirmado. Os arrays CSR seguem aviso conservador CC BY-NC 4.0, com a divergência FlyWire/Zenodo documentada.

## Arquivo histórico — encerramento da FLYNN V2 em 26/10/2026

- [Relatório científico final](docs/FINAL_RESEARCH_REPORT.md)
- [Análise técnica e científica da falha](docs/FINAL_FAILURE_ANALYSIS.md)
- [Histórico de incidentes](docs/INCIDENT_HISTORY.md)
- [Postmortem do processo de desenvolvimento](docs/DEVELOPMENT_PROCESS_POSTMORTEM.md)
- [Resultados experimentais finais](docs/EXPERIMENTAL_RESULTS_FINAL.md)
- [Arquitetura final](docs/FINAL_ARCHITECTURE.md)
- [Estado de reprodutibilidade](docs/REPRODUCIBILITY_STATUS.md)
- [Inventário de descomissionamento — não executado](docs/DECOMMISSION_INVENTORY.md)
- [Snapshot dos 31 arquivos instalados](archive/runtime-installed/2026-10-26/README.md)
- [Hash dos arquivos de código](archive/runtime-installed/2026-10-26/source.sha256)
- [Manifesto de dados/checkpoints — hashes e caminhos, sem payloads](archive/runtime-installed/2026-10-26/data-preservation/data.sha256)
- [Estado da preservação dos dados e hashes](archive/runtime-installed/2026-10-26/data-preservation/STATUS.md)

A história original do desenvolvimento permanece acessível nos documentos e registros históricos abaixo. As conclusões finais se referem somente à implementação e às evidências observadas.

> **Non-commercial research project · public repository · open knowledge**

Flynn is an experimental neuro-synthetic research project that studies what can be learned from running a biologically anchored neural core inside a persistent sensorimotor loop.

The intended component path was:

```text
world → sensory transduction → continuous LIF brain → descending readout
→ Pinocchio body dynamics → Lethe synthetic morphology → world
```

The neural substrate is derived from the **FlyWire FAFB v783** adult female *Drosophila melanogaster* connectome. The historical runtime used a continuous LIF implementation, a persistent world, homeostatic state, an append-only causal ledger and a synthetic body represented by the Lethe sigil.

## Acknowledgment — RackGenius infrastructure support

On **2026-11-03**, [RackGenius](https://rackgenius.com/), through its **Genius Impact** initiative, approved one year of sponsored infrastructure for Flynn's independent, non-commercial, open research. Special thanks to **Ethan Boucon**, founder and co-owner, for supporting the project.

- **Provisioned service:** 2GB Value KVM VPS in **Detroit, Michigan, USA** (Detroit replaced the initially proposed Grand Rapids location due to inventory).
- **Commercial terms confirmed by email:** US$0.00 at activation, annual billing cycle, next due date **2027-11-03**. At the end of the year, eligibility may be re-verified through RackGenius or a paid renewal chosen; **no free renewal is assumed**.
- **Operational boundary:** the hosting account and VPS service were activated, but Linux installation, SSH access, network reachability, persistence and the research runtime have **not yet been tested on this VPS**.
- **Capacity boundary:** this 2 GB plan is below the historical 4 GB RAM baseline proposal. Suitability for the full neural workload must be measured; infrastructure sponsorship does not establish scientific or product functionality.

This support enables a new experimental development stage; it does not restore the temporal continuity of any previous resident. Historical failures, negative results and reports remain available and unchanged.

See [Research rehosting and infrastructure](docs/RESEARCH_REHOSTING.md).

## Current status

```text
PROJECT=FLYNN
PROJECT_STATUS=EM_DESENVOLVIMENTO
RESEARCH_STATUS=NEW_EXPERIMENTAL_PHASE_PREPARATION
CURRENT_RUNTIME_STATUS=NOT_VALIDATED_ON_RACKGENIUS
NEW_PHASE_STARTED=2026-11-03
INFRASTRUCTURE_SPONSOR=RACKGENIUS
RACKGENIUS_VPS=2GB_VALUE_KVM_VPS_PROVISIONED
RACKGENIUS_LOCATION=DETROIT_MI_USA
RACKGENIUS_OS_INSTALL=PENDING
RACKGENIUS_SSH=PENDING
RACKGENIUS_NEXT_DUE_DATE=2027-11-03
HISTORICAL_FLYNN_V2_STATUS=ENDED_2026-10-26
HISTORICAL_V2_LAST_OBSERVED_RUNTIME_STATUS=FAILED_AFTER_RESTART_LIMIT
HISTORICAL_V2_LAST_OBSERVED_AT_UTC=2026-10-26T15:43:26Z
FULL_CAUSAL_LOOP=NOT_DEMONSTRATED
ARCHIVE_STATUS=PARTIAL_PENDING_DATA_DECISION

FORMER_AUTHORITATIVE_HOST=MAX
FORMER_PROVIDER=ORACLE_CLOUD
RESIDENT_CONTINUITY_INTERRUPTED_EXTERNALLY=YES

NON_COMMERCIAL=YES
PUBLIC_REPOSITORY=YES
OPEN_KNOWLEDGE_COMMITMENT=YES
```

The historical FLYNN V2 phase ended on **2026-10-26**; a **new development stage began on 2026-11-03**. The former Oracle-hosted MAX runtime, the later Flynn V2 runtime on `flynn-1gb` and any future RackGenius runtime are separate experimental episodes. The V2 installation ran, but a complete neural-to-body causal loop was not demonstrated. On 2026-10-26 the VM was read through its existing IAP SSH path; `flynn-v2-resident.service` remained failed. The resident was not restarted. Nothing in the new infrastructure award changes that historical conclusion.

The historical reopening on **2026-09-21** remains part of the record. The recovered episode 3 and episode 5 databases/checkpoints and the FAFB-v783 CSR arrays are downloadable from the final GitHub Release. SHA-256 digests match the source-side and local files. The data notice applies the stricter CC BY-NC 4.0 non-commercial condition and documents the FlyWire/Zenodo metadata discrepancy.

## Research purpose

Flynn is an independent, non-commercial academic and technical inquiry, now entering a new experimental stage.

The research questions include:

- what persistent spiking-neural dynamics look like when coupled to an embodied closed loop;
- how a biologically anchored neural core interacts with synthetic sensory and motor boundaries;
- how temporal continuity, homeostasis, memory mechanisms and persistent state affect observed behavior;
- what can and cannot legitimately be inferred from recurrent LIF activity and connectome-derived structure;
- how to make experiments of this kind reproducible, inspectable and useful to other researchers, students and independent builders.

The project deliberately distinguishes observed results from interpretation. No claim of consciousness, sentience, associative learning or biological equivalence is made without evidence.

## Open knowledge commitment

The historical archive and renewed research follow a simple principle: **share the technical knowledge, failures and negative results produced by the experiment.**

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

## Historical FLYNN V2 archive — 2026-10-26

`FULL_CAUSAL_LOOP=NOT_DEMONSTRATED`: visual LIF activity was persisted, while descending activity, nonzero actuation, body displacement and effective proprioceptive return were not demonstrated. The installed source snapshot is preserved with per-file SHA-256 hashes and an explicit comparison against the public repository revision. The final Release contains the identified episode databases, metadata, checkpoints and connectome CSR arrays; see `PRESERVATION_MANIFEST_v2.json` and the conservative data-license notice. Tick 88,000 remains an unconfirmed checkpoint, not a verified causal boundary.

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

The repository preserves the historical research archive and documents a new development phase; its contents do not certify a turnkey or independently reproduced runtime.

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

A new experimental rehost is planned on the RackGenius VPS. If deployed, it will be a scientifically distinct temporal episode, not a continuation of the historical resident. No new running resident has been validated as of 2026-11-03.

```text
SOURCE_CODE_BACKUP != RESIDENT_STATE_BACKUP
REHOST != UNINTERRUPTED_CONTINUATION
```

That distinction is part of the experiment, not something to hide.
