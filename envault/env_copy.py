"""Copy (clone) an env version from one environment prefix to another."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .bundle import EnvBundle
from .config import EnvaultConfig
from .push import _make_version
from .storage import S3Storage, StorageError
from .versioning import latest_version, VersioningError


class CopyError(Exception):
    """Raised when an env copy operation fails."""


@dataclass
class CopyResult:
    source_key: str
    dest_key: str
    version: str

    def __str__(self) -> str:
        return f"Copied {self.source_key} -> {self.dest_key} (version {self.version})"


def copy_env(
    config: EnvaultConfig,
    storage: S3Storage,
    dest_prefix: str,
    source_version: Optional[str] = None,
) -> CopyResult:
    """Copy the latest (or specified) version from config.prefix to dest_prefix.

    The bundle bytes are copied verbatim — no re-encryption is performed.
    """
    try:
        if source_version is None:
            ver = latest_version(storage, config.prefix)
            if ver is None:
                raise CopyError(f"No versions found under prefix '{config.prefix}'")
            source_version = str(ver)

        source_key = f"{config.prefix}/{source_version}.env.age"
        try:
            bundle_bytes = storage.download(source_key)
        except StorageError as exc:
            raise CopyError(f"Failed to download source bundle: {exc}") from exc

        new_version = _make_version()
        dest_key = f"{dest_prefix}/{new_version}.env.age"

        try:
            storage.upload(dest_key, bundle_bytes)
        except StorageError as exc:
            raise CopyError(f"Failed to upload to destination: {exc}") from exc

        return CopyResult(
            source_key=source_key,
            dest_key=dest_key,
            version=new_version,
        )
    except VersioningError as exc:
        raise CopyError(str(exc)) from exc
