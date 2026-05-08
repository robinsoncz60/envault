"""Tests for envault.env_copy."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from envault.env_copy import copy_env, CopyError, CopyResult
from envault.storage import StorageError
from envault.versioning import EnvVersion


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_config(prefix: str = "staging") -> MagicMock:
    cfg = MagicMock()
    cfg.prefix = prefix
    cfg.bucket = "my-bucket"
    cfg.endpoint_url = "https://s3.example.com"
    cfg.aws_access_key_id = "AK"
    cfg.aws_secret_access_key = "SK"
    return cfg


def _make_storage(bundle_bytes: bytes = b"fake-bundle") -> MagicMock:
    storage = MagicMock()
    storage.download.return_value = bundle_bytes
    storage.upload.return_value = "dest/20240101T000000Z.env.age"
    return storage


# ---------------------------------------------------------------------------
# CopyResult
# ---------------------------------------------------------------------------

def test_copy_result_str() -> None:
    result = CopyResult(
        source_key="staging/v1.env.age",
        dest_key="production/v2.env.age",
        version="v2",
    )
    text = str(result)
    assert "staging/v1.env.age" in text
    assert "production/v2.env.age" in text
    assert "v2" in text


# ---------------------------------------------------------------------------
# copy_env
# ---------------------------------------------------------------------------

@patch("envault.env_copy._make_version", return_value="20240601T120000Z")
@patch("envault.env_copy.latest_version")
def test_copy_uses_latest_when_no_version_given(mock_latest, mock_ver) -> None:
    mock_latest.return_value = EnvVersion("staging", "20240101T000000Z")
    config = _make_config()
    storage = _make_storage()

    result = copy_env(config, storage, dest_prefix="production")

    storage.download.assert_called_once_with("staging/20240101T000000Z.env.age")
    storage.upload.assert_called_once()
    assert result.dest_key == "production/20240601T120000Z.env.age"
    assert result.version == "20240601T120000Z"


@patch("envault.env_copy._make_version", return_value="20240601T120000Z")
def test_copy_uses_explicit_version(mock_ver) -> None:
    config = _make_config()
    storage = _make_storage()

    result = copy_env(
        config, storage, dest_prefix="production", source_version="20240101T000000Z"
    )

    storage.download.assert_called_once_with("staging/20240101T000000Z.env.age")
    assert result.source_key == "staging/20240101T000000Z.env.age"


@patch("envault.env_copy.latest_version", return_value=None)
def test_raises_when_no_versions_found(mock_latest) -> None:
    config = _make_config()
    storage = _make_storage()

    with pytest.raises(CopyError, match="No versions found"):
        copy_env(config, storage, dest_prefix="production")


@patch("envault.env_copy._make_version", return_value="20240601T120000Z")
def test_raises_on_download_error(mock_ver) -> None:
    config = _make_config()
    storage = _make_storage()
    storage.download.side_effect = StorageError("not found")

    with pytest.raises(CopyError, match="Failed to download"):
        copy_env(
            config, storage, dest_prefix="production", source_version="20240101T000000Z"
        )


@patch("envault.env_copy._make_version", return_value="20240601T120000Z")
def test_raises_on_upload_error(mock_ver) -> None:
    config = _make_config()
    storage = _make_storage()
    storage.upload.side_effect = StorageError("forbidden")

    with pytest.raises(CopyError, match="Failed to upload"):
        copy_env(
            config, storage, dest_prefix="production", source_version="20240101T000000Z"
        )
