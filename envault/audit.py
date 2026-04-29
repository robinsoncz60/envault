"""Audit log support — records push/pull events locally."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from envault.exceptions import EnvaultError


class AuditError(EnvaultError):
    """Raised when audit log operations fail."""


_DEFAULT_LOG_PATH = Path.home() / ".envault" / "audit.log"


@dataclass
class AuditEntry:
    action: str        # "push" or "pull"
    env: str           # environment name, e.g. "production"
    version: str       # version string
    user: str          # os username
    timestamp: str     # ISO-8601

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AuditEntry":
        return cls(**data)

    def __str__(self) -> str:
        return f"[{self.timestamp}] {self.action} env={self.env} version={self.version} user={self.user}"


def _log_path(override: Path | None = None) -> Path:
    return override if override is not None else _DEFAULT_LOG_PATH


def record(
    action: str,
    env: str,
    version: str,
    log_file: Path | None = None,
) -> AuditEntry:
    """Append an audit entry to the log and return it."""
    entry = AuditEntry(
        action=action,
        env=env,
        version=version,
        user=os.getlogin(),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    path = _log_path(log_file)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as fh:
            fh.write(json.dumps(entry.to_dict()) + "\n")
    except OSError as exc:
        raise AuditError(f"Failed to write audit log: {exc}") from exc
    return entry


def read_log(log_file: Path | None = None) -> List[AuditEntry]:
    """Return all audit entries from the log, oldest first."""
    path = _log_path(log_file)
    if not path.exists():
        return []
    entries: List[AuditEntry] = []
    try:
        with path.open() as fh:
            for line in fh:
                line = line.strip()
                if line:
                    entries.append(AuditEntry.from_dict(json.loads(line)))
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        raise AuditError(f"Failed to read audit log: {exc}") from exc
    return entries
