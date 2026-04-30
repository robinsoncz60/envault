"""Tests for envault.share."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest

from envault.share import share, ShareError
from envault.bundle import EnvBundle, encode_bundle
from envault.versioning import EnvVersion
from datetime import datetime, timezone


ENV_NAME = "myapp"
VERSION = "20240101T000000Z"
PLAINTEXT = b"SECRET=hunter2\nDB=postgres"
CIPHERTEXT = b"age-encrypted-bytes"
PUB_KEY = "age1abcdef1234567890"
PRIV_KEY = "AGE-SECRET-KEY-XYZ"


def _make_bundle() -> EnvBundle:
    return EnvBundle(
        ciphertext=CIPHERTEXT,
        env_name=ENV_NAME,
        version=VERSION,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


def _make_storage(bundle: EnvBundle) -> MagicMock:
    storage = MagicMock()
    storage.download.return_value = encode_bundle(bundle)
    storage.upload.return_value = f"envault/{ENV_NAME}/{VERSION}-shared-age1abcdef1234"
    return storage


@patch("envault.share.encrypt", return_value=b"new-ciphertext")
@patch("envault.share.decrypt", return_value=PLAINTEXT)
@patch("envault.share.latest_version")
def test_returns_s3_keys_for_each_recipient(mock_latest, mock_decrypt, mock_encrypt):
    mock_latest.return_value = EnvVersion(env_name=ENV_NAME, version=VERSION, s3_key="k")
    bundle = _make_bundle()
    storage = _make_storage(bundle)

    keys = share(storage, ENV_NAME, PRIV_KEY, [PUB_KEY, PUB_KEY])

    assert len(keys) == 2
    assert storage.upload.call_count == 2


@patch("envault.share.encrypt", return_value=b"new-ciphertext")
@patch("envault.share.decrypt", return_value=PLAINTEXT)
@patch("envault.share.latest_version")
def test_uses_explicit_version_when_provided(mock_latest, mock_decrypt, mock_encrypt):
    bundle = _make_bundle()
    storage = _make_storage(bundle)

    share(storage, ENV_NAME, PRIV_KEY, [PUB_KEY], version=VERSION)

    mock_latest.assert_not_called()
    storage.download.assert_called_once_with(ENV_NAME, VERSION)


def test_raises_when_no_recipients():
    storage = MagicMock()
    with pytest.raises(ShareError, match="At least one recipient"):
        share(storage, ENV_NAME, PRIV_KEY, [])


@patch("envault.share.latest_version", return_value=None)
def test_raises_when_no_versions_exist(mock_latest):
    storage = MagicMock()
    with pytest.raises(ShareError, match="No versions found"):
        share(storage, ENV_NAME, PRIV_KEY, [PUB_KEY])


@patch("envault.share.decrypt", side_effect=Exception("decrypt failed"))
@patch("envault.share.latest_version")
def test_raises_on_download_failure(mock_latest, mock_decrypt):
    mock_latest.return_value = EnvVersion(env_name=ENV_NAME, version=VERSION, s3_key="k")
    storage = MagicMock()
    storage.download.side_effect = RuntimeError("S3 unreachable")

    with pytest.raises(ShareError, match="Failed to download"):
        share(storage, ENV_NAME, PRIV_KEY, [PUB_KEY])


@patch("envault.share.encrypt")
@patch("envault.share.decrypt", return_value=PLAINTEXT)
@patch("envault.share.latest_version")
def test_raises_on_encrypt_failure(mock_latest, mock_decrypt, mock_encrypt):
    from envault.crypto import CryptoError
    mock_latest.return_value = EnvVersion(env_name=ENV_NAME, version=VERSION, s3_key="k")
    mock_encrypt.side_effect = CryptoError("bad key")
    bundle = _make_bundle()
    storage = _make_storage(bundle)

    with pytest.raises(ShareError, match="Failed to encrypt for recipient"):
        share(storage, ENV_NAME, PRIV_KEY, [PUB_KEY])
