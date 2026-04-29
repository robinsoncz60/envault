"""Version management for encrypted .env files stored in S3."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from envault.storage import S3Storage


class VersioningError(Exception):
    """Raised when version management operations fail."""


@dataclass
class EnvVersion:
    version_id: str
    uploaded_at: datetime
    size: int
    etag: str

    def __str__(self) -> str:
        ts = self.uploaded_at.strftime("%Y-%m-%d %H:%M:%S UTC")
        return f"v{self.version_id}  {ts}  {self.size} bytes"


def list_versions(storage: "S3Storage", env_name: str) -> list[EnvVersion]:
    """Return all stored versions for *env_name*, newest first."""
    prefix = storage._key(env_name, "")
    try:
        paginator = storage.client.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=storage.bucket, Prefix=prefix)
        objects = [obj for page in pages for obj in page.get("Contents", [])]
    except Exception as exc:  # pragma: no cover
        raise VersioningError(f"Failed to list versions: {exc}") from exc

    versions: list[EnvVersion] = []
    for obj in objects:
        key = obj["Key"]
        match = re.search(r"/(\d+)\.age$", key)
        if not match:
            continue
        versions.append(
            EnvVersion(
                version_id=match.group(1),
                uploaded_at=obj["LastModified"].replace(tzinfo=None),
                size=obj["Size"],
                etag=obj["ETag"].strip('"'),
            )
        )

    versions.sort(key=lambda v: v.version_id, reverse=True)
    return versions


def latest_version(storage: "S3Storage", env_name: str) -> EnvVersion | None:
    """Return the most recent version or *None* if none exist."""
    versions = list_versions(storage, env_name)
    return versions[0] if versions else None


def next_version_id(storage: "S3Storage", env_name: str) -> str:
    """Return the next zero-padded version id (e.g. '0003')."""
    latest = latest_version(storage, env_name)
    if latest is None:
        return "0001"
    return str(int(latest.version_id) + 1).zfill(4)
