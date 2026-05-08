"""Tests for envault.env_rename."""
from __future__ import annotations

import base64
import json
from unittest.mock import MagicMock, patch

import pytest

from envault.bundle import EnvBundle
from envault.config import EnvaultConfig
from envault.env_rename import RenameError, RenameResult, _parse_env, _render_env, rename_key
from envault.keystore import KeyPair


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_config() -> EnvaultConfig:
    return EnvaultConfig(
        env="prod",
        bucket="my-bucket",
        region="us-east-1",
        public_key="age1pub",
    )


def _make_storage(bundle_bytes: bytes) -> MagicMock:
    s = MagicMock()
    s.download.return_value = bundle_bytes
    return s


def _make_keypair() -> KeyPair:
    return KeyPair(public_key="age1pub", private_key="AGE-SECRET-KEY-1")


def _bundle_bytes(plaintext: str) -> bytes:
    ct = base64.b64encode(plaintext.encode()).decode()
    b = EnvBundle(ciphertext=ct, recipients=["age1pub"], version="v1")
    return json.dumps(b.to_dict()).encode()


# ---------------------------------------------------------------------------
# _parse_env / _render_env
# ---------------------------------------------------------------------------

def test_parse_env_basic():
    assert _parse_env("A=1\nB=2\n") == {"A": "1", "B": "2"}


def test_parse_env_skips_comments_and_blanks():
    text = "# comment\n\nA=hello\n"
    assert _parse_env(text) == {"A": "hello"}


def test_render_env_produces_lines():
    result = _render_env({"X": "1", "Y": "2"})
    assert "X=1" in result
    assert "Y=2" in result


# ---------------------------------------------------------------------------
# RenameResult
# ---------------------------------------------------------------------------

def test_rename_result_str():
    r = RenameResult(old_key="OLD", new_key="NEW", s3_key="prod/abc.json")
    assert "OLD" in str(r)
    assert "NEW" in str(r)
    assert "prod/abc.json" in str(r)


# ---------------------------------------------------------------------------
# rename_key
# ---------------------------------------------------------------------------

def _do_rename(old_key="DB_HOST", new_key="DATABASE_HOST", version=None, extra_pairs=None):
    pairs = {"DB_HOST": "localhost", "PORT": "5432"}
    if extra_pairs:
        pairs.update(extra_pairs)
    plaintext = "\n".join(f"{k}={v}" for k, v in pairs.items()) + "\n"
    storage = _make_storage(_bundle_bytes(plaintext))
    config = _make_config()
    keypair = _make_keypair()

    with patch("envault.env_rename.latest_version", return_value="prod/v1.json"), \
         patch("envault.env_rename.decrypt", side_effect=lambda ct, _pk: ct.decode()), \
         patch("envault.env_rename.push", return_value="prod/v2.json") as mock_push:
        result = rename_key(config, storage, keypair, old_key, new_key, version=version)
        return result, mock_push


def test_success_returns_rename_result():
    result, _ = _do_rename()
    assert isinstance(result, RenameResult)
    assert result.old_key == "DB_HOST"
    assert result.new_key == "DATABASE_HOST"
    assert result.s3_key == "prod/v2.json"


def test_push_called_with_renamed_plaintext():
    _, mock_push = _do_rename()
    assert mock_push.called
    pushed_plaintext = mock_push.call_args.kwargs["plaintext"]
    assert "DATABASE_HOST=localhost" in pushed_plaintext
    assert "DB_HOST" not in pushed_plaintext


def test_raises_when_old_key_missing():
    with pytest.raises(RenameError, match="not found"):
        _do_rename(old_key="NONEXISTENT", new_key="WHATEVER")


def test_raises_when_new_key_already_exists():
    with pytest.raises(RenameError, match="already exists"):
        _do_rename(old_key="DB_HOST", new_key="PORT")


def test_raises_when_keys_are_same():
    with pytest.raises(RenameError, match="same"):
        _do_rename(old_key="DB_HOST", new_key="DB_HOST")


def test_raises_when_no_versions():
    config = _make_config()
    storage = MagicMock()
    keypair = _make_keypair()
    with patch("envault.env_rename.latest_version", return_value=None):
        with pytest.raises(RenameError, match="No versions"):
            rename_key(config, storage, keypair, "A", "B")
