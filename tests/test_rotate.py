"""Tests for envault.rotate."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from envault.rotate import RotateError, rotate


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_config(env: str = "prod") -> SimpleNamespace:
    return SimpleNamespace(env=env, bucket="my-bucket")


def _make_storage(download_return: bytes = b"bundle-bytes") -> MagicMock:
    s = MagicMock()
    s.download.return_value = download_return
    s.upload.return_value = "prod/v1.bundle"
    return s


def _make_keypair(pub: str = "age1pub", priv_path: str = "/keys/priv.key") -> SimpleNamespace:
    return SimpleNamespace(public_key=pub, private_key_path=priv_path)


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------

class TestRotate:
    @patch("envault.rotate.encode_bundle", return_value=b"new-bundle")
    @patch("envault.rotate.encrypt", return_value=b"new-ciphertext")
    @patch("envault.rotate.decrypt", return_value=b"plaintext")
    @patch("envault.rotate.decode_bundle")
    @patch("envault.rotate._make_version", return_value="20240101T000000Z")
    @patch("envault.rotate.latest_version")
    def test_returns_s3_key_on_success(
        self, mock_lv, mock_mv, mock_decode, mock_dec, mock_enc, mock_encode
    ):
        mock_lv.return_value = SimpleNamespace(s3_key="prod/old.bundle")
        mock_decode.return_value = SimpleNamespace(ciphertext=b"old-ct")
        storage = _make_storage()
        key = rotate(
            _make_config(), storage, _make_keypair(), _make_keypair("age1new"), "alice"
        )
        assert key == "prod/20240101T000000Z.bundle"
        storage.upload.assert_called_once()

    @patch("envault.rotate.latest_version", return_value=None)
    def test_raises_when_no_versions(self, _):
        with pytest.raises(RotateError, match="No existing versions"):
            rotate(_make_config(), _make_storage(), _make_keypair(), _make_keypair(), "alice")

    @patch("envault.rotate.latest_version")
    def test_raises_when_download_fails(self, mock_lv):
        mock_lv.return_value = SimpleNamespace(s3_key="prod/old.bundle")
        storage = _make_storage()
        storage.download.side_effect = RuntimeError("network error")
        with pytest.raises(RotateError, match="Failed to download"):
            rotate(_make_config(), storage, _make_keypair(), _make_keypair(), "alice")

    @patch("envault.rotate.decode_bundle", side_effect=ValueError("bad bundle"))
    @patch("envault.rotate.latest_version")
    def test_raises_when_decode_fails(self, mock_lv, _):
        mock_lv.return_value = SimpleNamespace(s3_key="prod/old.bundle")
        with pytest.raises(RotateError, match="Failed to decode"):
            rotate(_make_config(), _make_storage(), _make_keypair(), _make_keypair(), "alice")

    @patch("envault.rotate.decrypt", side_effect=Exception("bad key"))
    @patch("envault.rotate.decode_bundle")
    @patch("envault.rotate.latest_version")
    def test_raises_when_decrypt_fails(self, mock_lv, mock_decode, _):
        mock_lv.return_value = SimpleNamespace(s3_key="prod/old.bundle")
        mock_decode.return_value = SimpleNamespace(ciphertext=b"ct")
        with pytest.raises(RotateError, match="Decryption with old key failed"):
            rotate(_make_config(), _make_storage(), _make_keypair(), _make_keypair(), "alice")

    @patch("envault.rotate.encrypt", side_effect=Exception("enc fail"))
    @patch("envault.rotate.decrypt", return_value=b"pt")
    @patch("envault.rotate.decode_bundle")
    @patch("envault.rotate.latest_version")
    def test_raises_when_encrypt_fails(self, mock_lv, mock_decode, mock_dec, _):
        mock_lv.return_value = SimpleNamespace(s3_key="prod/old.bundle")
        mock_decode.return_value = SimpleNamespace(ciphertext=b"ct")
        with pytest.raises(RotateError, match="Encryption with new key failed"):
            rotate(_make_config(), _make_storage(), _make_keypair(), _make_keypair(), "alice")
