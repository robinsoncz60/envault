"""Promote an env bundle from one environment to another (e.g. staging -> production)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .bundle import EnvBundle, decode_bundle
from .config import EnvaultConfig
from .crypto import encrypt, decrypt
from .exceptions import EnvaultError
from .push import _make_version
from .storage import S3Storage
from .versioning import latest_version


class PromoteError(EnvaultError):
    """Raised when a promotion operation fails."""


@dataclass
class PromoteResult:
    source_env: str
    target_env: str
    source_version: str
    target_s3_key: str

    def __str__(self) -> str:
        return (
            f"Promoted {self.source_env}@{self.source_version} "
            f"-> {self.target_env} ({self.target_s3_key})"
        )


def promote(
    config: EnvaultConfig,
    storage: S3Storage,
    source_env: str,
    target_env: str,
    source_private_key: str,
    target_public_key: str,
    version: Optional[str] = None,
    promoted_by: str = "unknown",
) -> PromoteResult:
    """Decrypt a bundle from *source_env* and re-encrypt it for *target_env*."""
    # Resolve version
    if version is None:
        ver = latest_version(storage, env=source_env)
        if ver is None:
            raise PromoteError(f"No versions found for environment '{source_env}'")
        version = ver.version

    # Download source bundle
    source_key = f"{source_env}/{version}.bundle"
    try:
        raw = storage.download(source_key)
    except Exception as exc:
        raise PromoteError(f"Failed to download source bundle: {exc}") from exc

    # Decode and decrypt
    try:
        bundle = decode_bundle(raw)
        plaintext = decrypt(bundle.ciphertext, source_private_key)
    except Exception as exc:
        raise PromoteError(f"Failed to decrypt source bundle: {exc}") from exc

    # Re-encrypt for target
    try:
        new_ciphertext = encrypt(plaintext, target_public_key)
    except Exception as exc:
        raise PromoteError(f"Failed to re-encrypt for target: {exc}") from exc

    # Build new bundle and upload
    new_version = _make_version()
    new_bundle = EnvBundle(
        ciphertext=new_ciphertext,
        version=new_version,
        env=target_env,
        pushed_by=promoted_by,
        promoted_from=f"{source_env}@{version}",
    )
    target_key = f"{target_env}/{new_version}.bundle"
    try:
        storage.upload(target_key, new_bundle.encode())
    except Exception as exc:
        raise PromoteError(f"Failed to upload promoted bundle: {exc}") from exc

    return PromoteResult(
        source_env=source_env,
        target_env=target_env,
        source_version=version,
        target_s3_key=target_key,
    )
