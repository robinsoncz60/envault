"""Tests for envault.tags."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from envault.storage import StorageError
from envault.tags import (
    Tag,
    TagError,
    delete_tag,
    get_tag,
    list_tags,
    set_tag,
)

_TAG_KEY = ".envault/tags.json"


def _make_storage(index: dict | None = None) -> MagicMock:
    storage = MagicMock()
    if index is None:
        storage.download.side_effect = StorageError("not found")
    else:
        storage.download.return_value = json.dumps(index).encode()
    storage.upload.return_value = _TAG_KEY
    return storage


class TestTag:
    def test_to_dict_roundtrip(self):
        tag = Tag(name="stable", version_key="env/v1.json", message="first release")
        assert Tag.from_dict(tag.to_dict()) == tag

    def test_from_dict_missing_key_raises(self):
        with pytest.raises(TagError, match="Missing field"):
            Tag.from_dict({"name": "oops"})

    def test_str_with_message(self):
        tag = Tag(name="stable", version_key="env/v1.json", message="prod")
        assert "stable" in str(tag)
        assert "prod" in str(tag)

    def test_str_without_message(self):
        tag = Tag(name="stable", version_key="env/v1.json")
        result = str(tag)
        assert "stable" in result
        assert "—" not in result


class TestSetTag:
    def test_creates_new_tag(self):
        storage = _make_storage()
        tag = set_tag(storage, "stable", "env/v1.json", message="first")
        assert tag.name == "stable"
        assert tag.version_key == "env/v1.json"
        storage.upload.assert_called_once()

    def test_overwrites_existing_tag(self):
        existing = {"stable": {"name": "stable", "version_key": "env/v0.json", "message": None}}
        storage = _make_storage(existing)
        tag = set_tag(storage, "stable", "env/v1.json")
        assert tag.version_key == "env/v1.json"
        uploaded_payload = json.loads(storage.upload.call_args[0][1].decode())
        assert uploaded_payload["stable"]["version_key"] == "env/v1.json"

    def test_raises_on_upload_failure(self):
        storage = _make_storage()
        storage.upload.side_effect = StorageError("s3 down")
        with pytest.raises(TagError, match="Failed to save"):
            set_tag(storage, "stable", "env/v1.json")


class TestGetTag:
    def test_returns_existing_tag(self):
        index = {"stable": {"name": "stable", "version_key": "env/v1.json", "message": None}}
        storage = _make_storage(index)
        tag = get_tag(storage, "stable")
        assert tag.name == "stable"

    def test_raises_when_tag_missing(self):
        storage = _make_storage({})
        with pytest.raises(TagError, match="Tag not found"):
            get_tag(storage, "nonexistent")


class TestDeleteTag:
    def test_removes_tag_from_index(self):
        index = {"stable": {"name": "stable", "version_key": "env/v1.json", "message": None}}
        storage = _make_storage(index)
        delete_tag(storage, "stable")
        uploaded_payload = json.loads(storage.upload.call_args[0][1].decode())
        assert "stable" not in uploaded_payload

    def test_raises_when_tag_missing(self):
        storage = _make_storage({})
        with pytest.raises(TagError, match="Tag not found"):
            delete_tag(storage, "ghost")


class TestListTags:
    def test_returns_sorted_tags(self):
        index = {
            "zeta": {"name": "zeta", "version_key": "env/v3.json", "message": None},
            "alpha": {"name": "alpha", "version_key": "env/v1.json", "message": None},
        }
        storage = _make_storage(index)
        tags = list_tags(storage)
        assert [t.name for t in tags] == ["alpha", "zeta"]

    def test_returns_empty_list_when_no_index(self):
        storage = _make_storage(None)
        assert list_tags(storage) == []
