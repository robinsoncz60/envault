"""Tests for envault.cli_rollback."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from envault.cli_rollback import rollback_cmd
from envault.config import ConfigError
from envault.env_rollback import RollbackError, RollbackResult
from envault.keystore import KeystoreError


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


def _fake_config():
    cfg = MagicMock()
    cfg.bucket = "test-bucket"
    cfg.endpoint_url = "http://localhost:9000"
    cfg.region = "us-east-1"
    cfg.env = "staging"
    return cfg


def _fake_keypair():
    kp = MagicMock()
    kp.private_key_path = "/tmp/test.key"
    return kp


# ---------------------------------------------------------------------------
# run_rollback_cmd
# ---------------------------------------------------------------------------

@patch("envault.cli_rollback.rollback")
@patch("envault.cli_rollback.S3Storage")
@patch("envault.cli_rollback.load_keypair", return_value=_fake_keypair())
@patch("envault.cli_rollback.load_config")
def test_success_prints_result(mock_cfg, mock_kp, mock_s3, mock_rollback, runner):
    mock_cfg.return_value = _fake_config()
    mock_rollback.return_value = RollbackResult(
        source_version="v1",
        new_version="staging/v2.bundle",
        env="KEY=val\n",
    )

    result = runner.invoke(rollback_cmd, ["run"])

    assert result.exit_code == 0
    assert "v1" in result.output
    assert "staging/v2.bundle" in result.output


@patch("envault.cli_rollback.load_config", side_effect=ConfigError("missing"))
def test_exits_on_config_error(mock_cfg, runner):
    result = runner.invoke(rollback_cmd, ["run"])
    assert result.exit_code != 0
    assert "missing" in result.output


@patch("envault.cli_rollback.load_keypair", side_effect=KeystoreError("no key"))
@patch("envault.cli_rollback.load_config")
def test_exits_on_keystore_error(mock_cfg, mock_kp, runner):
    mock_cfg.return_value = _fake_config()
    result = runner.invoke(rollback_cmd, ["run"])
    assert result.exit_code != 0
    assert "no key" in result.output


@patch("envault.cli_rollback.rollback", side_effect=RollbackError("only one"))
@patch("envault.cli_rollback.S3Storage")
@patch("envault.cli_rollback.load_keypair")
@patch("envault.cli_rollback.load_config")
def test_exits_on_rollback_error(mock_cfg, mock_kp, mock_s3, mock_rb, runner):
    mock_cfg.return_value = _fake_config()
    mock_kp.return_value = _fake_keypair()
    result = runner.invoke(rollback_cmd, ["run"])
    assert result.exit_code != 0
    assert "only one" in result.output


@patch("envault.cli_rollback.rollback")
@patch("envault.cli_rollback.S3Storage")
@patch("envault.cli_rollback.load_keypair")
@patch("envault.cli_rollback.load_config")
def test_passes_explicit_version(mock_cfg, mock_kp, mock_s3, mock_rb, runner):
    mock_cfg.return_value = _fake_config()
    mock_kp.return_value = _fake_keypair()
    mock_rb.return_value = RollbackResult("v0", "staging/new.bundle", "")

    runner.invoke(rollback_cmd, ["run", "--version", "v0"])

    _, kwargs = mock_rb.call_args
    assert kwargs.get("target_version") == "v0" or mock_rb.call_args[0][3] == "v0"
