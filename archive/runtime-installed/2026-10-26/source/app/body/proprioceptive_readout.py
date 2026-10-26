"""Factual synthetic sensor readout of the current LETHE body state.

This module measures the existing Pinocchio state and canonical sigil graph.
It intentionally does not choose a neural target or convert measurements to
LIF conductance; that projection remains an explicit scientific/authorial
decision.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from .pinocchio_sigil import SIGIL_EDGES, SIGIL_MODULES, SIGIL_PARENT, PinocchioSigilBody


class SyntheticProprioceptiveReadout:
    """Read joint, node, and edge geometry without inventing forces or strain."""

    def __init__(self, body: PinocchioSigilBody):
        self.body = body
        self._tree_pairs = {frozenset((parent, child)) for child, parent in SIGIL_PARENT.items()}

    def sample(self, *, sequence: int, time_ms: float, timestamp_utc: str) -> dict[str, Any]:
        if sequence < 0 or not math.isfinite(time_ms) or time_ms < 0 or not timestamp_utc:
            raise ValueError("proprioceptive sample requires a valid sequence, time, and timestamp")
        body = self.body
        node_positions: dict[str, list[float]] = {}
        node_velocities: dict[str, list[float]] = {}
        for name, frame_id in body.frame_ids.items():
            placement = body.data.oMf[frame_id]
            velocity = body.pin.getFrameVelocity(
                body.model, body.data, frame_id, body.pin.LOCAL_WORLD_ALIGNED
            )
            node_positions[name] = [float(x) for x in placement.translation]
            node_velocities[name] = [float(x) for x in velocity.linear]

        edge_states = []
        for source, target in SIGIL_EDGES:
            p0 = np.asarray(node_positions[source], dtype=float)
            p1 = np.asarray(node_positions[target], dtype=float)
            length = float(np.linalg.norm(p1 - p0))
            initial = math.hypot(
                SIGIL_MODULES[target]["x"] - SIGIL_MODULES[source]["x"],
                SIGIL_MODULES[target]["y"] - SIGIL_MODULES[source]["y"],
            )
            dynamic_link = frozenset((source, target)) in self._tree_pairs
            edge_states.append({
                "source": source,
                "target": target,
                "canonical_length_sigil_units": initial,
                "observed_length_sigil_units": length,
                "length_delta_sigil_units": length - initial,
                "dynamic_joint_link": dynamic_link,
                "mechanical_constraint": "RIGID_LINK_IN_PINOCCHIO_TREE" if dynamic_link else "NONE_GRAPH_EDGE_ONLY",
                "length_delta_interpretation": "JOINT_LINK_LENGTH_RESIDUAL_NOT_MATERIAL_STRAIN"
                    if dynamic_link else "ENDPOINT_SEPARATION_ONLY_NOT_MATERIAL_STRAIN",
                "tension": None,
            })

        return {
            "schema": "flynn.synthetic_proprioceptive_readout.v1",
            "source": "PinocchioSigilBody",
            "provenance": "SYNTHETIC_BODY_STATE_MEASUREMENT_NOT_BIOLOGICAL_SENSOR",
            "sequence": sequence,
            "time_ms": float(time_ms),
            "timestamp_utc": timestamp_utc,
            "units": {
                "q": "radian",
                "qdot": "radian_per_second",
                "node_position": "sigil_coordinate_units",
                "node_linear_velocity": "sigil_coordinate_units_per_second",
                "edge_lengths": "sigil_coordinate_units",
                "tension": "not_computed",
            },
            "body_model": {
                "node_count": len(node_positions),
                "canonical_edge_count": len(SIGIL_EDGES),
                "dynamic_tree_link_count": len(self._tree_pairs),
                "graph_only_edge_count": len(SIGIL_EDGES) - len(self._tree_pairs),
                "central_eb_anchored": False,
                "base_joint_model": "PINOCCHIO_PLANAR_XY_YAW_SYNTHETIC",
                "graph_only_edges_are_mechanical_constraints": False,
            },
            "q": [float(x) for x in body.q],
            "qdot": [float(x) for x in body.qdot],
            "base_state": body.state_snapshot()["base_state"],
            "joint_state_by_name": {
                name: {
                    "q_index": int(body.model.joints[joint_id].idx_q),
                    "qdot_index": int(body.model.joints[joint_id].idx_v),
                    "position_rad": float(body.q[body.model.joints[joint_id].idx_q]),
                    "velocity_rad_per_second": float(body.qdot[body.model.joints[joint_id].idx_v]),
                }
                for name, joint_id in body.joint_ids.items()
                if name != body.ROOT
            },
            "nodes": {
                name: {"position": node_positions[name], "linear_velocity": node_velocities[name]}
                for name in body.frame_ids
            },
            "edges": edge_states,
            "centroid": [float(x) for x in body.physical_centroid()],
            "global_translation": "PINOCCHIO_PLANAR_XY_YAW",
            "computed_tensions": None,
            "neural_projection": "BLOCKED_NO_APPROVED_NEURAL_TARGET_OR_TRANSDUCTION_GAIN",
        }
