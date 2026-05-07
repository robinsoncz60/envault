"""Tests for envault.env_diff_report."""

import pytest
from envault.env_diff_report import (
    DiffReport,
    DiffReportEntry,
    DiffReportError,
    _parse_env,
    build_report,
)


# --- _parse_env ---

def test_parse_env_basic():
    result = _parse_env("FOO=bar\nBAZ=qux\n")
    assert result == {"FOO": "bar", "BAZ": "qux"}


def test_parse_env_ignores_comments_and_blanks():
    text = "# comment\n\nFOO=bar\n"
    assert _parse_env(text) == {"FOO": "bar"}


def test_parse_env_handles_value_with_equals():
    result = _parse_env("URL=http://x.com?a=1")
    assert result["URL"] == "http://x.com?a=1"


def test_parse_env_skips_lines_without_equals():
    result = _parse_env("NOEQUALS\nFOO=bar")
    assert "NOEQUALS" not in result
    assert result["FOO"] == "bar"


# --- DiffReportEntry.__str__ ---

def test_entry_str_added():
    e = DiffReportEntry(key="X", status="added", new_value="1")
    assert str(e) == "+ X=1"


def test_entry_str_removed():
    e = DiffReportEntry(key="X", status="removed", old_value="1")
    assert str(e) == "- X=1"


def test_entry_str_changed():
    e = DiffReportEntry(key="X", status="changed", old_value="a", new_value="b")
    assert "~" in str(e)
    assert "a" in str(e)
    assert "b" in str(e)


def test_entry_str_unchanged():
    e = DiffReportEntry(key="X", status="unchanged", new_value="v")
    assert str(e).startswith("  ")


# --- build_report ---

OLD_ENV = "FOO=old\nBAR=same\nGONE=bye\n"
NEW_ENV = "FOO=new\nBAR=same\nFRESH=hello\n"


@pytest.fixture
def report():
    return build_report("v1", "v2", OLD_ENV, NEW_ENV)


def test_report_from_to_versions(report):
    assert report.from_version == "v1"
    assert report.to_version == "v2"


def test_report_detects_added(report):
    keys = [e.key for e in report.added]
    assert "FRESH" in keys


def test_report_detects_removed(report):
    keys = [e.key for e in report.removed]
    assert "GONE" in keys


def test_report_detects_changed(report):
    keys = [e.key for e in report.changed]
    assert "FOO" in keys


def test_report_unchanged_not_in_changed(report):
    keys = [e.key for e in report.changed]
    assert "BAR" not in keys


def test_report_has_changes_true(report):
    assert report.has_changes is True


def test_report_has_changes_false():
    r = build_report("v1", "v2", "A=1\n", "A=1\n")
    assert r.has_changes is False


def test_report_str_contains_versions(report):
    s = str(report)
    assert "v1" in s
    assert "v2" in s


def test_report_str_omits_unchanged(report):
    s = str(report)
    # BAR is unchanged, should not appear in the diff lines
    assert "BAR" not in s


def test_empty_envs_produce_no_changes():
    r = build_report("a", "b", "", "")
    assert not r.has_changes
    assert r.entries == []
