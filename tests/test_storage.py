"""Tests for envault.storage."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from envault.storage import S3Storage, StorageError

PROJECT = "myapp"
VERSION = "v1"
DATA = b"encrypted-blob"
BUCKET = "test-bucket"


@pytest.fixture()
def mock_client():
    with patch("envault.storage.boto3.session.Session") as mock_session:
        client = MagicMock()
        mock_session.return_value.client.return_value = client
        yield client


@pytest.fixture()
def storage(mock_client):  # noqa: ARG001
    return S3Storage(bucket=BUCKET, prefix="envault")


# ---------------------------------------------------------------------------
# upload
# ---------------------------------------------------------------------------

class TestUpload:
    def test_returns_s3_key(self, storage, mock_client):
        key = storage.upload(PROJECT, VERSION, DATA)
        assert key == f"envault/{PROJECT}/{VERSION}.env.age"

    def test_calls_put_object(self, storage, mock_client):
        storage.upload(PROJECT, VERSION, DATA)
        mock_client.put_object.assert_called_once_with(
            Bucket=BUCKET,
            Key=f"envault/{PROJECT}/{VERSION}.env.age",
            Body=DATA,
        )

    def test_raises_storage_error_on_client_error(self, storage, mock_client):
        mock_client.put_object.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Denied"}}, "PutObject"
        )
        with pytest.raises(StorageError, match="Upload failed"):
            storage.upload(PROJECT, VERSION, DATA)


# ---------------------------------------------------------------------------
# download
# ---------------------------------------------------------------------------

class TestDownload:
    def test_returns_bytes(self, storage, mock_client):
        mock_client.get_object.return_value = {"Body": MagicMock(read=lambda: DATA)}
        result = storage.download(PROJECT, VERSION)
        assert result == DATA

    def test_raises_storage_error_on_client_error(self, storage, mock_client):
        mock_client.get_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "Not found"}}, "GetObject"
        )
        # NoSuchKey via generic ClientError path
        with pytest.raises(StorageError):
            storage.download(PROJECT, VERSION)


# ---------------------------------------------------------------------------
# list_versions
# ---------------------------------------------------------------------------

class TestListVersions:
    def test_returns_sorted_versions(self, storage, mock_client):
        paginator = MagicMock()
        paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "envault/myapp/v2.env.age"},
                    {"Key": "envault/myapp/v1.env.age"},
                ]
            }
        ]
        mock_client.get_paginator.return_value = paginator
        versions = storage.list_versions(PROJECT)
        assert versions == ["v1", "v2"]

    def test_returns_empty_list_when_no_objects(self, storage, mock_client):
        paginator = MagicMock()
        paginator.paginate.return_value = [{"Contents": []}]
        mock_client.get_paginator.return_value = paginator
        assert storage.list_versions(PROJECT) == []

    def test_raises_storage_error_on_failure(self, storage, mock_client):
        mock_client.get_paginator.side_effect = ClientError(
            {"Error": {"Code": "NoSuchBucket", "Message": "Missing"}}, "ListObjectsV2"
        )
        with pytest.raises(StorageError, match="List failed"):
            storage.list_versions(PROJECT)
