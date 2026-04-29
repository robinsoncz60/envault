"""push: encrypt a local .env file and upload it as a versioned bundle."""

from __future__ import annotations

import datetime
from pathlib import Path

from envault.bundle import EnvBundle, encode_bundle
from envault.config import EnvaultConfig
from envault.crypto import encrypt
from envault.keystore import load_keypair
from envault.storage import S3Storage


class PushError(Exception):
    """Raised when a push operation fails."""


def _make_version() -> str:
    """Return an ISO-8601 UTC timestamp suitable for use as a version string."""
    return datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


def push(
    env_path: Path,
    config: EnvaultConfig,
    storage: S3Storage,
    comment: str | None = None,
) -> str:
    """Encrypt *env_path* and upload it to *storage*.

    Returns the S3 key of the uploaded object.
    """
    if not env_path.exists():
        raise PushError(f".env file not found: {env_path}")

    plaintext = env_path.read_bytes()

    try:
        keypair = load_keypair(config.environment)
    except Exception as exc:
        raise PushError(f"Could not load keypair: {exc}") from exc

    try:
        ciphertext = encrypt(plaintext, keypair.public_key)
    except Exception as exc:
        raise PushError(f"Encryption failed: {exc}") from exc

    version = _make_version()
    bundle = EnvBundle(
        environment=config.environment,
        version=version,
        ciphertext=ciphertext,
        public_key=keypair.public_key,
        comment=comment,
    )

    payload = encode_bundle(bundle)

    try:
        s3_key = storage.upload(config.environment, version, payload)
    except Exception as exc:
        raise PushError(f"Upload failed: {exc}") from exc

    return s3_key
