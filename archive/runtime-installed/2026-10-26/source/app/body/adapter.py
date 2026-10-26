"""
Flynn Virtual Body Adapter (Gate 013).
Implements FlynnBodyInterface for Caverna de Hipnos 2D virtual environment.

Guarantees:
1. SENSE: Derives body-local perception with Euclidean distance checks. Zero phantom sensation.
2. ACT: Executes strictly neutral motor primitives: INTERACT, ESCAPE, BACKWARD, TURN, STOP.
3. NON-COGNITION: The body never reasons, plans, or interprets intent.
4. AUDIT & FAIL-CLOSED: Reports ZeroClaw executor integration status (Gate 013-Z).
"""

import math
import time
from typing import Dict, Any, List, Optional, Tuple

from app.body.contract import (
    BodyObservation,
    BodyAction,
    BodyState,
    BodyResult,
    FlynnBodyInterface,
    ALLOWED_NEUTRAL_PRIMITIVES,
    DISALLOWED_SEMANTIC_COMMANDS,
    PROHIBITED_SECURITY_CAPABILITIES
)
from app.world.geometry import (
    ARENA_BOUNDS,
    INTERACTION_RADIUS,
    euclidean_distance,
    clamp_to_arena
)


class CavernaVirtualBody(FlynnBodyInterface):
    """
    Persistent Virtual Body in Caverna de Hipnos.
    Tracks 2D spatial position, angular heading orientation, and neutral effector states.
    """

    def __init__(self, initial_pos: Tuple[float, float] = (0.0, 0.0), initial_orientation: float = 0.0):
        self.position: Tuple[float, float] = initial_pos
        self.orientation: float = initial_orientation  # Heading in degrees [0, 360)
        self.current_action: str = "STOP"
        self.interaction_target: Optional[str] = None
        self.body_status: str = "quiescent"
        self.last_world_displacement: Tuple[float, float] = (0.0, 0.0)
        self.total_world_distance: float = 0.0
        self.physical_motion_status: str = "quiescent"
        self.last_sensory_return: Dict[str, Any] = {}

        self.total_sense_count: int = 0
        self.total_act_count: int = 0
        self.zeroclaw_present: bool = True  # Deterministic ZeroClaw executor present
        self.zeroclaw_role: str = "EXECUTION_INTERLOCK"
        self.zeroclaw_status: str = "DETERMINISTIC_ALLOWLIST_ACTIVE"
        self.openclaw_present: bool = False
        self.openclaw_rejected: bool = True
        self.openclaw_role: str = "REJECTED"
        self.openclaw_status: str = "REJECTED_GATE013Z"


    def update(self, dt_ms: float, channels: Dict[str, float], t_ms: float, escape_laterality: float = 0.0, proboscis_drive: float = 0.0):
        """Session.advance telemetry compatibility."""
        turn = channels.get('turn', 0.0)
        if turn > 0.3:
            bias = channels.get('turn_bias', 0.0)
            d_deg = (1.0 if bias >= 0 else -1.0) * turn * 50.0 * (dt_ms / 1000.0)
            self.orientation = (self.orientation + d_deg) % 360.0

    def as_dict(self) -> Dict[str, Any]:
        """Session.advance telemetry compatibility."""
        return self.status()

    def capabilities(self) -> Dict[str, Any]:
        return {
            "sensory_channels": ["sweet", "bitter", "wind", "sound", "looming", "contact"],
            "motor_primitives": list(ALLOWED_NEUTRAL_PRIMITIVES),
            "prohibited_capabilities": list(PROHIBITED_SECURITY_CAPABILITIES),
            "cognitive_decision_making": False,
            "llm_in_loop": False,
            "zeroclaw_role": self.zeroclaw_role,
            "zeroclaw_executes_body_primitive": False,
            "body_state_mutation_owner": "CavernaVirtualBody",
            "zeroclaw_present": self.zeroclaw_present,
            "openclaw_role": self.openclaw_role,
            "openclaw_present": self.openclaw_present,
            "openclaw_rejected": self.openclaw_rejected
        }

    def status(self) -> Dict[str, Any]:
        return {
            "body_adapter": "CavernaVirtualBody",
            "position": list(self.position),
            "orientation": round(self.orientation, 2),
            "current_action": self.current_action,
            "body_status": self.body_status,
            "world_displacement": list(self.last_world_displacement),
            "world_distance_travelled": round(self.total_world_distance, 8),
            "physical_motion_status": self.physical_motion_status,
            "sensory_return": self.last_sensory_return,
            "zeroclaw_present": self.zeroclaw_present,
            "zeroclaw_role": self.zeroclaw_role,
            "zeroclaw_executes_body_primitive": False,
            "body_state_mutation_owner": "CavernaVirtualBody",
            "zeroclaw_status": self.zeroclaw_status,
            "openclaw_present": self.openclaw_present,
            "openclaw_role": self.openclaw_role,
            "openclaw_status": self.openclaw_status,
            "openclaw_rejected": self.openclaw_rejected,
            "total_sense_events": self.total_sense_count,
            "total_act_events": self.total_act_count,
            "is_embodied": True
        }

    def apply_physical_displacement(self, displacement: Tuple[float, float]) -> Dict[str, Any]:
        """Apply measured Pinocchio displacement to the canonical world body.

        This method has no semantic action and does not select a target.  The
        arena clamp is reported explicitly so a boundary cannot masquerade as
        successful locomotion.
        """
        before = tuple(self.position)
        requested = (float(displacement[0]), float(displacement[1]))
        unclamped = (before[0] + requested[0], before[1] + requested[1])
        after = clamp_to_arena(*unclamped)
        applied = (after[0] - before[0], after[1] - before[1])
        distance = math.hypot(applied[0], applied[1])
        self.position = after
        self.last_world_displacement = applied
        self.total_world_distance += distance
        self.physical_motion_status = "moving_physical" if distance > 0.0 else "quiescent"
        return {
            "position_before": list(before),
            "position_after": list(after),
            "requested_displacement": list(requested),
            "applied_displacement": list(applied),
            "distance": distance,
            "clamped": after != unclamped,
            "provenance": "PINOCCHIO_FRAME_CENTROID_DELTA"
        }

    def sense(self, world_engine) -> BodyObservation:
        """
        Transforms world geometry into body-local sensory observation.
        PHANTOM_SENSORY_INPUT = 0: Only stimuli with physical exposure are perceived.
        """
        self.total_sense_count += 1
        signals = world_engine.compute_sensory_exposure(self.position)
        displacement_distance = math.hypot(*self.last_world_displacement)
        if displacement_distance > 0.0:
            signals["synthetic_proprioception"] = {
                "modality": "synthetic_proprioception",
                "intensity": min(1.0, displacement_distance / 0.05),
                "position": list(self.position),
                "displacement": list(self.last_world_displacement),
                "distance": round(displacement_distance, 8),
                "body_capacity": round(float(getattr(world_engine, "body_capacity", 0.0)), 8),
                "provenance": "SYNTHETIC_FACTUAL_RUNTIME_SIGNAL",
                "neural_injection": "NONE"
            }

        detected_entities = []
        distances = {}

        # Distance to all known entities
        for name, obj in world_engine.objects.items():
            d = euclidean_distance(self.position, obj.position)
            distances[name] = round(d, 3)
            if d <= INTERACTION_RADIUS:
                detected_entities.append({
                    "name": name,
                    "entity_type": obj.entity_type,
                    "distance": round(d, 3),
                    "available": obj.available
                })

        env_conds = {
            "wind": world_engine.conditions["wind"].level,
            "sound": world_engine.conditions["sound"].level,
            "looming": world_engine.events["looming"].state
        }

        return BodyObservation(
            active_signals=signals,
            detected_entities=detected_entities,
            distances=distances,
            environmental_conditions=env_conds,
            window_focus=world_engine.window_variable,
            timestamp=time.time(),
            neural_time_ms=world_engine.current_neural_t_ms,
            provenance={
                "world": "CAVERNA_RESIDENT",
                "proprioception": "SYNTHETIC_FACTUAL_RUNTIME_SIGNAL",
                "neural_injection": "NO_REGISTERED_PROPRIOCEPTION_MODALITY",
                "body_position": list(self.position),
                "world_displacement": list(self.last_world_displacement),
            }
        )

    def act(
        self,
        action: BodyAction,
        world_engine: Optional[Any] = None,
        homeostasis: Optional[Any] = None
    ) -> BodyResult:
        """
        Executes an allowlisted neutral motor primitive.
        Rejects semantic and prohibited actions.
        """
        prim = action.primitive.upper()

        if prim in DISALLOWED_SEMANTIC_COMMANDS:
            return BodyResult(
                action_id=action.action_id,
                primitive=prim,
                status="DENIED",
                consequence={"error": f"Semantic command '{prim}' rejected. Flynn uses neutral primitives."}
            )

        if prim not in ALLOWED_NEUTRAL_PRIMITIVES:
            return BodyResult(
                action_id=action.action_id,
                primitive=prim,
                status="DENIED",
                consequence={"error": f"Unregistered primitive '{prim}' rejected by allowlist."}
            )

        self.total_act_count += 1
        self.current_action = prim
        consequence: Dict[str, Any] = {"primitive": prim}
        world_consequence: Optional[Dict[str, Any]] = None

        if prim == "STOP":
            self.body_status = "quiescent"
            consequence["detail"] = "Effectors ceased; quiescent stance maintained."

        elif prim == "TURN":
            self.body_status = "turning"
            d_theta = float(action.parameters.get("d_theta", 15.0))
            # Direction can be biased by lateralized DNa01/DNa02
            direction = action.parameters.get("direction", "right")
            delta = d_theta if direction == "right" else -d_theta
            self.orientation = (self.orientation + delta) % 360.0
            consequence["new_orientation"] = round(self.orientation, 2)
            consequence["delta_deg"] = delta

        elif prim == "BACKWARD":
            self.body_status = "walking_backward"
            step = float(action.parameters.get("step", 0.2))
            rad = math.radians(self.orientation)
            dx = -math.cos(rad) * step
            dy = -math.sin(rad) * step
            self.position = clamp_to_arena(self.position[0] + dx, self.position[1] + dy)
            consequence["new_position"] = list(self.position)

        elif prim == "ESCAPE":
            self.body_status = "escaping"
            # Jump / rapid displacement in opposite heading direction
            rad = math.radians((self.orientation + 180.0) % 360.0)
            dx = math.cos(rad) * 1.5
            dy = math.sin(rad) * 1.5
            self.position = clamp_to_arena(self.position[0] + dx, self.position[1] + dy)
            consequence["escape_displacement"] = [round(dx, 2), round(dy, 2)]
            consequence["new_position"] = list(self.position)

        elif prim == "INTERACT":
            self.body_status = "interacting"
            consequence["effector"] = "MN9_proboscis"
            # Interaction is an effector observation only.  Resource
            # consumption is owned by ContinuousWorldEngine.observe_body and
            # occurs on physical contact, never as a proximity side effect of
            # this neutral primitive.
            if world_engine is not None:
                contacts = getattr(world_engine, "resource_contacts", {})
                consequence["interaction_target"] = next(
                    (name for name, in_contact in contacts.items() if in_contact),
                    "substrate",
                )
                consequence["ingestion_occurred"] = False

        return BodyResult(
            action_id=action.action_id,
            primitive=prim,
            status="SUCCESS",
            consequence=consequence,
            world_consequence=world_consequence,
            timestamp=time.time()
        )

    def snapshot(self) -> BodyState:
        return BodyState(
            position=self.position,
            orientation=self.orientation,
            current_action=self.current_action,
            interaction_target=self.interaction_target,
            body_status=self.body_status,
            last_world_displacement=self.last_world_displacement,
            total_world_distance=self.total_world_distance,
            physical_motion_status=self.physical_motion_status
        )

    def restore(self, state: BodyState) -> None:
        self.position = state.position
        self.orientation = state.orientation
        self.current_action = state.current_action
        self.interaction_target = state.interaction_target
        self.body_status = state.body_status
        self.last_world_displacement = tuple(state.last_world_displacement)
        self.total_world_distance = float(state.total_world_distance)
        self.physical_motion_status = state.physical_motion_status


BODY_ADAPTER = CavernaVirtualBody()
