"""Tests for envault.env_promote."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from envault.env_promote import PromoteError, PromoteResult, promote
from envault.bundle import EnvBundle
from envault.versioning import EnvVersion


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_config():
    cfg = MagicMock()
    cfg.env = "staging"
    return cfg


def _make_storage(bundle_bytes: bytes = b"BUNDLE"):
    storage = MagicMock()
    storage.download.return_value = bundle_bytes
    storage.upload.return_value = "staging/v1.bundle"
    return storage


def _make_version_obj(version="20240101T000000Z"):
    v = MagicMock(spec=EnvVersion)
    v.version = version
    return v


# ---------------------------------------------------------------------------
# PromoteResult
# ---------------------------------------------------------------------------

def test_promote_result_str():
    r = PromoteResult(
        source_env="staging",
        target_env="production",
        source_version="20240101T000000Z",
        target_s3_key="production/20240102T000000Z.bundle",
    )
    s = str(r)
    assert "staging" in s
    assert "production" in s
    assert "20240101T000000Z" in s


# ---------------------------------------------------------------------------
# promote()
# ---------------------------------------------------------------------------

@patch("envault.env_promote._make_version", return_value="20240102T000000Z")
@patch("envault.env_promote.encrypt", return_value=b"NEW_CIPHER")
@patch("envault.env_promote.decrypt", return_value=b"PLAINTEXT")
@patch("envault.env_promote.decode_bundle")
@patch("envault.env_promote.latest_version")
def test_promote_success(mock_lv, mock_decode, mock_decrypt, mock_encrypt, mock_mkv):
    bundle = MagicMock(spec=EnvBundle)
    bundle.ciphertext = b"OLD_CIPHER"
    bundle.encode.return_value = b"ENCODED_BUNDLE"
    mock_decode.return_value = bundle
    mock_lv.return_value = _make_version_obj("20240101T000000Z")

    storage = _make_storage()
    result = promote(
        config=_make_config(),
        storage=storage,
        source_env="staging",
        target_env="production",
        source_private_key="priv",
        target_public_key="pub",
        promoted_by="alice",
    )

    assert isinstance(result, PromoteResult)
    assert result.source_env == "staging"
    assert result.target_env == "production"
    assert result.source_version == "20240101T000000Z"
    assert result.target_s3_key == "production/20240102T000000Z.bundle"
    storage.upload.assert_called_once()


@patch("envault.env_promote.latest_version", return_value=None)
def test_promote_raises_when_no_versions(mock_lv):
    with pytest.raises(PromoteError, match="No versions found"):
        promote(
            config=_make_config(),
            storage=_make_storage(),
            source_env="staging",
            target_env="production",
            source_private_key="priv",
            target_public_key="pub",
        )


@patch("envault.env_promote.latest_version")
@patch("envault.env_promote.decode_bundle")
def test_promote_raises_on_download_failure(mock_decode, mock_lv):
    mock_lv.return_value = _make_version_obj()
    storage = _make_storage()
    storage.download.side_effect = RuntimeError("S3 error")

    with pytest.raises(PromoteError, match="Failed to download"):
        promote(
            config=_make_config(),
            storage=storage,
            source_env="staging",
            target_env="production",
            source_private_key="priv",
            target_public_key="pub",
        )


@patch("envault.env_promote._make_version", return_value="20240102T000000Z")
@patch("envault.env_promote.encrypt")
@patch("envault.env_promote.decrypt", return_value=b"PLAINTEXT")
@patch("envault.env_promote.decode_bundle")
@patch("envault.env_promote.latest_version")
def test_promote_uses_explicit_version(mock_lv, mock_decode, mock_decrypt, mock_encrypt, mock_mkv):
    bundle = MagicMock(spec=EnvBundle)
    bundle.ciphertext = b"CIPHER"
    bundle.encode.return_value = b"ENC"
    mock_decode.return_value = bundle
    mock_encrypt.return_value = b"NEW"

    storage = _make_storage()
    promote(
        config=_make_config(),
        storage=storage,
        source_env="staging",
        target_env="production",
        source_private_key="priv",
        target_public_key="pub",
        version="20231231T120000Z",
    )

    storage.download.assert_called_once_with("staging/20231231T120000Z.bundle")
    mock_lv.assert_not_called()
