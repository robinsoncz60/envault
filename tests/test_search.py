"""Tests for envault.search."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from envault.search import SearchError, SearchMatch, _parse_env, search
from envault.versioning import EnvVersion


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_version(tag: str) -> EnvVersion:
    v = MagicMock(spec=EnvVersion)
    v.s3_key = f"envault/default/{tag}.bundle"
    v.__str__ = lambda self: tag  # noqa: ARG005
    return v


def _make_storage(versions, bundle_bytes: bytes = b"{}"):
    storage = MagicMock()
    storage.download.return_value = bundle_bytes
    with patch("envault.search.list_versions", return_value=versions):
        yield storage


# ---------------------------------------------------------------------------
# _parse_env
# ---------------------------------------------------------------------------

def test_parse_env_basic():
    result = _parse_env("FOO=bar\nBAZ=qux")
    assert result == {"FOO": "bar", "BAZ": "qux"}


def test_parse_env_ignores_comments():
    result = _parse_env("# comment\nFOO=bar")
    assert "# comment" not in result
    assert result["FOO"] == "bar"


def test_parse_env_handles_value_with_equals():
    result = _parse_env("URL=http://x.com?a=1")
    assert result["URL"] == "http://x.com?a=1"


def test_parse_env_skips_blank_lines():
    result = _parse_env("\n\nFOO=1\n")
    assert list(result.keys()) == ["FOO"]


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------

def _run_search(versions, plaintext: str, query: str, **kwargs):
    storage = MagicMock()
    storage.download.return_value = b"bundle-bytes"

    fake_bundle = MagicMock()
    fake_bundle.ciphertext = b"ct"

    with patch("envault.search.list_versions", return_value=versions), \
         patch("envault.search.decode_bundle", return_value=fake_bundle), \
         patch("envault.search.decrypt", return_value=plaintext):
        return search(storage, "/fake/key.txt", query, **kwargs)


def test_returns_empty_when_no_match():
    v = _make_version("v1")
    matches = _run_search([v], "FOO=bar", "NOTPRESENT")
    assert matches == []


def test_finds_key_match():
    v = _make_version("v1")
    matches = _run_search([v], "DATABASE_URL=postgres://localhost", "database")
    assert len(matches) == 1
    assert matches[0].key == "DATABASE_URL"


def test_finds_value_match_when_enabled():
    v = _make_version("v1")
    matches = _run_search([v], "FOO=supersecret", "supersecret",
                          search_keys=False, search_values=True)
    assert len(matches) == 1
    assert matches[0].value == "supersecret"


def test_no_search_target_raises():
    with pytest.raises(SearchError, match="At least one"):
        _run_search([], "", "q", search_keys=False, search_values=False)


def test_max_versions_limits_results():
    versions = [_make_version(f"v{i}") for i in range(5)]
    matches = _run_search(versions, "KEY=val", "KEY", max_versions=2)
    # only 2 versions inspected → at most 2 matches
    assert len(matches) <= 2


def test_search_match_str():
    v = _make_version("v42")
    m = SearchMatch(version=v, key="FOO", value="bar")
    assert "FOO" in str(m)
    assert "bar" in str(m)


def test_raises_search_error_on_decrypt_failure():
    storage = MagicMock()
    storage.download.return_value = b"bytes"
    v = _make_version("v1")

    with patch("envault.search.list_versions", return_value=[v]), \
         patch("envault.search.decode_bundle", side_effect=Exception("boom")):
        with pytest.raises(SearchError, match="Failed to inspect"):
            search(storage, "/key", "FOO")
