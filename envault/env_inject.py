"""env_inject.py – inject decrypted env vars into a subprocess environment."""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from envault.bundle import decode_bundle
from envault.crypto import decrypt
from envault.exceptions import EnvaultError


class InjectError(EnvaultError):
    """Raised when injection fails."""


@dataclass
class InjectResult:
    command: List[str]
    returncode: int
    injected_keys: List[str] = field(default_factory=list)

    def __str__(self) -> str:  # pragma: no cover
        keys = ", ".join(self.injected_keys) if self.injected_keys else "(none)"
        return f"Command {self.command!r} exited {self.returncode}; injected keys: {keys}"


def _parse_env(plaintext: str) -> Dict[str, str]:
    """Parse KEY=VALUE lines, ignoring comments and blanks."""
    result: Dict[str, str] = {}
    for line in plaintext.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        result[key.strip()] = value.strip()
    return result


def inject(
    *,
    command: List[str],
    ciphertext: bytes,
    private_key_path: str,
    extra_env: Optional[Dict[str, str]] = None,
    override: bool = True,
) -> InjectResult:
    """Decrypt *ciphertext* and run *command* with the env vars injected.

    Args:
        command: The subprocess command to execute.
        ciphertext: Encrypted .env bundle ciphertext.
        private_key_path: Path to the age private key file.
        extra_env: Additional env vars to merge in (applied after decryption).
        override: If True, decrypted keys override existing process env vars.

    Returns:
        InjectResult with the command, return code, and injected key names.

    Raises:
        InjectError: On decryption failure or empty command.
    """
    if not command:
        raise InjectError("command must not be empty")

    try:
        plaintext = decrypt(ciphertext, private_key_path)
    except Exception as exc:
        raise InjectError(f"decryption failed: {exc}") from exc

    parsed = _parse_env(plaintext.decode())
    if extra_env:
        parsed.update(extra_env)

    env = dict(os.environ)
    if override:
        env.update(parsed)
    else:
        for k, v in parsed.items():
            env.setdefault(k, v)

    try:
        proc = subprocess.run(command, env=env)  # noqa: S603
    except FileNotFoundError as exc:
        raise InjectError(f"command not found: {command[0]!r}") from exc

    return InjectResult(
        command=command,
        returncode=proc.returncode,
        injected_keys=list(parsed.keys()),
    )
