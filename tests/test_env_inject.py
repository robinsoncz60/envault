"""Tests for envault.env_inject."""
from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from envault.env_inject import InjectError, InjectResult, _parse_env, inject


# ---------------------------------------------------------------------------
# _parse_env
# ---------------------------------------------------------------------------

def test_parse_env_basic():
    text = "FOO=bar\nBAZ=qux\n"
    assert _parse_env(text) == {"FOO": "bar", "BAZ": "qux"}


def test_parse_env_ignores_comments_and_blanks():
    text = "# comment\n\nKEY=val\n"
    assert _parse_env(text) == {"KEY": "val"}


def test_parse_env_handles_value_with_equals():
    text = "URL=http://x.com?a=1&b=2\n"
    assert _parse_env(text) == {"URL": "http://x.com?a=1&b=2"}


def test_parse_env_skips_lines_without_equals():
    text = "NOEQUALS\nGOOD=yes\n"
    assert _parse_env(text) == {"GOOD": "yes"}


# ---------------------------------------------------------------------------
# InjectResult
# ---------------------------------------------------------------------------

def test_inject_result_fields():
    r = InjectResult(command=["echo"], returncode=0, injected_keys=["A", "B"])
    assert r.command == ["echo"]
    assert r.returncode == 0
    assert r.injected_keys == ["A", "B"]


# ---------------------------------------------------------------------------
# inject()
# ---------------------------------------------------------------------------

def _make_completed(returncode: int = 0):
    m = MagicMock()
    m.returncode = returncode
    return m


def _fake_decrypt(ciphertext, private_key_path):
    return b"FOO=bar\nBAZ=qux\n"


@patch("envault.env_inject.subprocess.run")
@patch("envault.env_inject.decrypt", side_effect=_fake_decrypt)
def test_inject_runs_command(mock_decrypt, mock_run):
    mock_run.return_value = _make_completed(0)
    result = inject(
        command=["echo", "hello"],
        ciphertext=b"enc",
        private_key_path="/key",
    )
    assert result.returncode == 0
    assert set(result.injected_keys) == {"FOO", "BAZ"}
    mock_run.assert_called_once()


@patch("envault.env_inject.subprocess.run")
@patch("envault.env_inject.decrypt", side_effect=_fake_decrypt)
def test_inject_passes_env_to_subprocess(mock_decrypt, mock_run):
    mock_run.return_value = _make_completed(0)
    inject(command=["true"], ciphertext=b"enc", private_key_path="/key")
    _, kwargs = mock_run.call_args
    env = kwargs.get("env") or mock_run.call_args[1].get("env") or mock_run.call_args[0][1] if len(mock_run.call_args[0]) > 1 else mock_run.call_args[1]["env"]
    # env is passed as keyword argument
    call_env = mock_run.call_args.kwargs.get("env") or mock_run.call_args[1].get("env")
    assert call_env is not None
    assert call_env["FOO"] == "bar"


@patch("envault.env_inject.subprocess.run")
@patch("envault.env_inject.decrypt", side_effect=_fake_decrypt)
def test_inject_extra_env_merged(mock_decrypt, mock_run):
    mock_run.return_value = _make_completed(0)
    result = inject(
        command=["true"],
        ciphertext=b"enc",
        private_key_path="/key",
        extra_env={"EXTRA": "value"},
    )
    assert "EXTRA" in result.injected_keys


@patch("envault.env_inject.decrypt", side_effect=RuntimeError("bad decrypt"))
def test_inject_raises_on_decrypt_failure(mock_decrypt):
    with pytest.raises(InjectError, match="decryption failed"):
        inject(command=["echo"], ciphertext=b"bad", private_key_path="/key")


def test_inject_raises_on_empty_command():
    with pytest.raises(InjectError, match="must not be empty"):
        inject(command=[], ciphertext=b"enc", private_key_path="/key")


@patch("envault.env_inject.decrypt", side_effect=_fake_decrypt)
@patch("envault.env_inject.subprocess.run", side_effect=FileNotFoundError)
def test_inject_raises_when_command_not_found(mock_run, mock_decrypt):
    with pytest.raises(InjectError, match="command not found"):
        inject(command=["no-such-cmd"], ciphertext=b"enc", private_key_path="/key")
