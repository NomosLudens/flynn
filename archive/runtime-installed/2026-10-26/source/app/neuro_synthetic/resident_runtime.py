"""Bounded, single-writer launcher for the approved Flynn V2 resident loop.

This launcher only composes the existing v783 LIF, world transducers,
PicoClaw bridge, Pinocchio worker, and paired checkpoint path. It never
creates calibration inputs or selects behavior. Its dedicated state root is
separate from every instrumental and historical database.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import logging
from logging.handlers import RotatingFileHandler
import os
import signal
import shutil
import socketserver
import stat
import threading
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .descending_readout import DescendingReadoutV2
from .neural_core import NeuralCore
from .picoclaw_port import PicoClawMCPPort
from .pipeline import NeuralActivityPipeline
from .proprioceptive_transducer import SyntheticProprioceptiveTransducer
from .signed_connectome import SignedConnectome
from .sqlite_store import FlynnStore
from .visual_light_transducer import VisualLightTransducer
from .world_runtime import FlynnWorldRuntime
from app.world.continuous_world import ContinuousWorldEngine
from app.brain.homeostasis_v2 import HomeostasisConfig, HomeostasisEngineV2, MODEL_EPOCH


EXECUTION_KIND = "RESIDENT"
INSTANCE_ID = "flynn-1gb"
CHUNK_MS = 20.0
# Bound this episode's owned data, then derive free-space reserve from the
# actual database, journal, log and checkpoint footprint on the mounted volume.
MAX_RESIDENT_DATA_BYTES = 1_073_741_824
MIN_CHECKPOINT_RESERVE_BYTES = 1_048_576
LOG_MAX_BYTES = 10 * 1024 * 1024
LOG_BACKUP_COUNT = 3
CHECKPOINT_KEEP = 2
STOP = False


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _logger(root: Path) -> logging.Logger:
    logger = logging.getLogger("flynn.resident")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    handler = RotatingFileHandler(
        root / "resident.log", maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT, encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    return logger


def _log(logger: logging.Logger, event: str, **values: Any) -> None:
    logger.info(json.dumps({"at_utc": _utc_now(), "event": event, **values},
                           sort_keys=True, separators=(",", ":"), allow_nan=False))


def _episode_identity(root: Path) -> tuple[str, dict[str, Any]]:
    marker = root / "episode.json"
    if marker.exists():
        metadata = json.loads(marker.read_text(encoding="utf-8"))
        episode = metadata.get("episode_id")
        if (metadata.get("schema") != "flynn.resident_episode.v1"
                or metadata.get("execution_kind") != EXECUTION_KIND
                or metadata.get("instance_id") != INSTANCE_ID
                or not isinstance(episode, str) or not episode.startswith("resident-v2:")):
            raise RuntimeError("resident episode marker is invalid; refusing to create a replacement identity")
        return episode, metadata
    if any((root / name).exists() for name in ("episode-v2.sqlite3", "world.sqlite3")):
        raise RuntimeError("resident state exists without its identity marker; refusing to create a new episode")
    episode = f"resident-v2:{INSTANCE_ID}:{uuid.uuid4().hex}"
    metadata = {
        "schema": "flynn.resident_episode.v1",
        "execution_kind": EXECUTION_KIND,
        "instance_id": INSTANCE_ID,
        "episode_id": episode,
        "created_at_utc": _utc_now(),
        "dataset_version": "fafb-v783",
    }
    temporary = root / ".episode.json.tmp"
    with temporary.open("x", encoding="utf-8") as output:
        json.dump(metadata, output, sort_keys=True, separators=(",", ":"))
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, marker)
    directory_fd = os.open(root, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    return episode, metadata


def _persist_episode_metadata(root: Path, metadata: dict[str, Any]) -> None:
    """Atomically persist lifecycle markers without advancing either simulation clock."""
    temporary = root / ".episode.json.tmp"
    with temporary.open("w", encoding="utf-8") as output:
        json.dump(metadata, output, sort_keys=True, separators=(",", ":"))
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, root / "episode.json")
    directory_fd = os.open(root, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def _resident_bytes(root: Path) -> int:
    return sum(
        path.stat().st_blocks * 512 if path.stat().st_blocks else path.stat().st_size
        for path in root.rglob("*") if path.is_file() and not path.is_symlink()
    )


def _required_disk_reserve_bytes(root: Path) -> int:
    """Reserve a second copy of current episode data plus one checkpoint write.

    The proportional reserve covers a rollback/journal-sized write and preserves
    a complete copy of the current causal state. It scales with the files on
    disk instead of consuming a fixed fraction of the VM's 10 GiB volume.
    """
    data_bytes = _resident_bytes(root)
    checkpoints = [
        path for path in (root / "checkpoints").glob("flynn-world-lif-*.npz*")
        if path.is_file() and not path.is_symlink()
    ]
    next_checkpoint_bytes = max(
        (path.stat().st_blocks * 512 if path.stat().st_blocks else path.stat().st_size
         for path in checkpoints), default=MIN_CHECKPOINT_RESERVE_BYTES,
    )
    transient_bytes = sum(
        (root / f"{name}{suffix}").stat().st_blocks * 512
        for name in ("episode-v2.sqlite3", "world.sqlite3")
        for suffix in ("-wal", "-shm", "-journal")
        if (root / f"{name}{suffix}").is_file()
    )
    return 2 * data_bytes + next_checkpoint_bytes + transient_bytes


def _prune_checkpoints(checkpoint_dir: Path, latest: Path, logger: logging.Logger) -> None:
    files = sorted(checkpoint_dir.glob("flynn-world-lif-*.npz"), key=lambda path: path.stat().st_mtime_ns)
    keep = {latest.resolve()}
    keep.update(path.resolve() for path in files[-CHECKPOINT_KEEP:])
    for path in files:
        if path.resolve() not in keep:
            _log(logger, "resident_checkpoint_retired", path=path.name,
                 sha256=_sha256_file(path), reason="bounded_latest_two_checkpoint_retention")
            path.unlink()


def _config_path(name: str) -> Path:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} must point to a verified private FlyWire/LETHE artifact")
    path = Path(value).expanduser().resolve()
    if not path.is_file() and not path.is_dir():
        raise FileNotFoundError(f"configured resident artifact is unavailable: {name}")
    return path


def _handle_signal(_signum: int, _frame: Any) -> None:
    global STOP
    STOP = True


def _start_world_operator_socket(runtime: FlynnWorldRuntime, root: Path, logger: logging.Logger):
    socket_path = root / "world-command.sock"
    if os.path.lexists(socket_path):
        if not stat.S_ISSOCK(socket_path.lstat().st_mode):
            raise RuntimeError("world operator socket path exists and is not a socket")
        socket_path.unlink()

    class Handler(socketserver.StreamRequestHandler):
        def handle(self) -> None:
            raw = self.rfile.readline(4097)
            try:
                if not raw or len(raw) > 4096 or not raw.endswith(b"\n"):
                    raise ValueError("one bounded newline-terminated JSON command is required")
                request = json.loads(raw.decode("utf-8"))
                if (not isinstance(request, dict)
                        or set(request) != {"cmd_type", "variable", "payload"}
                        or request.get("cmd_type") != "set_illumination"
                        or request.get("variable") != "illumination"):
                    raise ValueError("only the normalized illumination world stimulus is accepted")
                payload = request.get("payload")
                value = payload.get("value") if isinstance(payload, dict) and set(payload) == {"value"} else None
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0.0 <= float(value) <= 1.0:
                    raise ValueError("illumination value must be a number in [0, 1]")
                receipt = self.server.runtime.world.enqueue_command(
                    "set_illumination", "illumination", {"value": float(value)},
                )
                generation_id = self.server.runtime.pipeline.causal_generation_id
                _log(logger, "world_operator_command_queued",
                     episode_id=self.server.runtime.pipeline.aggregator.episode_id,
                     generation_id=generation_id, origin="local_unix_operator_socket",
                     command_id=receipt["command_id"], cmd_type="set_illumination",
                     variable="illumination", value=float(value),
                     received_at_utc=receipt["received_at_utc"])
                response = {"status": "QUEUED", "receipt": receipt}
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RuntimeError) as error:
                response = {"status": "REJECTED", "error": str(error)}
            self.wfile.write(json.dumps(response, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n")

    class Server(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
        daemon_threads = True
        block_on_close = False

    server = Server(str(socket_path), Handler)
    server.runtime = runtime
    os.chmod(socket_path, 0o600)
    thread = threading.Thread(target=server.serve_forever, name="flynn-world-operator-socket", daemon=True)
    thread.start()
    _log(logger, "world_operator_socket_ready", socket_path=socket_path.name,
         allowed_command="set_illumination", value_range=[0.0, 1.0])
    return server, thread, socket_path


def run() -> int:
    root = Path(os.environ.get("FLYNN_RESIDENT_ROOT", "/var/lib/flynn-v2/resident")).expanduser().resolve()
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(root, 0o700)
    lock_path = root / "resident.lock"
    lock = lock_path.open("a+")
    try:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        raise RuntimeError("another resident writer already owns this episode") from exc

    logger = _logger(root)
    episode_id, episode_metadata = _episode_identity(root)
    previous_start = episode_metadata.get("last_start_at_utc")
    previous_stop = episode_metadata.get("last_stop_at_utc")
    project_root = Path(os.environ.get("FLYNN_PROJECT_ROOT", "/home/tonyus-dev/flynn-v2-vm-validation-20261019/code")).resolve()
    # Preserve the venv entrypoint symlink; resolving it bypasses site-packages.
    lif_python = Path(os.path.abspath(os.environ.get("FLYNN_LIF_PYTHON", "/home/tonyus-dev/flynn-v2-vm-validation-20261019/python-neural-env/bin/python")))
    pin_python = Path(os.environ.get("FLYNN_PINOCCHIO_PYTHON", "/home/tonyus-dev/flynn-v2-vm-validation-20261019/python-pinocchio-env/bin/python")).absolute()
    bridge = Path(os.environ.get("FLYNN_PICOCLAW_BRIDGE", "/home/tonyus-dev/flynn-v2-vm-validation-20261019/bin/picoclaw-bridge")).resolve()
    if not lif_python.is_file() or not pin_python.is_file() or not bridge.is_file():
        raise RuntimeError("verified isolated Python/Go runtimes are missing; resident start refused")

    csr_dir = _config_path("FLYNN_V2_CSR_DIR")
    roots_path = _config_path("FLYNN_V2_CANONICAL_ROOTS")
    motor_manifest = _config_path("FLYNN_V2_DN_MANIFEST")
    proprio_manifest = _config_path("FLYNN_V2_PROPRIO_MANIFEST")
    visual_manifest = _config_path("FLYNN_V2_VISUAL_MANIFEST")
    db_path = root / "episode-v2.sqlite3"
    world_db_path = root / "world.sqlite3"
    checkpoint_dir = root / "checkpoints"
    checkpoint_dir.mkdir(mode=0o700, exist_ok=True)
    if _resident_bytes(root) > MAX_RESIDENT_DATA_BYTES:
        raise RuntimeError("resident state already exceeds the safe 1 GiB data cap")

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)
    connectome_started = time.perf_counter()
    connectome = SignedConnectome.load(csr_dir=csr_dir, canonical_roots_path=roots_path)
    if len(connectome.root_ids) != 139255 or connectome.manifest_sha256 != "499c77e789f2abeac9d21739ae106054381ad7758ab68caee9e0834dc0580045":
        raise RuntimeError("loaded CSR differs from the approved complete v783 artifact")
    store = FlynnStore(db_path)
    existing_rows = int(store.connection.execute("SELECT COUNT(*) FROM events").fetchone()[0])
    if existing_rows and store.connection.execute(
        "SELECT value FROM metadata WHERE key='execution_kind'"
    ).fetchone() != (EXECUTION_KIND,):
        raise RuntimeError("resident SQLite identity is not explicitly RESIDENT")
    mapping_hash = store.register_mapping(
        "fafb-v783", (int(value) for value in connectome.root_ids),
        connectome.manifest["canonical_population"]["root_ids_sha256"],
    )
    if mapping_hash != connectome.mapping_sha256:
        raise RuntimeError("resident SQLite canonical mapping differs from CSR")
    # Desired mode defaults to sampled. The pipeline remains in its persisted
    # current mode (legacy episodes therefore start dense) until one new
    # paired checkpoint is confirmed, then transitions at that boundary.
    requested_persistence_mode = os.environ.get("FLYNN_PERSISTENCE_MODE", "sampled").strip().lower()
    if requested_persistence_mode not in {"dense", "sampled"}:
        raise RuntimeError("FLYNN_PERSISTENCE_MODE must be 'dense' or 'sampled'")
    pipeline = NeuralActivityPipeline(
        store=store, episode_id=episode_id, dataset_version="fafb-v783",
        manifest_sha256=connectome.manifest_sha256,
        mapping_sha256=connectome.mapping_sha256,
        root_ids=(int(value) for value in connectome.root_ids),
        restore_latest_cursor=False,
        sampling_window_ms=1000.0,
        requested_persistence_mode=requested_persistence_mode,
    )
    active_generation = store.active_causal_generation()
    if active_generation is not None and active_generation.get("episode_id") != episode_id:
        raise RuntimeError("resident runtime causal generation belongs to another episode")
    initial_generation_ready = False
    if active_generation is None:
        active_checkpoint = store.active_checkpoint()
        if active_checkpoint is not None or existing_rows:
            raise RuntimeError("resident database has prior state but no active causal generation")
        generation_id = uuid.uuid4().hex
        generation_time = _utc_now()
        store.activate_causal_generation(
            episode_id=episode_id, generation_id=generation_id,
            parent_generation_id=None, checkpoint_state_id=None,
            checkpoint_sha256=None, checkpoint_tick=0,
            created_at_utc=generation_time,
            event_id=f"causal-generation-start:{episode_id}:{generation_id}",
            event_payload={
                "episode_id": episode_id,
                "previous_generation_id": None,
                "new_generation_id": generation_id,
                "checkpoint_state_id": None,
                "checkpoint_sha256": None,
                "last_confirmed_tick": 0,
                "unreconciled_tail": None,
                "created_at_utc": generation_time,
                "transition": "INITIAL_RESIDENT_GENERATION",
            },
        )
        pipeline.activate_causal_generation(generation_id)
        active_generation = {"episode_id": episode_id, "generation_id": generation_id}
        initial_generation_ready = True
    elif active_generation.get("checkpoint_state_id") is None:
        component_state_count = int(store.connection.execute(
            "SELECT COUNT(*) FROM component_states"
        ).fetchone()[0])
        if (active_generation.get("checkpoint_tick") != 0
                or active_generation.get("parent_generation_id") is not None
                or existing_rows != 1 or component_state_count):
            raise RuntimeError("uncheckpointed causal generation contains state requiring reconciliation")
        active_checkpoint = None
        initial_generation_ready = True
    else:
        active_checkpoint = store.active_checkpoint()
    saved_homeostasis = (active_checkpoint or {}).get("state", {}).get("homeostasis_state")
    cpu_budget_seconds = float(os.environ.get(
        "FLYNN_HOMEOSTASIS_CPU_SECONDS_PER_FULL_RESERVE", "3600",
    ))
    if isinstance(saved_homeostasis, dict):
        if saved_homeostasis.get("model_epoch") != MODEL_EPOCH:
            raise RuntimeError("active checkpoint energy model differs; preserve it and start a new resident episode")
        initial_reserve = saved_homeostasis.get("energy_reserve")
        initial_neural_time_ms = saved_homeostasis.get("neural_time_ms")
        homeostasis_seeded_from_operator = False
    else:
        if active_checkpoint is not None:
            raise RuntimeError(
                "legacy checkpoint has no compatible CPU-budget state; preserve it and start a new resident episode"
            )
        configured_reserve = os.environ.get("FLYNN_HOMEOSTASIS_INITIAL_RESERVE")
        if configured_reserve is None:
            raise RuntimeError(
                "new resident episode requires operator-defined FLYNN_HOMEOSTASIS_INITIAL_RESERVE"
            )
        initial_reserve = float(configured_reserve)
        initial_neural_time_ms = 0.0
        homeostasis_seeded_from_operator = True
    homeostasis = HomeostasisEngineV2(
        initial_energy_reserve=initial_reserve,
        initial_neural_time_ms=initial_neural_time_ms,
        config=HomeostasisConfig(cpu_seconds_per_full_reserve=cpu_budget_seconds),
    )
    core = NeuralCore(connectome=connectome, pipeline=pipeline, episode_id=episode_id)
    readout = DescendingReadoutV2(motor_manifest, expected_connectome_sha256=connectome.matrix_sha256)
    visual = VisualLightTransducer(visual_manifest, expected_connectome_sha256=connectome.matrix_sha256)
    proprio = SyntheticProprioceptiveTransducer(
        proprio_manifest, expected_connectome_sha256=connectome.matrix_sha256,
    )
    world = ContinuousWorldEngine(db_path=world_db_path)
    port = PicoClawMCPPort(
        executable=bridge, database_path=db_path, project_root=project_root,
        python_executable=str(lif_python), pinocchio_python=pin_python,
        population_manifest=motor_manifest, timeout_seconds=60,
        resident_mode=True, causal_generation_id=active_generation["generation_id"],
    )
    runtime = FlynnWorldRuntime(
        world=world, pipeline=pipeline, neural_core=core, picoclaw_port=port,
        visual_light_transducer=visual, proprioceptive_transducer=proprio,
        descending_readout=readout, execution_kind=EXECUTION_KIND,
        homeostasis=homeostasis,
        homeostasis_seeded_from_operator=homeostasis_seeded_from_operator,
    )
    world_command_server = None
    world_command_thread = None
    world_command_socket = None
    _log(logger, "resident_starting", episode_id=episode_id, instance_id=INSTANCE_ID,
         execution_kind=EXECUTION_KIND, execution_user=os.getuid(),
         homeostasis_model_epoch=homeostasis.epoch,
         homeostasis_cpu_seconds_per_full_reserve=homeostasis.config.cpu_seconds_per_full_reserve,
         connectome_load_ms=round((time.perf_counter() - connectome_started) * 1000, 3),
         connectome_sha256=connectome.matrix_sha256,
         mapping_sha256=connectome.mapping_sha256,
         visual_manifest_sha256=visual.manifest_sha256,
         motor_manifest_sha256=readout.manifest_sha256,
         proprio_manifest_sha256=proprio.manifest_sha256,
         starting_at_utc=_utc_now())
    try:
        port.start()
        restored = runtime.restore_integrated_checkpoint()
        if restored is None:
            if existing_rows and not initial_generation_ready:
                raise RuntimeError("resident database has prior events but no valid paired checkpoint")
            cycle = runtime.advance_synchronized(CHUNK_MS)
            if cycle.get("execution_kind") != EXECUTION_KIND:
                raise RuntimeError("initial resident cycle was not persisted with RESIDENT identity")
            checkpoint = runtime.save_integrated_checkpoint(checkpoint_dir)
            _prune_checkpoints(checkpoint_dir, Path(checkpoint["checkpoint_file"]), logger)
            mode_change = pipeline.transition_persistence_mode(requested_persistence_mode, checkpoint)
            _log(logger, "resident_first_checkpoint", episode_id=episode_id,
                 tick=checkpoint["neural_tick"], neural_time_ms=checkpoint["neural_time_ms"],
                 world_time_ms=checkpoint["world_time_ms"], sha256=checkpoint["checkpoint_sha256"],
                 bytes=checkpoint["checkpoint_bytes"],
                 persistence_mode=pipeline.persistence_mode,
                 persistence_mode_changed=mode_change is not None)
        else:
            if restored.get("execution_kind") != EXECUTION_KIND:
                raise RuntimeError("restored checkpoint is not explicitly RESIDENT")
            if previous_start:
                downtime_started = previous_stop or previous_start
                downtime_kind = "AFTER_CLEAN_STOP" if previous_stop else "AFTER_UNCLEAN_INTERRUPTION"
                store.record_event(
                    event_id=f"resident-interruption:{episode_id}:{uuid.uuid4().hex}",
                    event_type="RESIDENT_EXTERNAL_DOWNTIME",
                    source="resident_supervisor",
                    occurred_at_utc=_utc_now(),
                    neural_time_ms=core.engine.neural_time_ms,
                    payload={"episode_id": episode_id, "gap_started_at_utc": downtime_started,
                             "previous_run_started_at_utc": previous_start,
                             "previous_clean_stop_at_utc": previous_stop,
                             "gap_classification": downtime_kind,
                             "resumed_at_utc": _utc_now(), "clock_policy": "NO_SYNTHETIC_TICK_ADVANCE"},
                    provenance_sha256=connectome.matrix_sha256,
                )
            _log(logger, "resident_checkpoint_restored", episode_id=episode_id,
                 tick=restored["neural_tick"], neural_time_ms=restored["neural_time_ms"],
                 world_time_ms=restored["world_time_ms"], sha256=restored["checkpoint_sha256"])

        if homeostasis_seeded_from_operator:
            boundary = (active_checkpoint or {}).get("state", {})
            seed_tick = int(boundary.get("neural_tick", 0))
            seed_checkpoint_sha = boundary.get("checkpoint_sha256")
            seed_at_utc = boundary.get("saved_at_utc") or episode_metadata["created_at_utc"]
            generation_id = pipeline.causal_generation_id
            seed_id = (
                f"homeostasis-v2-seed:{episode_id}:{generation_id}:"
                f"{seed_checkpoint_sha or 'tick-0'}"
            )
            store.record_event(
                event_id=seed_id,
                event_type="HOMEOSTASIS_V2_SEEDED_AT_CONFIRMED_BOUNDARY",
                source="explicit_operator_configuration",
                occurred_at_utc=seed_at_utc,
                neural_time_ms=homeostasis.neural_time_ms,
                provenance_sha256=homeostasis.config_hash,
                payload={
                    "episode_id": episode_id,
                    "causal_generation_id": generation_id,
                    "checkpoint_sha256": seed_checkpoint_sha,
                    "checkpoint_tick": seed_tick,
                    "energy_reserve": homeostasis.energy_reserve,
                    "model_epoch": homeostasis.epoch,
                    "config_hash": homeostasis.config_hash,
                    "initialization_source": "OPERATOR_CONFIGURED_AT_CONFIRMED_BOUNDARY",
                },
            )

        episode_metadata["last_start_at_utc"] = _utc_now()
        episode_metadata["last_stop_at_utc"] = None
        episode_metadata["run_sequence"] = int(episode_metadata.get("run_sequence", 0)) + 1
        _persist_episode_metadata(root, episode_metadata)

        world_command_server, world_command_thread, world_command_socket = _start_world_operator_socket(
            runtime, root, logger,
        )
        while not STOP:
            data_bytes = _resident_bytes(root)
            disk = shutil.disk_usage(root)
            required_disk_reserve_bytes = _required_disk_reserve_bytes(root)
            if data_bytes >= MAX_RESIDENT_DATA_BYTES or disk.free < required_disk_reserve_bytes:
                store.record_event(
                    event_id=f"resident-stop-storage:{episode_id}:{uuid.uuid4().hex}",
                    event_type="RESIDENT_SAFE_STOP_STORAGE_LIMIT",
                    source="resident_supervisor", occurred_at_utc=_utc_now(),
                    neural_time_ms=core.engine.neural_time_ms,
                    payload={"episode_id": episode_id, "resident_bytes": data_bytes,
                             "disk_free_bytes": disk.free,
                             "required_disk_reserve_bytes": required_disk_reserve_bytes,
                             "configured_resident_data_cap_bytes": MAX_RESIDENT_DATA_BYTES},
                    provenance_sha256=connectome.matrix_sha256,
                )
                _log(logger, "resident_safe_stop_storage_limit", resident_bytes=data_bytes,
                     disk_free_bytes=disk.free, required_disk_reserve_bytes=required_disk_reserve_bytes,
                     neural_time_ms=core.engine.neural_time_ms)
                episode_metadata["last_stop_at_utc"] = _utc_now()
                episode_metadata["last_stop_reason"] = "SAFE_STORAGE_LIMIT"
                episode_metadata["last_clean_tick"] = int(core.engine.tick)
                _persist_episode_metadata(root, episode_metadata)
                return 0
            cycle = runtime.advance_synchronized(CHUNK_MS)
            if cycle.get("execution_kind") != EXECUTION_KIND:
                raise RuntimeError("resident loop received an instrumental cycle")
            checkpoint = runtime.save_integrated_checkpoint(checkpoint_dir)
            _prune_checkpoints(checkpoint_dir, Path(checkpoint["checkpoint_file"]), logger)
            mode_change = pipeline.transition_persistence_mode(requested_persistence_mode, checkpoint)
            if mode_change is not None:
                _log(logger, "resident_persistence_mode_changed", episode_id=episode_id,
                     generation_id=pipeline.causal_generation_id,
                     from_mode=mode_change["previous_mode"], to_mode=mode_change["mode"],
                     after_tick=mode_change["effective_after_tick"],
                     checkpoint_sha256=mode_change["effective_after_checkpoint_sha256"])
            _log(logger, "resident_cycle_committed", episode_id=episode_id,
                 cycle_sequence=cycle["cycle_sequence"], tick=cycle["end_tick"],
                 neural_time_ms=cycle["end_neural_time_ms"], world_time_ms=cycle["end_world_time_ms"],
                 total_spikes=sum(int(item.get("spikes", 0)) for item in cycle["frames"]),
                 dn_spikes=sum(int(item.get("dn_spikes", 0)) for item in cycle["frames"]),
                 picoclaw_acks=cycle["picoclaw_frame_ack_count"],
                 proprioception=cycle["proprioceptive_input_status"],
                 elapsed_real_ms=cycle["elapsed_real_ms"], cpu_ms=cycle["cpu_ms"],
                 checkpoint_bytes=checkpoint["checkpoint_bytes"],
                 persistence_mode=pipeline.persistence_mode,
                 resident_bytes=_resident_bytes(root), disk_free_bytes=shutil.disk_usage(root).free)

        episode_metadata["last_stop_at_utc"] = _utc_now()
        episode_metadata["last_clean_tick"] = int(core.engine.tick)
        episode_metadata["last_stop_reason"] = "SIGTERM_OR_OPERATOR_STOP"
        _persist_episode_metadata(root, episode_metadata)
        _log(logger, "resident_clean_shutdown", episode_id=episode_id,
             tick=core.engine.tick, neural_time_ms=core.engine.neural_time_ms)
        return 0
    finally:
        if world_command_server is not None:
            world_command_server.shutdown()
            world_command_server.server_close()
            if world_command_thread is not None:
                world_command_thread.join(timeout=2.0)
            if world_command_socket is not None:
                world_command_socket.unlink(missing_ok=True)
        port.close()
        store.close()
        lock.close()


def main() -> None:
    try:
        raise SystemExit(run())
    except SystemExit:
        raise
    except Exception as error:
        print(f"FLYNN_RESIDENT_FATAL={type(error).__name__}: {error}", file=sys.stderr, flush=True)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
