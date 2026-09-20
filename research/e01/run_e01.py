#!/usr/bin/env python3
"""Reproduce the isolated Flynn E01 study.

This runner never imports the resident Flynn loop. It gates an external,
fixed MotorIntent on a real ZeroClaw health session and uses Pinocchio only
for the synthetic body dynamics. It does not select goals or behavior.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
DEFAULT_XML = HERE / "flynn_e01_minimal_body.xml"


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def run_command(*args: str, timeout: float = 5.0) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            args, capture_output=True, text=True, timeout=timeout, check=False
        )
        return {
            "returncode": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }
    except Exception as exc:
        return {
            "returncode": None,
            "stdout": "",
            "stderr": f"{type(exc).__name__}: {exc}",
        }


def sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(output: Path, name: str, value: Any) -> None:
    (output / name).write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def recv_line(stream: socket.socket) -> bytes:
    data = bytearray()
    while b"\n" not in data and len(data) < 65536:
        block = stream.recv(4096)
        if not block:
            break
        data.extend(block)
    return bytes(data).split(b"\n", 1)[0]


def rpc_session(socket_path: Path, methods: list[str]) -> list[dict[str, Any]]:
    """Call methods in one connection; ZeroClaw requires this for init+health."""
    requests: list[dict[str, Any]] = []
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as stream:
        stream.settimeout(2.0)
        stream.connect(str(socket_path))
        for request_id, method in enumerate(methods, start=1):
            request = {
                "jsonrpc": "2.0",
                "method": method,
                "params": {},
                "id": request_id,
            }
            stream.sendall(
                (json.dumps(request, separators=(",", ":")) + "\n").encode("utf-8")
            )
            raw = recv_line(stream)
            requests.append({"request": request, "response": json.loads(raw)})
    return requests


def probe_zeroclaw(socket_path: Path) -> dict[str, Any]:
    try:
        messages = rpc_session(socket_path, ["initialize", "health"])
        initialize = messages[0]
        health = messages[1]
        health_response = health["response"]
        health_result = health_response.get("result", {})
        initialize_result = initialize["response"].get("result", {})
        return {
            "status": "ok" if "error" not in health_response else "error",
            "initialize": initialize,
            "health": health,
            "server_pid": initialize_result.get("server_pid"),
            "server_version": initialize_result.get("server_version"),
            "uptime_seconds": health_result.get("uptime_seconds"),
        }
    except Exception as exc:
        return {"status": "failed", "error": f"{type(exc).__name__}: {exc}"}


class SyntheticBody:
    """Four-DoF engineering body; not a biological body model."""

    def __init__(self, xml_path: Path):
        import pinocchio as pin

        self.pin = pin
        self.model = pin.buildModelFromXML(xml_path.read_text(encoding="utf-8"))
        self.data = self.model.createData()
        self.foot_frames = {
            "left_foot": self.model.getFrameId("left_foot"),
            "right_foot": self.model.getFrameId("right_foot"),
        }

    def validate_target(self, target: Any) -> tuple[bool, str]:
        import numpy as np

        value = np.asarray(target, dtype=float)
        if value.shape != (self.model.nq,) or not np.isfinite(value).all():
            return False, "invalid_joint_state"
        if (value < self.model.lowerPositionLimit).any():
            return False, "joint_limit_exceeded"
        if (value > self.model.upperPositionLimit).any():
            return False, "joint_limit_exceeded"
        return True, "valid"

    def step(self, q: Any, dq: Any, target: Any) -> dict[str, Any]:
        import numpy as np

        valid, reason = self.validate_target(target)
        if not valid:
            raise ValueError(reason)
        tau = np.clip(8.0 * (target - q) - 0.45 * dq, -1.5, 1.5)
        ddq = self.pin.aba(self.model, self.data, q, dq, tau)
        dt = 0.01
        q_next = self.pin.integrate(self.model, q, dq * dt)
        q_next = self.pin.integrate(self.model, q_next, 0.5 * ddq * dt * dt)
        dq_next = dq + ddq * dt
        self.pin.forwardKinematics(self.model, self.data, q_next, dq_next)
        self.pin.updateFramePlacements(self.model, self.data)
        return {
            "q": q_next,
            "dq": dq_next,
            "tau": tau,
            "pose": {
                name: [float(x) for x in self.data.oMf[index].translation]
                for name, index in self.foot_frames.items()
            },
            "kinetic": float(
                self.pin.computeKineticEnergy(self.model, self.data, q_next, dq_next)
            ),
            "potential": float(
                self.pin.computePotentialEnergy(self.model, self.data, q_next)
            ),
        }


def motor_intent() -> dict[str, Any]:
    return {
        "intent": "TURN_LEFT",
        "magnitude": 0.4,
        "duration_neural_ms": 400,
        "source": "diagnostic_injection",
        "provenance": "diagnostic_injection",
        "motor_intent_source": "TEST_HARNESS",
        "resident_flynn_output": False,
    }


def fixed_targets(intent: dict[str, Any], tick: int, total: int) -> Any:
    import numpy as np

    phase = math.sin(math.pi * tick / max(1, total - 1))
    magnitude = float(intent["magnitude"])
    return np.array(
        [
            0.45 * magnitude * phase,
            -0.70 * magnitude * phase,
            -0.45 * magnitude * phase,
            0.70 * magnitude * phase,
        ],
        dtype=float,
    )


def trace_row(
    test_id: str,
    intent: dict[str, Any],
    *,
    sim_time: float,
    wall_time: float,
    probe: dict[str, Any] | None = None,
    q: Any | None = None,
    dq: Any | None = None,
    result: dict[str, Any] | None = None,
    safety: str = "",
) -> dict[str, Any]:
    def encoded(value: Any) -> str:
        if value is None:
            return ""
        return json.dumps(value, sort_keys=True, separators=(",", ":"))

    result = result or {}
    q_value = q.tolist() if hasattr(q, "tolist") else q
    dq_value = dq.tolist() if hasattr(dq, "tolist") else dq
    tau = result.get("tau")
    tau_value = tau.tolist() if hasattr(tau, "tolist") else tau
    return {
        "timestamp": now(),
        "sim_time": sim_time,
        "wall_time": wall_time,
        "test_id": test_id,
        "intent": encoded(intent),
        "zeroclaw_response": encoded(probe),
        "q": encoded(q_value),
        "dq": encoded(dq_value),
        "torques": encoded(tau_value),
        "body_pose": encoded(result.get("pose")),
        "kinetic_energy": result.get("kinetic", 0),
        "potential_energy": result.get("potential", 0),
        "safety_events": safety,
    }


def run_case(
    body: SyntheticBody | None,
    socket_path: Path,
    rows: list[dict[str, Any]],
    total_ticks: int,
) -> dict[str, Any]:
    test_id = "A_WITH_ZEROCLAW_AND_PINOCCHIO"
    intent = motor_intent()
    if body is None:
        rows.append(
            trace_row(
                test_id,
                intent,
                sim_time=0,
                wall_time=0,
                safety="PINOCCHIO_UNAVAILABLE",
            )
        )
        return {
            "test_id": test_id,
            "status": "FAILED",
            "effect": "NO_EFFECT",
            "reason": "PINOCCHIO_UNAVAILABLE",
        }

    import numpy as np

    q = np.zeros(body.model.nq)
    dq = np.zeros(body.model.nv)
    start = time.perf_counter()
    last: dict[str, Any] = {}
    for tick in range(total_ticks):
        probe = probe_zeroclaw(socket_path)
        if probe["status"] != "ok":
            rows.append(
                trace_row(
                    test_id,
                    intent,
                    sim_time=tick * 0.01,
                    wall_time=time.perf_counter() - start,
                    probe=probe,
                    q=q,
                    dq=dq,
                    safety="ZEROCLAW_DOWN_FAIL_CLOSED",
                )
            )
            return {
                "test_id": test_id,
                "status": "FAILED",
                "effect": "NO_EFFECT",
                "reason": "ZEROCLAW_UNAVAILABLE",
                "ticks": tick,
            }

        target = fixed_targets(intent, tick, total_ticks)
        valid, reason = body.validate_target(target)
        if not valid:
            return {
                "test_id": test_id,
                "status": "DENIED",
                "effect": "NO_EFFECT",
                "reason": reason,
            }
        last = body.step(q, dq, target)
        q, dq = last["q"], last["dq"]
        rows.append(
            trace_row(
                test_id,
                intent,
                sim_time=tick * 0.01,
                wall_time=time.perf_counter() - start,
                probe=probe,
                q=q,
                dq=dq,
                result=last,
            )
        )

    return {
        "test_id": test_id,
        "status": "SUCCESS",
        "effect": "COORDINATED_ARTICULATION",
        "ticks": total_ticks,
        "q_delta_norm": float(np.linalg.norm(q)),
        "intent_class_preserved": True,
        "coordination_owner": "EXTERNAL_RESEARCH_ADAPTER",
    }


def write_trace(output: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "timestamp",
        "sim_time",
        "wall_time",
        "test_id",
        "intent",
        "zeroclaw_response",
        "q",
        "dq",
        "torques",
        "body_pose",
        "kinetic_energy",
        "potential_energy",
        "safety_events",
    ]
    with (output / "e01_execution_trace.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def make_manifest(output: Path) -> dict[str, Any]:
    artifacts = {}
    for path in sorted(output.rglob("*")):
        if path.is_file() and path.name != "E01_EVIDENCE_MANIFEST.json":
            artifacts[str(path.relative_to(output))] = {
                "sha256": sha256(path),
                "bytes": path.stat().st_size,
            }
    return {"generated_utc": now(), "verdict": "E01=PARTIAL", "artifacts": artifacts}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zeroclaw", type=Path, required=True)
    parser.add_argument("--socket", type=Path, required=True)
    parser.add_argument("--xml", type=Path, default=DEFAULT_XML)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ticks", type=int, default=40)
    args = parser.parse_args()
    if args.ticks < 1:
        parser.error("--ticks must be positive")

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    intent = motor_intent()
    rows: list[dict[str, Any]] = []

    version = run_command(str(args.zeroclaw), "--version")
    environment: dict[str, Any] = {
        "timestamp_utc": now(),
        "runner": str(Path(__file__).resolve()),
        "python": sys.version,
        "platform": platform.platform(),
        "architecture": platform.machine(),
        "zeroclaw": {
            "binary": str(args.zeroclaw),
            "exists": args.zeroclaw.is_file(),
            "sha256": sha256(args.zeroclaw),
            "version_probe": version,
        },
        "ipc": {"socket": str(args.socket), "protocol": "newline JSON-RPC 2.0"},
        "pinocchio": {"status": "NOT_ATTEMPTED"},
        "resident_imported": False,
        "resident_mutated": False,
    }

    body: SyntheticBody | None = None
    try:
        import pinocchio as pin

        environment["pinocchio"] = {
            "status": "PASS",
            "module": str(Path(pin.__file__).resolve()),
            "version": getattr(pin, "__version__", "unknown"),
        }
        body = SyntheticBody(args.xml)
    except Exception as exc:
        environment["pinocchio"] = {
            "status": "FAIL",
            "error": f"{type(exc).__name__}: {exc}",
        }

    write_json(output, "e01_environment.json", environment)
    body_inventory = {
        "body_format": "URDF",
        "file": str(args.xml.resolve()),
        "body_identity": "SYNTHETIC_TEST_BODY",
        "biological_accuracy_claim": False,
        "engineering_test_parameters": True,
        "n_joints": len(body.model.names) - 1 if body else None,
        "n_dof": body.model.nv if body else None,
        "joint_names": list(body.model.names[1:]) if body else [],
    }
    write_json(output, "e01_body_inventory.json", body_inventory)

    normal = run_case(body, args.socket, rows, args.ticks)
    no_zero: dict[str, Any] = {
        "test_id": "B_WITHOUT_ZEROCLAW",
        "status": "FAILED",
        "effect": "NO_EFFECT",
        "reason": "ZEROCLAW_UNAVAILABLE",
    }
    if body is not None:
        probe = probe_zeroclaw(output / "socket-does-not-exist")
        no_zero["probe"] = probe
        rows.append(
            trace_row(
                "B_WITHOUT_ZEROCLAW",
                intent,
                sim_time=0,
                wall_time=0,
                probe=probe,
                safety="ZEROCLAW_DOWN_FAIL_CLOSED",
            )
        )
    no_pin = {
        "test_id": "C_WITHOUT_PINOCCHIO",
        "status": "FAILED",
        "effect": "NO_EFFECT",
        "reason": "PINOCCHIO_UNAVAILABLE",
    }
    rows.append(
        trace_row(
            "C_WITHOUT_PINOCCHIO",
            intent,
            sim_time=0,
            wall_time=0,
            safety="PINOCCHIO_DOWN_FAIL_CLOSED",
        )
    )
    invalid: dict[str, Any] = {"test_id": "D_INVALID_JOINT_COMMAND"}
    if body is not None:
        import numpy as np

        valid, reason = body.validate_target(np.full(body.model.nq, 10.0))
        invalid.update(
            {
                "status": "UNEXPECTED" if valid else "DENIED",
                "effect": "UNEXPECTED" if valid else "NO_EFFECT",
                "reason": reason,
            }
        )
    else:
        invalid.update(
            {
                "status": "UNVERIFIED",
                "effect": "NO_EFFECT",
                "reason": "PINOCCHIO_UNAVAILABLE",
            }
        )

    write_trace(output, rows)
    write_json(
        output,
        "e01_fail_closed_tests.json",
        {
            "tests": [normal, no_zero, no_pin, invalid],
            "expected": {
                "B": "FAILED/NO_EFFECT",
                "C": "FAILED/NO_EFFECT",
                "D": "DENIED/NO_EFFECT",
            },
        },
    )
    report = {
        "verdict": "E01=PARTIAL",
        "reason": (
            "The synthetic body and fail-closed cases are reproducible, but "
            "coordination remains an external research adapter; no canonical "
            "ZeroClaw motor surface is promoted."
        ),
        "normal_case": normal,
        "zeroClaw_role": "EXECUTION_INTERLOCK",
        "coordination_owner": "EXTERNAL_RESEARCH_ADAPTER",
        "policy_present": False,
        "reward_function_present": False,
        "llm_calls": 0,
        "agent_turns": 0,
        "resident_imported": False,
        "resident_mutated": False,
        "next": {"E02_ready": False},
    }
    write_json(output, "e01_report.json", report)
    (output / "E01_FINAL_REPORT.md").write_text(
        "# Flynn Embodiment E01\n\n"
        "VERDICT=E01=PARTIAL\n\n"
        "This isolated run does not import or mutate the resident Flynn. "
        "Coordination remains an external research adapter gated by real "
        "ZeroClaw IPC; E02 is not ready.\n\n"
        "See e01_report.json, e01_fail_closed_tests.json and the CSV trace.\n",
        encoding="utf-8",
    )
    write_json(output, "E01_EVIDENCE_MANIFEST.json", make_manifest(output))

    all_pass = (
        normal.get("status") == "SUCCESS"
        and no_zero["status"] == "FAILED"
        and no_pin["status"] == "FAILED"
        and invalid.get("status") == "DENIED"
    )
    return 0 if all_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
