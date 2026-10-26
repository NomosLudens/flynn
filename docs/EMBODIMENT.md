# Embodiment and morphology

The installed Pinocchio body is a synthetic realization of the Flynn/LETHE sigil, not a reconstructed fly body. The source recovered 23 named glyph modules, 30 canonical graph edges and a 22-link parent tree used by the dynamics model.

## Physical model and structural graph

The 22 parent-tree links are the dynamic tree selected by `SIGIL_PARENT`. The other eight canonical edges are retained as graph/display relationships only. The runtime explicitly records `graph_only_edges_are_mechanical_constraints=false`; there is no evidence that they should be treated as joints, rigid links or contact constraints.

The eight graph-only edges are:

1. `OPTIC_L → DN_TAKEOFF`
2. `OPTIC_R → DN_TAKEOFF`
3. `OPTIC_R → DN_LONG_MODE`
4. `AUDITORY_L → DN_STEERING`
5. `AUDITORY_R → DN_STEERING`
6. `SUPERIOR_R → FEMALE_HUB`
7. `CIRCADIAN_PACEMAKER → SUPERIOR_R`
8. `VENTROLAT_R → DN_TAKEOFF`

The free root is `JointModelPlanar`, providing synthetic X/Y/yaw coordinates. The body metadata labels it `PINOCCHIO_PLANAR_XY_YAW_SYNTHETIC`; it does not anchor the base to the central ellipsoid. A proprioception description called the frame “CENTRAL_EB anchored,” so these metadata are inconsistent. No physical ground contact or validated glifo locomotion was established.

The model applies deterministic contrast-based actuation over sorted descending-neuron indices. That adapter is an instrumental mapping, not an anatomical motor-unit correspondence. When descending activity was zero, requested and executed torques were zero. Pinocchio step dispatch was observed, but the pose and velocity remained static.

## Proprioceptive return

The transducer manifest contained 2,646 mechanosensory roots. Its values were derived from the Pinocchio joint positions and velocities. The resident body did not move, so sampled transduction reported `NO_PHYSICAL_DEVIATION_NO_NEURAL_INPUT` and `proprioceptive_target_count=0`. Persisting a body checkpoint or proprioception record is not evidence that a nonzero proprioceptive signal entered a subsequent LIF step.

## Dependency

The VM package inventory identified Pinocchio distribution `pin==4.1.0` and `cmeel==0.61.0` in the dedicated Pinocchio Python environment (NumPy 2.2.6). Import required the unit's native-library path; an unconfigured shell import failed to resolve `libgomp.so.1`. Pinocchio is a rigid-body dynamics library; using it does not validate the supplied sigil geometry or its mechanics. [Official Pinocchio documentation](https://gepetto.github.io/doc/pinocchio/doxygen-html/) and Carpentier et al., “The Pinocchio C++ library,” [DOI 10.1109/SII.2019.8700380](https://doi.org/10.1109/SII.2019.8700380).
