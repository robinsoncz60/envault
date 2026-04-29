"""Tests for the CLI commands."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from envault.cli import cli
from envault.crypto import CryptoError
from envault.keystore import KeystoreError
from envault.push import PushError
from envault.pull import PullError


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


class TestKeygen:
    def test_generates_and_saves_keypair(self, runner: CliRunner) -> None:
        mock_kp = MagicMock(public_key="age1abc")
        with patch("envault.cli.keypair_exists", return_value=False), \
             patch("envault.cli.generate_keypair", return_value=mock_kp), \
             patch("envault.cli.save_keypair") as mock_save:
            result = runner.invoke(cli, ["keygen", "--name", "mykey"])
        assert result.exit_code == 0
        assert "age1abc" in result.output
        mock_save.assert_called_once_with("mykey", mock_kp)

    def test_exits_if_keypair_already_exists(self, runner: CliRunner) -> None:
        with patch("envault.cli.keypair_exists", return_value=True):
            result = runner.invoke(cli, ["keygen", "--name", "mykey"])
        assert result.exit_code == 1
        assert "already exists" in result.output

    def test_exits_on_crypto_error(self, runner: CliRunner) -> None:
        with patch("envault.cli.keypair_exists", return_value=False), \
             patch("envault.cli.generate_keypair", side_effect=CryptoError("age missing")):
            result = runner.invoke(cli, ["keygen"])
        assert result.exit_code == 1
        assert "age missing" in result.output


class TestPushCmd:
    def test_push_success(self, runner: CliRunner, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("KEY=val")
        mock_cfg = MagicMock()
        mock_kp = MagicMock()
        with patch("envault.cli.load_config", return_value=mock_cfg), \
             patch("envault.cli.load_keypair", return_value=mock_kp), \
             patch("envault.cli.S3Storage"), \
             patch("envault.cli.push", return_value="v20240101_120000") as mock_push:
            result = runner.invoke(cli, ["push-cmd", str(env_file)])
        assert result.exit_code == 0
        assert "v20240101_120000" in result.output
        mock_push.assert_called_once()

    def test_push_error_exits(self, runner: CliRunner, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("KEY=val")
        with patch("envault.cli.load_config"), \
             patch("envault.cli.load_keypair"), \
             patch("envault.cli.S3Storage"), \
             patch("envault.cli.push", side_effect=PushError("encryption failed")):
            result = runner.invoke(cli, ["push-cmd", str(env_file)])
        assert result.exit_code == 1
        assert "encryption failed" in result.output


class TestPullCmd:
    def test_pull_success(self, runner: CliRunner, tmp_path: Path) -> None:
        output = tmp_path / ".env"
        mock_cfg = MagicMock()
        mock_kp = MagicMock()
        with patch("envault.cli.load_config", return_value=mock_cfg), \
             patch("envault.cli.load_keypair", return_value=mock_kp), \
             patch("envault.cli.S3Storage"), \
             patch("envault.cli.pull") as mock_pull:
            result = runner.invoke(cli, ["pull-cmd", "--output", str(output)])
        assert result.exit_code == 0
        assert str(output) in result.output
        mock_pull.assert_called_once()

    def test_pull_error_exits(self, runner: CliRunner) -> None:
        with patch("envault.cli.load_config"), \
             patch("envault.cli.load_keypair"), \
             patch("envault.cli.S3Storage"), \
             patch("envault.cli.pull", side_effect=PullError("not found")):
            result = runner.invoke(cli, ["pull-cmd"])
        assert result.exit_code == 1
        assert "not found" in result.output


class TestVersionsCmd:
    def test_lists_versions(self, runner: CliRunner) -> None:
        mock_v1 = MagicMock(__str__=lambda self: "v20240101_120000")
        mock_v2 = MagicMock(__str__=lambda self: "v20240101_110000")
        with patch("envault.cli.load_config"), \
             patch("envault.cli.S3Storage"), \
             patch("envault.cli.list_versions", return_value=[mock_v1, mock_v2]):
            result = runner.invoke(cli, ["versions"])
        assert result.exit_code == 0
        assert "v20240101_120000" in result.output

    def test_shows_no_versions_message(self, runner: CliRunner) -> None:
        with patch("envault.cli.load_config"), \
             patch("envault.cli.S3Storage"), \
             patch("envault.cli.list_versions", return_value=[]):
            result = runner.invoke(cli, ["versions"])
        assert result.exit_code == 0
        assert "No versions found" in result.output
