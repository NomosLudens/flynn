# Neural model and connectome

**Status:** an experimental connectome-derived LIF network ran; biological equivalence and closed-loop behavior were not demonstrated.

## Source and mapping

The installed matrix was identified as FlyWire FAFB release v783, with a canonical ordered population of 139,255 root IDs. Runtime manifest metadata identifies a signed Shiu CSR with 15,091,983 directed source/target pairs and 54,492,922 synapses. Direction is presynaptic root ID to postsynaptic root ID; the sign rule is `Excitatory * Connectivity`. Runtime matrix SHA-256: `efeb23fb99098e9c390f6869969b2a121a2ee92c833cfc45ecb2c1d8e1af0347`. Ordered root-map SHA-256: `b0c012e1e5abc6242e4f620e666216d2928c9821c1ad9cef0b61117a9d3c0240`.

The runtime kept root IDs and compact indices aligned in the sampled neural activity frames. The descending manifest contained 1,303 unique roots, all represented in the canonical population. `DescendingReadoutV2` checked the root/index pair against the population map. No cross-index mismatch was found in the observed path.

The Connectome CSR arrays are installed outside the Git checkout under the VM's dated package tree. The arrays were not copied to GitHub: they are large data assets with their own upstream provenance and license terms. The source snapshot and checksums preserve the runtime code identity, not those array bytes.

## LIF state machine

The installed model ID is `shiu-lif-experimental-v783-flynn-v1`. It uses float64 state arrays and explicit time steps:

| Parameter | Value |
|---|---:|
| Rest and reset voltage | −52 mV |
| Threshold | −45 mV |
| Membrane time constant | 20 ms |
| Synaptic time constant | 5 ms |
| Refractory period | 2.2 ms |
| Directed synaptic delay | 1.8 ms |
| Synaptic weight | 0.275 mV per signed count |
| Time step | 0.1 ms |

The implementation advances every neuron on every tick and schedules outgoing CSR edges only when a source spikes. It does not add spontaneous spikes or behavioral drive. Checkpoints retain voltage, conductance, refractory deadlines, delayed input slots and frame spike counts. These rules are a computational model, not a calibrated biophysical reconstruction.

## Resident sensory observation

The instantiated sensory transducers were visual light and body-derived synthetic proprioception. The visual map selected 11,118 roots annotated as R1-6, R7 or R8. A full normalized global light command (`1.0`) applied `0.5` conductance per tick to that target set. It was explicitly labeled `INSTRUMENTAL_SYNTHETIC_NOT_BIOPHYSICAL`.

In sampled 1-second aggregate windows from 4,020 through 8,020 ms, the visual roots spiked and each window contained roughly 1.0 million total spikes. The descending readout remained at zero. The aggregate population therefore proves neural activity under the synthetic drive; it does not establish meaningful visual perception, behavior, learning, or a failure of the readout.

The installed matrix had three direct visual-to-descending edges. Their existence alone does not prove an effective path under this global scalar stimulus. The direct mechanosensory-to-descending edge count was 22,576, but no body deviation drove that sensor in the resident observation.

## References

1. Dorkenwald et al., “Neuronal wiring diagram of an adult brain,” *Nature* 634, 124–138 (2024), analysis based on FlyWire v783. [Paper and version statement](https://doi.org/10.1038/s41586-024-07558-y).
2. Schlegel et al., “Whole-brain annotation and multi-connectome cell typing of Drosophila,” *Nature* (2024). [Paper](https://doi.org/10.1038/s41586-024-07686-5).
3. Shiu et al., “A Drosophila computational brain model reveals sensorimotor processing,” *Nature* (2024). [Paper](https://doi.org/10.1038/s41586-024-07763-9).
4. Abbott, “Lapicque’s introduction of the integrate-and-fire model neuron (1907),” *Brain Research Bulletin* 50(5–6), 303–304 (1999). [Paper](https://doi.org/10.1016/S0361-9230(99)00161-6).
