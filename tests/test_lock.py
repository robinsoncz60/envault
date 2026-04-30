"""Tests for envault.lock."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from envault.lock import LockError, acquire, release, _lock_path, LOCK_FILENAME, STALE_AFTER


@pytest.fixture()
def tmp(tmp_path: Path) -> Path:
    return tmp_path


class TestAcquire:
    def test_creates_lock_file(self, tmp: Path) -> None:
        lock = acquire(tmp)
        assert lock.exists()
        assert lock.name == LOCK_FILENAME

    def test_lock_contains_pid(self, tmp: Path) -> None:
        lock = acquire(tmp)
        assert int(lock.read_text().strip()) == os.getpid()

    def test_returns_lock_path(self, tmp: Path) -> None:
        lock = acquire(tmp)
        assert lock == _lock_path(tmp)

    def test_raises_when_already_locked(self, tmp: Path) -> None:
        acquire(tmp)
        with pytest.raises(LockError, match="Could not acquire lock"):
            acquire(tmp, timeout=0)

    def test_error_message_includes_path(self, tmp: Path) -> None:
        acquire(tmp)
        with pytest.raises(LockError, match=str(tmp)):
            acquire(tmp, timeout=0)

    def test_removes_stale_lock_and_acquires(self, tmp: Path) -> None:
        lock_path = _lock_path(tmp)
        lock_path.write_text("99999")
        # backdate modification time so it looks stale
        stale_mtime = time.time() - STALE_AFTER - 10
        os.utime(lock_path, (stale_mtime, stale_mtime))

        lock = acquire(tmp, timeout=1)
        assert lock.exists()
        assert int(lock.read_text().strip()) == os.getpid()


class TestRelease:
    def test_removes_lock_file(self, tmp: Path) -> None:
        lock = acquire(tmp)
        release(lock)
        assert not lock.exists()

    def test_release_nonexistent_is_silent(self, tmp: Path) -> None:
        lock = _lock_path(tmp)
        # Should not raise even if lock never existed
        release(lock)

    def test_acquire_after_release_succeeds(self, tmp: Path) -> None:
        lock = acquire(tmp)
        release(lock)
        lock2 = acquire(tmp)
        assert lock2.exists()
