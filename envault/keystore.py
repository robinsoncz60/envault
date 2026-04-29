"""Manages age keypair storage and retrieval on the local filesystem."""

import os
import stat
from pathlib import Path

DEFAULT_KEY_DIR = Path.home() / ".config" / "envault"
PRIVATE_KEY_FILE = "identity.txt"
PUBLIC_KEY_FILE = "recipient.txt"


class KeystoreError(Exception):
    """Raised when keypair storage or retrieval fails."""


def _key_dir() -> Path:
    """Return the key directory, respecting ENVAULT_KEY_DIR env override."""
    override = os.environ.get("ENVAULT_KEY_DIR")
    return Path(override) if override else DEFAULT_KEY_DIR


def save_keypair(private_key: str, public_key: str, key_dir: Path | None = None) -> Path:
    """Persist an age keypair to disk with restrictive permissions.

    Args:
        private_key: The age private key (identity) string.
        public_key: The age public key (recipient) string.
        key_dir: Directory to write keys into. Defaults to ~/.config/envault.

    Returns:
        The directory where the keys were saved.

    Raises:
        KeystoreError: If the directory cannot be created or keys cannot be written.
    """
    directory = key_dir or _key_dir()
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise KeystoreError(f"Cannot create key directory '{directory}': {exc}") from exc

    priv_path = directory / PRIVATE_KEY_FILE
    pub_path = directory / PUBLIC_KEY_FILE

    try:
        priv_path.write_text(private_key)
        priv_path.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0o600
        pub_path.write_text(public_key)
    except OSError as exc:
        raise KeystoreError(f"Cannot write keypair to '{directory}': {exc}") from exc

    return directory


def load_keypair(key_dir: Path | None = None) -> tuple[str, str]:
    """Load the age keypair from disk.

    Returns:
        A (private_key, public_key) tuple.

    Raises:
        KeystoreError: If either key file is missing or unreadable.
    """
    directory = key_dir or _key_dir()
    priv_path = directory / PRIVATE_KEY_FILE
    pub_path = directory / PUBLIC_KEY_FILE

    for path in (priv_path, pub_path):
        if not path.exists():
            raise KeystoreError(
                f"Key file not found: '{path}'. Run 'envault init' to generate a keypair."
            )

    try:
        return priv_path.read_text().strip(), pub_path.read_text().strip()
    except OSError as exc:
        raise KeystoreError(f"Cannot read keypair from '{directory}': {exc}") from exc


def keypair_exists(key_dir: Path | None = None) -> bool:
    """Return True if both key files are present on disk."""
    directory = key_dir or _key_dir()
    return (directory / PRIVATE_KEY_FILE).exists() and (directory / PUBLIC_KEY_FILE).exists()
