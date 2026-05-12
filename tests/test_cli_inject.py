"""Tests for envault.cli_inject."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from envault.cli_inject import inject_cmd
from envault.config import ConfigError
from envault.env_inject import InjectError, InjectResult
from envault.keystore import KeystoreError
from envault.storage import StorageError


@pytest.fixture()
def runner():
    return CliRunner()


def _fake_config():
    cfg = MagicMock()
    cfg.bucket = "my-bucket"
    cfg.environment = "staging"
    cfg.endpoint_url = None
    return cfg


def _fake_keypair():
    kp = MagicMock()
    kp.private_key_path = "/home/user/.envault/staging.key"
    return kp


def _fake_version():
    v = MagicMock()
    v.s3_key = "staging/20240101T000000Z.bundle"
    return v


def _fake_bundle():
    b = MagicMock()
    b.ciphertext = b"encrypted"
    return b


@patch("envault.cli_inject.decode_bundle", return_value=_fake_bundle())
@patch("envault.cli_inject.inject", return_value=InjectResult(command=["true"], returncode=0, injected_keys=["FOO"]))
@patch("envault.cli_inject.S3Storage")
@patch("envault.cli_inject.latest_version", return_value=_fake_version())
@patch("envault.cli_inject.load_keypair", return_value=_fake_keypair())
@patch("envault.cli_inject.load_config", return_value=_fake_config())
def test_success_exits_with_command_returncode(
    mock_cfg, mock_kp, mock_lv, mock_storage_cls, mock_inject, mock_decode, runner
):
    mock_storage_cls.return_value.download.return_value = b"bundle"
    result = runner.invoke(inject_cmd, ["run", "true"])
    assert result.exit_code == 0


@patch("envault.cli_inject.load_config", side_effect=ConfigError("missing config"))
def test_exits_on_config_error(mock_cfg, runner):
    result = runner.invoke(inject_cmd, ["run", "echo", "hi"])
    assert result.exit_code == 1
    assert "Config error" in result.output


@patch("envault.cli_inject.load_keypair", side_effect=KeystoreError("no key"))
@patch("envault.cli_inject.load_config", return_value=_fake_config())
def test_exits_on_keystore_error(mock_cfg, mock_kp, runner):
    result = runner.invoke(inject_cmd, ["run", "echo", "hi"])
    assert result.exit_code == 1
    assert "Keystore error" in result.output


@patch("envault.cli_inject.S3Storage")
@patch("envault.cli_inject.latest_version", side_effect=StorageError("s3 down"))
@patch("envault.cli_inject.load_keypair", return_value=_fake_keypair())
@patch("envault.cli_inject.load_config", return_value=_fake_config())
def test_exits_on_storage_error(mock_cfg, mock_kp, mock_lv, mock_storage_cls, runner):
    result = runner.invoke(inject_cmd, ["run", "echo", "hi"])
    assert result.exit_code == 1
    assert "Storage error" in result.output


@patch("envault.cli_inject.decode_bundle", return_value=_fake_bundle())
@patch("envault.cli_inject.inject", side_effect=InjectError("bad decrypt"))
@patch("envault.cli_inject.S3Storage")
@patch("envault.cli_inject.latest_version", return_value=_fake_version())
@patch("envault.cli_inject.load_keypair", return_value=_fake_keypair())
@patch("envault.cli_inject.load_config", return_value=_fake_config())
def test_exits_on_inject_error(
    mock_cfg, mock_kp, mock_lv, mock_storage_cls, mock_inject, mock_decode, runner
):
    mock_storage_cls.return_value.download.return_value = b"bundle"
    result = runner.invoke(inject_cmd, ["run", "true"])
    assert result.exit_code == 1
    assert "Inject error" in result.output
