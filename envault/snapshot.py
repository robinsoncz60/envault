"""Snapshot support: tag a specific version with a human-readable name."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from envault.storage import S3Storage, StorageError

SNAPSHOT_PREFIX = "snapshots/"


class SnapshotError(Exception):
    pass


@dataclass
class Snapshot:
    name: str
    s3_key: str
    created_by: str
    note: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "s3_key": self.s3_key,
            "created_by": self.created_by,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Snapshot":
        try:
            return cls(
                name=data["name"],
                s3_key=data["s3_key"],
                created_by=data["created_by"],
                note=data.get("note", ""),
            )
        except KeyError as exc:
            raise SnapshotError(f"Missing snapshot field: {exc}") from exc

    def __str__(self) -> str:
        note_part = f" — {self.note}" if self.note else ""
        return f"{self.name} -> {self.s3_key} (by {self.created_by}){note_part}"


def _snapshot_key(env: str, name: str) -> str:
    return f"{SNAPSHOT_PREFIX}{env}/{name}.json"


def save_snapshot(
    storage: S3Storage,
    env: str,
    snapshot: Snapshot,
) -> str:
    """Persist a snapshot to S3. Returns the S3 key."""
    key = _snapshot_key(env, snapshot.name)
    payload = json.dumps(snapshot.to_dict()).encode()
    try:
        storage.upload(key, payload)
    except StorageError as exc:
        raise SnapshotError(f"Failed to save snapshot: {exc}") from exc
    return key


def load_snapshot(storage: S3Storage, env: str, name: str) -> Snapshot:
    """Retrieve a named snapshot from S3."""
    key = _snapshot_key(env, name)
    try:
        data = storage.download(key)
    except StorageError as exc:
        raise SnapshotError(f"Snapshot '{name}' not found: {exc}") from exc
    try:
        return Snapshot.from_dict(json.loads(data))
    except (json.JSONDecodeError, SnapshotError) as exc:
        raise SnapshotError(f"Corrupt snapshot data: {exc}") from exc


def list_snapshots(storage: S3Storage, env: str) -> list[Snapshot]:
    """List all snapshots for an env, sorted alphabetically by name."""
    prefix = f"{SNAPSHOT_PREFIX}{env}/"
    try:
        keys = storage.list(prefix)
    except StorageError as exc:
        raise SnapshotError(f"Failed to list snapshots: {exc}") from exc
    snapshots = []
    for key in keys:
        try:
            data = storage.download(key)
            snapshots.append(Snapshot.from_dict(json.loads(data)))
        except (StorageError, SnapshotError, json.JSONDecodeError):
            continue
    return sorted(snapshots, key=lambda s: s.name)
