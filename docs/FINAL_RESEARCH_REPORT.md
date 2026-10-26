# Flynn V2: final research report and archive

**Project:** `NomosLudens/flynn`  
**Mission:** `FLYNN_FINAL_ARCHIVE_2026-10-26`  
**Project status:** `ENDED`  
**Full causal loop:** `NOT_DEMONSTRATED`  
**Final scientific verdict:** partial experimental integration; not a demonstrated embodied neural organism.

## Abstract

Flynn V2 installed a connectome-derived LIF network based on FlyWire FAFB v783, a synthetic visual-light transducer, descending population readout, deterministic PicoClaw coordination, a Pinocchio sigil body, body-derived proprioception and a CPU-budget homeostasis model. In the resident observation, global synthetic light produced persisted spikes among 11,118 visual roots. Descending neurons remained silent, motor torque remained zero, the body did not move, and no effective proprioceptive input reached a later neural frame. A 30-minute real-time observation advanced approximately 1,380 ms of neural time. The full causal loop was not demonstrated. The resident later failed after SQLite lock errors and automatic starts rejected a checkpoint without its required atomic confirmed-cycle record. No further experiment or recovery attempt is authorized by this archival mission.

## 1. Introduction and objective

The research objective was to explore whether a persistent, connectome-anchored spiking model could operate with synthetic sensory input and an embodied feedback loop. The implementation aimed to preserve episode identity, generations, checkpoints and data provenance. The project deliberately does not claim consciousness, sentience, learning or biological equivalence.

## 2. Scientific background

The structural substrate came from the FlyWire adult female *Drosophila melanogaster* FAFB v783 connectome. The installed signed CSR is a runtime preprocessing of structural connectivity and predicted sign information. The LIF model is a simplified point-neuron model. Pinocchio provides rigid-body algorithms; it does not supply or validate the Flynn sigil's geometry. See [neural model](NEURAL_MODEL.md) and [embodiment](EMBODIMENT.md).

## 3. Method

The installed resident advanced the LIF state at 0.1-ms steps, used a 20-ms neural coordinator cycle, persisted events/states/checkpoint cursors in SQLite, and exposed `set_illumination` through an existing restricted command path. The visual transducer mapped a global scalar into conductance for 11,118 visual roots. The body model used a synthetic planar X/Y/yaw base and 22 selected tree links. Homeostasis debited measured process CPU costs against a normalized 3,600-CPU-second reserve. The archive used only existing VM, GitHub and storage access; no credentials or cloud services were created.

## 4. Architecture and provenance

At capture, the VM source directory was `/home/tonyus-dev/flynn-v2-vm-validation-20261019/resident-app`; systemd invoked the runtime package's Python 3.10 environment. The VM tree had no Git metadata sufficient to identify a source commit. A 31-file Python source snapshot is preserved under `archive/runtime-installed/2026-10-26/source/` with the VM SHA-256 manifest. Against public `master` at `f69f6c0d2193e128df97ca58cabca75c06636172`, 8 files matched byte-for-byte, 4 differed, and 19 were absent. Exact per-file results are in `archive/runtime-installed/2026-10-26/README.md`.

## 5. Experiments and results

The visual command reached the mapped visual population and was followed by persisted spikes. Aggregate windows contained 381,696 to 1,021,001 spikes, with Desc activity zero throughout the sampled windows. PicoClaw receipts were confirmed for coordination, but the motor status was zero torque and observation-only. Pinocchio step dispatch did not produce a body displacement. Proprioceptive transduction reported no physical deviation and zero neural targets. See [experimental results](EXPERIMENTAL_RESULTS.md).

The observed 30-minute interval advanced approximately 1,380 ms neural time. Stage measurements showed the neural core and aggregation as the largest CPU cost. These rates belong to that measured run only.

## 6. Persistence and incidents

The current episode-5 causal cursor is episode `resident-v2:flynn-1gb:19bc839e52474f3f9a3ec12eefaf1647`, generation `ffc7f14f56c149268e695faaf40a0451`, tick 87,800. Persisted records reach 8,800 ms but that cycle lacks the atomic confirmation record required for a restorable boundary. Two lock errors and subsequent failed automatic starts are recorded in [incident history](INCIDENT_HISTORY.md). The last observed service state is failed; no restore was attempted in this mission.

Earlier episode-3 history has Cloud Storage catalog coverage to tick 3,786,800, across multiple generations. Local episode-3 data reaches tick 4,468,400. Episode 5 and data after that earlier archive boundary remain on the VM. The SHA-256 manifest lists all inventoried episode databases, checkpoint arrays and archive metadata; it is not a copy of their contents.

## 7. Discussion and limitations

Input-driven activity and component coordination were observed. They do not close the neural, motor, body or proprioceptive loop. The global-light input was not a calibrated visual scene; motor readout was a deterministic instrumental mapping; eight sigil edges remained structural only; the base was synthetic and free. The homeostasis model represented measured CPU use, not metabolism. The VM's limited RAM/disk and measured slow neural-time progression constrained the experiment. These limitations are detailed in [scientific limitations](SCIENTIFIC_LIMITATIONS.md).

## 8. Conclusion

Flynn V2 is archived as an experimental software system with partial runtime evidence and a negative closed-loop result. The research project is ended. The public code/docs archive does not include the current SQLite episode databases, checkpoint arrays or the remaining connectome assets. Those data remain on the VM pending a separate preservation decision; the VM must not be deleted while they are the only copy.

## References

1. Dorkenwald et al. (2024), “Neuronal wiring diagram of an adult brain,” *Nature* 634, 124–138. [https://doi.org/10.1038/s41586-024-07558-y](https://doi.org/10.1038/s41586-024-07558-y).
2. Schlegel et al. (2024), “Whole-brain annotation and multi-connectome cell typing of Drosophila.” [https://doi.org/10.1038/s41586-024-07686-5](https://doi.org/10.1038/s41586-024-07686-5).
3. Shiu et al. (2024), “A Drosophila computational brain model reveals sensorimotor processing.” [https://doi.org/10.1038/s41586-024-07763-9](https://doi.org/10.1038/s41586-024-07763-9).
4. Abbott (1999), “Lapicque’s introduction of the integrate-and-fire model neuron (1907).” [https://doi.org/10.1016/S0361-9230(99)00161-6](https://doi.org/10.1016/S0361-9230(99)00161-6).
5. Carpentier et al. (2019), “The Pinocchio C++ library.” [https://doi.org/10.1109/SII.2019.8700380](https://doi.org/10.1109/SII.2019.8700380).
