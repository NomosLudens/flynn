"""
Authoritative Continuous World Engine for Caverna de Hipnos (Gate 013).
Maintains spatial objects, persistent environmental conditions, and transient events.

Guarantees:
- Single mutation owner (HTTP requests enqueue commands; world ticks update state).
- Strict synchronization with continuous neural time (zero drift).
- Continuous sensory transduction without browser or web-service dependency.
- Zero phantom sensation (PHANTOM_SENSORY_INPUT = 0).
- Explicit looming event lifecycle (start, duration, end).
"""

import time
import queue
import sqlite3
import json
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from app.world.geometry import (
    ARENA_BOUNDS,
    INTERACTION_RADIUS,
    WorldObject,
    PersistentCondition,
    TransientEvent,
    euclidean_distance,
    clamp_to_arena
)

DEFAULT_CAVERNA_DB = Path("/home/ubuntu/Portifolio/flynn-max/runtime/data/caverna.db")


@dataclass(frozen=True)
class PublishedWorldState:
    """Immutable snapshot of the world published atomically per tick."""
    world_time_ms: float
    neural_time_ms: float
    sweet: Dict[str, Any]
    bitter: Dict[str, Any]
    wind: Dict[str, Any]
    sound: Dict[str, Any]
    looming: Dict[str, Any]
    contact: Dict[str, Any]
    window: Dict[str, Any]
    active_conditions: List[str]
    active_events: List[str]
    body_position: List[float]
    resource_distances: Dict[str, float]
    resource_contacts: Dict[str, bool]
    last_contact: Optional[Dict[str, Any]]
    last_consumption: Optional[Dict[str, Any]]
    world_scale: float
    timestamp_utc: str


