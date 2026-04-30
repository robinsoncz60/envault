"""Diff two .env versions by decrypting and comparing their keys."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from envault.bundle import EnvBundle, decode_bundle
from envault.crypto import decrypt
from envault.exceptions import EnvaultError
from envault.storage import S3Storage
from envault.versioning import EnvVersion


class DiffError(EnvaultError):
    """Raised when a diff operation fails."""


@dataclass
class DiffResult:
    added: List[str]
    removed: List[str]
    changed: List[str]
    unchanged: List[str]

    def has_changes(self) -> bool:
        return bool(self.added or self.removed or self.changed)

    def __str__(self) -> str:
        lines: List[str] = []
        for key in sorted(self.added):
            lines.append(f"+ {key}")
        for key in sorted(self.removed):
            lines.append(f"- {key}")
        for key in sorted(self.changed):
            lines.append(f"~ {key}")
        return "\n".join(lines) if lines else "(no changes)"


def _parse_env(plaintext: str) -> Dict[str, str]:
    """Parse KEY=VALUE lines into a dict, ignoring comments and blanks."""
    result: Dict[str, str] = {}
    for line in plaintext.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            result[key.strip()] = value.strip()
    return result


def _decrypt_version(storage: S3Storage, version: EnvVersion, private_key: str) -> Dict[str, str]:
    try:
        raw = storage.download(version.s3_key)
    except Exception as exc:
        raise DiffError(f"Failed to download {version.s3_key}: {exc}") from exc

    try:
        bundle = decode_bundle(raw)
    except Exception as exc:
        raise DiffError(f"Failed to decode bundle for {version.s3_key}: {exc}") from exc

    try:
        plaintext = decrypt(bundle.ciphertext, private_key)
    except Exception as exc:
        raise DiffError(f"Failed to decrypt {version.s3_key}: {exc}") from exc

    return _parse_env(plaintext)


def diff_versions(
    storage: S3Storage,
    old_version: EnvVersion,
    new_version: EnvVersion,
    private_key: str,
) -> DiffResult:
    """Return a DiffResult comparing two encrypted .env versions."""
    old_env = _decrypt_version(storage, old_version, private_key)
    new_env = _decrypt_version(storage, new_version, private_key)

    old_keys = set(old_env)
    new_keys = set(new_env)

    added = sorted(new_keys - old_keys)
    removed = sorted(old_keys - new_keys)
    changed = sorted(k for k in old_keys & new_keys if old_env[k] != new_env[k])
    unchanged = sorted(k for k in old_keys & new_keys if old_env[k] == new_env[k])

    return DiffResult(added=added, removed=removed, changed=changed, unchanged=unchanged)
