"""Tests for envault.pull."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from envault.bundle import EnvBundle
from envault.config import EnvaultConfig
from envault.pull import PullError, pull
from envault.versioning import EnvVersion


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_config() -> EnvaultConfig:
    return EnvaultConfig(
        env_name="myapp",
        bucket="test-bucket",
        prefix="envault",
        endpoint_url="http://localhost:9000",
    )


def _make_keypair():
    kp = MagicMock()
    kp.private_key = b"private"
    return kp


def _make_bundle(ciphertext: bytes = b"cipherdata") -> EnvBundle:
    return EnvBundle(ciphertext=ciphertext, env_name="myapp", version="20240101T000000Z")


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------

class TestPull:
    @patch("envault.pull.S3Storage")
    @patch("envault.pull.decrypt", return_value=b"KEY=value\n")
    @patch("envault.pull.decode_bundle")
    @patch("envault.pull.latest_version")
    @patch("envault.pull.load_keypair")
    def test_writes_plaintext_to_output_path(
        self, mock_load, mock_latest, mock_decode, mock_decrypt, mock_storage_cls, tmp_path
    ):
        mock_load.return_value = _make_keypair()
        mock_latest.return_value = EnvVersion("myapp", "20240101T000000Z")
        mock_decode.return_value = _make_bundle()
        mock_storage_cls.return_value.download.return_value = b"bundledata"

        out = tmp_path / ".env"
        resolved = pull(_make_config(), out)

        assert out.read_bytes() == b"KEY=value\n"
        assert resolved == "20240101T000000Z"

    @patch("envault.pull.S3Storage")
    @patch("envault.pull.decrypt", return_value=b"KEY=value\n")
    @patch("envault.pull.decode_bundle")
    @patch("envault.pull.load_keypair")
    def test_explicit_version_skips_latest_lookup(
        self, mock_load, mock_decode, mock_decrypt, mock_storage_cls, tmp_path
    ):
        mock_load.return_value = _make_keypair()
        mock_decode.return_value = _make_bundle()
        mock_storage_cls.return_value.download.return_value = b"bundledata"

        out = tmp_path / ".env"
        resolved = pull(_make_config(), out, version="20230101T000000Z")

        assert resolved == "20230101T000000Z"
        mock_storage_cls.return_value.download.assert_called_once_with("myapp", "20230101T000000Z")

    @patch("envault.pull.load_keypair", side_effect=Exception("no key"))
    def test_raises_pull_error_when_keypair_missing(self, _, tmp_path):
        with pytest.raises(PullError, match="Could not load keypair"):
            pull(_make_config(), tmp_path / ".env")

    @patch("envault.pull.S3Storage")
    @patch("envault.pull.latest_version", return_value=None)
    @patch("envault.pull.load_keypair")
    def test_raises_when_no_versions_exist(self, mock_load, _, mock_storage_cls, tmp_path):
        mock_load.return_value = _make_keypair()
        mock_storage_cls.return_value.download.return_value = b""

        with pytest.raises(PullError, match="No versions found"):
            pull(_make_config(), tmp_path / ".env")

    @patch("envault.pull.S3Storage")
    @patch("envault.pull.decrypt", side_effect=Exception("bad key"))
    @patch("envault.pull.decode_bundle")
    @patch("envault.pull.latest_version")
    @patch("envault.pull.load_keypair")
    def test_raises_on_decryption_failure(
        self, mock_load, mock_latest, mock_decode, mock_decrypt, mock_storage_cls, tmp_path
    ):
        mock_load.return_value = _make_keypair()
        mock_latest.return_value = EnvVersion("myapp", "20240101T000000Z")
        mock_decode.return_value = _make_bundle()
        mock_storage_cls.return_value.download.return_value = b"bundledata"

        with pytest.raises(PullError, match="Decryption failed"):
            pull(_make_config(), tmp_path / ".env")
