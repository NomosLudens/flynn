"""
Flynn Continuous Brain Runtime: Autonomous Neural Clock (Gate 013 Integrated Architecture).
Owns GLOBAL_SESSION exclusively and advances neural time chunk by chunk.
Guarantees:
- Exactly ONE call site to Session.advance in the entire codebase (DIRECT_SESSION_ADVANCE_OUTSIDE_CLOCK = 0).
- Fully integrated continuous WorldLoop & BodyLoop synchronized to continuous neural time.
- Sensory transduction with Euclidean perception checks: PHANTOM_SENSORY_INPUT = 0.
- Descending action bridge mapping real DNs/MN9 to neutral primitives: INTERACT, ESCAPE, BACKWARD, TURN, STOP.
- Anti-spam guard: quiescence/STOP does not emit tick spam; records only transitions & meaningful actions.
- Bounded thread-safe stimulus queue (QUEUE_MAXSIZE=32, COMMAND_TIMEOUT=5.0s, UUID4).
- Immutable PublishedBrainState published atomically per tick (ENGINE_MUTABLE_STATE_READ_BY_HTTP = NO).
- Zero dependency on browser or flynn-web service (WORLD_BROWSER_DEPENDENT=NO, WORLD_WEB_SERVICE_DEPENDENT=NO).
"""
import os
import time
import uuid
import queue
import sqlite3
import threading
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
import numpy as np

from app.world.continuous_world import ContinuousWorldEngine
from app.body.adapter import CavernaVirtualBody
from app.body.pinocchio_sigil import PinocchioSigilBody
from app.body.contract import BodyAction, BodyResult
from app.body.zeroclaw import ZEROCLAW_EXECUTOR
from app.body.openclaw import OPENCLAW_EXECUTOR
from app.brain.plasticity import PlasticityEngine
from app.brain.dn_recorder import DNTemporalRecorder

# Modality key mapping for fruit-fly-lab
MODALITY_ALIASES = {
    "sugar": "taste_sugar",
    "sweet": "taste_sugar",
    "taste_sugar": "taste_sugar",
    "bitter": "taste_bitter",
    "taste_bitter": "taste_bitter",
    "vinegar": "odor_vinegar",
    "food": "odor_vinegar",
    "geosmin": "odor_geosmin",
    "wind": "wind",
    "sound": "sound",
    "touch": "touch_head",
    "touch_head": "touch_head",
    "looming": "looming",
    "temp_hot": "heat",
    "temp_cold": "cold",
}

DEFAULT_LEDGER_PATH = Path("/home/ubuntu/Portifolio/flynn-max/runtime/data/flynn_ledger.db")
ALIVE_BODY_CAPACITY_FLOOR = 0.01
LOCOMOTION_EPSILON = 0.001
BODY_GEOMETRY_EPSILON = 0.000001


def body_capacity_from_energy(energy_reserve: float) -> float:
    """Map resident energy to capacity, preserving a minimal live reserve."""
    value = float(energy_reserve)
    if not np.isfinite(value):
        return 0.0
    clipped = float(np.clip(value, 0.0, 1.0))
    return max(ALIVE_BODY_CAPACITY_FLOOR, clipped)


def classify_body_motion(
    world_position_delta: List[float],
    body_geometry_delta: float,
    locomotion_epsilon: float = LOCOMOTION_EPSILON,
    geometry_epsilon: float = BODY_GEOMETRY_EPSILON,
) -> str:
    """Classify motion from world displacement, with geometry as a separate fact."""
    world_delta = np.asarray(world_position_delta, dtype=float)
    world_distance = float(np.linalg.norm(world_delta)) if world_delta.size else 0.0
    if world_distance > locomotion_epsilon:
        return "LOCOMOTION"
    if float(body_geometry_delta) > geometry_epsilon:
        return "BODY_MOTION_WITHOUT_LOCOMOTION"
    return "REST"


