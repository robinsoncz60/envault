"""Rename a key across the latest (or specified) .env version."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from envault.config import EnvaultConfig
from envault.crypto import decrypt
from envault.keystore import KeyPair
from envault.push import push
from envault.storage import S3Storage
from envault.versioning import latest_version


class RenameError(Exception):
    """Raised when a rename operation fails."""


@dataclass
class RenameResult:
    old_key: str
    new_key: str
    s3_key: str

    def __str__(self) -> str:
        return f"Renamed {self.old_key!r} -> {self.new_key!r} and pushed {self.s3_key}"


def _parse_env(text: str) -> dict[str, str]:
    """Parse KEY=VALUE lines; skip comments and blanks."""
    result: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        k, _, v = stripped.partition("=")
        result[k.strip()] = v
    return result


def _render_env(pairs: dict[str, str]) -> str:
    """Render a dict back to KEY=VALUE lines."""
    return "\n".join(f"{k}={v}" for k, v in pairs.items()) + "\n"


def rename_key(
    config: EnvaultConfig,
    storage: S3Storage,
    keypair: KeyPair,
    old_key: str,
    new_key: str,
    version: Optional[str] = None,
) -> RenameResult:
    """Decrypt the target version, rename *old_key* to *new_key*, re-encrypt and push."""
    if not old_key:
        raise RenameError("old_key must not be empty")
    if not new_key:
        raise RenameError("new_key must not be empty")
    if old_key == new_key:
        raise RenameError("old_key and new_key are the same")

    ver = version or latest_version(storage, config.env)
    if ver is None:
        raise RenameError("No versions found; nothing to rename")

    bundle_bytes = storage.download(ver)

    import json
    import base64
    from envault.bundle import EnvBundle

    bundle = EnvBundle.from_dict(json.loads(bundle_bytes))
    plaintext = decrypt(base64.b64decode(bundle.ciphertext), keypair.private_key)

    pairs = _parse_env(plaintext)
    if old_key not in pairs:
        raise RenameError(f"Key {old_key!r} not found in environment")
    if new_key in pairs:
        raise RenameError(f"Key {new_key!r} already exists in environment")

    pairs[new_key] = pairs.pop(old_key)
    new_plaintext = _render_env(pairs)

    s3_key = push(
        config=config,
        storage=storage,
        keypair=keypair,
        plaintext=new_plaintext,
    )
    return RenameResult(old_key=old_key, new_key=new_key, s3_key=s3_key)
