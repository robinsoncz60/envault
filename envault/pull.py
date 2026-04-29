"""Pull and decrypt the latest (or a specific) version of a .env file."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .bundle import BundleError, decode_bundle
from .config import EnvaultConfig
from .crypto import CryptoError, decrypt
from .keystore import KeystoreError, load_keypair
from .storage import S3Storage, StorageError
from .versioning import VersioningError, latest_version, list_versions


class PullError(Exception):
    """Raised when a pull operation fails."""


def pull(
    config: EnvaultConfig,
    output_path: Path,
    *,
    version: Optional[str] = None,
    profile: str = "default",
) -> str:
    """Download and decrypt a .env file to *output_path*.

    Returns the resolved version string that was pulled.
    """
    try:
        keypair = load_keypair(profile)
    except KeystoreError as exc:
        raise PullError(f"Could not load keypair for profile '{profile}': {exc}") from exc

    storage = S3Storage(
        bucket=config.bucket,
        prefix=config.prefix,
        endpoint_url=config.endpoint_url,
    )

    try:
        if version is None:
            ver = latest_version(storage, config.env_name)
            if ver is None:
                raise PullError(
                    f"No versions found for env '{config.env_name}' in bucket '{config.bucket}'."
                )
            resolved = str(ver)
        else:
            resolved = version

        raw = storage.download(config.env_name, resolved)
    except StorageError as exc:
        raise PullError(f"Storage error: {exc}") from exc
    except VersioningError as exc:
        raise PullError(f"Versioning error: {exc}") from exc

    try:
        bundle = decode_bundle(raw)
    except BundleError as exc:
        raise PullError(f"Failed to decode bundle: {exc}") from exc

    try:
        plaintext = decrypt(bundle.ciphertext, keypair.private_key)
    except CryptoError as exc:
        raise PullError(f"Decryption failed: {exc}") from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(plaintext)

    return resolved
