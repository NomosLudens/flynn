"""Measured operational CPU budget for Flynn V2.

The normalized reserve is an explicit compute budget, not biological energy.
E=1 represents 3,600 measured CPU seconds. Neural simulation time advances
independently. CPU use measured during one cycle is debited at the next causal
boundary, so the actuation and proprioception at a boundary share one energy
state. Assimilation is disabled until a verifiable source and conversion exist.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from typing import Any, Mapping


MODEL_EPOCH = "homeostasis-v2-measured-cpu-budget-1"
CHECKPOINT_SCHEMA_VERSION = 1
DEFAULT_CPU_SECONDS_PER_FULL_RESERVE = 3600.0


def _finite_number(value: Any, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a finite number")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not math.isfinite(number):
        raise ValueError(f"{name} must be a finite number")
    return number


@dataclass(frozen=True)
class HomeostasisConfig:
    """Parameters of the normalized operational CPU budget."""

    cpu_seconds_per_full_reserve: float = DEFAULT_CPU_SECONDS_PER_FULL_RESERVE

    def __post_init__(self) -> None:
        budget = _finite_number(self.cpu_seconds_per_full_reserve, "cpu_seconds_per_full_reserve")
        if budget <= 0.0:
            raise ValueError("cpu_seconds_per_full_reserve must be positive")
        object.__setattr__(self, "cpu_seconds_per_full_reserve", budget)

    @property
    def config_hash(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class HomeostasisEngineV2:
    """Track neural time and measured CPU cost as episode-bound state."""

    def __init__(
        self,
        *,
        initial_energy_reserve: float,
        initial_neural_time_ms: float = 0.0,
        config: HomeostasisConfig | None = None,
    ) -> None:
        self.config = config or HomeostasisConfig()
        self._energy_reserve = self._bounded_energy(initial_energy_reserve, "initial_energy_reserve")
        self._neural_time_ms = self._nonnegative(initial_neural_time_ms, "initial_neural_time_ms")
        self._cumulative_energy_loss = 0.0
        self._cumulative_assimilation = 0.0
        self._cumulative_cpu_seconds = 0.0
        self._cumulative_cpu_seconds_by_stage: dict[str, float] = {}
        self._pending_cpu_seconds_by_stage: dict[str, float] = {}
        self._pending_cpu_event_id: str | None = None
        self._last_cpu_charge_event_id: str | None = None

    @staticmethod
    def _nonnegative(value: Any, name: str) -> float:
        number = _finite_number(value, name)
        if number < 0.0:
            raise ValueError(f"{name} cannot be negative")
        return number

    @staticmethod
    def _bounded_energy(value: Any, name: str) -> float:
        number = _finite_number(value, name)
        if not 0.0 <= number <= 1.0:
            raise ValueError(f"{name} must be within [0, 1]")
        return number

    @classmethod
    def _validated_stage_costs(cls, costs_by_stage: Mapping[str, float]) -> dict[str, float]:
        if not isinstance(costs_by_stage, Mapping) or not costs_by_stage:
            raise ValueError("costs_by_stage must be a non-empty mapping")
        result: dict[str, float] = {}
        for stage, value in costs_by_stage.items():
            if not isinstance(stage, str) or not stage.strip():
                raise ValueError("CPU stage names must be non-empty strings")
            result[stage] = cls._nonnegative(value, f"cpu_seconds[{stage}]")
        if not any(result.values()):
            raise ValueError("measured CPU costs must include a positive value")
        return result

    @property
    def energy_reserve(self) -> float:
        return self._energy_reserve

    @property
    def feeding_drive(self) -> float:
        return 1.0 - self._energy_reserve

    @property
    def body_capacity(self) -> float:
        return self._energy_reserve

    @property
    def neural_time_ms(self) -> float:
        return self._neural_time_ms

    @property
    def cumulative_energy_loss(self) -> float:
        return self._cumulative_energy_loss

    @property
    def cumulative_assimilation(self) -> float:
        return self._cumulative_assimilation

    @property
    def cumulative_cpu_seconds(self) -> float:
        return self._cumulative_cpu_seconds

    @property
    def pending_cpu_seconds_by_stage(self) -> dict[str, float]:
        return dict(self._pending_cpu_seconds_by_stage)

    @property
    def modulation_factor(self) -> float:
        """Neural modulation is intentionally absent from this model."""
        return 1.0

    @property
    def epoch(self) -> str:
        return MODEL_EPOCH

    @property
    def config_hash(self) -> str:
        return self.config.config_hash

    def tick_neural(self, delta_neural_ms: float) -> float:
        """Advance neural time without converting it into energy use."""
        delta_ms = self._nonnegative(delta_neural_ms, "delta_neural_ms")
        self._neural_time_ms = self._nonnegative(
            self._neural_time_ms + delta_ms, "next_neural_time_ms"
        )
        return self._energy_reserve

    def record_cpu_costs(self, *, event_id: str, costs_by_stage: Mapping[str, float]) -> None:
        """Queue measured costs from a completed cycle for the next boundary."""
        if not isinstance(event_id, str) or not event_id.strip():
            raise ValueError("event_id must be a non-empty string")
        costs = self._validated_stage_costs(costs_by_stage)
        if self._pending_cpu_event_id is not None:
            if self._pending_cpu_event_id != event_id or self._pending_cpu_seconds_by_stage != costs:
                raise RuntimeError("a different CPU cost is pending at this causal boundary")
            return
        if event_id == self._last_cpu_charge_event_id:
            return
        self._pending_cpu_event_id = event_id
        self._pending_cpu_seconds_by_stage = costs

    def apply_pending_cpu_costs(self) -> float:
        """Debit the prior cycle's measured costs exactly once."""
        if self._pending_cpu_event_id is None:
            return self._energy_reserve
        costs = self._pending_cpu_seconds_by_stage
        total = self._nonnegative(sum(costs.values()), "total_cpu_seconds")
        applied_loss = min(self._energy_reserve, total / self.config.cpu_seconds_per_full_reserve)
        self._energy_reserve -= applied_loss
        self._cumulative_energy_loss = self._nonnegative(
            self._cumulative_energy_loss + applied_loss, "cumulative_energy_loss"
        )
        self._cumulative_cpu_seconds = self._nonnegative(
            self._cumulative_cpu_seconds + total, "cumulative_cpu_seconds"
        )
        for stage, seconds in costs.items():
            self._cumulative_cpu_seconds_by_stage[stage] = (
                self._cumulative_cpu_seconds_by_stage.get(stage, 0.0) + seconds
            )
        self._last_cpu_charge_event_id = self._pending_cpu_event_id
        self._pending_cpu_event_id = None
        self._pending_cpu_seconds_by_stage = {}
        return self._energy_reserve

    def assimilate(self, amount: float) -> float:
        """Reject unproven energy input; no source conversion is configured."""
        raise RuntimeError("energy assimilation is disabled: no verified source or conversion is configured")

    def serialize_checkpoint(self) -> dict[str, Any]:
        """Return the complete budget state required for causal restoration."""
        return {
            "schema_version": CHECKPOINT_SCHEMA_VERSION,
            "model_epoch": self.epoch,
            "config_hash": self.config_hash,
            "energy_units": "normalized_cpu_budget_fraction",
            "cpu_seconds_per_full_reserve": self.config.cpu_seconds_per_full_reserve,
            "neural_time_ms": self._neural_time_ms,
            "energy_reserve": self._energy_reserve,
            "cumulative_energy_loss": self._cumulative_energy_loss,
            "cumulative_assimilation": self._cumulative_assimilation,
            "cumulative_cpu_seconds": self._cumulative_cpu_seconds,
            "cumulative_cpu_seconds_by_stage": dict(sorted(self._cumulative_cpu_seconds_by_stage.items())),
            "pending_cpu_event_id": self._pending_cpu_event_id,
            "pending_cpu_seconds_by_stage": dict(sorted(self._pending_cpu_seconds_by_stage.items())),
            "last_cpu_charge_event_id": self._last_cpu_charge_event_id,
        }

    def restore_checkpoint(self, checkpoint: Mapping[str, Any]) -> None:
        """Restore only a complete checkpoint for this exact budget model."""
        if not isinstance(checkpoint, Mapping):
            raise ValueError("checkpoint must be a mapping")
        if checkpoint.get("schema_version") != CHECKPOINT_SCHEMA_VERSION:
            raise ValueError("unsupported homeostasis checkpoint schema")
        if checkpoint.get("model_epoch") != self.epoch:
            raise ValueError("checkpoint model epoch does not match")
        if checkpoint.get("config_hash") != self.config_hash:
            raise ValueError("checkpoint configuration does not match")
        if checkpoint.get("energy_units") != "normalized_cpu_budget_fraction":
            raise ValueError("checkpoint energy units do not match")

        neural_time_ms = self._nonnegative(checkpoint.get("neural_time_ms"), "checkpoint.neural_time_ms")
        energy_reserve = self._bounded_energy(checkpoint.get("energy_reserve"), "checkpoint.energy_reserve")
        cumulative_energy_loss = self._nonnegative(
            checkpoint.get("cumulative_energy_loss"), "checkpoint.cumulative_energy_loss"
        )
        cumulative_assimilation = self._nonnegative(
            checkpoint.get("cumulative_assimilation"), "checkpoint.cumulative_assimilation"
        )
        cumulative_cpu_seconds = self._nonnegative(
            checkpoint.get("cumulative_cpu_seconds"), "checkpoint.cumulative_cpu_seconds"
        )
        cumulative_by_stage = checkpoint.get("cumulative_cpu_seconds_by_stage")
        pending_by_stage = checkpoint.get("pending_cpu_seconds_by_stage")
        if not isinstance(cumulative_by_stage, Mapping) or not isinstance(pending_by_stage, Mapping):
            raise ValueError("checkpoint CPU stage totals must be mappings")
        cumulative_by_stage = (
            {key: self._nonnegative(value, f"checkpoint.cumulative_cpu_seconds_by_stage[{key}]")
             for key, value in cumulative_by_stage.items()}
        )
        pending_by_stage = (
            self._validated_stage_costs(pending_by_stage) if pending_by_stage else {}
        )
        pending_event_id = checkpoint.get("pending_cpu_event_id")
        if bool(pending_event_id) != bool(pending_by_stage):
            raise ValueError("checkpoint pending CPU event and costs must be present together")

        self._neural_time_ms = neural_time_ms
        self._energy_reserve = energy_reserve
        self._cumulative_energy_loss = cumulative_energy_loss
        self._cumulative_assimilation = cumulative_assimilation
        self._cumulative_cpu_seconds = cumulative_cpu_seconds
        self._cumulative_cpu_seconds_by_stage = dict(cumulative_by_stage)
        self._pending_cpu_event_id = pending_event_id
        self._pending_cpu_seconds_by_stage = dict(pending_by_stage)
        self._last_cpu_charge_event_id = checkpoint.get("last_cpu_charge_event_id")


__all__ = ["HomeostasisConfig", "HomeostasisEngineV2"]
