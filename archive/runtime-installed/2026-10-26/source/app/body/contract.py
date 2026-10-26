"""
Authoritative Flynn Body Contract (Gate 013).
Sensorimotor embodiment interface separating neural decision substrate from physical/virtual actuation.

Principles:
1. Flynn is the decision substrate; body does NOT decide for Flynn.
2. Neutral primitives strictly aligned with real descending outputs: INTERACT, ESCAPE, BACKWARD, TURN, STOP.
3. No high-level semantic intentions in neural commands (no EAT, SEEK_SUGAR, etc.).
4. Strict action provenance: source=flynn, origin_type=resident_brain.
5. Minimal necessary body state: position, orientation, current_action, interaction_target, body_status.
"""

from dataclasses import dataclass, asdict, field
from typing import Dict, Any, List, Optional, Tuple
import time
from datetime import datetime, timezone
import uuid

ALLOWED_NEUTRAL_PRIMITIVES = {
    "INTERACT",
    "ESCAPE",
    "BACKWARD",
    "TURN",
    "STOP"
}

DISALLOWED_SEMANTIC_COMMANDS = {
    "EAT",
    "ASK_FOOD",
    "SEEK_SUGAR",
    "LIKE",
    "DISLIKE",
    "REQUEST_CONTACT"
}

PROHIBITED_SECURITY_CAPABILITIES = {
    "arbitrary_shell",
    "arbitrary_filesystem",
    "arbitrary_web",
    "arbitrary_messages",
    "arbitrary_purchases",
    "credentials",
    "ssh",
    "systemd",
    "package_manager"
}


@dataclass
class BodyObservation:
    """Local sensory observation of the world from the body's spatial perspective."""
    active_signals: Dict[str, Any]
    detected_entities: List[Dict[str, Any]]
    distances: Dict[str, float]
    environmental_conditions: Dict[str, Any]
    window_focus: str
    timestamp: float
    neural_time_ms: float
    provenance: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BodyAction:
    """Neural motor command emitted exclusively by Flynn's descending readout."""
    action_id: str
    timestamp_utc: str
    neural_time_ms: float
    source: str
    origin_type: str
    brain_instance_id: str
    brain_session_id: str
    descending_outputs: Dict[str, float]
    primitive: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    causal_chain_id: Optional[str] = None
    parent_event_id: Optional[str] = None

    def __post_init__(self):
        # Validate neural primitive neutrality
        prim_upper = self.primitive.upper()
        if prim_upper in DISALLOWED_SEMANTIC_COMMANDS:
            raise ValueError(
                f"Semantic command violation: '{self.primitive}' is not a valid neutral motor primitive. "
                f"Disallowed: {DISALLOWED_SEMANTIC_COMMANDS}"
            )
        if prim_upper not in ALLOWED_NEUTRAL_PRIMITIVES:
            raise ValueError(
                f"Invalid motor primitive '{self.primitive}'. Allowed neutral primitives: {ALLOWED_NEUTRAL_PRIMITIVES}"
            )
        self.primitive = prim_upper

        # Validate provenance rule (Section 7)
        if self.source == "flynn":
            if self.origin_type != "resident_brain":
                raise ValueError(
                    f"Provenance violation: source='flynn' requires origin_type='resident_brain', got '{self.origin_type}'"
                )
            if not self.brain_instance_id or not self.brain_session_id:
                raise ValueError("Provenance violation: Flynn actions must carry active brain instance and session IDs")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BodyState:
    """Minimal necessary spatial and functional embodiment state."""
    position: Tuple[float, float]
    orientation: float  # Heading angle in degrees [0, 360)
    current_action: str
    interaction_target: Optional[str]
    body_status: str
    last_world_displacement: Tuple[float, float] = (0.0, 0.0)
    total_world_distance: float = 0.0
    physical_motion_status: str = "quiescent"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "position": list(self.position),
            "orientation": round(self.orientation, 2),
            "current_action": self.current_action,
            "interaction_target": self.interaction_target,
            "body_status": self.body_status
            ,"last_world_displacement": list(self.last_world_displacement)
            ,"total_world_distance": round(self.total_world_distance, 8)
            ,"physical_motion_status": self.physical_motion_status
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'BodyState':
        pos = tuple(d.get("position", (0.0, 0.0)))
        return cls(
            position=(float(pos[0]), float(pos[1])),
            orientation=float(d.get("orientation", 0.0)),
            current_action=str(d.get("current_action", "STOP")),
            interaction_target=d.get("interaction_target"),
            body_status=str(d.get("body_status", "quiescent")),
            last_world_displacement=tuple(d.get("last_world_displacement", (0.0, 0.0)))[:2],
            total_world_distance=float(d.get("total_world_distance", 0.0)),
            physical_motion_status=str(d.get("physical_motion_status", "quiescent"))
        )


@dataclass
class BodyResult:
    """Outcome of an executed BodyAction."""
    action_id: str
    primitive: str
    status: str  # SUCCESS, DENIED, FAILED, NO_EFFECT
    consequence: Dict[str, Any]
    world_consequence: Optional[Dict[str, Any]] = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class FlynnBodyInterface:
    """Abstract interface for Flynn embodiment."""

    def sense(self, world_state: Dict[str, Any]) -> BodyObservation:
        raise NotImplementedError

    def act(self, action: BodyAction) -> BodyResult:
        raise NotImplementedError

    def snapshot(self) -> BodyState:
        raise NotImplementedError

    def restore(self, state: BodyState) -> None:
        raise NotImplementedError
