"""Tag management for envault versions.

Allows users to assign human-readable tags (e.g. 'stable', 'release-1.2')
to specific version keys stored in S3.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, List, Optional

from envault.storage import S3Storage, StorageError


class TagError(Exception):
    """Raised when a tag operation fails."""


_TAG_INDEX_KEY = ".envault/tags.json"
_VALID_TAG_CHARS = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.")


def _validate_tag_name(name: str) -> None:
    """Raise TagError if the tag name is empty or contains invalid characters."""
    if not name:
        raise TagError("Tag name must not be empty")
    invalid = set(name) - _VALID_TAG_CHARS
    if invalid:
        raise TagError(
            f"Tag name {name!r} contains invalid characters: {sorted(invalid)}"
        )


@dataclass
class Tag:
    name: str
    version_key: str
    message: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        return {"name": self.name, "version_key": self.version_key, "message": self.message}

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "Tag":
        for field in ("name", "version_key"):
            if field not in data:
                raise TagError(f"Missing field in tag data: {field}")
        return cls(
            name=str(data["name"]),
            version_key=str(data["version_key"]),
            message=str(data["message"]) if data.get("message") else None,
        )

    def __str__(self) -> str:
        msg_part = f" — {self.message}" if self.message else ""
        return f"{self.name} -> {self.version_key}{msg_part}"


def _load_index(storage: S3Storage) -> Dict[str, Dict]:
    try:
        raw = storage.download(_TAG_INDEX_KEY)
        return json.loads(raw.decode())
    except StorageError:
        return {}


def _save_index(storage: S3Storage, index: Dict[str, Dict]) -> None:
    try:
        storage.upload(_TAG_INDEX_KEY, json.dumps(index).encode())
    except StorageError as exc:
        raise TagError(f"Failed to save tag index: {exc}") from exc


def set_tag(storage: S3Storage, name: str, version_key: str, message: Optional[str] = None) -> Tag:
    """Create or update a tag pointing to version_key."""
    _validate_tag_name(name)
    index = _load_index(storage)
    tag = Tag(name=name, version_key=version_key, message=message)
    index[name] = tag.to_dict()
    _save_index(storage, index)
    return tag


def get_tag(storage: S3Storage, name: str) -> Tag:
    """Retrieve a tag by name. Raises TagError if not found."""
    index = _load_index(storage)
    if name not in index:
        raise TagError(f"Tag not found: {name!r}")
    return Tag.from_dict(index[name])


def delete_tag(storage: S3Storage, name: str) -> None:
    """Remove a tag. Raises TagError if it does not exist."""
    index = _load_index(storage)
    if name not in index:
        raise TagError(f"Tag not found: {name!r}")
    del index[name]
    _save_index(storage, index)


def list_tags(storage: S3Storage) -> List[Tag]:
    """Return all tags sorted alphabetically by name."""
    index = _load_index(storage)
    return sorted([Tag.from_dict(v) for v in index.values()], key=lambda t: t.name)
