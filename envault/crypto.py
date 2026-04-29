"""Age encryption/decryption helpers for envault."""

import subprocess
import tempfile
import os
from pathlib import Path


class CryptoError(Exception):
    """Raised when encryption or decryption fails."""
    pass


def encrypt(plaintext: bytes, recipient_public_key: str) -> bytes:
    """
    Encrypt plaintext bytes using age with the given recipient public key.

    Requires `age` to be installed and available on PATH.
    """
    try:
        result = subprocess.run(
            ["age", "--recipient", recipient_public_key, "--armor"],
            input=plaintext,
            capture_output=True,
        )
    except FileNotFoundError:
        raise CryptoError(
            "'age' binary not found. Install it from https://github.com/FiloSottile/age"
        )

    if result.returncode != 0:
        raise CryptoError(f"Encryption failed: {result.stderr.decode().strip()}")

    return result.stdout


def decrypt(ciphertext: bytes, identity_path: str | Path) -> bytes:
    """
    Decrypt age-encrypted ciphertext using the given identity (private key) file.

    Requires `age` to be installed and available on PATH.
    """
    identity_path = Path(identity_path)
    if not identity_path.exists():
        raise CryptoError(f"Identity file not found: {identity_path}")

    try:
        result = subprocess.run(
            ["age", "--decrypt", "--identity", str(identity_path)],
            input=ciphertext,
            capture_output=True,
        )
    except FileNotFoundError:
        raise CryptoError(
            "'age' binary not found. Install it from https://github.com/FiloSottile/age"
        )

    if result.returncode != 0:
        raise CryptoError(f"Decryption failed: {result.stderr.decode().strip()}")

    return result.stdout


def generate_keypair() -> tuple[str, str]:
    """
    Generate a new age keypair.

    Returns a (public_key, private_key_block) tuple.
    """
    try:
        result = subprocess.run(["age-keygen"], capture_output=True)
    except FileNotFoundError:
        raise CryptoError(
            "'age-keygen' binary not found. Install it from https://github.com/FiloSottile/age"
        )

    if result.returncode != 0:
        raise CryptoError(f"Key generation failed: {result.stderr.decode().strip()}")

    private_key_block = result.stdout.decode()
    # age-keygen writes the public key to stderr as a comment
    public_key_line = result.stderr.decode().strip()
    # Format: "# public key: age1..."
    public_key = public_key_line.split("public key: ", 1)[-1].strip()

    return public_key, private_key_block
