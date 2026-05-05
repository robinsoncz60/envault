"""Tests for envault.hooks."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from envault.hooks import HookConfig, HookError, run_hooks


# ---------------------------------------------------------------------------
# HookConfig
# ---------------------------------------------------------------------------

class TestHookConfig:
    def test_from_dict_populates_all_phases(self):
        data = {
            "pre_push": ["make lint"],
            "post_push": ["echo pushed"],
            "pre_pull": ["echo pulling"],
            "post_pull": ["make test"],
        }
        cfg = HookConfig.from_dict(data)
        assert cfg.pre_push == ["make lint"]
        assert cfg.post_push == ["echo pushed"]
        assert cfg.pre_pull == ["echo pulling"]
        assert cfg.post_pull == ["make test"]

    def test_from_dict_defaults_to_empty_lists(self):
        cfg = HookConfig.from_dict({})
        assert cfg.pre_push == []
        assert cfg.post_push == []
        assert cfg.pre_pull == []
        assert cfg.post_pull == []


# ---------------------------------------------------------------------------
# run_hooks
# ---------------------------------------------------------------------------

def _make_completed(returncode: int, stderr: str = "") -> MagicMock:
    result = MagicMock(spec=subprocess.CompletedProcess)
    result.returncode = returncode
    result.stderr = stderr
    return result


class TestRunHooks:
    def test_runs_nothing_when_list_is_empty(self):
        # Should not raise and not call subprocess at all
        with patch("envault.hooks.subprocess.run") as mock_run:
            run_hooks([])
            mock_run.assert_not_called()

    def test_calls_subprocess_for_each_command(self):
        with patch("envault.hooks.subprocess.run", return_value=_make_completed(0)) as mock_run:
            run_hooks(["echo a", "echo b"])
            assert mock_run.call_count == 2

    def test_passes_cwd_to_subprocess(self, tmp_path: Path):
        with patch("envault.hooks.subprocess.run", return_value=_make_completed(0)) as mock_run:
            run_hooks(["echo hi"], cwd=tmp_path)
            _, kwargs = mock_run.call_args
            assert kwargs["cwd"] == tmp_path

    def test_raises_hook_error_on_nonzero_exit(self):
        with patch(
            "envault.hooks.subprocess.run",
            return_value=_make_completed(1, stderr="something went wrong"),
        ):
            with pytest.raises(HookError, match="exit 1"):
                run_hooks(["bad-command"])

    def test_raises_hook_error_when_command_not_found(self):
        with patch(
            "envault.hooks.subprocess.run",
            side_effect=FileNotFoundError,
        ):
            with pytest.raises(HookError, match="not found"):
                run_hooks(["nonexistent-tool"])

    def test_stops_at_first_failing_command(self):
        call_count = 0

        def fake_run(cmd, **kwargs):
            nonlocal call_count
            call_count += 1
            return _make_completed(1)

        with patch("envault.hooks.subprocess.run", side_effect=fake_run):
            with pytest.raises(HookError):
                run_hooks(["fail", "should-not-run"])

        assert call_count == 1
