"""Tests for envault.watch."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from envault.watch import WatchError, WatchState, watch


# ---------------------------------------------------------------------------
# WatchState
# ---------------------------------------------------------------------------


class TestWatchState:
    def test_current_hash_is_deterministic(self, tmp_path: Path) -> None:
        f = tmp_path / ".env"
        f.write_text("KEY=value")
        state = WatchState(path=f)
        assert state.current_hash() == state.current_hash()

    def test_has_changed_returns_false_when_unchanged(self, tmp_path: Path) -> None:
        f = tmp_path / ".env"
        f.write_text("KEY=value")
        state = WatchState(path=f)
        state.seed()
        assert state.has_changed() is False

    def test_has_changed_returns_true_after_modification(self, tmp_path: Path) -> None:
        f = tmp_path / ".env"
        f.write_text("KEY=value")
        state = WatchState(path=f)
        state.seed()
        f.write_text("KEY=new_value")
        assert state.has_changed() is True

    def test_has_changed_updates_last_hash(self, tmp_path: Path) -> None:
        f = tmp_path / ".env"
        f.write_text("KEY=value")
        state = WatchState(path=f)
        state.seed()
        f.write_text("KEY=new_value")
        state.has_changed()
        # Second call should return False because hash was updated
        assert state.has_changed() is False

    def test_has_changed_returns_false_when_file_missing(self, tmp_path: Path) -> None:
        f = tmp_path / ".env"
        state = WatchState(path=f)
        assert state.has_changed() is False

    def test_seed_sets_last_hash(self, tmp_path: Path) -> None:
        f = tmp_path / ".env"
        f.write_text("KEY=value")
        state = WatchState(path=f)
        assert state.last_hash is None
        state.seed()
        assert state.last_hash is not None

    def test_seed_handles_missing_file(self, tmp_path: Path) -> None:
        f = tmp_path / ".env"
        state = WatchState(path=f)
        state.seed()  # should not raise
        assert state.last_hash is None


# ---------------------------------------------------------------------------
# watch()
# ---------------------------------------------------------------------------


def test_watch_raises_when_file_missing(tmp_path: Path) -> None:
    with pytest.raises(WatchError, match="File not found"):
        watch(tmp_path / "missing.env", on_change=lambda p: None, max_iterations=0)


def test_watch_calls_on_change_when_file_modified(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("KEY=original")

    callback = MagicMock()
    call_count = 0

    def fake_sleep(interval: float) -> None:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            env_file.write_text("KEY=modified")

    with patch("envault.watch.time.sleep", side_effect=fake_sleep):
        watch(env_file, on_change=callback, interval=0.0, max_iterations=2)

    callback.assert_called_once_with(env_file)


def test_watch_does_not_call_on_change_when_file_unchanged(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("KEY=value")

    callback = MagicMock()

    with patch("envault.watch.time.sleep"):
        watch(env_file, on_change=callback, interval=0.0, max_iterations=3)

    callback.assert_not_called()
