"""Tests for envault.env_rollback."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from envault.config import EnvaultConfig
from envault.env_rollback import RollbackError, RollbackResult, rollback
from envault.versioning import EnvVersion


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config() -> EnvaultConfig:
    cfg = MagicMock(spec=EnvaultConfig)
    cfg.env = "production"
    cfg.bucket = "my-bucket"
    return cfg


def _make_storage(versions: list[EnvVersion], bundle_bytes: bytes = b"BUNDLE"):
    storage = MagicMock()
    storage.download.return_value = bundle_bytes
    return storage


def _make_keypair():
    kp = MagicMock()
    kp.private_key_path = "/home/user/.envault/private.key"
    return kp


def _version(ver: str) -> EnvVersion:
    v = MagicMock(spec=EnvVersion)
    v.version = ver
    v.s3_key = f"production/{ver}.bundle"
    return v


# ---------------------------------------------------------------------------
# RollbackResult
# ---------------------------------------------------------------------------

def test_rollback_result_str():
    r = RollbackResult(
        source_version="20240101T000000Z",
        new_version="production/20240102T000000Z.bundle",
        env="KEY=val",
    )
    assert "20240101T000000Z" in str(r)
    assert "20240102T000000Z" in str(r)


# ---------------------------------------------------------------------------
# rollback()
# ---------------------------------------------------------------------------

@patch("envault.env_rollback.push", return_value="production/new.bundle")
@patch("envault.env_rollback.decrypt", return_value="KEY=value\n")
@patch("envault.env_rollback.decode_bundle")
@patch("envault.env_rollback.list_versions")
def test_rolls_back_to_previous_version(
    mock_list, mock_decode, mock_decrypt, mock_push
):
    versions = [_version("v2"), _version("v1")]
    mock_list.return_value = versions
    mock_decode.return_value = MagicMock(ciphertext=b"cipher")

    result = rollback(_make_config(), _make_storage(versions), _make_keypair())

    assert result.source_version == "v1"
    assert result.new_version == "production/new.bundle"
    assert result.env == "KEY=value\n"


@patch("envault.env_rollback.push", return_value="production/new.bundle")
@patch("envault.env_rollback.decrypt", return_value="KEY=value\n")
@patch("envault.env_rollback.decode_bundle")
@patch("envault.env_rollback.list_versions")
def test_rolls_back_to_explicit_version(
    mock_list, mock_decode, mock_decrypt, mock_push
):
    versions = [_version("v3"), _version("v2"), _version("v1")]
    mock_list.return_value = versions
    mock_decode.return_value = MagicMock(ciphertext=b"cipher")

    result = rollback(
        _make_config(), _make_storage(versions), _make_keypair(), target_version="v1"
    )

    assert result.source_version == "v1"


@patch("envault.env_rollback.list_versions", return_value=[])
def test_raises_when_no_versions(mock_list):
    with pytest.raises(RollbackError, match="No versions found"):
        rollback(_make_config(), MagicMock(), _make_keypair())


@patch("envault.env_rollback.list_versions")
def test_raises_when_only_one_version(mock_list):
    mock_list.return_value = [_version("v1")]
    with pytest.raises(RollbackError, match="Only one version"):
        rollback(_make_config(), MagicMock(), _make_keypair())


@patch("envault.env_rollback.list_versions")
def test_raises_when_target_version_not_found(mock_list):
    mock_list.return_value = [_version("v2"), _version("v1")]
    with pytest.raises(RollbackError, match="not found"):
        rollback(
            _make_config(), MagicMock(), _make_keypair(), target_version="v99"
        )
