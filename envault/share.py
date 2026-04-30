"""Share encrypted .env bundles with additional recipients by re-encrypting with their public keys."""

from __future__ import annotations

from pathlib import Path
from typing import List

from .bundle import EnvBundle, decode_bundle, encode_bundle
from .crypto import encrypt, decrypt, CryptoError
from .exceptions import EnvaultError
from .storage import S3Storage
from .versioning import latest_version


class ShareError(EnvaultError):
    """Raised when a share operation fails."""


def share(
    storage: S3Storage,
    env_name: str,
    sender_private_key: str,
    recipient_public_keys: List[str],
    version: str | None = None,
) -> List[str]:
    """Re-encrypt the latest (or specified) bundle for one or more new recipients.

    Returns the list of S3 keys where the new bundles were uploaded.
    """
    if not recipient_public_keys:
        raise ShareError("At least one recipient public key must be provided")

    # Resolve version
    if version is None:
        ver = latest_version(storage, env_name)
        if ver is None:
            raise ShareError(f"No versions found for env '{env_name}'")
        version = str(ver)

    # Download the existing bundle
    try:
        raw = storage.download(env_name, version)
    except Exception as exc:
        raise ShareError(f"Failed to download bundle: {exc}") from exc

    bundle = decode_bundle(raw)

    # Decrypt the ciphertext with sender's private key
    try:
        plaintext = decrypt(bundle.ciphertext, sender_private_key)
    except CryptoError as exc:
        raise ShareError(f"Failed to decrypt bundle: {exc}") from exc

    uploaded_keys: List[str] = []

    for idx, pub_key in enumerate(recipient_public_keys):
        try:
            new_ciphertext = encrypt(plaintext, pub_key)
        except CryptoError as exc:
            raise ShareError(
                f"Failed to encrypt for recipient {idx}: {exc}"
            ) from exc

        new_bundle = EnvBundle(
            ciphertext=new_ciphertext,
            env_name=bundle.env_name,
            version=bundle.version,
            created_at=bundle.created_at,
        )

        recipient_tag = pub_key[:16].replace(" ", "_")
        share_version = f"{version}-shared-{recipient_tag}"

        try:
            s3_key = storage.upload(
                env_name, share_version, encode_bundle(new_bundle)
            )
        except Exception as exc:
            raise ShareError(f"Failed to upload shared bundle: {exc}") from exc

        uploaded_keys.append(s3_key)

    return uploaded_keys
