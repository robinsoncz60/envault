"""Tests for envault.versioning."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from envault.versioning import (
    EnvVersion,
    VersioningError,
    list_versions,
    latest_version,
    next_version_id,
)


def _make_storage(bucket: str = "my-bucket", prefix: str = "envault") -> MagicMock:
    storage = MagicMock()
    storage.bucket = bucket
    storage._key = lambda name, vid: f"{prefix}/{name}/{vid}"
    return storage


def _make_s3_object(key: str, size: int = 100, etag: str = '"abc"') -> dict:
    return {
        "Key": key,
        "LastModified": datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        "Size": size,
        "ETag": etag,
    }


class TestListVersions:
    def test_returns_empty_list_when_no_objects(self):
        storage = _make_storage()
        paginator = MagicMock()
        paginator.paginate.return_value = [{"Contents": []}]
        storage.client.get_paginator.return_value = paginator

        result = list_versions(storage, "production")
        assert result == []

    def test_returns_versions_sorted_newest_first(self):
        storage = _make_storage()
        paginator = MagicMock()
        paginator.paginate.return_value = [
            {
                "Contents": [
                    _make_s3_object("envault/production/0001.age", size=200),
                    _make_s3_object("envault/production/0003.age", size=220),
                    _make_s3_object("envault/production/0002.age", size=210),
                ]
            }
        ]
        storage.client.get_paginator.return_value = paginator

        result = list_versions(storage, "production")
        assert [v.version_id for v in result] == ["0003", "0002", "0001"]

    def test_skips_keys_without_version_pattern(self):
        storage = _make_storage()
        paginator = MagicMock()
        paginator.paginate.return_value = [
            {
                "Contents": [
                    _make_s3_object("envault/production/0001.age"),
                    _make_s3_object("envault/production/meta.json"),
                ]
            }
        ]
        storage.client.get_paginator.return_value = paginator

        result = list_versions(storage, "production")
        assert len(result) == 1
        assert result[0].version_id == "0001"

    def test_strips_etag_quotes(self):
        storage = _make_storage()
        paginator = MagicMock()
        paginator.paginate.return_value = [
            {"Contents": [_make_s3_object("envault/production/0001.age", etag='"deadbeef"')]}
        ]
        storage.client.get_paginator.return_value = paginator

        result = list_versions(storage, "production")
        assert result[0].etag == "deadbeef"


class TestLatestVersion:
    def test_returns_none_when_no_versions(self):
        storage = _make_storage()
        paginator = MagicMock()
        paginator.paginate.return_value = [{}]
        storage.client.get_paginator.return_value = paginator

        assert latest_version(storage, "staging") is None

    def test_returns_highest_version(self):
        storage = _make_storage()
        paginator = MagicMock()
        paginator.paginate.return_value = [
            {
                "Contents": [
                    _make_s3_object("envault/staging/0001.age"),
                    _make_s3_object("envault/staging/0002.age"),
                ]
            }
        ]
        storage.client.get_paginator.return_value = paginator

        result = latest_version(storage, "staging")
        assert result is not None
        assert result.version_id == "0002"


class TestNextVersionId:
    def test_returns_0001_when_no_existing_versions(self):
        storage = _make_storage()
        paginator = MagicMock()
        paginator.paginate.return_value = [{}]
        storage.client.get_paginator.return_value = paginator

        assert next_version_id(storage, "dev") == "0001"

    def test_increments_latest_version(self):
        storage = _make_storage()
        paginator = MagicMock()
        paginator.paginate.return_value = [
            {"Contents": [_make_s3_object("envault/dev/0005.age")]}
        ]
        storage.client.get_paginator.return_value = paginator

        assert next_version_id(storage, "dev") == "0006"


def test_env_version_str():
    v = EnvVersion(
        version_id="0003",
        uploaded_at=datetime(2024, 6, 1, 12, 30, 0),
        size=512,
        etag="abc123",
    )
    assert "v0003" in str(v)
    assert "512 bytes" in str(v)
