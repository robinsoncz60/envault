"""Tests for envault.push."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from envault.push import PushError, _make_version, push


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_config(environment: str = "staging") -> MagicMock:
    cfg = MagicMock()
    cfg.environment = environment
    return cfg


def _make_storage(s3_key: str = "staging/20240101T000000Z.bundle") -> MagicMock:
    storage = MagicMock()
    storage.upload.return_value = s3_key
    return storage


def _make_keypair(public_key: str = "age1abc") -> MagicMock:
    kp = MagicMock()
    kp.public_key = public_key
    return kp


# ---------------------------------------------------------------------------
# _make_version
# ---------------------------------------------------------------------------

def test_make_version_format():
    v = _make_version()
    assert len(v) == 16
    assert v.endswith("Z")
    assert "T" in v


# ---------------------------------------------------------------------------
# push
# ---------------------------------------------------------------------------

class TestPush:
    def test_returns_s3_key(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_bytes(b"KEY=value")

        with (
            patch("envault.push.load_keypair", return_value=_make_keypair()),
            patch("envault.push.encrypt", return_value=b"ciphertext"),
        ):
            storage = _make_storage("staging/v1.bundle")
            result = push(env_file, _make_config(), storage)

        assert result == "staging/v1.bundle"

    def test_calls_upload_with_payload_bytes(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_bytes(b"SECRET=1")

        storage = _make_storage()
        with (
            patch("envault.push.load_keypair", return_value=_make_keypair()),
            patch("envault.push.encrypt", return_value=b"enc"),
        ):
            push(env_file, _make_config(), storage)

        _env, _ver, payload = storage.upload.call_args[0]
        assert isinstance(payload, bytes)

    def test_raises_when_env_file_missing(self, tmp_path):
        with pytest.raises(PushError, match="not found"):
            push(tmp_path / "missing.env", _make_config(), _make_storage())

    def test_raises_when_keypair_load_fails(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_bytes(b"K=v")
        with (
            patch("envault.push.load_keypair", side_effect=RuntimeError("no key")),
            pytest.raises(PushError, match="Could not load keypair"),
        ):
            push(env_file, _make_config(), _make_storage())

    def test_raises_when_encrypt_fails(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_bytes(b"K=v")
        with (
            patch("envault.push.load_keypair", return_value=_make_keypair()),
            patch("envault.push.encrypt", side_effect=RuntimeError("age error")),
            pytest.raises(PushError, match="Encryption failed"),
        ):
            push(env_file, _make_config(), _make_storage())

    def test_raises_when_upload_fails(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_bytes(b"K=v")
        storage = _make_storage()
        storage.upload.side_effect = RuntimeError("S3 error")
        with (
            patch("envault.push.load_keypair", return_value=_make_keypair()),
            patch("envault.push.encrypt", return_value=b"enc"),
            pytest.raises(PushError, match="Upload failed"),
        ):
            push(env_file, _make_config(), storage)
