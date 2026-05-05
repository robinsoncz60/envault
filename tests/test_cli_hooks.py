"""Tests for envault.cli_hooks."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from envault.cli_hooks import hooks_cmd
from envault.config import ConfigError
from envault.hooks import HookError


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


def _fake_config(hooks: dict | None = None) -> MagicMock:
    cfg = MagicMock()
    cfg.hooks = hooks or {}
    return cfg


# ---------------------------------------------------------------------------
# list sub-command
# ---------------------------------------------------------------------------

class TestListHooksCmd:
    def test_shows_configured_hooks(self, runner: CliRunner):
        cfg = _fake_config({"pre_push": ["make lint"], "post_pull": ["echo done"]})
        with patch("envault.cli_hooks.load_config", return_value=cfg):
            result = runner.invoke(hooks_cmd, ["list"])
        assert result.exit_code == 0
        assert "pre_push" in result.output
        assert "make lint" in result.output
        assert "post_pull" in result.output

    def test_shows_no_hooks_message_when_empty(self, runner: CliRunner):
        cfg = _fake_config({})
        with patch("envault.cli_hooks.load_config", return_value=cfg):
            result = runner.invoke(hooks_cmd, ["list"])
        assert result.exit_code == 0
        assert "No hooks configured" in result.output

    def test_exits_on_config_error(self, runner: CliRunner):
        with patch("envault.cli_hooks.load_config", side_effect=ConfigError("missing config")):
            result = runner.invoke(hooks_cmd, ["list"])
        assert result.exit_code != 0
        assert "missing config" in result.output


# ---------------------------------------------------------------------------
# run sub-command
# ---------------------------------------------------------------------------

class TestRunHooksCmd:
    def test_runs_phase_hooks_successfully(self, runner: CliRunner):
        cfg = _fake_config({"pre_push": ["echo hello"]})
        with patch("envault.cli_hooks.load_config", return_value=cfg), \
             patch("envault.cli_hooks.run_hooks") as mock_run:
            result = runner.invoke(hooks_cmd, ["run", "pre_push"])
        assert result.exit_code == 0
        mock_run.assert_called_once_with(["echo hello"])
        assert "successfully" in result.output

    def test_shows_message_when_no_hooks_for_phase(self, runner: CliRunner):
        cfg = _fake_config({})
        with patch("envault.cli_hooks.load_config", return_value=cfg):
            result = runner.invoke(hooks_cmd, ["run", "post_push"])
        assert result.exit_code == 0
        assert "No hooks defined" in result.output

    def test_exits_on_hook_error(self, runner: CliRunner):
        cfg = _fake_config({"pre_pull": ["bad-cmd"]})
        with patch("envault.cli_hooks.load_config", return_value=cfg), \
             patch("envault.cli_hooks.run_hooks", side_effect=HookError("hook failed")):
            result = runner.invoke(hooks_cmd, ["run", "pre_pull"])
        assert result.exit_code != 0
        assert "hook failed" in result.output

    def test_rejects_invalid_phase(self, runner: CliRunner):
        result = runner.invoke(hooks_cmd, ["run", "invalid_phase"])
        assert result.exit_code != 0
