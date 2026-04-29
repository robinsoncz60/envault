"""Key rotation: re-encrypt the latest env bundle under a new keypair."""

from __future__ import annotations

from pathlib import Path

from envault.bundle import decode_bundle, encode_bundle
from envault.config import EnvaultConfig
from envault.crypto import decrypt, encrypt
from envault.exceptions import EnvaultError
from envault.keystore import KeyPair, load_keypair, save_keypair
from envault.pull import PullError
from envault.push import _make_version, PushError
from envault.storage import S3Storage
from envault.versioning import latest_version


class RotateError(EnvaultError):
    """Raised when key rotation fails."""


def rotate(
    config: EnvaultConfig,
    storage: S3Storage,
    old_keypair: KeyPair,
    new_keypair: KeyPair,
    pushed_by: str,
) -> str:
    """Re-encrypt the latest bundle with *new_keypair* and push a new version.

    Returns the S3 key of the newly uploaded bundle.
    Raises RotateError on any failure.
    """
    version = latest_version(storage, config.env)
    if version is None:
        raise RotateError("No existing versions found — nothing to rotate.")

    try:
        raw = storage.download(version.s3_key)
    except Exception as exc:  # noqa: BLE001
        raise RotateError(f"Failed to download bundle: {exc}") from exc

    try:
        bundle = decode_bundle(raw)
    except Exception as exc:  # noqa: BLE001
        raise RotateError(f"Failed to decode bundle: {exc}") from exc

    try:
        plaintext = decrypt(bundle.ciphertext, old_keypair.private_key_path)
    except Exception as exc:  # noqa: BLE001
        raise RotateError(f"Decryption with old key failed: {exc}") from exc

    try:
        new_ciphertext = encrypt(plaintext, new_keypair.public_key)
    except Exception as exc:  # noqa: BLE001
        raise RotateError(f"Encryption with new key failed: {exc}") from exc

    new_bundle_bytes = encode_bundle(new_ciphertext, pushed_by)
    new_version_id = _make_version()
    s3_key = f"{config.env}/{new_version_id}.bundle"

    try:
        storage.upload(s3_key, new_bundle_bytes)
    except Exception as exc:  # noqa: BLE001
        raise RotateError(f"Upload of rotated bundle failed: {exc}") from exc

    return s3_key
