"""Roll back to a previous version of a .env bundle."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from envault.bundle import EnvBundle, decode_bundle
from envault.config import EnvaultConfig
from envault.crypto import decrypt
from envault.keystore import KeyPair
from envault.push import _make_version, push
from envault.storage import S3Storage
from envault.versioning import EnvVersion, list_versions


class RollbackError(Exception):
    """Raised when a rollback operation fails."""


@dataclass
class RollbackResult:
    source_version: str
    new_version: str
    env: str

    def __str__(self) -> str:
        return (
            f"Rolled back from {self.source_version} "
            f"to new version {self.new_version}"
        )


def rollback(
    config: EnvaultConfig,
    storage: S3Storage,
    keypair: KeyPair,
    target_version: Optional[str] = None,
) -> RollbackResult:
    """Re-push a previous version as the new latest version.

    If *target_version* is None the second-most-recent version is used
    (i.e. "undo the last push").
    """
    versions: list[EnvVersion] = list_versions(storage, config.env)
    if not versions:
        raise RollbackError("No versions found – nothing to roll back to.")

    if target_version is None:
        if len(versions) < 2:
            raise RollbackError(
                "Only one version exists; cannot roll back further."
            )
        source: EnvVersion = versions[1]  # sorted newest-first
    else:
        matches = [v for v in versions if v.version == target_version]
        if not matches:
            raise RollbackError(
                f"Version {target_version!r} not found."
            )
        source = matches[0]

    bundle_data = storage.download(source.s3_key)
    bundle: EnvBundle = decode_bundle(bundle_data)

    plaintext: str = decrypt(
        bundle.ciphertext, keypair.private_key_path
    )

    new_s3_key = push(
        config=config,
        storage=storage,
        keypair=keypair,
        plaintext=plaintext,
    )

    return RollbackResult(
        source_version=source.version,
        new_version=new_s3_key,
        env=plaintext,
    )
