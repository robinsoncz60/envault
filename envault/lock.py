"""Lock file management to prevent concurrent envault operations on the same project."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Optional

LOCK_FILENAME = ".envault.lock"
DEFAULT_TIMEOUT = 30  # seconds
STALE_AFTER = 300  # 5 minutes


class LockError(Exception):
    """Raised when a lock cannot be acquired or is invalid."""


def _lock_path(directory: Path) -> Path:
    return directory / LOCK_FILENAME


def acquire(directory: Path, timeout: int = DEFAULT_TIMEOUT) -> Path:
    """Acquire a lock in *directory*, blocking up to *timeout* seconds.

    Returns the path to the lock file on success.
    Raises LockError if the lock cannot be acquired within the timeout.
    """
    lock = _lock_path(directory)
    deadline = time.monotonic() + timeout

    while True:
        # Remove stale lock left by a crashed process
        if lock.exists():
            try:
                age = time.time() - lock.stat().st_mtime
                if age > STALE_AFTER:
                    lock.unlink(missing_ok=True)
            except OSError:
                pass

        try:
            fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w") as f:
                f.write(str(os.getpid()))
            return lock
        except FileExistsError:
            if time.monotonic() >= deadline:
                pid = _read_pid(lock)
                hint = f" (held by PID {pid})" if pid else ""
                raise LockError(
                    f"Could not acquire lock at {lock}{hint}. "
                    "Another envault process may be running."
                )
            time.sleep(0.2)


def release(lock: Path) -> None:
    """Release a previously acquired lock."""
    try:
        lock.unlink(missing_ok=True)
    except OSError as exc:
        raise LockError(f"Failed to release lock at {lock}: {exc}") from exc


def _read_pid(lock: Path) -> Optional[int]:
    try:
        return int(lock.read_text().strip())
    except (OSError, ValueError):
        return None
