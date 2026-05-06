"""Tests for envault.cli_watch."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from envault.cli_watch import watch_cmd
from envault.config import EnvaultConfig
from envault.watch import WatchError


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


def _fake_config() -> EnvaultConfig:
    return EnvaultConfig(
        environment="staging",
        bucket="my-bucket",
        prefix="envault",
        region="us-east-1",
    )


def _fake_keypair() -> MagicMock:
    kp = MagicMock()
    kp.public_key = "age1abc"
    kp.private_key = "AGE-SECRET-KEY-1abc"
    return kp


class TestWatchCmd:
    def test_exits_on_config_error(self, runner: CliRunner, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("KEY=val")

        with patch("envault.cli_watch.load_config", side_effect=Exception("bad config")):
            result = runner.invoke(watch_cmd, [str(env_file)])

        assert result.exit_code != 0

    def test_exits_on_keystore_error(self, runner: CliRunner, tmp_path: Path) -> None:
        from envault.keystore import KeystoreError

        env_file = tmp_path / ".env"
        env_file.write_text("KEY=val")

        with patch("envault.cli_watch.load_config", return_value=_fake_config()), \
             patch("envault.cli_watch.load_keypair", side_effect=KeystoreError("no key")):
            result = runner.invoke(watch_cmd, [str(env_file)])

        assert result.exit_code != 0
        assert "no key" in result.output

    def test_prints_watching_message(self, runner: CliRunner, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("KEY=val")

        with patch("envault.cli_watch.load_config", return_value=_fake_config()), \
             patch("envault.cli_watch.load_keypair", return_value=_fake_keypair()), \
             patch("envault.cli_watch.watch", side_effect=KeyboardInterrupt):
            result = runner.invoke(watch_cmd, [str(env_file), "--interval", "1"])

        assert "Watching" in result.output
        assert "Stopped watching" in result.output
        assert result.exit_code == 0

    def test_exits_on_watch_error(self, runner: CliRunner, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("KEY=val")

        with patch("envault.cli_watch.load_config", return_value=_fake_config()), \
             patch("envault.cli_watch.load_keypair", return_value=_fake_keypair()), \
             patch("envault.cli_watch.watch", side_effect=WatchError("poll failed")):
            result = runner.invoke(watch_cmd, [str(env_file)])

        assert result.exit_code != 0
        assert "poll failed" in result.output

    def test_on_change_calls_push(self, runner: CliRunner, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("KEY=val")
        captured_callback: list = []

        def fake_watch(path, on_change, interval, **kw):
            captured_callback.append(on_change)

        mock_push = MagicMock(return_value="envault/staging/v1.env.age")

        with patch("envault.cli_watch.load_config", return_value=_fake_config()), \
             patch("envault.cli_watch.load_keypair", return_value=_fake_keypair()), \
             patch("envault.cli_watch.watch", side_effect=fake_watch), \
             patch("envault.cli_watch.push", mock_push):
            runner.invoke(watch_cmd, [str(env_file)])

        assert captured_callback, "watch was never called with a callback"
        captured_callback[0](env_file)
        mock_push.assert_called_once()
