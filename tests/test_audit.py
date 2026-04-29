"""Tests for envault.audit."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from envault.audit import AuditEntry, AuditError, record, read_log


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _fake_login() -> str:
    return "testuser"


# ---------------------------------------------------------------------------
# AuditEntry
# ---------------------------------------------------------------------------


class TestAuditEntry:
    def test_to_dict_roundtrip(self):
        entry = AuditEntry(
            action="push",
            env="staging",
            version="20240101T000000Z",
            user="alice",
            timestamp="2024-01-01T00:00:00+00:00",
        )
        assert AuditEntry.from_dict(entry.to_dict()) == entry

    def test_str_contains_fields(self):
        entry = AuditEntry(
            action="pull",
            env="prod",
            version="v1",
            user="bob",
            timestamp="2024-06-01T12:00:00+00:00",
        )
        s = str(entry)
        assert "pull" in s
        assert "prod" in s
        assert "v1" in s
        assert "bob" in s

    def test_from_dict_missing_key_raises(self):
        with pytest.raises(TypeError):
            AuditEntry.from_dict({"action": "push"})


# ---------------------------------------------------------------------------
# record()
# ---------------------------------------------------------------------------


class TestRecord:
    def test_creates_log_file(self, tmp_path):
        log_file = tmp_path / "sub" / "audit.log"
        with patch("os.getlogin", return_value="testuser"):
            record("push", "production", "20240101T000000Z", log_file=log_file)
        assert log_file.exists()

    def test_appends_json_line(self, tmp_path):
        log_file = tmp_path / "audit.log"
        with patch("os.getlogin", return_value="testuser"):
            record("push", "production", "v1", log_file=log_file)
            record("pull", "staging", "v2", log_file=log_file)
        lines = log_file.read_text().strip().splitlines()
        assert len(lines) == 2
        data = json.loads(lines[0])
        assert data["action"] == "push"
        assert data["env"] == "production"

    def test_returns_audit_entry(self, tmp_path):
        log_file = tmp_path / "audit.log"
        with patch("os.getlogin", return_value="ci"):
            entry = record("pull", "dev", "abc", log_file=log_file)
        assert isinstance(entry, AuditEntry)
        assert entry.user == "ci"

    def test_raises_audit_error_on_write_failure(self, tmp_path):
        log_file = tmp_path / "audit.log"
        log_file.mkdir()  # make it a directory so open() fails
        with patch("os.getlogin", return_value="x"):
            with pytest.raises(AuditError):
                record("push", "env", "v1", log_file=log_file)


# ---------------------------------------------------------------------------
# read_log()
# ---------------------------------------------------------------------------


class TestReadLog:
    def test_returns_empty_list_when_no_file(self, tmp_path):
        assert read_log(log_file=tmp_path / "missing.log") == []

    def test_returns_entries_in_order(self, tmp_path):
        log_file = tmp_path / "audit.log"
        with patch("os.getlogin", return_value="u"):
            record("push", "a", "v1", log_file=log_file)
            record("pull", "b", "v2", log_file=log_file)
        entries = read_log(log_file=log_file)
        assert len(entries) == 2
        assert entries[0].action == "push"
        assert entries[1].action == "pull"

    def test_raises_on_corrupt_line(self, tmp_path):
        log_file = tmp_path / "audit.log"
        log_file.write_text("not-json\n")
        with pytest.raises(AuditError):
            read_log(log_file=log_file)
