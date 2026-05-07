"""Tests for envault.env_lint."""

from pathlib import Path

import pytest

from envault.env_lint import LintError, LintIssue, LintResult, lint, lint_file


# ---------------------------------------------------------------------------
# LintResult helpers
# ---------------------------------------------------------------------------

def test_lint_result_ok_when_no_issues():
    result = LintResult()
    assert result.ok is True


def test_lint_result_not_ok_when_issues_present():
    result = LintResult(issues=[LintIssue(1, "FOO", "W001", "dup")])
    assert result.ok is False


def test_lint_result_str_no_issues():
    assert str(LintResult()) == "No issues found."


def test_lint_issue_str():
    issue = LintIssue(3, "MY_KEY", "W002", "Empty value")
    s = str(issue)
    assert "line 3" in s
    assert "W002" in s
    assert "MY_KEY" in s


# ---------------------------------------------------------------------------
# lint() — clean input
# ---------------------------------------------------------------------------

def test_clean_env_returns_no_issues():
    src = "DB_HOST=localhost\nDB_PORT=5432\nAPP_NAME=myapp\n"
    result = lint(src)
    assert result.ok


def test_ignores_comments_and_blank_lines():
    src = "# This is a comment\n\nFOO=bar\n"
    result = lint(src)
    assert result.ok


# ---------------------------------------------------------------------------
# lint() — E001 / E002
# ---------------------------------------------------------------------------

def test_e001_invalid_line():
    result = lint("NOTAVALIDLINE\n")
    codes = [i.code for i in result.issues]
    assert "E001" in codes


def test_e002_empty_key():
    result = lint("=somevalue\n")
    codes = [i.code for i in result.issues]
    assert "E002" in codes


# ---------------------------------------------------------------------------
# lint() — W001 duplicate keys
# ---------------------------------------------------------------------------

def test_w001_duplicate_key():
    src = "FOO=bar\nFOO=baz\n"
    result = lint(src)
    codes = [i.code for i in result.issues]
    assert "W001" in codes


def test_no_duplicate_when_keys_differ():
    src = "FOO=bar\nFOO2=baz\n"
    result = lint(src)
    assert result.ok


# ---------------------------------------------------------------------------
# lint() — W002 empty value
# ---------------------------------------------------------------------------

def test_w002_empty_value():
    result = lint("MY_VAR=\n")
    codes = [i.code for i in result.issues]
    assert "W002" in codes


# ---------------------------------------------------------------------------
# lint() — W003 placeholder sensitive value
# ---------------------------------------------------------------------------

def test_w003_sensitive_placeholder():
    result = lint("API_KEY=changeme\n")
    codes = [i.code for i in result.issues]
    assert "W003" in codes


def test_w003_not_raised_for_real_looking_value():
    result = lint("API_KEY=ak_live_abc123xyz\n")
    assert result.ok


# ---------------------------------------------------------------------------
# lint() — W004 unmatched quote
# ---------------------------------------------------------------------------

def test_w004_unmatched_single_quote():
    result = lint("FOO='bar\n")
    codes = [i.code for i in result.issues]
    assert "W004" in codes


def test_no_w004_for_matched_quotes():
    result = lint('FOO="bar"\n')
    assert result.ok


# ---------------------------------------------------------------------------
# lint_file()
# ---------------------------------------------------------------------------

def test_lint_file_reads_and_lints(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text("DB=postgres\nSECRET=changeme\n", encoding="utf-8")
    result = lint_file(env_file)
    codes = [i.code for i in result.issues]
    assert "W003" in codes


def test_lint_file_raises_lint_error_on_missing_file(tmp_path: Path):
    with pytest.raises(LintError, match="Cannot read"):
        lint_file(tmp_path / "nonexistent.env")
