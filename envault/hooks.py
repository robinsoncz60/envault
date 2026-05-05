"""Pre/post hook execution for push and pull operations."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from envault.exceptions import EnvaultError


class HookError(EnvaultError):
    """Raised when a hook script fails or cannot be executed."""


@dataclass
class HookConfig:
    pre_push: List[str] = field(default_factory=list)
    post_push: List[str] = field(default_factory=list)
    pre_pull: List[str] = field(default_factory=list)
    post_pull: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "HookConfig":
        return cls(
            pre_push=data.get("pre_push", []),
            post_push=data.get("post_push", []),
            pre_pull=data.get("pre_pull", []),
            post_pull=data.get("post_pull", []),
        )


def run_hooks(
    commands: List[str],
    cwd: Optional[Path] = None,
    env: Optional[dict] = None,
) -> None:
    """Execute a list of shell hook commands sequentially.

    Args:
        commands: Shell command strings to run in order.
        cwd: Working directory for subprocess execution.
        env: Optional environment variables to pass to subprocesses.

    Raises:
        HookError: If any command exits with a non-zero return code.
    """
    for cmd in commands:
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=cwd,
                env=env,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as exc:
            raise HookError(f"Hook command not found: {cmd}") from exc

        if result.returncode != 0:
            raise HookError(
                f"Hook command failed (exit {result.returncode}): {cmd}\n"
                f"{result.stderr.strip()}"
            )
