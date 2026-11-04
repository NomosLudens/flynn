"""Python-to-PicoClaw v0.2.9 deterministic JSONL process port.

This adapter is opt-in: callers provide a locally built Flynn bridge binary.
It forwards only already-persisted, provenance-bound LIF frame observations.
It does not request or infer physical actions.
"""

from __future__ import annotations

import json
import hashlib
import os
import subprocess
import threading
import time
import uuid
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


from .sqlite_store import picoclaw_frame_digest


PROTOCOL_VERSION = "flynn.picoclaw.frame.v1"


class PicoClawMCPPort:
    """Keep the actual Go/PicoClaw MCP Manager process alive across frames."""

    def __init__(
        self,
        *,
        executable: str | Path,
        database_path: str | Path,
        project_root: str | Path,
        python_executable: str = "python3",
        pinocchio_python: str | Path | None = None,
        population_manifest: str | Path | None = None,
        resident_mode: bool = False,
        causal_generation_id: str | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.executable = str(Path(executable).resolve())
        self.database_path = str(Path(database_path).resolve())
        self.project_root = str(Path(project_root).resolve())
        self.python_executable = python_executable
        # Keep the venv's `bin/python` symlink itself: resolving it to the base
        # interpreter bypasses that environment's site-packages.
        self.pinocchio_python = os.path.abspath(os.fspath(pinocchio_python)) if pinocchio_python else None
        self.population_manifest = str(Path(population_manifest).resolve()) if population_manifest else None
        self.resident_mode = bool(resident_mode)
        self.causal_generation_id = causal_generation_id
        if self.resident_mode and not self.causal_generation_id:
            raise ValueError("resident PicoClaw coordination requires the persisted causal generation")
        self.timeout_seconds = timeout_seconds
        self._lock = threading.Lock()
        self._process: subprocess.Popen[str] | None = None
        self._delivery_epoch: str | None = None

    def start(self) -> None:
        with self._lock:
            self._start_locked()

    def _start_locked(self) -> subprocess.Popen[str]:
        if self._process is not None and self._process.poll() is None:
            return self._process
        if not Path(self.executable).is_file():
            raise FileNotFoundError(f"PicoClaw bridge binary not found: {self.executable}")
        if not Path(self.database_path).is_file():
            raise FileNotFoundError(f"existing Flynn V2 database not found: {self.database_path}")
        env = os.environ.copy()
        delivery_epoch = uuid.uuid4().hex
        env.update({
            "FLYNN_V2_DB": self.database_path,
            "FLYNN_PROJECT_ROOT": self.project_root,
            "FLYNN_PYTHON_EXECUTABLE": self.python_executable,
            "FLYNN_PICOCLAW_DELIVERY_EPOCH": delivery_epoch,
        })
        if self.resident_mode:
            env["FLYNN_RESIDENT_SINGLE_WRITER"] = "1"
            env["FLYNN_CAUSAL_GENERATION_ID"] = str(self.causal_generation_id)
        if self.pinocchio_python:
            env["FLYNN_PINOCCHIO_PYTHON"] = self.pinocchio_python
        if self.population_manifest:
            env["FLYNN_PINOCCHIO_POPULATION_MANIFEST"] = self.population_manifest
        self._process = subprocess.Popen(
            [self.executable], cwd=self.project_root, env=env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=None,
            text=True, encoding="utf-8", bufsize=1,
        )
        self._delivery_epoch = delivery_epoch
        return self._process

    @property
    def delivery_epoch(self) -> str:
        with self._lock:
            self._start_locked()
            if self._delivery_epoch is None:
                raise RuntimeError("PicoClaw delivery epoch was not initialized")
            return self._delivery_epoch

    def coordinate_persisted_frame(self, state: dict[str, Any], *,
                                   dn_readout: dict[str, Any] | None = None,
                                   receipt: dict[str, Any] | None = None) -> dict[str, Any]:
        """Forward a latest aggregator snapshot; fail closed on every mismatch."""
        required = (
            "episode_id", "sequence", "neural_time_ms", "dataset_version",
            "mapping_sha256", "manifest_sha256", "core_id", "model_sha256",
            "config_sha256", "connectome_sha256", "start_tick", "end_tick",
            "dt_ms", "active_neuron_count", "total_spikes", "input_sha256",
            "mapped_spikes",
        )
        if any(state.get(key) is None for key in required):
            raise ValueError("persisted neural frame lacks full LIF provenance")
        if self.resident_mode and state.get("causal_generation_id") != self.causal_generation_id:
            raise ValueError("persisted neural frame differs from the active causal generation")
        if state["dataset_version"] != "fafb-v783":
            raise ValueError("PicoClaw port accepts only the approved FAFB v783 frames")
        timestamp = datetime.now(timezone.utc).isoformat()
        if self.resident_mode and (not isinstance(receipt, dict)
                or receipt.get("status") not in {"PREPARED", "CONFIRMED"}):
            raise ValueError("resident PicoClaw call requires its durable coordinator receipt")
        generation_id = str(state.get("causal_generation_id") or "legacy")
        event_id = f"{state['episode_id']}:generation:{generation_id}:frame:{state['sequence']}"
        idempotency_key = f"{state['episode_id']}|{generation_id}|{state['sequence']}"
        frame_digest = picoclaw_frame_digest(state, dn_readout)
        if self.resident_mode and (receipt.get("idempotency_key") != idempotency_key
                or receipt.get("frame_digest") != frame_digest):
            raise ValueError("resident PicoClaw receipt does not match the exact transient frame")
        delivery_epoch = str(receipt.get("delivery_epoch") or "")
        payload = {key: state[key] for key in (
            "dataset_version", "mapping_sha256", "manifest_sha256", "core_id",
            "model_sha256", "config_sha256", "connectome_sha256", "start_tick",
            "end_tick", "dt_ms", "active_neuron_count", "total_spikes",
            "input_sha256", "mapped_spikes",
        )}
        if state.get("causal_generation_id"):
            payload["causal_generation_id"] = state["causal_generation_id"]
        if self.resident_mode:
            current_epoch = self.delivery_epoch
            if receipt.get("status") == "PREPARED" and delivery_epoch != current_epoch:
                raise RuntimeError("indeterminate prepared PicoClaw operation belongs to a prior bridge epoch; reconciliation required")
            payload["delivery_epoch"] = delivery_epoch
        if dn_readout is not None:
            if (dn_readout.get("population") != "flywire-v2.1.0-descending-1303"
                    or dn_readout.get("connectome_sha256") != state["connectome_sha256"]
                    or len(dn_readout.get("spike_counts", [])) != 1303
                    or dn_readout.get("total_spikes") != sum(dn_readout["spike_counts"])):
                raise ValueError("PicoClaw motor readout differs from the authorized 1303-DN contract")
            payload["dn_readout"] = (
                {**dn_readout, "homeostasis_state": state["homeostasis_state"]}
                if "homeostasis_state" in state else dn_readout
            )
        message = {
            "protocol_version": PROTOCOL_VERSION,
            "request_id": hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()[:32],
            "event_id": event_id,
            "episode_id": state["episode_id"],
            "source_component": "neural_activity_aggregator",
            "event_type": "NEURAL_FRAME_OBSERVED",
            "simulation_time_ms": state["neural_time_ms"],
            "sequence": state["sequence"],
            "occurred_at_utc": timestamp,
            "provenance_sha256": state["input_sha256"],
            "causal_generation_id": generation_id,
            "idempotency_key": idempotency_key,
            "frame_digest": frame_digest,
            "payload": payload,
        }
        with self._lock:
            process = self._start_locked()
            if process.stdin is None or process.stdout is None:
                raise RuntimeError("PicoClaw bridge stdio is unavailable")
            process_cpu_before = self._process_tree_cpu_seconds(process.pid)
            started = time.perf_counter()
            process.stdin.write(json.dumps(message, separators=(",", ":"), allow_nan=False) + "\n")
            process.stdin.flush()
            line = self._readline_timeout(process, self.timeout_seconds)
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            process_cpu_after = self._process_tree_cpu_seconds(process.pid)
        process_tree_cpu_ms = (
            max(0.0, process_cpu_after - process_cpu_before) * 1000.0
            if process_cpu_before is not None and process_cpu_after is not None else None
        )
        try:
            response = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RuntimeError("PicoClaw bridge returned invalid JSONL") from exc
        if response.get("request_id") != message["request_id"] or response.get("error"):
            raise RuntimeError(f"PicoClaw coordination failed: {response.get('error', 'request ID mismatch')}")
        result = response.get("result")
        if not isinstance(result, dict) or result.get("provider_used") is not False:
            raise RuntimeError("PicoClaw bridge did not confirm deterministic no-provider execution")
        mcp_result = result.get("mcp_result", {}).get("structuredContent", {})
        if (mcp_result.get("status") not in {"FRAME_COORDINATED_OBSERVATION_ONLY", "IDEMPOTENT_RETRY"}
                or mcp_result.get("source_provenance_sha256") != state["input_sha256"]
                or mcp_result.get("sequence") != state["sequence"]
                or (state.get("causal_generation_id") is not None
                    and mcp_result.get("causal_generation_id") != state["causal_generation_id"])):
            raise RuntimeError("PicoClaw MCP acknowledgement does not match the persisted neural frame")
        return {
            **mcp_result,
            "pico_bridge_elapsed_ms": elapsed_ms,
            "picoclaw_process_tree_cpu_ms": process_tree_cpu_ms,
            "upstream_call_elapsed_ms": result.get("elapsed_ms"),
            "pinocchio_timing": mcp_result.get("pinocchio_timing"),
            "pinocchio_result": mcp_result.get("pinocchio_result"),
            "receipt_status": "CONFIRMED" if mcp_result.get("status") == "IDEMPOTENT_RETRY" else "PREPARED",
            "receipt_key": idempotency_key,
            "frame_digest": frame_digest,
            "receipt_result_sha256": mcp_result.get("receipt_result_sha256"),
            "output_state_id": mcp_result.get("output_state_id"),
            "body_checkpoint_state_id": mcp_result.get("body_checkpoint_state_id"),
            "provider_used": False,
        }

    @staticmethod
    def _process_tree_cpu_seconds(root_pid: int) -> float | None:
        """Read Linux CPU counters for the live PicoClaw/MCP process tree."""
        if not Path("/proc").is_dir():
            return None
        ticks_per_second = float(os.sysconf("SC_CLK_TCK"))
        pending = [int(root_pid)]
        seen: set[int] = set()
        total_ticks = 0
        while pending:
            pid = pending.pop()
            if pid in seen:
                continue
            seen.add(pid)
            try:
                raw_stat = Path(f"/proc/{pid}/stat").read_text(encoding="ascii")
                fields = raw_stat[raw_stat.rfind(")") + 2:].split()
                total_ticks += int(fields[11]) + int(fields[12])
                children = Path(f"/proc/{pid}/task/{pid}/children").read_text(encoding="ascii")
                pending.extend(int(child) for child in children.split())
            except (OSError, ValueError, IndexError):
                continue
        return total_ticks / ticks_per_second

    def dispatch_motor_calibration(self, *, calibration_id: str, sequence: int,
                                    neural_time_ms: float, occurred_at_utc: str,
                                    readout: dict[str, Any], root_ids: list[int],
                                    chunk_ms: float = 20.0,
                                    body_episode_id: str | None = None,
                                    body_stream_id: str | None = None) -> dict[str, Any]:
        """Route an external calibration-only packet through PicoClaw to the real body worker."""
        if not calibration_id.startswith("instrumental-motor-calibration:"):
            raise ValueError("calibration ID must identify a separate external instrument")
        counts = readout.get("spike_counts")
        if (readout.get("population") != "flywire-v2.1.0-descending-1303" or
                len(counts or []) != 1303 or len(root_ids) != 1303 or
                (sum(counts) <= 0 and sequence == 0) or
                chunk_ms != 20.0 or readout.get("total_spikes") != sum(counts)):
            raise ValueError("calibration packet differs from the authorized motor population contract")
        if bool(body_episode_id) != bool(body_stream_id):
            raise ValueError("body episode and stream IDs must be supplied together")
        message = {
            "protocol_version": PROTOCOL_VERSION,
            "request_id": uuid.uuid4().hex,
            "event_id": f"{calibration_id}:step:{sequence}",
            "episode_id": calibration_id,
            "source_component": "external_calibration_equipment",
            "event_type": "MOTOR_CALIBRATION",
            "simulation_time_ms": float(neural_time_ms),
            "sequence": int(sequence),
            "occurred_at_utc": occurred_at_utc,
            "provenance_sha256": readout["manifest_sha256"],
            "payload": {
                "dataset_version": "fafb-v783",
                "mapping_sha256": readout["mapping_sha256"],
                "manifest_sha256": readout["manifest_sha256"],
                "connectome_sha256": readout["connectome_sha256"],
                "calibration_id": calibration_id,
                "population_mapping_sha256": readout["mapping_sha256"],
                "compact_indices": readout["compact_indices"],
                "root_ids": [int(value) for value in root_ids],
                "spike_counts": [int(value) for value in counts],
                "chunk_ms": chunk_ms,
                **({"body_episode_id": body_episode_id, "body_stream_id": body_stream_id}
                   if body_episode_id and body_stream_id else {}),
            },
        }
        with self._lock:
            process = self._start_locked()
            if process.stdin is None or process.stdout is None:
                raise RuntimeError("PicoClaw bridge stdio is unavailable")
            started = time.perf_counter()
            process.stdin.write(json.dumps(message, separators=(",", ":"), allow_nan=False) + "\n")
            process.stdin.flush()
            line = self._readline_timeout(process, max(self.timeout_seconds, 60.0))
            elapsed_ms = (time.perf_counter() - started) * 1000.0
        response = json.loads(line)
        if response.get("request_id") != message["request_id"] or response.get("error"):
            raise RuntimeError(f"PicoClaw motor calibration failed: {response.get('error', 'request ID mismatch')}")
        result = response.get("result", {})
        if result.get("provider_used") is not False:
            raise RuntimeError("PicoClaw motor calibration unexpectedly used a model provider")
        content = result.get("mcp_result", {}).get("structuredContent", {})
        if (content.get("status") != "MOTOR_CALIBRATION_APPLIED_NOT_FLYNN_ACTIVITY" or
                content.get("origin") != "ARTIFICIAL_CALIBRATION_ONLY_NOT_FLYNN_ACTIVITY" or
                content.get("calibration_id") != calibration_id or
                (sum(counts) > 0 and (content.get("torque_max_abs", 0) <= 0 or
                                      content.get("q_delta_max_abs", 0) <= 0))):
            raise RuntimeError("PicoClaw/Pinocchio did not return a verified calibrated physical state")
        return {**content, "pico_bridge_elapsed_ms": elapsed_ms,
                "upstream_call_elapsed_ms": result.get("elapsed_ms"), "provider_used": False}

    @staticmethod
    def _readline_timeout(process: subprocess.Popen[str], timeout_seconds: float) -> str:
        """Read one JSONL line with a bounded timeout without another thread."""
        import selectors

        assert process.stdout is not None
        selector = selectors.DefaultSelector()
        try:
            selector.register(process.stdout, selectors.EVENT_READ)
            if not selector.select(timeout_seconds):
                process.kill()
                raise TimeoutError("PicoClaw JSONL response exceeded its deadline")
            line = process.stdout.readline()
            if not line:
                raise RuntimeError(f"PicoClaw bridge exited with status {process.poll()}")
            return line
        finally:
            selector.close()

    def close(self) -> None:
        with self._lock:
            process, self._process = self._process, None
            if process is None:
                return
            if process.stdin is not None:
                process.stdin.close()
            try:
                process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=1.0)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()

    def __enter__(self) -> "PicoClawMCPPort":
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
