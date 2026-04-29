"""S3-compatible backend for storing and retrieving encrypted .env files."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError


class StorageError(Exception):
    """Raised when a storage operation fails."""


class S3Storage:
    """Thin wrapper around boto3 for envault's S3 operations."""

    def __init__(
        self,
        bucket: str,
        prefix: str = "envault",
        endpoint_url: Optional[str] = None,
        region: Optional[str] = None,
    ) -> None:
        self.bucket = bucket
        self.prefix = prefix.rstrip("/")

        session = boto3.session.Session()
        self._client = session.client(
            "s3",
            endpoint_url=endpoint_url or os.getenv("ENVAULT_S3_ENDPOINT"),
            region_name=region or os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _key(self, project: str, version: str) -> str:
        return f"{self.prefix}/{project}/{version}.env.age"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def upload(self, project: str, version: str, data: bytes) -> str:
        """Upload *data* and return the S3 key."""
        key = self._key(project, version)
        try:
            self._client.put_object(Bucket=self.bucket, Key=key, Body=data)
        except (BotoCoreError, ClientError) as exc:
            raise StorageError(f"Upload failed: {exc}") from exc
        return key

    def download(self, project: str, version: str) -> bytes:
        """Download and return the raw bytes for *project*/*version*."""
        key = self._key(project, version)
        try:
            response = self._client.get_object(Bucket=self.bucket, Key=key)
            return response["Body"].read()
        except self._client.exceptions.NoSuchKey:
            raise StorageError(f"Version '{version}' not found for project '{project}'.")
        except (BotoCoreError, ClientError) as exc:
            raise StorageError(f"Download failed: {exc}") from exc

    def list_versions(self, project: str) -> list[str]:
        """Return a sorted list of available version strings for *project*."""
        prefix = f"{self.prefix}/{project}/"
        try:
            paginator = self._client.get_paginator("list_objects_v2")
            versions: list[str] = []
            for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
                for obj in page.get("Contents", []):
                    name = obj["Key"].removeprefix(prefix)
                    if name.endswith(".env.age"):
                        versions.append(name.removesuffix(".env.age"))
            return sorted(versions)
        except (BotoCoreError, ClientError) as exc:
            raise StorageError(f"List failed: {exc}") from exc
