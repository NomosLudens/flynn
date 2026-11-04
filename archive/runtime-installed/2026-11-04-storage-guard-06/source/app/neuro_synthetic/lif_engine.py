"""Experimental Shiu LIF state machine for the Flynn V2 neural core."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .signed_connectome import SignedConnectome


@dataclass(frozen=True)
class LIFParameters:
    v_rest_mv: float = -52.0
    v_reset_mv: float = -52.0
    v_threshold_mv: float = -45.0
    tau_m_ms: float = 20.0
    tau_syn_ms: float = 5.0
    refractory_ms: float = 2.2
    delay_ms: float = 1.8
    synapse_weight_mv: float = 0.275
    dt_ms: float = 0.1

    @property
    def refractory_steps(self) -> int:
        return round(self.refractory_ms / self.dt_ms)

    @property
    def delay_steps(self) -> int:
        return round(self.delay_ms / self.dt_ms)


PARAMETERS = LIFParameters()
DELAY_SLOTS = PARAMETERS.delay_steps + 1
MODEL_ID = "shiu-lif-experimental-v783-flynn-v1"


def _validate_parameters(parameters: LIFParameters) -> None:
    if parameters.dt_ms <= 0 or parameters.tau_m_ms <= 0 or parameters.tau_syn_ms <= 0:
        raise ValueError("time step and time constants must be positive")
    for label, duration in (("delay", parameters.delay_ms), ("refractory", parameters.refractory_ms)):
        if abs(duration / parameters.dt_ms - round(duration / parameters.dt_ms)) > 1e-12:
            raise ValueError(f"{label} must be an integer multiple of the explicit time step")
    if parameters.delay_steps <= 0 or parameters.refractory_steps <= 0:
        raise ValueError("delay and refractory durations must be at least one time step")


class LIFEngine:
    """Vectorized float64 LIF dynamics and deterministic delayed CSR propagation.

    This class does not create drive, behavior, or spontaneous spikes. With the
    approved resting initialization and no input, it remains silent.
    """

    STATE_VERSION = 1

    def __init__(self, connectome: SignedConnectome, parameters: LIFParameters = PARAMETERS):
        _validate_parameters(parameters)
        self.connectome = connectome
        self.parameters = parameters
        self.neuron_count = len(connectome.root_ids)
        if self.neuron_count < 1:
            raise ValueError("connectome has no neurons")
        if connectome.indptr.shape != (self.neuron_count + 1,):
            raise ValueError("connectome CSR rows do not match the root-ID population")
        if int(connectome.indptr[-1]) != len(connectome.indices) or len(connectome.indices) != len(connectome.signed_count):
            raise ValueError("connectome CSR arrays are inconsistent")

        self.v = np.full(self.neuron_count, parameters.v_rest_mv, dtype=np.float64)
        self.g = np.zeros(self.neuron_count, dtype=np.float64)
        self.refractory_until_tick = np.zeros(self.neuron_count, dtype=np.int64)
        self.delay_buffer = np.zeros((parameters.delay_steps + 1, self.neuron_count), dtype=np.float64)
        self.frame_spike_counts = np.zeros(self.neuron_count, dtype=np.uint32)
        self.tick = 0
        # Refractory expirations are derived from the checkpointed per-neuron
        # deadline vector. This count lets the silent/all-eligible case avoid
        # allocating a 139k-element index vector every neural tick.
        self._refractory_expiry_counts = np.zeros(parameters.refractory_steps + 1, dtype=np.int64)
        self._refractory_active_count = 0
        self._voltage_current = np.empty(self.neuron_count, dtype=np.float64)
        self._decay_m = float(np.exp(-parameters.dt_ms / parameters.tau_m_ms))
        self._decay_syn = float(np.exp(-parameters.dt_ms / parameters.tau_syn_ms))
        self._coupling = parameters.tau_syn_ms / (parameters.tau_m_ms - parameters.tau_syn_ms)

    @property
    def neural_time_ms(self) -> float:
        return self.tick * self.parameters.dt_ms

    def step(self, *, external_indices: np.ndarray | None = None,
             external_g_increment: float | np.ndarray = 0.0) -> np.ndarray:
        """Advance exactly one explicit dt and return compact indexes that spiked."""
        tick = self.tick
        if external_indices is not None:
            indexes = np.asarray(external_indices, dtype=np.int64)
            if indexes.ndim != 1 or np.any(indexes < 0) or np.any(indexes >= self.neuron_count):
                raise ValueError("external input indices are outside the canonical population")
            if len(np.unique(indexes)) != indexes.size:
                raise ValueError("external input indices must be unique within one transducer packet")
            increments = np.asarray(external_g_increment, dtype=np.float64)
            if increments.ndim == 0:
                if isinstance(external_g_increment, bool):
                    raise ValueError("external conductance increment must not be boolean")
            elif increments.shape != indexes.shape:
                raise ValueError("per-target conductance increments must match the target index vector")
            if not np.isfinite(increments).all() or np.any(increments < 0):
                raise ValueError("external conductance increment must be finite and non-negative")
            if increments.ndim == 0:
                if float(increments) > 0:
                    self.g[indexes] += float(increments)
            elif np.any(increments > 0):
                self.g[indexes] += increments
        expiry_slot = tick % self._refractory_expiry_counts.size
        expired_now = int(self._refractory_expiry_counts[expiry_slot])
        if expired_now:
            self._refractory_active_count -= expired_now
            self._refractory_expiry_counts[expiry_slot] = 0
            if self._refractory_active_count < 0:
                raise RuntimeError("refractory expiry accounting underflow")

        if self._refractory_active_count == 0:
            # Preserve the same operation order as the indexed reference path,
            # but update the dense arrays directly when every neuron is eligible.
            np.multiply(self.g, self._coupling, out=self._voltage_current)
            self._voltage_current *= self._decay_m - self._decay_syn
            self.v -= self.parameters.v_rest_mv
            self.v *= self._decay_m
            self.v += self.parameters.v_rest_mv
            self.v += self._voltage_current
            self.g *= self._decay_syn
            spiking = np.flatnonzero(self.v > self.parameters.v_threshold_mv)
        else:
            eligible = np.flatnonzero(self.refractory_until_tick <= tick)
            if eligible.size:
                old_g = self.g[eligible].copy()
                next_g = old_g * self._decay_syn
                next_v = (
                    self.parameters.v_rest_mv
                    + (self.v[eligible] - self.parameters.v_rest_mv) * self._decay_m
                    + old_g * self._coupling * (self._decay_m - self._decay_syn)
                )
                self.g[eligible] = next_g
                self.v[eligible] = next_v
                spiking = eligible[next_v > self.parameters.v_threshold_mv]
            else:
                spiking = np.empty(0, dtype=np.int64)

        # Brian2 schedule: thresholds, then synaptic pathways, then reset.
        # A spike at t schedules its directed outgoing edges for t + delay_steps.
        due_slot = self.delay_buffer[tick % self.delay_buffer.shape[0]]
        if spiking.size:
            target_slot = self.delay_buffer[(tick + self.parameters.delay_steps) % self.delay_buffer.shape[0]]
            for source in spiking:
                start = int(self.connectome.indptr[source])
                end = int(self.connectome.indptr[source + 1])
                if end > start:
                    target_indexes = self.connectome.indices[start:end]
                    increments = self.connectome.signed_count[start:end].astype(np.float64)
                    increments *= self.parameters.synapse_weight_mv
                    np.add.at(target_slot, target_indexes, increments)

        # Due on_pre events occur after this tick's group update and before reset;
        # they change g now and participate in the next group update.
        self.g += due_slot
        due_slot.fill(0.0)

        if spiking.size:
            if np.any(self.frame_spike_counts[spiking] == np.iinfo(np.uint32).max):
                raise OverflowError("spike count exceeds the frame's uint32 representation")
            self.frame_spike_counts[spiking] += 1
            self.v[spiking] = self.parameters.v_reset_mv
            self.g[spiking] = 0.0
            refractory_until = tick + self.parameters.refractory_steps
            self.refractory_until_tick[spiking] = refractory_until
            self._refractory_active_count += int(spiking.size)
            self._refractory_expiry_counts[
                refractory_until % self._refractory_expiry_counts.size
            ] += int(spiking.size)

        self.tick += 1
        return spiking

    def advance(self, steps: int, *, external_indices: np.ndarray | None = None,
                external_g_increment: float | np.ndarray = 0.0) -> int:
        if isinstance(steps, bool) or not isinstance(steps, int) or steps < 0:
            raise ValueError("steps must be a non-negative integer")
        spike_total = 0
        for _ in range(steps):
            spike_total += self.step(
                external_indices=external_indices,
                external_g_increment=external_g_increment,
            ).size
        return int(spike_total)

    def sparse_frame_counts(self) -> tuple[tuple[int, int], ...]:
        """Read the current sparse frame without clearing its durable cursor."""
        nonzero = np.flatnonzero(self.frame_spike_counts)
        return tuple((int(index), int(self.frame_spike_counts[index])) for index in nonzero)

    def drain_frame_counts(self) -> tuple[tuple[int, int], ...]:
        """Return and clear sparse counts at a frame boundary."""
        result = self.sparse_frame_counts()
        self.frame_spike_counts.fill(0)
        return result

    def export_state(self) -> dict[str, Any]:
        if np.any(self.frame_spike_counts):
            raise RuntimeError("checkpoint only at a drained neural frame boundary")
        return {
            "state_version": self.STATE_VERSION,
            "tick": self.tick,
            "v": self.v,
            "g": self.g,
            "refractory_until_tick": self.refractory_until_tick,
            "delay_buffer": self.delay_buffer,
            "frame_spike_counts": self.frame_spike_counts,
        }

    def restore_state(self, state: dict[str, Any]) -> None:
        if state.get("state_version") != self.STATE_VERSION:
            raise ValueError("unsupported LIF checkpoint state version")
        tick = state.get("tick")
        if isinstance(tick, bool) or not isinstance(tick, int) or tick < 0:
            raise ValueError("checkpoint tick must be a non-negative integer")
        expected = {
            "v": (self.v.shape, np.dtype(np.float64)),
            "g": (self.g.shape, np.dtype(np.float64)),
            "refractory_until_tick": (self.refractory_until_tick.shape, np.dtype(np.int64)),
            "delay_buffer": (self.delay_buffer.shape, np.dtype(np.float64)),
            "frame_spike_counts": (self.frame_spike_counts.shape, np.dtype(np.uint32)),
        }
        for name, (shape, dtype) in expected.items():
            array = state.get(name)
            if not isinstance(array, np.ndarray) or array.shape != shape or array.dtype != dtype:
                raise ValueError(f"checkpoint {name} shape or dtype does not match the active core")
            if np.issubdtype(dtype, np.floating) and not np.all(np.isfinite(array)):
                raise ValueError(f"checkpoint {name} contains non-finite values")
        if np.any(state["frame_spike_counts"]):
            raise ValueError("checkpoint contains undrained frame counts")
        self.v[:] = state["v"]
        self.g[:] = state["g"]
        self.refractory_until_tick[:] = state["refractory_until_tick"]
        self.delay_buffer[:] = state["delay_buffer"]
        self.frame_spike_counts[:] = state["frame_spike_counts"]
        self.tick = tick
        refractory = self.refractory_until_tick
        active = refractory > tick
        self._refractory_active_count = int(np.count_nonzero(active))
        self._refractory_expiry_counts.fill(0)
        if self._refractory_active_count:
            slots = refractory[active] % self._refractory_expiry_counts.size
            self._refractory_expiry_counts[:] = np.bincount(
                slots, minlength=self._refractory_expiry_counts.size,
            )
