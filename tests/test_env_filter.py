"""Tests for envault.env_filter."""

import pytest

from envault.env_filter import FilterError, FilterResult, filter_env, _parse_env


# ---------------------------------------------------------------------------
# _parse_env helpers
# ---------------------------------------------------------------------------

def test_parse_env_basic():
    text = "FOO=bar\nBAZ=qux\n"
    assert _parse_env(text) == {"FOO": "bar", "BAZ": "qux"}


def test_parse_env_ignores_comments_and_blanks():
    text = "# comment\n\nFOO=bar\n"
    assert _parse_env(text) == {"FOO": "bar"}


def test_parse_env_handles_value_with_equals():
    text = "URL=http://example.com?a=1\n"
    assert _parse_env(text) == {"URL": "http://example.com?a=1"}


def test_parse_env_skips_lines_without_equals():
    text = "NOEQUALS\nFOO=bar\n"
    assert _parse_env(text) == {"FOO": "bar"}


# ---------------------------------------------------------------------------
# filter_env — error cases
# ---------------------------------------------------------------------------

def test_raises_when_no_filter_criteria_given():
    with pytest.raises(FilterError, match="At least one"):
        filter_env("FOO=bar\n")


# ---------------------------------------------------------------------------
# filter_env — prefix filtering
# ---------------------------------------------------------------------------

def test_prefix_filter_matches_correct_keys():
    text = "AWS_KEY=abc\nAWS_SECRET=xyz\nDB_HOST=localhost\n"
    result = filter_env(text, prefixes=["AWS_"])
    assert result.matched == {"AWS_KEY": "abc", "AWS_SECRET": "xyz"}
    assert result.excluded == {"DB_HOST": "localhost"}


def test_multiple_prefixes_union():
    text = "AWS_KEY=a\nGCP_KEY=b\nDB_HOST=c\n"
    result = filter_env(text, prefixes=["AWS_", "GCP_"])
    assert set(result.matched) == {"AWS_KEY", "GCP_KEY"}
    assert set(result.excluded) == {"DB_HOST"}


# ---------------------------------------------------------------------------
# filter_env — pattern filtering
# ---------------------------------------------------------------------------

def test_glob_pattern_filter():
    text = "SECRET_KEY=s\nSECRET_TOKEN=t\nPUBLIC_URL=u\n"
    result = filter_env(text, patterns=["SECRET_*"])
    assert set(result.matched) == {"SECRET_KEY", "SECRET_TOKEN"}
    assert result.excluded == {"PUBLIC_URL": "u"}


# ---------------------------------------------------------------------------
# filter_env — explicit key list
# ---------------------------------------------------------------------------

def test_explicit_keys_filter():
    text = "FOO=1\nBAR=2\nBAZ=3\n"
    result = filter_env(text, keys=["FOO", "BAZ"])
    assert result.matched == {"FOO": "1", "BAZ": "3"}
    assert result.excluded == {"BAR": "2"}


# ---------------------------------------------------------------------------
# filter_env — invert flag
# ---------------------------------------------------------------------------

def test_invert_flips_matched_and_excluded():
    text = "AWS_KEY=a\nDB_HOST=b\n"
    result = filter_env(text, prefixes=["AWS_"], invert=True)
    assert result.matched == {"DB_HOST": "b"}
    assert result.excluded == {"AWS_KEY": "a"}


# ---------------------------------------------------------------------------
# FilterResult.__str__
# ---------------------------------------------------------------------------

def test_filter_result_str():
    r = FilterResult(matched={"A": "1"}, excluded={"B": "2", "C": "3"})
    s = str(r)
    assert "matched=1" in s
    assert "excluded=2" in s
