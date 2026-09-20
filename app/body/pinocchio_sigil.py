"""Live Pinocchio embodiment of the canonical Lethe sigil graph.

This is deliberately a transparent engineering boundary.  It does not select
behaviour, read homeostasis, or interpret the named DN channels.  Every
descending neuron contributes to a deterministic bucketed torque vector, and
Pinocchio owns the persistent generalized state and forward kinematics.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import numpy as np


_PINOCCHIO_SITE = Path(
    "/home/ubuntu/Portifolio/flynn-max/runtime/research/embodiment_e01/.venv/lib/python3.12/site-packages"
)


def _load_pinocchio():
    try:
        import pinocchio as pin
        return pin
    except ImportError:
        # Reuse the already validated isolated E01 wheel.  The resident venv
        # remains unchanged; this only adds an import search path in-process.
        prefix = _PINOCCHIO_SITE / "cmeel.prefix"
        for candidate in (
            prefix / "lib/python3.12/site-packages",
            _PINOCCHIO_SITE,
        ):
            if candidate.exists() and str(candidate) not in sys.path:
                sys.path.insert(0, str(candidate))
        import pinocchio as pin
        return pin


# Exact node identity, positions, radii, and edges recovered from the
# canonical runtime/app/web/static/index.html BASE_MODULES/BASE_EDGES.
SIGIL_MODULES = {
    "OPTIC_L": {"x": -0.80, "y": -0.12, "r": 0.12, "side": "L"},
    "OPTIC_R": {"x": 0.80, "y": -0.12, "r": 0.12, "side": "R"},
    "ANTENNAL_L": {"x": -0.42, "y": 0.28, "r": 0.08, "side": "L"},
    "ANTENNAL_R": {"x": 0.42, "y": 0.28, "r": 0.08, "side": "R"},
    "AUDITORY_L": {"x": -0.58, "y": 0.06, "r": 0.09, "side": "L"},
    "AUDITORY_R": {"x": 0.58, "y": 0.06, "r": 0.09, "side": "R"},
    "GNATHAL_SEZ": {"x": 0.0, "y": 0.52, "r": 0.11, "side": "M"},
    "MUSHROOM_L": {"x": -0.30, "y": -0.34, "r": 0.09, "side": "L"},
    "MUSHROOM_R": {"x": 0.30, "y": -0.34, "r": 0.09, "side": "R"},
    "CENTRAL_EB": {"x": 0.0, "y": -0.05, "r": 0.09, "side": "M"},
    "CENTRAL_FB": {"x": 0.0, "y": -0.22, "r": 0.10, "side": "M"},
    "SUPERIOR_L": {"x": -0.34, "y": -0.12, "r": 0.09, "side": "L"},
    "SUPERIOR_R": {"x": 0.34, "y": -0.12, "r": 0.09, "side": "R"},
    "VENTROLAT_L": {"x": -0.52, "y": -0.25, "r": 0.10, "side": "L"},
    "VENTROLAT_R": {"x": 0.52, "y": -0.25, "r": 0.10, "side": "R"},
    "FEMALE_HUB": {"x": 0.0, "y": 0.14, "r": 0.08, "side": "M"},
    "CIRCADIAN_PACEMAKER": {"x": 0.0, "y": -0.42, "r": 0.07, "side": "M"},
    "DN_TAKEOFF": {"x": 0.0, "y": -0.68, "r": 0.08, "side": "M"},
    "DN_LONG_MODE": {"x": 0.22, "y": -0.62, "r": 0.07, "side": "M"},
    "DN_STEERING": {"x": -0.22, "y": -0.62, "r": 0.07, "side": "M"},
    "DN_FEEDING": {"x": 0.0, "y": 0.76, "r": 0.09, "side": "M"},
    "DN_CANDIDATE": {"x": 0.34, "y": 0.62, "r": 0.08, "side": "M"},
    "DN_UNKNOWN": {"x": -0.34, "y": 0.62, "r": 0.08, "side": "M"},
}

SIGIL_EDGES = [
    ("OPTIC_L", "VENTROLAT_L"), ("OPTIC_R", "VENTROLAT_R"),
    ("OPTIC_L", "DN_TAKEOFF"), ("OPTIC_R", "DN_TAKEOFF"),
    ("OPTIC_L", "DN_LONG_MODE"), ("OPTIC_R", "DN_LONG_MODE"),
    ("ANTENNAL_L", "MUSHROOM_L"), ("ANTENNAL_R", "MUSHROOM_R"),
    ("AUDITORY_L", "VENTROLAT_L"), ("AUDITORY_R", "VENTROLAT_R"),
    ("AUDITORY_L", "DN_STEERING"), ("AUDITORY_R", "DN_STEERING"),
    ("GNATHAL_SEZ", "DN_FEEDING"), ("GNATHAL_SEZ", "DN_CANDIDATE"),
    ("GNATHAL_SEZ", "DN_UNKNOWN"),
    ("MUSHROOM_L", "SUPERIOR_L"), ("MUSHROOM_R", "SUPERIOR_R"),
    ("SUPERIOR_L", "CENTRAL_FB"), ("SUPERIOR_R", "CENTRAL_FB"),
    ("CENTRAL_FB", "CENTRAL_EB"), ("CENTRAL_EB", "DN_STEERING"),
    ("SUPERIOR_L", "FEMALE_HUB"), ("SUPERIOR_R", "FEMALE_HUB"),
    ("FEMALE_HUB", "GNATHAL_SEZ"),
    ("CIRCADIAN_PACEMAKER", "SUPERIOR_L"),
    ("CIRCADIAN_PACEMAKER", "SUPERIOR_R"),
    ("VENTROLAT_L", "SUPERIOR_L"), ("VENTROLAT_R", "SUPERIOR_R"),
    ("VENTROLAT_L", "DN_TAKEOFF"), ("VENTROLAT_R", "DN_TAKEOFF"),
]

# A spanning tree for Pinocchio.  The eight remaining canonical edges stay
# as live connective graph edges in the renderer; no canonical edge is lost.
SIGIL_PARENT = {
    "CENTRAL_FB": "CENTRAL_EB", "DN_STEERING": "CENTRAL_EB",
    "SUPERIOR_L": "CENTRAL_FB", "SUPERIOR_R": "CENTRAL_FB",
    "MUSHROOM_L": "SUPERIOR_L", "MUSHROOM_R": "SUPERIOR_R",
    "VENTROLAT_L": "SUPERIOR_L", "VENTROLAT_R": "SUPERIOR_R",
    "FEMALE_HUB": "SUPERIOR_L", "GNATHAL_SEZ": "FEMALE_HUB",
    "DN_FEEDING": "GNATHAL_SEZ", "DN_CANDIDATE": "GNATHAL_SEZ",
    "DN_UNKNOWN": "GNATHAL_SEZ", "ANTENNAL_L": "MUSHROOM_L",
    "ANTENNAL_R": "MUSHROOM_R", "OPTIC_L": "VENTROLAT_L",
    "OPTIC_R": "VENTROLAT_R", "AUDITORY_L": "VENTROLAT_L",
    "AUDITORY_R": "VENTROLAT_R", "DN_TAKEOFF": "VENTROLAT_L",
    "DN_LONG_MODE": "OPTIC_L", "CIRCADIAN_PACEMAKER": "SUPERIOR_L",
}


class PinocchioSigilBody:
    """Persistent 22-DOF kinematic/dynamic realization of the 23-node sigil."""

    ROOT = "CENTRAL_EB"
    DT_SEC = 0.020
    MAX_TORQUE = 0.010
    MAX_SPEED = 1.0

    def __init__(self, dn_idx: np.ndarray, chunk_ms: float):
        self.pin = _load_pinocchio()
        self.chunk_ms = float(chunk_ms)
        self.dn_idx = np.asarray(dn_idx, dtype=np.int64)
        if self.dn_idx.ndim != 1 or self.dn_idx.size == 0:
            raise ValueError("Pinocchio sigil body requires descending-neuron indices")
        self.model = self.pin.Model()
        root_placement = self.pin.SE3(
            np.eye(3), np.array([SIGIL_MODULES[self.ROOT]["x"], SIGIL_MODULES[self.ROOT]["y"], 0.0])
        )
        # Pinocchio has no generic fixed joint in the Python collection.  A
        # zeroed root RZ joint is used as a fixed base: its q/qdot/torque are
        # explicitly held at zero on every step.
        root_joint = self.model.addJoint(0, self.pin.JointModelRZ(), root_placement, self.ROOT)
        self.model.appendBodyToJoint(
            root_joint, self.pin.Inertia(0.01, np.zeros(3), np.diag([0.001, 0.001, 0.001])),
            self.pin.SE3.Identity(),
        )
        self.frame_ids = {self.ROOT: self.model.addFrame(
            self.pin.Frame(self.ROOT, root_joint, root_joint, self.pin.SE3.Identity(), self.pin.FrameType.BODY)
        )}
        self.joint_ids: dict[str, int] = {self.ROOT: root_joint}
        self._add_children(self.ROOT)
        self.data = self.model.createData()
        self.q = np.zeros(self.model.nq, dtype=float)
        self.qdot = np.zeros(self.model.nv, dtype=float)
        self.requested_actuation = np.zeros(self.model.nv, dtype=float)
        self.executed_actuation = np.zeros(self.model.nv, dtype=float)
        self.motor_vector = np.zeros(self.model.nv, dtype=float)
        self.torque = np.zeros(self.model.nv, dtype=float)
        self.body_capacity = 1.0
        self.state_seq = 0
        self.last_dn_spike_sum = 0
        self.last_dn_active = 0
        self.update_kinematics()

    def _add_children(self, parent: str) -> None:
        for child, child_parent in SIGIL_PARENT.items():
            if child_parent != parent:
                continue
            p = SIGIL_MODULES[parent]
            c = SIGIL_MODULES[child]
            offset = np.array([c["x"] - p["x"], c["y"] - p["y"], 0.0], dtype=float)
            jid = self.model.addJoint(
                self.joint_ids.get(parent, 0), self.pin.JointModelRZ(),
                self.pin.SE3(np.eye(3), offset), child,
            )
            self.model.appendBodyToJoint(
                jid, self.pin.Inertia(0.01, np.zeros(3), np.diag([0.001, 0.001, 0.001])),
                self.pin.SE3.Identity(),
            )
            self.joint_ids[child] = jid
            self.frame_ids[child] = self.model.addFrame(
                self.pin.Frame(child, jid, jid, self.pin.SE3.Identity(), self.pin.FrameType.BODY)
            )
            self._add_children(child)

    def _motor_vector(self, delta_spikes: np.ndarray) -> np.ndarray:
        delta = np.asarray(delta_spikes, dtype=np.int64)
        dn_delta = delta[self.dn_idx]
        n = self.model.nv - 1
        buckets = np.arange(dn_delta.size, dtype=np.int64) % n
        counts = np.bincount(buckets, weights=dn_delta.astype(float), minlength=n)
        members = np.bincount(buckets, minlength=n).astype(float)
        rates_hz = counts / np.maximum(members, 1.0) / (self.chunk_ms * 1e-3)
        # Centering removes a common-mode population rate; only measured
        # differences across the complete DN population produce torque.
        centered = rates_hz - float(np.mean(rates_hz))
        torque = np.zeros(self.model.nv, dtype=float)
        torque[1:] = np.tanh(centered / 60.0) * self.MAX_TORQUE
        return torque

    def update_kinematics(self) -> None:
        self.pin.forwardKinematics(self.model, self.data, self.q, self.qdot)
        self.pin.updateFramePlacements(self.model, self.data)

    def physical_centroid(self) -> np.ndarray:
        """Return the arithmetic mean of the live physical frame positions.

        This is a locomotion measurement only.  It is deliberately separate
        from the generalized deformation state (q/qdot) and from the DN
        motor request.  The fixed CENTRAL_EB base is included because it is a
        physical frame in the canonical 23-node body.
        """
        points = [self.data.oMf[fid].translation[:2] for fid in self.frame_ids.values()]
        return np.mean(np.asarray(points, dtype=float), axis=0)

    def step(self, delta_spikes: np.ndarray, neural_time_ms: float, actuation_scale: float = 1.0) -> None:
        """Advance the body using neural actuation limited by physical capacity.

        ``actuation_scale`` is supplied by the clock's energy-to-capacity
        boundary. It scales execution magnitude only; the raw DN-derived
        request and its direction remain unchanged.
        """
        if not np.isfinite(actuation_scale):
            raise ValueError("body actuation capacity must be finite")
        self.body_capacity = float(np.clip(actuation_scale, 0.0, 1.0))
        self.state_seq += 1
        self.requested_actuation = self._motor_vector(delta_spikes)
        self.executed_actuation = self.requested_actuation * self.body_capacity
        self.motor_vector = self.executed_actuation.copy()
        # Physical damping is part of the body dynamics, not a behaviour
        # selector.  It prevents the normalized display-scale body from
        # integrating a persistent raw-rate difference into saturation.
        self.torque = np.clip(self.executed_actuation - 0.05 * self.qdot,
                              -self.MAX_TORQUE, self.MAX_TORQUE)
        dn_delta = np.asarray(delta_spikes, dtype=np.int64)[self.dn_idx]
        self.last_dn_spike_sum = int(dn_delta.sum())
        self.last_dn_active = int(np.count_nonzero(dn_delta))
        ddq = self.pin.aba(self.model, self.data, self.q, self.qdot, self.torque)
        ddq[0] = 0.0
        self.qdot = np.clip(self.qdot + ddq * self.DT_SEC, -self.MAX_SPEED, self.MAX_SPEED)
        self.qdot[0] = 0.0
        self.q = self.pin.integrate(self.model, self.q, self.qdot * self.DT_SEC)
        self.q[0] = 0.0
        self.q = np.clip(self.q, self.model.lowerPositionLimit, self.model.upperPositionLimit)
        self.update_kinematics()

    def restore_snapshot(self, snapshot: dict[str, Any]) -> None:
        """Restore persistent Pinocchio state without introducing behavior."""
        if not isinstance(snapshot, dict):
            return
        for name in ("q", "qdot", "requested_actuation", "executed_actuation", "motor_vector", "torque"):
            values = snapshot.get(name)
            if values is None:
                continue
            target = getattr(self, name)
            values_array = np.asarray(values, dtype=float)
            if values_array.shape != target.shape:
                raise ValueError(f"Invalid Pinocchio snapshot shape for {name}")
            setattr(self, name, values_array.copy())
        self.body_capacity = float(np.clip(snapshot.get("body_capacity", 1.0), 0.0, 1.0))
        self.state_seq = int(snapshot.get("state_seq", self.state_seq))
        self.last_dn_spike_sum = int(snapshot.get("dn_spike_sum", self.last_dn_spike_sum))
        self.last_dn_active = int(snapshot.get("dn_active_neurons", self.last_dn_active))
        self.q[0] = 0.0
        self.qdot[0] = 0.0
        self.update_kinematics()

    def state_snapshot(self) -> dict[str, Any]:
        nodes = {}
        for name, fid in self.frame_ids.items():
            t = self.data.oMf[fid].translation
            nodes[name] = [round(float(t[0]), 6), round(float(t[1]), 6)]
        return {
            "engine": "pinocchio",
            "body_id": "lethe_sigil_fafb_v783",
            "state_seq": self.state_seq,
            "neural_time_ms": None,
            "q": [round(float(x), 8) for x in self.q],
            "qdot": [round(float(x), 8) for x in self.qdot],
            "requested_actuation": [round(float(x), 8) for x in self.requested_actuation],
            "executed_actuation": [round(float(x), 8) for x in self.executed_actuation],
            "motor_vector": [round(float(x), 8) for x in self.motor_vector],
            "torque": [round(float(x), 8) for x in self.torque],
            "body_capacity": round(float(self.body_capacity), 8),
            "body_capacity_function": "f(E)=clip(E,0,1)",
            "active_body_output_capacity": round(float(self.body_capacity), 8),
            "nodes": nodes,
            "physical_centroid": [round(float(x), 8) for x in self.physical_centroid()],
            "locomotion_reference": "PINOCCHIO_FRAME_CENTROID_DELTA",
            "dn_source_count": int(self.dn_idx.size),
            "dn_spike_sum": self.last_dn_spike_sum,
            "dn_active_neurons": self.last_dn_active,
            "topology_nodes": len(SIGIL_MODULES),
            "topology_edges": len(SIGIL_EDGES),
            "tree_joints": int(self.model.njoints - 1),
        }
