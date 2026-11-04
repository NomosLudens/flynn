"""Shared disk budget and serialized write guard for Flynn persistence."""

from __future__ import annotations

import fcntl
import os
import shutil
import stat
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


MAX_RESIDENT_DATA_BYTES = 1_073_741_824
DISK_WARNING_FREE_BYTES = 8 * 1024**3
DISK_STOP_FREE_BYTES = 6 * 1024**3
INITIAL_CHECKPOINT_RESERVE_BYTES = 1_073_741_824
LOG_MAX_BYTES = 10 * 1024 * 1024
LOG_BACKUP_COUNT = 3
LOCK_PATH = Path("/tmp/.flynn-storage-write-guard.lock")

_PROCESS_LOCK = threading.RLock()
_PROCESS_STATE = threading.local()


class StorageBudgetError(OSError):
    """A persistent write was refused to preserve the configured disk margin."""

    def __init__(self, budget: dict[str, int | bool], operation: str):
        self.budget = budget
        self.operation = operation
        super().__init__(
            f"FLYNN storage guard refused {operation}: free={budget['free_bytes']} "
            f"required={budget['required_free_bytes']}"
        )


def _existing_path(path: Path) -> Path:
    candidate = path
    while not candidate.exists():
        parent = candidate.parent
        if parent == candidate:
            raise FileNotFoundError(f"no existing path for disk measurement: {path}")
        candidate = parent
    return candidate


def resident_bytes(root: Path) -> int:
    return sum(
        path.stat().st_blocks * 512 if path.stat().st_blocks else path.stat().st_size
        for path in root.rglob("*") if path.is_file() and not path.is_symlink()
    )


def required_disk_reserve_bytes(root: Path) -> int:
    """Keep rollback, remaining episode capacity, checkpoint and log reserves."""
    data_bytes = resident_bytes(root)
    checkpoints = [
        path for path in (root / "checkpoints").glob("*.npz*")
        if path.is_file() and not path.is_symlink()
    ]
    next_checkpoint_bytes = max([
        INITIAL_CHECKPOINT_RESERVE_BYTES,
        *(path.stat().st_blocks * 512 if path.stat().st_blocks else path.stat().st_size
          for path in checkpoints),
    ])
    transient_bytes = sum(
        (root / f"{name}{suffix}").stat().st_blocks * 512
        for name in ("episode-v2.sqlite3", "world.sqlite3", "runtime.sqlite3")
        for suffix in ("-wal", "-shm", "-journal")
        if (root / f"{name}{suffix}").is_file()
    )
    remaining_episode_cap = max(0, MAX_RESIDENT_DATA_BYTES - data_bytes)
    log_rotation_reserve = LOG_MAX_BYTES * (LOG_BACKUP_COUNT + 1)
    return (2 * data_bytes + remaining_episode_cap + next_checkpoint_bytes
            + transient_bytes + log_rotation_reserve)


def disk_budget(
    root: Path,
    *,
    warning_free_bytes: int = DISK_WARNING_FREE_BYTES,
    stop_free_bytes: int = DISK_STOP_FREE_BYTES,
    operation_reserve_bytes: int = 0,
) -> dict[str, int | bool]:
    """Measure the target filesystem and report warning/stop thresholds."""
    if min(warning_free_bytes, stop_free_bytes, operation_reserve_bytes) < 0:
        raise ValueError("disk budget values must be non-negative")
    free_bytes = shutil.disk_usage(_existing_path(root)).free
    required_free_bytes = stop_free_bytes + operation_reserve_bytes
    return {
        "free_bytes": free_bytes,
        "warning_free_bytes": warning_free_bytes,
        "stop_free_bytes": stop_free_bytes,
        "operation_reserve_bytes": operation_reserve_bytes,
        "required_free_bytes": required_free_bytes,
        "warning": free_bytes <= warning_free_bytes,
        "stop": free_bytes <= stop_free_bytes or free_bytes < required_free_bytes,
    }


@contextmanager
def guarded_disk_write(
    root: Path,
    *,
    operation_reserve_bytes: int,
    operation: str,
    emergency: bool = False,
) -> Iterator[dict[str, int | bool]]:
    """Serialize participating writers across processes and hold the lock through I/O."""
    _PROCESS_LOCK.acquire()
    depth = getattr(_PROCESS_STATE, "depth", 0)
    lock_fd: int | None = None
    try:
        if depth == 0:
            flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
            lock_fd = os.open(LOCK_PATH, flags, 0o600)
            if not stat.S_ISREG(os.fstat(lock_fd).st_mode):
                raise OSError("Flynn storage guard lock is not a regular file")
            os.fchmod(lock_fd, 0o600)
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
            _PROCESS_STATE.lock_fd = lock_fd
            _PROCESS_STATE.operation_reserve_bytes = operation_reserve_bytes
            _PROCESS_STATE.root = root.resolve()
        else:
            _PROCESS_STATE.depth = depth + 1
            outer_root = getattr(_PROCESS_STATE, "root", None)
            outer_reserve = int(getattr(_PROCESS_STATE, "operation_reserve_bytes", 0))
            if root.resolve() != outer_root or operation_reserve_bytes > outer_reserve:
                budget = disk_budget(root, operation_reserve_bytes=required_disk_reserve_bytes(root)
                                     + operation_reserve_bytes)
                raise StorageBudgetError(budget, operation)
            budget = getattr(_PROCESS_STATE, "budget", None)
            if budget is None:
                raise RuntimeError("nested Flynn storage guard has no outer budget")
            yield budget
            return
        _PROCESS_STATE.depth = depth + 1

        if emergency:
            budget = disk_budget(root, stop_free_bytes=0, operation_reserve_bytes=operation_reserve_bytes)
        else:
            reserve = required_disk_reserve_bytes(root) + operation_reserve_bytes
            budget = disk_budget(root, operation_reserve_bytes=reserve)
        if budget["stop"]:
            raise StorageBudgetError(budget, operation)
        _PROCESS_STATE.budget = budget
        yield budget
    finally:
        current_depth = getattr(_PROCESS_STATE, "depth", 0)
        if current_depth > 0:
            _PROCESS_STATE.depth = current_depth - 1
            if current_depth == 1:
                active_fd = getattr(_PROCESS_STATE, "lock_fd", None)
                if active_fd is not None:
                    fcntl.flock(active_fd, fcntl.LOCK_UN)
                    os.close(active_fd)
                    _PROCESS_STATE.lock_fd = None
                _PROCESS_STATE.operation_reserve_bytes = 0
                _PROCESS_STATE.root = None
                _PROCESS_STATE.budget = None
        elif lock_fd is not None:
            os.close(lock_fd)
        _PROCESS_LOCK.release()
