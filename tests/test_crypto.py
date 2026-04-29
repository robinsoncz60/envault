"""Tests for envault.crypto module."""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from envault.crypto import encrypt, decrypt, generate_keypair, CryptoError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_run(returncode=0, stdout=b"", stderr=b""):
    mock = MagicMock()
    mock.returncode = returncode
    mock.stdout = stdout
    mock.stderr = stderr
    return mock


# ---------------------------------------------------------------------------
# encrypt
# ---------------------------------------------------------------------------

class TestEncrypt:
    def test_returns_stdout_on_success(self):
        mock_result = _make_mock_run(stdout=b"-----BEGIN AGE ENCRYPTED FILE-----\n")
        with patch("envault.crypto.subprocess.run", return_value=mock_result) as mock_run:
            result = encrypt(b"SECRET=abc", "age1abc123")
        assert result == b"-----BEGIN AGE ENCRYPTED FILE-----\n"
        mock_run.assert_called_once()

    def test_raises_on_nonzero_returncode(self):
        mock_result = _make_mock_run(returncode=1, stderr=b"bad recipient")
        with patch("envault.crypto.subprocess.run", return_value=mock_result):
            with pytest.raises(CryptoError, match="Encryption failed"):
                encrypt(b"SECRET=abc", "bad-key")

    def test_raises_when_age_not_found(self):
        with patch("envault.crypto.subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(CryptoError, match="'age' binary not found"):
                encrypt(b"data", "age1abc")


# ---------------------------------------------------------------------------
# decrypt
# ---------------------------------------------------------------------------

class TestDecrypt:
    def test_returns_plaintext_on_success(self, tmp_path):
        identity_file = tmp_path / "key.txt"
        identity_file.write_text("AGE-SECRET-KEY-1...")

        mock_result = _make_mock_run(stdout=b"SECRET=abc")
        with patch("envault.crypto.subprocess.run", return_value=mock_result):
            result = decrypt(b"ciphertext", identity_file)
        assert result == b"SECRET=abc"

    def test_raises_if_identity_missing(self, tmp_path):
        with pytest.raises(CryptoError, match="Identity file not found"):
            decrypt(b"data", tmp_path / "nonexistent.txt")

    def test_raises_on_nonzero_returncode(self, tmp_path):
        identity_file = tmp_path / "key.txt"
        identity_file.write_text("AGE-SECRET-KEY-1...")

        mock_result = _make_mock_run(returncode=1, stderr=b"wrong key")
        with patch("envault.crypto.subprocess.run", return_value=mock_result):
            with pytest.raises(CryptoError, match="Decryption failed"):
                decrypt(b"ciphertext", identity_file)


# ---------------------------------------------------------------------------
# generate_keypair
# ---------------------------------------------------------------------------

class TestGenerateKeypair:
    def test_returns_public_and_private_key(self):
        mock_result = _make_mock_run(
            stdout=b"AGE-SECRET-KEY-1ABCDEF\n",
            stderr=b"# created: 2024-01-01\n# public key: age1xyz789\n",
        )
        with patch("envault.crypto.subprocess.run", return_value=mock_result):
            pub, priv = generate_keypair()
        assert pub == "age1xyz789"
        assert "AGE-SECRET-KEY" in priv

    def test_raises_when_age_keygen_not_found(self):
        with patch("envault.crypto.subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(CryptoError, match="'age-keygen' binary not found"):
                generate_keypair()
