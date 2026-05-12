"""Integration tests for env_inject: full parse → inject → subprocess chain."""
from __future__ import annotations

import os
import sys
import textwrap
from unittest.mock import patch

import pytest

from envault.env_inject import InjectError, inject, _parse_env


PLAINTEXT = textwrap.dedent("""\
    # database config
    DB_HOST=localhost
    DB_PORT=5432

    SECRET_KEY=supersecret
""")


def _fake_decrypt(ciphertext, private_key_path):
    return PLAINTEXT.encode()


@patch("envault.env_inject.decrypt", side_effect=_fake_decrypt)
def test_full_inject_chain_passes_vars_to_subprocess(mock_decrypt):
    """Decrypted vars should be visible inside the child process."""
    result = inject(
        command=[sys.executable, "-c", "import os, sys; sys.exit(0 if os.environ.get('DB_HOST')=='localhost' else 1)"],
        ciphertext=b"enc",
        private_key_path="/fake/key",
    )
    assert result.returncode == 0
    assert "DB_HOST" in result.injected_keys
    assert "SECRET_KEY" in result.injected_keys


@patch("envault.env_inject.decrypt", side_effect=_fake_decrypt)
def test_no_override_does_not_replace_existing_env(mock_decrypt):
    """With override=False, a pre-existing env var must not be overwritten."""
    with patch.dict(os.environ, {"DB_HOST": "original"}):
        result = inject(
            command=[
                sys.executable,
                "-c",
                "import os, sys; sys.exit(0 if os.environ['DB_HOST']=='original' else 1)",
            ],
            ciphertext=b"enc",
            private_key_path="/fake/key",
            override=False,
        )
    assert result.returncode == 0


@patch("envault.env_inject.decrypt", side_effect=_fake_decrypt)
def test_extra_env_available_in_subprocess(mock_decrypt):
    result = inject(
        command=[
            sys.executable,
            "-c",
            "import os, sys; sys.exit(0 if os.environ.get('EXTRA')=='hi' else 1)",
        ],
        ciphertext=b"enc",
        private_key_path="/fake/key",
        extra_env={"EXTRA": "hi"},
    )
    assert result.returncode == 0
    assert "EXTRA" in result.injected_keys


@patch("envault.env_inject.decrypt", side_effect=_fake_decrypt)
def test_nonzero_returncode_propagated(mock_decrypt):
    result = inject(
        command=[sys.executable, "-c", "import sys; sys.exit(42)"],
        ciphertext=b"enc",
        private_key_path="/fake/key",
    )
    assert result.returncode == 42


def test_empty_command_raises_before_decrypt():
    with pytest.raises(InjectError, match="must not be empty"):
        inject(command=[], ciphertext=b"enc", private_key_path="/key")