@dataclass
class StimulusCommand:
    """Bounded, thread-safe command with UUID and cancellation semantics."""
    command_id: str
    modality: str
    intensity: float
    duration_ms: float
    received_wall_monotonic: float
    timeout_sec: float = 5.0
    result_future: threading.Event = field(default_factory=threading.Event)
    response_data: Optional[Dict[str, Any]] = None
    error: Optional[Exception] = None
    cancelled: bool = False
    stimulus_dict: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class PublishedBrainState:
    """
    Immutable thread-safe snapshot published atomically per tick.
    HTTP endpoints consume ONLY this structure.
    ENGINE_MUTABLE_STATE_READ_BY_HTTP = NO.
    """
    instance_id: str
    neural_time_ms: float
    step_count: int
    loop_state: str
    wall_uptime_sec: float
    realtime_factor: float
    chunk_ms: float
    target_tick_ms: float
    last_tick_duration_ms: float
    chunk_execution_mean_ms: float
    chunk_execution_p95_ms: float
    tick_jitter_ms: float
    overrun_count: int
    queue_depth: int
    rolling_100ms_active_neurons: int
    rolling_100ms_spikes: int
    channels: Dict[str, float]
    proboscis_drive: float
    proboscis_hz: float
    motor_actions: List[str]
    state: str
    active_stimulus_modality: Optional[str]
    energy_reserve: float
    feeding_drive: float
    modulation_factor: float
    homeostasis_epoch: str
    body_position: List[float]
    body_orientation: float
    body_action: str
    body_status: str
    world_displacement: List[float]
    world_position_delta: List[float]
    world_position_delta_magnitude: float
    body_geometry_delta: float
    movement_class: str
    locomotion_epsilon: float
    world_distance_travelled: float
    distance_to_resource: Dict[str, float]
    contact_state: Dict[str, bool]
    last_contact: Optional[Dict[str, Any]]
    last_consumption: Optional[Dict[str, Any]]
    sensory_return: Dict[str, Any]
    locomotion_reference: str
    world_scale: float
    body_engine: str
    sigil_body: Dict[str, Any]
    world_time_ms: float
    active_conditions: List[str]
    active_events: List[str]
    plasticity_active: bool
    plasticity_deltas_count: int
    timestamp_utc: str