class ContinuousWorldEngine:
    """
    Authoritative Continuous World Engine.
    Advances synchronously with Flynn's neural clock ticks.
    """
    WORLD_SCALE = 1.0
    NUTRITIVE_RESOURCES = {"sweet", "bitter"}

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DEFAULT_CAVERNA_DB
        self.world_time_ms = 0.0
        self.current_neural_t_ms = 0.0

        # Command queue for external operator/human interactions
        self._command_queue: queue.Queue = queue.Queue(maxsize=128)

        # 1. World Objects (Resources / Affordances)
        self.objects: Dict[str, WorldObject] = {
            "sweet": WorldObject(
                name="sweet",
                entity_type="OBJECT",
                position=(3.0, 0.0),
                radius=0.5,
                available=False,
                offered=False,
                modality="taste_sugar",
                target_neuron="GRN_Sugar_SEZ"
            ),
            "bitter": WorldObject(
                name="bitter",
                entity_type="OBJECT",
                position=(-3.0, 0.0),
                radius=0.5,
                available=False,
                offered=False,
                modality="taste_bitter",
                target_neuron="GRN_Bitter_SEZ"
            ),
            "contact": WorldObject(
                name="contact",
                entity_type="OBJECT",
                position=(0.0, 3.0),
                radius=0.5,
                available=False,
                offered=False,
                modality="touch_head",
                target_neuron="Bristle_Mechanosensory"
            )
        }

        # 2. Persistent Environmental Conditions
        self.conditions: Dict[str, PersistentCondition] = {
            "wind": PersistentCondition(
                name="wind",
                entity_type="PERSISTENT_CONDITION",
                level="off",
                offered_level="none",
                vector=(1.0, 0.0),
                modality="wind",
                target_neuron="AMMC_Mechanosensory"
            ),
            "sound": PersistentCondition(
                name="sound",
                entity_type="PERSISTENT_CONDITION",
                level="off",
                offered_level="none",
                vector=(0.0, 0.0),
                modality="sound",
                target_neuron="AMMC_Auditory"
            )
        }

        # 3. Transient Events
        self.events: Dict[str, TransientEvent] = {
            "looming": TransientEvent(
                name="looming",
                entity_type="EVENT",
                state="none",
                offered=False,
                start_neural_t_ms=None,
                duration_ms=500.0,  # 500ms neural duration
                end_neural_t_ms=None,
                source_angle_deg=0.0,
                modality="looming",
                target_neuron="LPLC2_LC4_Lobula"
            )
        }

        # Window & Operator telemetry context
        self.window_variable: str = "sweet"
        self.window_action: int = 1
        self.pending_human_offer: Optional[Dict[str, Any]] = None
        self.pending_flynn_request: Optional[Dict[str, Any]] = None
        self.body_position: Tuple[float, float] = (0.0, 0.0)
        self.resource_distances: Dict[str, float] = {}
        self.resource_contacts: Dict[str, bool] = {}
        self.last_contact: Optional[Dict[str, Any]] = None
        self.last_consumption: Optional[Dict[str, Any]] = None

        # Published state
        self._published_state: Optional[PublishedWorldState] = None
        self._publish_snapshot()

    def enqueue_command(self, cmd_type: str, variable: str, payload: Optional[Dict[str, Any]] = None) -> None:
        """Thread-safe enqueueing of operator commands (HTTP does not mutate state)."""
        try:
            self._command_queue.put_nowait({
                "cmd_type": cmd_type,
                "variable": variable,
                "payload": payload or {},
                "enqueued_at": time.time()
            })
        except queue.Full:
            pass

    def tick(self, chunk_ms: float, current_neural_t_ms: float) -> None:
        """
        Advances the continuous world by chunk_ms, perfectly synchronized to neural time.
        Processes queued commands, advances event countdowns, and publishes state.
        """
        self.world_time_ms += chunk_ms
        self.current_neural_t_ms = current_neural_t_ms

        # 1. Process queued commands from operators/environment
        while not self._command_queue.empty():
            try:
                cmd = self._command_queue.get_nowait()
                self._apply_command(cmd)
            except queue.Empty:
                break

        # 2. Advance event timers (Section 19: Looming lifecycle)
        looming = self.events["looming"]
        if looming.state == "active":
            if looming.end_neural_t_ms is not None and self.current_neural_t_ms >= looming.end_neural_t_ms:
                looming.state = "ended"
                looming.offered = False
        elif looming.state == "ended":
            # Settle back to quiescent none after 1 tick
            looming.state = "none"

        # 3. Publish atomic immutable snapshot
        self._publish_snapshot()

    def _apply_command(self, cmd: Dict[str, Any]) -> None:
        cmd_type = cmd["cmd_type"].lower()
        var = cmd["variable"]
        p = cmd.get("payload", {})

        if cmd_type == "select_window":
            self.window_variable = var
            self.window_action = p.get("action_id", 1)

        elif cmd_type == "offer":
            lvl = p.get("level", "high")
            offer_data = {
                "variable": var,
                "level": lvl,
                "offered_at": datetime.now(timezone.utc).isoformat()
            }
            self.pending_human_offer = offer_data
            if var in self.objects:
                self.objects[var].offered = True
                if var in self.NUTRITIVE_RESOURCES:
                    self.objects[var].available = True
                    self.objects[var].offered_at = offer_data["offered_at"]
                    self.objects[var].consumed_at = None
            elif var in self.conditions:
                self.conditions[var].offered_level = lvl
            elif var in self.events:
                self.events[var].offered = True

        elif cmd_type == "fulfill":
            self.pending_human_offer = None
            if var in self.objects:
                self.objects[var].available = True
                self.objects[var].offered = False
            elif var in self.conditions:
                cond = self.conditions[var]
                cond.level = cond.offered_level if cond.offered_level != "none" else "high"
                cond.offered_level = "none"
            elif var in self.events:
                ev = self.events[var]
                ev.state = "active"
                ev.offered = False
                ev.start_neural_t_ms = self.current_neural_t_ms
                dur = float(p.get("duration_ms", 500.0))
                ev.duration_ms = dur
                ev.end_neural_t_ms = self.current_neural_t_ms + dur

        elif cmd_type == "deny":
            self.pending_human_offer = None
            if var in self.objects:
                self.objects[var].offered = False
            elif var in self.conditions:
                self.conditions[var].offered_level = "none"
            elif var in self.events:
                self.events[var].offered = False

        elif cmd_type == "remove":
            self.pending_human_offer = None
            if var in self.objects:
                self.objects[var].available = False
                self.objects[var].offered = False
            elif var in self.conditions:
                self.conditions[var].level = "off"
                self.conditions[var].offered_level = "none"
            elif var in self.events:
                self.events[var].state = "none"
                self.events[var].offered = False

        elif cmd_type == "set_level":
            lvl = p.get("level") or (p.get("payload", {}).get("level") if isinstance(p.get("payload"), dict) else None) or "off"
            if var in self.conditions:
                self.conditions[var].level = lvl

    def _publish_snapshot(self) -> None:
        active_conds = [k for k, v in self.conditions.items() if v.level != "off"]
        active_evs = [k for k, v in self.events.items() if v.state == "active"]

        self._published_state = PublishedWorldState(
            world_time_ms=round(self.world_time_ms, 2),
            neural_time_ms=round(self.current_neural_t_ms, 2),
            sweet=self.objects["sweet"].to_dict(),
            bitter=self.objects["bitter"].to_dict(),
            wind=self.conditions["wind"].to_dict(),
            sound=self.conditions["sound"].to_dict(),
            looming=self.events["looming"].to_dict(),
            contact=self.objects["contact"].to_dict(),
            window={
                "selected_variable": self.window_variable,
                "selected_action": self.window_action,
                "pending_human_offer": self.pending_human_offer,
                "pending_flynn_request": self.pending_flynn_request
            },
            active_conditions=active_conds,
            active_events=active_evs,
            body_position=list(self.body_position),
            resource_distances=dict(self.resource_distances),
            resource_contacts=dict(self.resource_contacts),
            last_contact=self.last_contact,
            last_consumption=self.last_consumption,
            world_scale=self.WORLD_SCALE,
            timestamp_utc=datetime.now(timezone.utc).isoformat()
        )

    @property
    def published_state(self) -> PublishedWorldState:
        return self._published_state

    def get_world_dict(self) -> Dict[str, Any]:
        """Compatible dictionary representation for existing Caverna web surface."""
        ps = self.published_state
        return {
            "sweet": dict(ps.sweet, distance_to_body=ps.resource_distances.get("sweet"), contact=ps.resource_contacts.get("sweet", False), consumed=bool(ps.sweet.get("consumed_at"))),
            "bitter": dict(ps.bitter, distance_to_body=ps.resource_distances.get("bitter"), contact=ps.resource_contacts.get("bitter", False), consumed=bool(ps.bitter.get("consumed_at"))),
            "wind": {"level": ps.wind["level"], "offered_level": ps.wind["offered_level"], "vector": ps.wind["vector"]},
            "sound": {"level": ps.sound["level"], "offered_level": ps.sound["offered_level"]},
            "looming": {"state": ps.looming["state"], "offered": ps.looming["offered"], "duration_ms": ps.looming["duration_ms"]},
            "contact": dict(ps.contact, distance_to_body=ps.resource_distances.get("contact"), contact=ps.resource_contacts.get("contact", False)),
            "window": ps.window,
            "arena_bounds": ARENA_BOUNDS,
            "world_time_ms": ps.world_time_ms,
            "neural_time_ms": ps.neural_time_ms,
            "timestamps": {"updated_at": ps.timestamp_utc}
            ,"body_position": list(ps.body_position)
            ,"distance_to_resource": dict(ps.resource_distances)
            ,"contact_state": dict(ps.resource_contacts)
            ,"last_contact": ps.last_contact
            ,"last_consumption": ps.last_consumption
            ,"world_scale": ps.world_scale
            ,"locomotion_reference": "PINOCCHIO_FRAME_CENTROID_DELTA"
        }

    def observe_body(self, body_pos: Tuple[float, float], neural_time_ms: float,
                     homeostasis: Optional[Any] = None) -> Dict[str, Any]:
        """Observe physical body/resource geometry and consume on contact only."""
        self.body_position = tuple(float(x) for x in body_pos[:2])
        self.current_neural_t_ms = float(neural_time_ms)
        self.resource_distances = {
            name: euclidean_distance(self.body_position, obj.position)
            for name, obj in self.objects.items()
        }
        self.resource_contacts = {
            name: bool(obj.available and self.resource_distances[name] <= obj.radius)
            for name, obj in self.objects.items()
        }
        self.last_contact = None
        self.last_consumption = None
        for name, obj in self.objects.items():
            if self.resource_contacts[name]:
                self.last_contact = {
                    "resource_id": obj.resource_id or name,
                    "resource_type": obj.entity_type,
                    "position": list(obj.position),
                    "distance": round(self.resource_distances[name], 8),
                    "contact_radius": obj.radius,
                    "neural_time_ms": self.current_neural_t_ms,
                    "provenance": "CAVERNA_RESIDENT_GEOMETRY"
                }
                if name in self.NUTRITIVE_RESOURCES:
                    # The consumed marker is authoritative for this object;
                    # this guard keeps a repeated resident tick idempotent
                    # even if a stale contact observation is replayed.
                    if obj.consumed_at is not None or not obj.available:
                        continue
                    before = float(homeostasis.energy_reserve) if homeostasis is not None else None
                    obj.available = False
                    obj.offered = False
                    obj.consumed_at = datetime.now(timezone.utc).isoformat()
                    after = None
                    if homeostasis is not None:
                        after = float(homeostasis.replenish(current_neural_t_ms=self.current_neural_t_ms))
                    self.last_consumption = {
                        **self.last_contact,
                        "consumed_at": obj.consumed_at,
                        "energy_before": before,
                        "energy_after": after,
                        "homeostasis_owner": "RESIDENT_HOMEOSTASIS",
                        "provenance": "CAVERNA_CONTACT_CONSUMPTION"
                    }
                    self.last_contact["consumed"] = True
        self._publish_snapshot()
        return {
            "body_position": list(self.body_position),
            "distance_to_resource": dict(self.resource_distances),
            "contact_state": dict(self.resource_contacts),
            "contact": self.last_contact,
            "consumption": self.last_consumption,
            "provenance": "CAVERNA_RESIDENT_GEOMETRY"
        }

    def compute_sensory_exposure(self, body_pos: Tuple[float, float]) -> Dict[str, Any]:
        """
        Evaluates sensory signals reaching receptors strictly based on physical geometry.
        PHANTOM_SENSORY_INPUT = 0: Zero signal if object out of range or condition off.
        """
        signals = {}

        # 1. Sweet object (taste_sugar)
        sweet = self.objects["sweet"]
        d_sweet = euclidean_distance(body_pos, sweet.position)
        if sweet.available and d_sweet <= INTERACTION_RADIUS:
            signals["taste_sugar"] = {
                "modality": "taste_sugar",
                "intensity": 1.0,
                "target_neuron": sweet.target_neuron,
                "distance": round(d_sweet, 3),
                "firing_rate_hz": 100.0
            }

        # 2. Bitter object (taste_bitter)
        bitter = self.objects["bitter"]
        d_bitter = euclidean_distance(body_pos, bitter.position)
        if bitter.available and d_bitter <= INTERACTION_RADIUS:
            signals["taste_bitter"] = {
                "modality": "taste_bitter",
                "intensity": 1.0,
                "target_neuron": bitter.target_neuron,
                "distance": round(d_bitter, 3),
                "firing_rate_hz": 100.0
            }

        # 3. Wind condition (persistent)
        wind = self.conditions["wind"]
        if wind.level != "off":
            rate = 120.0 if wind.level == "high" else 50.0
            signals["wind"] = {
                "modality": "wind",
                "intensity": 1.0 if wind.level == "high" else 0.5,
                "target_neuron": wind.target_neuron,
                "firing_rate_hz": rate
            }

        # 4. Sound condition
        sound = self.conditions["sound"]
        if sound.level != "off":
            rate = 100.0 if sound.level == "high" else 40.0
            signals["sound"] = {
                "modality": "sound",
                "intensity": 1.0 if sound.level == "high" else 0.5,
                "target_neuron": sound.target_neuron,
                "firing_rate_hz": rate
            }

        # 5. Looming event (transient)
        looming = self.events["looming"]
        if looming.state == "active":
            signals["looming"] = {
                "modality": "looming",
                "intensity": 1.0,
                "target_neuron": looming.target_neuron,
                "firing_rate_hz": 150.0
            }

        # 6. Contact object
        contact = self.objects["contact"]
        d_contact = euclidean_distance(body_pos, contact.position)
        if contact.available and d_contact <= INTERACTION_RADIUS:
            signals["touch_head"] = {
                "modality": "touch_head",
                "intensity": 1.0,
                "target_neuron": contact.target_neuron,
                "distance": round(d_contact, 3),
                "firing_rate_hz": 80.0
            }

        return signals

    def snapshot(self) -> Dict[str, Any]:
        return {
            "world_time_ms": self.world_time_ms,
            "current_neural_t_ms": self.current_neural_t_ms,
            "objects": {k: v.to_dict() for k, v in self.objects.items()},
            "conditions": {k: v.to_dict() for k, v in self.conditions.items()},
            "events": {k: v.to_dict() for k, v in self.events.items()},
            "window_variable": self.window_variable,
            "window_action": self.window_action
            ,"pending_human_offer": self.pending_human_offer
            ,"body_position": list(self.body_position)
            ,"resource_distances": self.resource_distances
            ,"resource_contacts": self.resource_contacts
            ,"last_contact": self.last_contact
            ,"last_consumption": self.last_consumption
            ,"world_scale": self.WORLD_SCALE
        }

    def restore(self, data: Dict[str, Any]) -> None:
        self.world_time_ms = float(data.get("world_time_ms", 0.0))
        self.current_neural_t_ms = float(data.get("current_neural_t_ms", 0.0))
        self.window_variable = data.get("window_variable", "sweet")
        self.window_action = data.get("window_action", 1)
        self.pending_human_offer = data.get("pending_human_offer")
        pos = data.get("body_position", (0.0, 0.0))
        self.body_position = (float(pos[0]), float(pos[1]))
        self.resource_distances = {str(k): float(v) for k, v in data.get("resource_distances", {}).items()}
        self.resource_contacts = {str(k): bool(v) for k, v in data.get("resource_contacts", {}).items()}
        self.last_contact = data.get("last_contact")
        self.last_consumption = data.get("last_consumption")

        for k, od in data.get("objects", {}).items():
            if k in self.objects:
                self.objects[k].available = bool(od.get("available", False))
                self.objects[k].offered = bool(od.get("offered", False))
                self.objects[k].resource_id = od.get("resource_id", self.objects[k].resource_id or k)
                self.objects[k].offered_at = od.get("offered_at")
                self.objects[k].consumed_at = od.get("consumed_at")
                pos = od.get("position", self.objects[k].position)
                self.objects[k].position = (float(pos[0]), float(pos[1]))

        for k, cd in data.get("conditions", {}).items():
            if k in self.conditions:
                self.conditions[k].level = cd.get("level", "off")
                self.conditions[k].offered_level = cd.get("offered_level", "none")

        for k, ed in data.get("events", {}).items():
            if k in self.events:
                self.events[k].state = ed.get("state", "none")
                self.events[k].offered = bool(ed.get("offered", False))
                self.events[k].start_neural_t_ms = ed.get("start_neural_t_ms")
                self.events[k].end_neural_t_ms = ed.get("end_neural_t_ms")

        self._publish_snapshot()
