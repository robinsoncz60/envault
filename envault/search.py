"""Search across versioned .env bundles for keys or values."""
from __future__ import annotations

import base64
from dataclasses import dataclass, field
from typing import List, Optional

from envault.bundle import EnvBundle, decode_bundle
from envault.crypto import decrypt
from envault.exceptions import EnvaultError
from envault.storage import S3Storage
from envault.versioning import EnvVersion, list_versions


class SearchError(EnvaultError):
    """Raised when a search operation fails."""


@dataclass
class SearchMatch:
    version: EnvVersion
    key: str
    value: str

    def __str__(self) -> str:
        return f"[{self.version}] {self.key}={self.value}"


def _parse_env(plaintext: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in plaintext.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, _, v = line.partition("=")
        result[k.strip()] = v.strip()
    return result


def search(
    storage: S3Storage,
    private_key_path: str,
    query: str,
    *,
    search_keys: bool = True,
    search_values: bool = False,
    max_versions: Optional[int] = None,
    environment: str = "default",
) -> List[SearchMatch]:
    """Search versioned bundles for *query* in keys and/or values.

    Returns a list of :class:`SearchMatch` objects sorted newest-first.
    """
    if not search_keys and not search_values:
        raise SearchError("At least one of search_keys or search_values must be True")

    versions = list_versions(storage, environment=environment)
    if max_versions is not None:
        versions = versions[:max_versions]

    matches: List[SearchMatch] = []
    needle = query.lower()

    for version in versions:
        try:
            raw = storage.download(version.s3_key)
            bundle = decode_bundle(raw)
            plaintext = decrypt(bundle.ciphertext, private_key_path)
        except Exception as exc:  # noqa: BLE001
            raise SearchError(f"Failed to inspect version {version}: {exc}") from exc

        env_vars = _parse_env(plaintext)
        for k, v in env_vars.items():
            key_match = search_keys and needle in k.lower()
            val_match = search_values and needle in v.lower()
            if key_match or val_match:
                matches.append(SearchMatch(version=version, key=k, value=v))

    return matches