class ContinuousBrainClock:
    """
    Autonomous Continuous Neural Clock managing Drosophila Whole-Brain LIF Simulation,
    Body, World, and Plasticity overlay.
    Single owner of Session.advance().
    """
    def __init__(
        self,
        session,
        instance_id: str,
        chunk_ms: float = 20.0,
        target_tick_ms: float = 250.0,
        queue_maxsize: int = 32,
        command_timeout: float = 5.0,
        rolling_window_ms: float = 100.0,
        ledger_path: Optional[Path] = None
    ):
        self.session = session
        self.instance_id = instance_id
        self.chunk_ms = float(chunk_ms)
        self.target_tick_ms = float(target_tick_ms)
        self.queue_maxsize = int(queue_maxsize)
        self.command_timeout = float(command_timeout)
        self.rolling_window_ms = float(rolling_window_ms)
        self.ledger_path = ledger_path or DEFAULT_LEDGER_PATH

        self.readout = getattr(self.session, "readout", None)
        if self.readout is None:
            from brain.motor.descending import DescendingReadout
            self.readout = DescendingReadout(self.session.c)
        # E01-N temporal observability is explicit opt-in and passive.  It reads
        # post-advance deltas only; normal resident operation creates no files.
        self.dn_recorder = DNTemporalRecorder.from_env(self.readout, self.chunk_ms)

        # Threading & Bounded Queue
        self._command_queue: queue.Queue = queue.Queue(maxsize=self.queue_maxsize)
        self._active_command: Optional[StimulusCommand] = None
        self._active_applied_wall_monotonic: float = 0.0
        self._active_stim_start_t: float = 0.0
        self._active_stim_end_t: float = 0.0
        self._active_decay_end_t: float = 0.0
        self._active_spike_start: Optional[np.ndarray] = None
        self._recent_completed_commands: Dict[str, Dict[str, Any]] = {}
        self._completed_ids_order: deque = deque(maxlen=128)

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._spike_history: deque = deque()

        # Embodiment, Continuous World, and Plasticity Components (Gate 013)
        self.session.clock = self
        from app.brain.homeostasis_v2 import HomeostasisEngineV2
        self.homeostasis = HomeostasisEngineV2(self.session)
        self.session.homeostasis = self.homeostasis

        self.world = ContinuousWorldEngine()
        self.body = CavernaVirtualBody()
        self._last_body_motion: Dict[str, Any] = {
            "position_before": list(self.body.position),
            "position_after": list(self.body.position),
            "requested_displacement": [0.0, 0.0],
            "applied_displacement": [0.0, 0.0],
            "distance": 0.0,
            "clamped": False,
            "provenance": "PINOCCHIO_FRAME_CENTROID_DELTA"
        }
        self._last_sensory_return: Dict[str, Any] = {}
        # E03 embodiment: persistent Pinocchio state driven only by the raw
        # post-advance activity of all descending neurons.  It is separate
        # from the legacy semantic/virtual action bridge below.
        self.sigil_body = PinocchioSigilBody(self.readout.dn_idx, self.chunk_ms)
        pending_sigil_state = getattr(self.session, "_pending_sigil_body_state", None)
        if pending_sigil_state:
            self.sigil_body.restore_snapshot(pending_sigil_state)
            delattr(self.session, "_pending_sigil_body_state")
        self._last_sigil_q = np.asarray(self.sigil_body.q, dtype=float).copy()
        self._last_body_geometry_delta = 0.0
        self._last_movement_class = "REST"
        self.zeroclaw = ZEROCLAW_EXECUTOR
        self.openclaw = self.zeroclaw  # backward compatibility
        self.plasticity = PlasticityEngine(self.session)

        self.session.world = self.world
        self.session.body = self.body
        self.session.plasticity = self.plasticity

        # Snapshot loading occurs before this clock exists during daemon
        # startup. Apply the pending states only after their live owners have
        # been constructed, preserving continuity without default reinit.
        pending_homeostasis = getattr(self.session, "_pending_homeostasis_v2", None)
        if pending_homeostasis:
            self.homeostasis.restore_checkpoint(pending_homeostasis)
            delattr(self.session, "_pending_homeostasis_v2")
        pending_body_state = getattr(self.session, "_pending_body_state", None)
        if pending_body_state:
            from app.body.contract import BodyState
            self.body.restore(BodyState.from_dict(pending_body_state))
            delattr(self.session, "_pending_body_state")
        pending_world_state = getattr(self.session, "_pending_world_state", None)
        if pending_world_state:
            self.world.restore(pending_world_state)
            delattr(self.session, "_pending_world_state")
        pending_plasticity_state = getattr(self.session, "_pending_plasticity_state", None)
        if pending_plasticity_state:
            self.plasticity.restore(pending_plasticity_state)
            delattr(self.session, "_pending_plasticity_state")

        # Action bridge state tracking (for anti-spam & state transitions)
        self._last_executed_primitive = "STOP"
        self._last_action_time_ms = 0.0

        # Telemetry & Pacing stats
        self.start_wall_monotonic = 0.0
        self.start_neural_time_ms = float(self.session.engine.t_ms)
        self.last_tick_monotonic = 0.0
        self.overrun_count = 0
        self.total_ticks = 0
        self._chunk_exec_times: deque = deque(maxlen=100)
        self._tick_intervals: deque = deque(maxlen=100)

        # Atomic published state
        self._published_state: Optional[PublishedBrainState] = None
        self._publish_state_snapshot("initializing")

    def _publish_state_snapshot(self, loop_state: str):
        """Creates and publishes an immutable PublishedBrainState atomically."""
        now_mono = time.perf_counter()
        now_utc = datetime.now(timezone.utc).isoformat()
        neural_t = float(self.session.engine.t_ms)
        neural_el = neural_t - self.start_neural_time_ms
        wall_uptime = (now_mono - self.start_wall_monotonic) if self.start_wall_monotonic > 0 else 0.0
        wall_el_ms = wall_uptime * 1000.0
        rf = (neural_el / wall_el_ms) if wall_el_ms > 0 else 0.0

        exec_times = list(self._chunk_exec_times)
        if exec_times:
            exec_mean = float(np.mean(exec_times))
            exec_p95 = float(np.percentile(exec_times, 95))
        else:
            exec_mean = 0.0
            exec_p95 = 0.0

        intervals = list(self._tick_intervals)
        if len(intervals) > 1:
            tick_jitter = float(np.std(intervals))
        else:
            tick_jitter = 0.0

        # Compute rolling window metrics (last 100ms)
        if self._spike_history:
            total_counts = np.sum([h[1] for h in self._spike_history], axis=0)
            active_cnt = int(np.count_nonzero(total_counts))
            rolling_spikes = int(total_counts.sum())
            prob_drive = float(self.readout.proboscis_drive(total_counts, window_ms=self.rolling_window_ms))
            if self.readout.proboscis_idx.size > 0:
                prob_hz = float(total_counts[self.readout.proboscis_idx].sum() / self.readout.proboscis_idx.size / (self.rolling_window_ms * 1e-3))
            else:
                prob_hz = 0.0
            channels = self.readout.channels(total_counts, window_ms=self.rolling_window_ms)
        else:
            n_neurons = self.session.c.n if hasattr(self.session.c, 'n') else 139255
            zero = np.zeros(n_neurons, dtype=np.int32)
            active_cnt = 0
            rolling_spikes = 0
            prob_drive = 0.0
            prob_hz = 0.0
            channels = self.readout.channels(zero, window_ms=self.rolling_window_ms)

        motor_actions = [k for k, v in channels.items() if v > 0.5]
        state_str = "STIMULATED" if self._active_command is not None else ("QUIESCENT" if len(motor_actions) == 0 else "ACTIVE")

        sigil_state = self.sigil_body.state_snapshot()
        sigil_state["neural_time_ms"] = round(neural_t, 2)
        world_delta = list(self.body.last_world_displacement)
        world_distance = float(np.linalg.norm(np.asarray(world_delta, dtype=float)))
        self._published_state = PublishedBrainState(
            instance_id=self.instance_id,
            neural_time_ms=round(neural_t, 2),
            step_count=int(self.session.engine.step_count),
            loop_state=loop_state,
            wall_uptime_sec=round(wall_uptime, 2),
            realtime_factor=round(rf, 4),
            chunk_ms=self.chunk_ms,
            target_tick_ms=self.target_tick_ms,
            last_tick_duration_ms=round(exec_times[-1], 2) if exec_times else 0.0,
            chunk_execution_mean_ms=round(exec_mean, 2),
            chunk_execution_p95_ms=round(exec_p95, 2),
            tick_jitter_ms=round(tick_jitter, 2),
            overrun_count=self.overrun_count,
            queue_depth=self._command_queue.qsize(),
            rolling_100ms_active_neurons=active_cnt,
            rolling_100ms_spikes=rolling_spikes,
            channels=channels,
            proboscis_drive=round(prob_drive, 4),
            proboscis_hz=round(prob_hz, 2),
            motor_actions=motor_actions,
            state=state_str,
            active_stimulus_modality=self._active_command.modality if self._active_command else None,
            energy_reserve=float(self.homeostasis.energy_reserve) if hasattr(self, 'homeostasis') else 1.0,
            feeding_drive=float(self.homeostasis.feeding_drive) if hasattr(self, 'homeostasis') else 0.0,
            modulation_factor=float(self.homeostasis.modulation_factor) if hasattr(self, 'homeostasis') else 1.0,
            homeostasis_epoch=str(self.homeostasis.epoch) if hasattr(self, 'homeostasis') else 'v2',
            body_position=list(self.body.position),
            body_orientation=round(self.body.orientation, 2),
            body_action=self.body.current_action,
            body_status=self.body.body_status,
            world_displacement=world_delta,
            world_position_delta=world_delta,
            world_position_delta_magnitude=round(world_distance, 8),
            body_geometry_delta=round(self._last_body_geometry_delta, 8),
            movement_class=self._last_movement_class,
            locomotion_epsilon=LOCOMOTION_EPSILON,
            world_distance_travelled=round(self.body.total_world_distance, 8),
            distance_to_resource=dict(self.world.resource_distances),
            contact_state=dict(self.world.resource_contacts),
            last_contact=self.world.last_contact,
            last_consumption=self.world.last_consumption,
            sensory_return=dict(self._last_sensory_return),
            locomotion_reference="PINOCCHIO_FRAME_CENTROID_DELTA",
            world_scale=self.world.WORLD_SCALE,
            body_engine="pinocchio_sigil",
            sigil_body=sigil_state,
            world_time_ms=round(self.world.world_time_ms, 2),
            active_conditions=self.world.published_state.active_conditions if self.world.published_state else [],
            active_events=self.world.published_state.active_events if self.world.published_state else [],
            plasticity_active=self.plasticity.active,
            plasticity_deltas_count=len(self.plasticity.learned_deltas),
            timestamp_utc=now_utc
        )

    @property
    def published_state(self) -> PublishedBrainState:
        """Lockless, immutable state access for HTTP handlers."""
        return self._published_state

    def start(self):
        """Starts the autonomous continuous neural integration loop."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self.start_wall_monotonic = time.perf_counter()
        self.last_tick_monotonic = self.start_wall_monotonic
        self.start_neural_time_ms = float(self.session.engine.t_ms)
        self._thread = threading.Thread(target=self._run_loop, name="ContinuousBrainLoop", daemon=True)
        self._thread.start()

    def stop(self):
        """Stops the neural integration loop cleanly."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=3.0)
        self.dn_recorder.close()
        self._publish_state_snapshot("stopped")

    def enqueue_stimulus(
        self,
        modality: str,
        intensity: float = 1.0,
        duration_ms: float = 100.0,
        stimulus_dict: Optional[dict] = None,
        command_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Submits stimulus command to bounded queue.
        Guarantees:
        - Rejection if queue full (HTTP 429 semantics)
        - Timeout handling (5s)
        - Duplicate protection via command_id
        - ZERO double advance (waits for normal chunks to advance)
        """
        if not command_id:
            command_id = uuid.uuid4().hex

        # Check duplicate protection
        if command_id in self._recent_completed_commands:
            return self._recent_completed_commands[command_id]

        cmd = StimulusCommand(
            command_id=command_id,
            modality=modality,
            intensity=intensity,
            duration_ms=duration_ms,
            received_wall_monotonic=time.perf_counter(),
            timeout_sec=self.command_timeout,
            stimulus_dict=stimulus_dict
        )

        try:
            self._command_queue.put(cmd, block=False)
        except queue.Full:
            raise queue.Full(f"Stimulus queue full (maxsize={self.queue_maxsize})")

        # Await completion by the continuous clock loop
        finished = cmd.result_future.wait(timeout=self.command_timeout)
        if not finished:
            cmd.cancelled = True
            raise TimeoutError(f"Stimulus command {command_id} timed out after {self.command_timeout}s")

        if cmd.error:
            raise cmd.error

        return cmd.response_data

    def _step_chunk(self):
        """
        THE ONLY SITE IN THE ENTIRE CODEBASE WHERE Session.advance IS CALLED.
        DIRECT_SESSION_ADVANCE_OUTSIDE_CLOCK = 0.
        """
        c0 = self.session.engine.spike_counts.copy()
        self.session.advance(duration_ms=self.chunk_ms)
        delta_spikes = self.session.engine.spike_counts - c0
        # Passive observer: sample after neural advancement, never reset or
        # write to canonical engine counters.
        self.dn_recorder.record(float(self.session.engine.t_ms), delta_spikes)

        # Maintain true rolling 100ms neural-time spike buffer
        current_t = float(self.session.engine.t_ms)
        cutoff_t = current_t - self.rolling_window_ms
        self._spike_history.append((current_t, delta_spikes))
        while self._spike_history and self._spike_history[0][0] <= cutoff_t:
            self._spike_history.popleft()

        return delta_spikes

    def _transduce_sensory_observation(self, observation):
        """
        Continuous Sensory Transduction (Gate 013 Section 16 & 17).
        Transduces persistent/active environmental signals when no explicit one-off command is overriding.
        PHANTOM_SENSORY_INPUT = 0 when no signals active.
        """
        if self._active_command is not None:
            return

        active_signals = observation.active_signals
        neural_modalities = []
        synthetic_signals = []
        for sig_info in active_signals.values():
            if sig_info.get("modality") == "synthetic_proprioception":
                synthetic_signals.append(sig_info)
            else:
                neural_modalities.append(sig_info.get("modality"))
        self._last_sensory_return = {
            **self._last_sensory_return,
            "signals_emitted": active_signals,
            "synthetic_proprioception": synthetic_signals,
            "neural_modalities_requested": neural_modalities,
            "neural_transduction": "SESSION_ADD_MODALITY" if neural_modalities else "NONE",
            "provenance": {
                "world": "CAVERNA_RESIDENT",
                "sensor": "SYNTHETIC_SENSOR_INTERFACE",
                "neural": "REAL_CONNECTOME_MODALITY" if neural_modalities else "NONE",
            },
        }
        if not active_signals:
            # Zero phantom sensation
            self.session.clear_stimuli()
            return

        # Deliver continuous sensory Poisson drive for active modalities
        self.session.clear_stimuli()
        for sig_name, sig_info in active_signals.items():
            if sig_info.get("modality") == "synthetic_proprioception":
                continue
            mod_key = MODALITY_ALIASES.get(sig_info["modality"], sig_info["modality"])
            try:
                self.session.add_modality(
                    mod_key,
                    intensity=sig_info.get("intensity", 1.0),
                    duration_ms=self.chunk_ms + 5.0
                )
            except Exception:
                pass

    def _evaluate_action_bridge(self):
        """
        Action Bridge & Motor Primitive Evaluation (Gate 013 Section 6, 7, 14, 15).
        Maps measured descending outputs to neutral primitives.
        Enforces: Anti-spam guard on quiescence/STOP.
        """
        if not self._spike_history:
            return

        total_counts = np.sum([h[1] for h in self._spike_history], axis=0)
        prob_drive = float(self.readout.proboscis_drive(total_counts, window_ms=self.rolling_window_ms))
        channels = self.readout.channels(total_counts, window_ms=self.rolling_window_ms)

        # Evaluate threshold crossing
        primitive = "STOP"
        params: Dict[str, Any] = {}

        if prob_drive >= 0.20:
            primitive = "INTERACT"
            params = {"drive": round(prob_drive, 4), "target": "proboscis_extension"}
        elif channels.get("escape_takeoff", 0.0) >= 0.50 or channels.get("escape_long_mode", 0.0) >= 0.50:
            primitive = "ESCAPE"
            params = {"takeoff": channels.get("escape_takeoff", 0.0), "long_mode": channels.get("escape_long_mode", 0.0)}
        elif channels.get("turn", 0.0) >= 0.50:
            primitive = "TURN"
            direction = "right" if channels.get("turn_bias", 0.0) >= 0.0 else "left"
            params = {"direction": direction, "d_theta": 15.0}
        elif channels.get("backward_walk", 0.0) >= 0.50:
            primitive = "BACKWARD"
            params = {"step": 0.2}
        else:
            primitive = "STOP"

        cur_t_ms = float(self.session.engine.t_ms)

        # Anti-spam Rule (Section 15):
        # If primitive is STOP and last action was STOP, do NOT spam ledger.
        if primitive == "STOP" and self._last_executed_primitive == "STOP":
            return

        # State transition or meaningful action detected
        action_id = f"act_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}"
        now_iso = datetime.now(timezone.utc).isoformat()
        sess_id = f"sess_{self.instance_id}_{int(cur_t_ms)}"
        causal_chain = f"chain_{action_id}"

        action = BodyAction(
            action_id=action_id,
            timestamp_utc=now_iso,
            neural_time_ms=cur_t_ms,
            source="flynn",
            origin_type="resident_brain",
            brain_instance_id=self.instance_id,
            brain_session_id=sess_id,
            descending_outputs=channels,
            primitive=primitive,
            parameters=params,
            causal_chain_id=causal_chain
        )

        # Gate action through ZeroClaw execution interlock first
        claw_res = self.zeroclaw.execute(action)

        if claw_res.status != "SUCCESS":
            # Interlock failed or backend down: fail closed, NO_EFFECT, heading unchanged
            res = BodyResult(
                action_id=action.action_id,
                primitive=primitive,
                status="FAILED",
                consequence={
                    "error": claw_res.consequence.get("error", "ZeroClaw interlock refused execution"),
                    "effect": "NO_EFFECT",
                    "status": "FAILED"
                }
            )
            self._log_body_action_ledger(action, res)
            return

        # Interlock passed: Execute spatial mutation on Virtual Body
        res = self.body.act(action, world_engine=self.world, homeostasis=self.homeostasis)

        self._last_executed_primitive = primitive
        self._last_action_time_ms = cur_t_ms

        # Record in canonical ledger
        self._log_body_action_ledger(action, res)

    def _log_body_action_ledger(self, action: BodyAction, result: BodyResult):
        """Records legitimate Flynn BodyAction in canonical flynn_ledger.db via official ledger API."""
        try:
            import sqlite3
            from app.ledger import record_ledger_event, LEDGER_DB_PATH
            sess_id = "sess_default"
            exp_id = "DEFAULT_EXPERIMENT"
            if LEDGER_DB_PATH.exists():
                conn = sqlite3.connect(str(LEDGER_DB_PATH), timeout=3.0)
                cur = conn.cursor()
                cur.execute("SELECT session_id, experiment_id FROM experiment_sessions WHERE ended_at_utc IS NULL ORDER BY started_at_utc DESC LIMIT 1")
                row = cur.fetchone()
                conn.close()
                if row:
                    sess_id, exp_id = row

            record_ledger_event(
                session_id=sess_id,
                experiment_id=exp_id,
                source="flynn",
                origin_type="resident_brain",
                event_type="BODY_ACTION",
                variable="motor_primitive",
                action=action.primitive,
                brain_instance_id=action.brain_instance_id,
                brain_session_id=action.brain_session_id,
                descending_outputs=action.descending_outputs,
                causal_chain_id=action.causal_chain_id,
                parent_event_id=action.parent_event_id,
                is_causal_root=(action.parent_event_id is None),
                evidence_class="measured-diagnostic",
                analytics_eligible=0,
                notes=json.dumps(result.consequence) if result.consequence else None
            )
        except Exception:
            pass

    def _check_and_start_next_stimulus(self):
        """Pops and initializes next pending stimulus if none is active."""
        if self._active_command is not None:
            return

        while not self._command_queue.empty():
            try:
                cmd: StimulusCommand = self._command_queue.get_nowait()
            except queue.Empty:
                break

            if cmd.cancelled:
                continue

            # Initialize active stimulus
            mod_key = MODALITY_ALIASES.get(cmd.modality, cmd.modality)
            self._active_command = cmd
            self._active_applied_wall_monotonic = time.perf_counter()
            self._active_stim_start_t = float(self.session.engine.t_ms)
            self._active_stim_end_t = self._active_stim_start_t + cmd.duration_ms
            self._active_decay_end_t = self._active_stim_end_t + 20.0  # 20ms fall decay
            self._active_spike_start = self.session.engine.spike_counts.copy()

            self.session.clear_stimuli()
            self.session.engine.clear_poisson()

            if cmd.stimulus_dict and "indices" in cmd.stimulus_dict and "rates" in cmd.stimulus_dict:
                idx = np.array(cmd.stimulus_dict["indices"], dtype=np.int64)
                rates = np.array(cmd.stimulus_dict["rates"], dtype=np.float64)
                self.session.engine.set_poisson(idx, rates)
            elif mod_key == "paired_vinegar_heat":
                self.session.add_modality("odor_vinegar", intensity=cmd.intensity, duration_ms=100.0, delay_ms=0.0)
                self.session.add_modality("heat", intensity=cmd.intensity, duration_ms=100.0, delay_ms=60.0)
            else:
                self.session.add_modality(mod_key, intensity=cmd.intensity, duration_ms=cmd.duration_ms)
            break

    def _check_and_finish_active_stimulus(self):
        """Finalizes active stimulus metrics when its decay window completes."""
        cmd = self._active_command
        if cmd is None:
            return

        current_t = float(self.session.engine.t_ms)
        if current_t >= self._active_decay_end_t:
            try:
                total_window_ms = round(current_t - self._active_stim_start_t, 2)
                stim_spikes = self.session.engine.spike_counts - self._active_spike_start
                total_spikes = int(stim_spikes.sum())
                active_neurons = int(np.count_nonzero(stim_spikes))

                channels = self.readout.channels(stim_spikes, window_ms=total_window_ms)
                rates = self.readout.rates(stim_spikes, window_ms=total_window_ms)
                prob_drive = float(self.readout.proboscis_drive(stim_spikes, window_ms=total_window_ms))
                if self.readout.proboscis_idx.size > 0 and total_window_ms > 0:
                    prob_hz = float(stim_spikes[self.readout.proboscis_idx].sum() / self.readout.proboscis_idx.size / (total_window_ms * 1e-3))
                else:
                    prob_hz = 0.0

                exec_latency_ms = (time.perf_counter() - self._active_applied_wall_monotonic) * 1000.0
                queue_latency_ms = (self._active_applied_wall_monotonic - cmd.received_wall_monotonic) * 1000.0

                trace = {
                    "status": "ok",
                    "command_id": cmd.command_id,
                    "instance_id": self.instance_id,
                    "brain_session_id": f"sess_{self.instance_id}_{int(self.session.engine.t_ms)}",
                    "session_t_ms": round(current_t, 2),
                    "modality": cmd.modality,
                    "duration_ms": total_window_ms,
                    "total_spikes": total_spikes,
                    "active_neurons": active_neurons,
                    "channels": channels,
                    "rates": rates,
                    "proboscis_drive": round(prob_drive, 4),
                    "proboscis_hz": round(prob_hz, 2),
                    "latency_ms": round(exec_latency_ms, 2),
                    "queue_latency_ms": round(queue_latency_ms, 2),
                    "received_wall_monotonic": cmd.received_wall_monotonic,
                    "applied_neural_time": self._active_stim_start_t,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

                # Cache in duplicate protection
                self._recent_completed_commands[cmd.command_id] = trace
                self._completed_ids_order.append(cmd.command_id)
                if len(self._completed_ids_order) > 64:
                    old_id = self._completed_ids_order.popleft()
                    self._recent_completed_commands.pop(old_id, None)

                cmd.response_data = trace
                self.session.clear_stimuli()
            except Exception as ex:
                cmd.error = ex
            finally:
                cmd.result_future.set()
                self._active_command = None

    def _run_loop(self):
        """The main autonomous continuous simulation loop."""
        while not self._stop_event.is_set():
            t_tick_start = time.perf_counter()
            self._tick_intervals.append(t_tick_start - self.last_tick_monotonic)
            self.last_tick_monotonic = t_tick_start

            # 1. Advance physiology along neural time
            self.homeostasis.tick_neural(self.chunk_ms)

            # 2. Advance continuous world along neural time
            cur_t_ms = float(self.session.engine.t_ms)
            self.world.tick(self.chunk_ms, cur_t_ms)

            # 3. Body local sensing (Euclidean distance, PHANTOM_SENSORY_INPUT = 0)
            observation = self.body.sense(self.world)

            # 4. Continuous sensory transduction
            self._transduce_sensory_observation(observation)

            # 5. Manage queued stimulus commands
            self._check_and_start_next_stimulus()

            # 6. Advance exactly ONE continuous chunk (Single site in codebase)
            delta_spikes = self._step_chunk()
            spiked_indices = np.flatnonzero(delta_spikes)

            # E03: the only neural-to-body boundary.  Energy limits physical
            # execution magnitude after the raw DN request is formed; it does
            # not alter DN activity, direction, channel selection, or policy.
            body_capacity = body_capacity_from_energy(self.homeostasis.energy_reserve)
            centroid_before = self.sigil_body.physical_centroid()
            self.sigil_body.step(
                delta_spikes,
                float(self.session.engine.t_ms),
                actuation_scale=body_capacity,
            )
            centroid_after = self.sigil_body.physical_centroid()
            physical_delta = (centroid_after - centroid_before) * self.world.WORLD_SCALE
            self._last_body_motion = self.body.apply_physical_displacement(physical_delta)
            current_q = np.asarray(self.sigil_body.q, dtype=float)
            self._last_body_geometry_delta = (
                float(np.max(np.abs(current_q - self._last_sigil_q)))
                if current_q.size and current_q.shape == self._last_sigil_q.shape else 0.0
            )
            self._last_sigil_q = current_q.copy()
            self._last_movement_class = classify_body_motion(
                self.body.last_world_displacement,
                self._last_body_geometry_delta,
            )
            self._last_sensory_return = self.world.observe_body(
                self.body.position,
                float(self.session.engine.t_ms),
                self.homeostasis,
            )
            self.body.last_sensory_return = dict(self._last_sensory_return)

            # 7. Synaptic plasticity step (active only during explicit PLASTICITY_EPOCH)
            if self.plasticity.active:
                self.plasticity.on_step_spikes(spiked_indices, float(self.session.engine.t_ms))

            # 8. Action Bridge & Motor Primitive execution
            self._evaluate_action_bridge()

            # 9. Finalize active stimulus command if complete
            self._check_and_finish_active_stimulus()

            # 10. Telemetry and pacing
            t_comp_end = time.perf_counter()
            comp_dur_ms = (t_comp_end - t_tick_start) * 1000.0
            self._chunk_exec_times.append(comp_dur_ms)
            self.total_ticks += 1

            # Pacing & Resource Coexistence:
            sleep_remaining_s = (self.target_tick_ms - comp_dur_ms) / 1000.0
            if sleep_remaining_s > 0.001:
                time.sleep(sleep_remaining_s)
            else:
                self.overrun_count += 1
                time.sleep(0.002)

            # 11. Atomically publish immutable state for lockless HTTP readers
            self._publish_state_snapshot("running")
