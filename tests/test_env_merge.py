"""Tests for envault.env_merge."""
import pytest

from envault.env_merge import (
    ConflictStrategy,
    MergeConflict,
    MergeError,
    MergeResult,
    _parse_env,
    _render_env,
    merge_envs,
)


# ---------------------------------------------------------------------------
# _parse_env
# ---------------------------------------------------------------------------

def test_parse_env_basic():
    result = _parse_env("FOO=bar\nBAZ=qux\n")
    assert result == {"FOO": "bar", "BAZ": "qux"}


def test_parse_env_ignores_comments_and_blanks():
    result = _parse_env("# comment\n\nFOO=bar")
    assert result == {"FOO": "bar"}


def test_parse_env_handles_value_with_equals():
    result = _parse_env("URL=http://x.com?a=1")
    assert result == {"URL": "http://x.com?a=1"}


def test_parse_env_skips_lines_without_equals():
    result = _parse_env("NOEQUALS\nFOO=bar")
    assert result == {"FOO": "bar"}


# ---------------------------------------------------------------------------
# _render_env
# ---------------------------------------------------------------------------

def test_render_env_produces_key_value_lines():
    out = _render_env({"A": "1", "B": "2"})
    assert "A=1" in out
    assert "B=2" in out
    assert out.endswith("\n")


# ---------------------------------------------------------------------------
# merge_envs — clean cases
# ---------------------------------------------------------------------------

def test_merge_adds_new_keys_from_incoming():
    result = merge_envs("A=1\n", "A=1\nB=2\n")
    assert "B=2" in result.merged
    assert result.added == ["B"]
    assert not result.has_conflicts


def test_merge_removes_keys_absent_in_incoming():
    result = merge_envs("A=1\nB=2\n", "A=1\n")
    assert "B" not in result.merged
    assert result.removed == ["B"]


def test_merge_clean_str_is_clean_merge():
    result = merge_envs("A=1\n", "A=1\n")
    assert str(result) == "Clean merge"


# ---------------------------------------------------------------------------
# merge_envs — conflict strategies
# ---------------------------------------------------------------------------

def test_conflict_strategy_theirs_takes_incoming_value():
    result = merge_envs("A=old\n", "A=new\n", strategy=ConflictStrategy.THEIRS)
    assert "A=new" in result.merged
    assert result.has_conflicts
    assert result.conflicts[0].key == "A"


def test_conflict_strategy_ours_keeps_base_value():
    result = merge_envs("A=old\n", "A=new\n", strategy=ConflictStrategy.OURS)
    assert "A=old" in result.merged
    assert result.has_conflicts


def test_conflict_strategy_error_raises_on_conflict():
    with pytest.raises(MergeError, match="Conflict on key"):
        merge_envs("A=old\n", "A=new\n", strategy=ConflictStrategy.ERROR)


# ---------------------------------------------------------------------------
# MergeResult.__str__
# ---------------------------------------------------------------------------

def test_str_shows_added_removed_conflicts():
    result = merge_envs("A=1\nB=old\n", "B=new\nC=3\n")
    summary = str(result)
    assert "Added" in summary
    assert "Removed" in summary
    assert "Conflicts" in summary


# ---------------------------------------------------------------------------
# MergeConflict.__str__
# ---------------------------------------------------------------------------

def test_conflict_str_contains_key_and_values():
    c = MergeConflict(key="X", base_value="a", incoming_value="b")
    s = str(c)
    assert "X" in s
    assert "a" in s
    assert "b" in s
