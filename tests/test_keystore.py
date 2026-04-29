"""Tests for envault.keystore — keypair persistence helpers."""

import stat
from pathlib import Path

import pytest

from envault.keystore import (
    KeystoreError,
    PRIVATE_KEY_FILE,
    PUBLIC_KEY_FILE,
    keypair_exists,
    load_keypair,
    save_keypair,
)

FAKE_PRIVATE = "AGE-SECRET-KEY-1FAKEPRIVATEKEYDATA"
FAKE_PUBLIC = "age1fakepublickeydata"


@pytest.fixture()
def key_dir(tmp_path: Path) -> Path:
    return tmp_path / "envault_keys"


class TestSaveKeypair:
    def test_creates_directory_if_missing(self, key_dir: Path) -> None:
        assert not key_dir.exists()
        save_keypair(FAKE_PRIVATE, FAKE_PUBLIC, key_dir=key_dir)
        assert key_dir.is_dir()

    def test_writes_both_key_files(self, key_dir: Path) -> None:
        save_keypair(FAKE_PRIVATE, FAKE_PUBLIC, key_dir=key_dir)
        assert (key_dir / PRIVATE_KEY_FILE).read_text() == FAKE_PRIVATE
        assert (key_dir / PUBLIC_KEY_FILE).read_text() == FAKE_PUBLIC

    def test_private_key_has_restrictive_permissions(self, key_dir: Path) -> None:
        save_keypair(FAKE_PRIVATE, FAKE_PUBLIC, key_dir=key_dir)
        mode = (key_dir / PRIVATE_KEY_FILE).stat().st_mode
        assert stat.S_IMODE(mode) == 0o600

    def test_returns_key_directory(self, key_dir: Path) -> None:
        result = save_keypair(FAKE_PRIVATE, FAKE_PUBLIC, key_dir=key_dir)
        assert result == key_dir

    def test_raises_on_unwritable_parent(self, tmp_path: Path) -> None:
        locked = tmp_path / "locked"
        locked.mkdir(mode=0o444)
        try:
            with pytest.raises(KeystoreError, match="Cannot create key directory"):
                save_keypair(FAKE_PRIVATE, FAKE_PUBLIC, key_dir=locked / "sub")
        finally:
            locked.chmod(0o755)  # restore so tmp_path cleanup works


class TestLoadKeypair:
    def test_returns_private_and_public_key(self, key_dir: Path) -> None:
        save_keypair(FAKE_PRIVATE, FAKE_PUBLIC, key_dir=key_dir)
        priv, pub = load_keypair(key_dir=key_dir)
        assert priv == FAKE_PRIVATE
        assert pub == FAKE_PUBLIC

    def test_strips_trailing_whitespace(self, key_dir: Path) -> None:
        key_dir.mkdir()
        (key_dir / PRIVATE_KEY_FILE).write_text(FAKE_PRIVATE + "\n")
        (key_dir / PUBLIC_KEY_FILE).write_text(FAKE_PUBLIC + "  ")
        priv, pub = load_keypair(key_dir=key_dir)
        assert priv == FAKE_PRIVATE
        assert pub == FAKE_PUBLIC

    def test_raises_when_private_key_missing(self, key_dir: Path) -> None:
        key_dir.mkdir()
        (key_dir / PUBLIC_KEY_FILE).write_text(FAKE_PUBLIC)
        with pytest.raises(KeystoreError, match="Key file not found"):
            load_keypair(key_dir=key_dir)

    def test_raises_when_public_key_missing(self, key_dir: Path) -> None:
        key_dir.mkdir()
        (key_dir / PRIVATE_KEY_FILE).write_text(FAKE_PRIVATE)
        with pytest.raises(KeystoreError, match="Key file not found"):
            load_keypair(key_dir=key_dir)


class TestKeypairExists:
    def test_returns_false_when_no_keys(self, key_dir: Path) -> None:
        key_dir.mkdir()
        assert keypair_exists(key_dir=key_dir) is False

    def test_returns_true_after_save(self, key_dir: Path) -> None:
        save_keypair(FAKE_PRIVATE, FAKE_PUBLIC, key_dir=key_dir)
        assert keypair_exists(key_dir=key_dir) is True

    def test_returns_false_when_only_one_key_present(self, key_dir: Path) -> None:
        key_dir.mkdir()
        (key_dir / PRIVATE_KEY_FILE).write_text(FAKE_PRIVATE)
        assert keypair_exists(key_dir=key_dir) is False
