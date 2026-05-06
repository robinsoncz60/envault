"""Watch a local .env file for changes and auto-push on modification."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from envault.exceptions import EnvaultError


class WatchError(EnvaultError):
    """Raised when the watch loop encounters an unrecoverable error."""


@dataclass
class WatchState:
    path: Path
    last_hash: Optional[str] = None

    def current_hash(self) -> str:
        """Return the SHA-256 hex digest of the watched file."""
        data = self.path.read_bytes()
        return hashlib.sha256(data).hexdigest()

    def has_changed(self) -> bool:
        """Return True if the file content differs from the last recorded hash."""
        try:
            current = self.current_hash()
        except FileNotFoundError:
            return False
        changed = current != self.last_hash
        if changed:
            self.last_hash = current
        return changed

    def seed(self) -> None:
        """Record the current hash without triggering a change event."""
        try:
            self.last_hash = self.current_hash()
        except FileNotFoundError:
            self.last_hash = None


def watch(
    env_path: Path,
    on_change: Callable[[Path], None],
    interval: float = 1.0,
    max_iterations: Optional[int] = None,
) -> None:
    """Poll *env_path* every *interval* seconds and call *on_change* when it changes.

    Args:
        env_path: Path to the .env file to watch.
        on_change: Callback invoked with the path whenever a change is detected.
        interval: Polling interval in seconds.
        max_iterations: Stop after this many iterations (useful for testing).
    """
    if not env_path.exists():
        raise WatchError(f"File not found: {env_path}")

    state = WatchState(path=env_path)
    state.seed()

    iterations = 0
    while max_iterations is None or iterations < max_iterations:
        time.sleep(interval)
        try:
            if state.has_changed():
                on_change(env_path)
        except Exception as exc:  # pragma: no cover
            raise WatchError(f"Error during watch callback: {exc}") from exc
        iterations += 1
