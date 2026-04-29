"""Tests for the `rotate` CLI sub-command."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from envault.cli_rotate import rotate_cmd
from envault.config import ConfigError
from envault.crypto import CryptoError
from envault.keystore import KeystoreError
from envault.rotate import RotateError


@pytest.fixture()
def runner():
    return CliRunner()


def _fake_config():
    return SimpleNamespace(
        env="prod",
        bucket="my-bucket",
        endpoint_url="http://localhost:9000",
        region="us-east-1",
    )


def _fake_keypair():
    return SimpleNamespace(public_key="age1oldpubkey", private_key_path="/keys/old.key")


class TestRotateCmd:
    @patch("envault.cli_rotate.save_keypair")
    @patch("envault.cli_rotate.rotate", return_value="prod/v2.bundle")
    @patch("envault.cli_rotate._kp_from_raw")
    @patch("envault.cli_rotate.generate_keypair", return_value=("age1new", "AGE-SECRET-KEY-NEW"))
    @patch("envault.cli_rotate.load_keypair", return_value=_fake_keypair())
    @patch("envault.cli_rotate.load_config", return_value=_fake_config())
    @patch("envault.cli_rotate.S3Storage")
    def test_success_prints_s3_key(
        self, mock_s3, mock_cfg, mock_lkp, mock_gen, mock_kp_raw, mock_rot, mock_save, runner
    ):
        result = runner.invoke(rotate_cmd, [])
        assert result.exit_code == 0
        assert "prod/v2.bundle" in result.output

    @patch("envault.cli_rotate.load_config", side_effect=ConfigError("missing file"))
    def test_exits_on_config_error(self, _, runner):
        result = runner.invoke(rotate_cmd, [])
        assert result.exit_code != 0
        assert "Config error" in result.output

    @patch("envault.cli_rotate.load_keypair", side_effect=KeystoreError("no key"))
    @patch("envault.cli_rotate.load_config", return_value=_fake_config())
    def test_exits_on_keystore_error(self, _, __, runner):
        result = runner.invoke(rotate_cmd, [])
        assert result.exit_code != 0
        assert "Keystore error" in result.output

    @patch("envault.cli_rotate.generate_keypair", side_effect=CryptoError("age missing"))
    @patch("envault.cli_rotate.load_keypair", return_value=_fake_keypair())
    @patch("envault.cli_rotate.load_config", return_value=_fake_config())
    def test_exits_on_crypto_error(self, _, __, ___, runner):
        result = runner.invoke(rotate_cmd, [])
        assert result.exit_code != 0
        assert "Key generation failed" in result.output

    @patch("envault.cli_rotate.rotate", side_effect=RotateError("no versions"))
    @patch("envault.cli_rotate._kp_from_raw")
    @patch("envault.cli_rotate.generate_keypair", return_value=("age1new", "AGE-SECRET-KEY-NEW"))
    @patch("envault.cli_rotate.load_keypair", return_value=_fake_keypair())
    @patch("envault.cli_rotate.load_config", return_value=_fake_config())
    @patch("envault.cli_rotate.S3Storage")
    def test_exits_on_rotate_error(self, _, __, ___, ____, _____, ______, runner):
        result = runner.invoke(rotate_cmd, [])
        assert result.exit_code != 0
        assert "Rotation failed" in result.output
