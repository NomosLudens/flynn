# Flynn — Research Rehosting and Infrastructure

**Date:** 2026-09-21  
**Project:** Flynn  
**Repository:** https://github.com/NomosLudens/flynn  
**Nature:** non-commercial, public research / open knowledge

## Purpose

Flynn is an independent research project exploring persistent embodied computation using a biologically anchored neural substrate and explicit synthetic interfaces.

The historical system combined a connectome-derived neural core, continuous LIF dynamics, sensory transduction, persistent world state, homeostasis, descending-neuron readout and a synthetic body. The original resident runtime was interrupted when its previous cloud tenancy became unavailable.

The project is now being reopened as a research initiative. The goal is not to pretend that the interrupted resident survived. The goal is to reconstruct a new runtime from preserved public artifacts, study it rigorously, and publish what is learned.

## Why we are seeking sponsored infrastructure

The experiment depends on persistence.

Batch execution can reproduce isolated calculations, but it cannot answer the same questions as a continuously running system with persistent neural time, body state, world state, homeostasis and causal history.

A persistent server would allow us to investigate:

- continuous spiking-neural dynamics;
- restart and persistence behavior;
- long-running sensorimotor closed loops;
- homeostatic effects over neural time;
- memory and plasticity mechanisms;
- stability, resource consumption and failure modes;
- reproducibility of observations across controlled experimental runs.

The project is non-commercial. It does not sell access, subscriptions, products or advertising.

## Technical baseline

We intentionally request a modest starting configuration.

```text
Operating system: Linux x86_64
CPU: 2 vCPU
RAM: 4 GB
Disk: 40 GB SSD
Network: stable public connectivity
Runtime: continuous / long-running
Access: SSH
```

If the provider considers a different configuration more appropriate, the project can be adapted to the resources available.

The server would be used for the Flynn research runtime, experiment logging, public technical validation and reproducibility work. It would not be used for cryptocurrency mining, resale, commercial hosting, game hosting or unrelated workloads.

## Scientific basis

The preserved neural dataset is based on FlyWire FAFB v783:

```text
139,255 neurons
3,732,460 connection pairs
50,666,648 synapses
1,305 descending neurons
473 descending-neuron types
```

The project distinguishes biological ancestry from synthetic engineering boundaries. Synthetic interfaces are labelled as such; they are not represented as biological reconstructions.

## Open knowledge

We want infrastructure support to produce knowledge that can be returned to the community.

The repository is public, and the project commits to sharing, where technically and legally possible:

- source code;
- experiment protocols and runbooks;
- architecture documentation;
- reproducibility notes;
- validation evidence;
- negative results;
- resource and stability findings;
- limitations and unresolved questions.

We welcome inspection, replication, criticism and reuse under the repository license.

## Epistemic commitment

Flynn follows a strict rule:

```text
IMPLEMENT -> OBSERVE_REAL_RESULT -> VALIDATE -> CLOSE_OR_FIX_REAL_BLOCKER
```

A successful process, build or deployment is not treated as proof of scientific behavior. Claims are limited to what has actually been observed.

In particular, the project does not currently claim proven consciousness, sentience or associative learning.

## Hosting application summary

**Project category:** Science & Research / Open Source

**Short description**

Flynn is a non-commercial open research project studying persistent embodied computation around a connectome-derived spiking-neural core. We are rebuilding the experiment from preserved public code after the original cloud runtime was interrupted. The objective is academic and technical: to study continuous neural dynamics, persistence, homeostasis, sensorimotor coupling and the limits of what can legitimately be inferred from them, while publishing the code, protocols, evidence, failures and reproducibility notes for others to inspect and reuse.

**Technical justification**

Flynn requires a persistent Linux server because the research object is a continuous neural/body/world loop rather than a static site or batch-only program. Long-running uptime is needed to preserve neural time, homeostatic state, body/world state and causal experiment history, and to test restart/persistence behavior under real conditions. A modest 2 vCPU, 4 GB RAM and 40 GB SSD Linux VPS is sufficient for the first stage. The workload is non-commercial and research-only. Any resulting technical knowledge, reproducibility procedures and validated findings will be returned to the public repository.
