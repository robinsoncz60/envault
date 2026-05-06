"""Tests for envault.snapshot."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from envault.snapshot import (
    Snapshot,
    SnapshotError,
    list_snapshots,
    load_snapshot,
    save_snapshot,
)
from envault.storage import StorageError


def _make_storage(keys=None, data=None):
    storage = MagicMock()
    storage.list.return_value = keys or []
    storage.download.return_value = json.dumps(data).encode() if data else b"{}"
    storage.upload.return_value = None
    return storage


def _make_snapshot(**kwargs):
    defaults = {"name": "v1-stable", "s3_key": "envs/prod/20240101.bundle", "created_by": "alice"}
    defaults.update(kwargs)
    return Snapshot(**defaults)


class TestSnapshot:
    def test_to_dict_roundtrip(self):
        snap = _make_snapshot(note="initial release")
        assert Snapshot.from_dict(snap.to_dict()) == snap

    def test_from_dict_missing_key_raises(self):
        with pytest.raises(SnapshotError, match="Missing snapshot field"):
            Snapshot.from_dict({"name": "x"})

    def test_str_includes_name_and_key(self):
        snap = _make_snapshot()
        result = str(snap)
        assert "v1-stable" in result
        assert "20240101.bundle" in result

    def test_str_includes_note_when_present(self):
        snap = _make_snapshot(note="hotfix")
        assert "hotfix" in str(snap)

    def test_str_omits_note_when_empty(self):
        snap = _make_snapshot(note="")
        assert "—" not in str(snap)


class TestSaveSnapshot:
    def test_returns_s3_key(self):
        storage = _make_storage()
        snap = _make_snapshot()
        key = save_snapshot(storage, "prod", snap)
        assert key == "snapshots/prod/v1-stable.json"

    def test_calls_upload_with_json_payload(self):
        storage = _make_storage()
        snap = _make_snapshot()
        save_snapshot(storage, "prod", snap)
        storage.upload.assert_called_once()
        _, payload = storage.upload.call_args[0]
        parsed = json.loads(payload)
        assert parsed["name"] == "v1-stable"

    def test_raises_on_storage_error(self):
        storage = _make_storage()
        storage.upload.side_effect = StorageError("connection refused")
        with pytest.raises(SnapshotError, match="Failed to save snapshot"):
            save_snapshot(storage, "prod", _make_snapshot())


class TestLoadSnapshot:
    def test_returns_snapshot(self):
        snap = _make_snapshot()
        storage = _make_storage(data=snap.to_dict())
        result = load_snapshot(storage, "prod", "v1-stable")
        assert result == snap

    def test_raises_when_not_found(self):
        storage = _make_storage()
        storage.download.side_effect = StorageError("not found")
        with pytest.raises(SnapshotError, match="not found"):
            load_snapshot(storage, "prod", "missing")

    def test_raises_on_corrupt_json(self):
        storage = _make_storage()
        storage.download.return_value = b"not-json"
        with pytest.raises(SnapshotError, match="Corrupt snapshot data"):
            load_snapshot(storage, "prod", "broken")


class TestListSnapshots:
    def test_returns_empty_list_when_no_objects(self):
        storage = _make_storage(keys=[])
        assert list_snapshots(storage, "prod") == []

    def test_returns_snapshots_sorted_by_name(self):
        snaps = [_make_snapshot(name="z-snap"), _make_snapshot(name="a-snap")]
        storage = MagicMock()
        storage.list.return_value = ["snapshots/prod/z-snap.json", "snapshots/prod/a-snap.json"]
        storage.download.side_effect = [
            json.dumps(snaps[0].to_dict()).encode(),
            json.dumps(snaps[1].to_dict()).encode(),
        ]
        result = list_snapshots(storage, "prod")
        assert [s.name for s in result] == ["a-snap", "z-snap"]

    def test_skips_corrupt_entries(self):
        storage = MagicMock()
        storage.list.return_value = ["snapshots/prod/bad.json"]
        storage.download.return_value = b"bad-json"
        result = list_snapshots(storage, "prod")
        assert result == []

    def test_raises_on_list_storage_error(self):
        storage = _make_storage()
        storage.list.side_effect = StorageError("forbidden")
        with pytest.raises(SnapshotError, match="Failed to list snapshots"):
            list_snapshots(storage, "prod")
