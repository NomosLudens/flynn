"""
Minimal Deterministic 2D Spatial Geometry for Caverna de Hipnos (Gate 013).
Provides spatial positions, heading orientations, entity categories, and distance calculations.

Principles:
1. 2D bounded plane: x in [-10.0, 10.0], y in [-10.0, 10.0].
2. Entities categorized into OBJECT, PERSISTENT CONDITION, and EVENT.
3. Sensory perception requires physical proximity (d <= R_interact). Zero phantom sensation.
4. Looming is an explicit transient event with start, duration, and end.
"""

import math
from dataclasses import dataclass, asdict
from typing import Tuple, Dict, Any, Optional

ARENA_BOUNDS = {
    "x_min": -10.0,
    "x_max": 10.0,
    "y_min": -10.0,
    "y_max": 10.0
}

INTERACTION_RADIUS = 1.0  # Units within which taste/contact interaction occurs


def euclidean_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def clamp_to_arena(x: float, y: float) -> Tuple[float, float]:
    cx = max(ARENA_BOUNDS["x_min"], min(ARENA_BOUNDS["x_max"], x))
    cy = max(ARENA_BOUNDS["y_min"], min(ARENA_BOUNDS["y_max"], y))
    return (cx, cy)


@dataclass
class WorldObject:
    """Physical resource/affordance situated at fixed or movable coordinates."""
    name: str
    entity_type: str  # OBJECT
    position: Tuple[float, float]
    radius: float
    available: bool
    offered: bool
    modality: str
    target_neuron: str
    resource_id: Optional[str] = None
    offered_at: Optional[str] = None
    consumed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "entity_type": self.entity_type,
            "position": list(self.position),
            "radius": self.radius,
            "available": self.available,
            "offered": self.offered,
            "modality": self.modality,
            "target_neuron": self.target_neuron
            ,"resource_id": self.resource_id or self.name
            ,"resource_type": self.entity_type
            ,"contact_radius": self.radius
            ,"offered_at": self.offered_at
            ,"consumed_at": self.consumed_at
        }


@dataclass
class PersistentCondition:
    """Persistent environmental condition with temporal continuity."""
    name: str
    entity_type: str  # PERSISTENT_CONDITION
    level: str  # 'off', 'low', 'high'
    offered_level: str  # 'none', 'low', 'high'
    vector: Tuple[float, float]  # Directional influence (e.g. wind heading)
    modality: str
    target_neuron: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "entity_type": self.entity_type,
            "level": self.level,
            "offered_level": self.offered_level,
            "vector": list(self.vector),
            "modality": self.modality,
            "target_neuron": self.target_neuron
        }


@dataclass
class TransientEvent:
    """Transient event with explicit start, duration, and end."""
    name: str
    entity_type: str  # EVENT
    state: str  # 'none', 'active', 'ended'
    offered: bool
    start_neural_t_ms: Optional[float]
    duration_ms: float
    end_neural_t_ms: Optional[float]
    source_angle_deg: float
    modality: str
    target_neuron: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "entity_type": self.entity_type,
            "state": self.state,
            "offered": self.offered,
            "start_neural_t_ms": self.start_neural_t_ms,
            "duration_ms": self.duration_ms,
            "end_neural_t_ms": self.end_neural_t_ms,
            "source_angle_deg": self.source_angle_deg,
            "modality": self.modality,
            "target_neuron": self.target_neuron
        }
