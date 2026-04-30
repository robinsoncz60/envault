"""Tests for envault.diff."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from envault.diff import DiffError, DiffResult, _parse_env, diff_versions
from envault.versioning import EnvVersion


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_version(tag: str) -> EnvVersion:
    return EnvVersion(tag=tag, s3_key=f"envs/default/{tag}.bundle", timestamp="2024-01-01T00:00:00Z")


def _make_storage(payloads: dict) -> MagicMock:
    storage = MagicMock()
    storage.download.side_effect = lambda key: payloads[key]
    return storage


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
    text = "URL=http://x.com?a=1\n"
    assert _parse_env(text) == {"URL": "http://x.com?a=1"}


# ---------------------------------------------------------------------------
# DiffResult
# ---------------------------------------------------------------------------

def test_diff_result_has_changes_true():
    dr = DiffResult(added=["A"], removed=[], changed=[], unchanged=[])
    assert dr.has_changes() is True


def test_diff_result_has_changes_false():
    dr = DiffResult(added=[], removed=[], changed=[], unchanged=["X"])
    assert dr.has_changes() is False


def test_diff_result_str_no_changes():
    dr = DiffResult(added=[], removed=[], changed=[], unchanged=["X"])
    assert str(dr) == "(no changes)"


def test_diff_result_str_shows_symbols():
    dr = DiffResult(added=["NEW"], removed=["OLD"], changed=["MOD"], unchanged=[])
    text = str(dr)
    assert "+ NEW" in text
    assert "- OLD" in text
    assert "~ MOD" in text


# ---------------------------------------------------------------------------
# diff_versions
# ---------------------------------------------------------------------------

def _setup_diff_patch(old_env: dict, new_env: dict):
    """Patch _decrypt_version to return pre-built dicts."""
    call_count = {"n": 0}
    results = [old_env, new_env]

    def fake_decrypt(storage, version, private_key):
        idx = call_count["n"]
        call_count["n"] += 1
        return results[idx]

    return fake_decrypt


def test_diff_detects_added_keys():
    with patch("envault.diff._decrypt_version", _setup_diff_patch({"A": "1"}, {"A": "1", "B": "2"})):
        result = diff_versions(MagicMock(), _make_version("v1"), _make_version("v2"), "key")
    assert result.added == ["B"]
    assert result.removed == []


def test_diff_detects_removed_keys():
    with patch("envault.diff._decrypt_version", _setup_diff_patch({"A": "1", "B": "2"}, {"A": "1"})):
        result = diff_versions(MagicMock(), _make_version("v1"), _make_version("v2"), "key")
    assert result.removed == ["B"]


def test_diff_detects_changed_keys():
    with patch("envault.diff._decrypt_version", _setup_diff_patch({"A": "old"}, {"A": "new"})):
        result = diff_versions(MagicMock(), _make_version("v1"), _make_version("v2"), "key")
    assert result.changed == ["A"]
    assert result.unchanged == []


def test_diff_raises_on_download_error():
    storage = MagicMock()
    storage.download.side_effect = RuntimeError("network")
    with pytest.raises(DiffError, match="Failed to download"):
        diff_versions(storage, _make_version("v1"), _make_version("v2"), "key")
