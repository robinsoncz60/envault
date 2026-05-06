"""Redaction utilities — mask sensitive values in .env output."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from envault.exceptions import EnvaultError


class RedactError(EnvaultError):
    """Raised when redaction fails."""


# Keys whose values are always fully masked regardless of user config.
_ALWAYS_REDACT: frozenset[str] = frozenset(
    {
        "PASSWORD",
        "PASSWD",
        "SECRET",
        "SECRET_KEY",
        "API_KEY",
        "PRIVATE_KEY",
        "TOKEN",
        "AUTH_TOKEN",
        "ACCESS_TOKEN",
        "DATABASE_URL",
    }
)

_MASK = "********"
_PARTIAL_VISIBLE = 4  # chars to show at start/end for partial masking


@dataclass
class RedactResult:
    original: str
    redacted: str
    masked_keys: List[str] = field(default_factory=list)

    def __str__(self) -> str:  # pragma: no cover
        return self.redacted


def _partial_mask(value: str) -> str:
    """Show first and last N chars; mask the middle."""
    if len(value) <= _PARTIAL_VISIBLE * 2:
        return _MASK
    return value[:_PARTIAL_VISIBLE] + "****" + value[-_PARTIAL_VISIBLE:]


def _parse_env(text: str) -> Dict[str, str]:
    """Return {key: raw_line} mapping for non-comment, non-blank lines."""
    result: Dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        key, _, _val = stripped.partition("=")
        result[key.strip()] = line
    return result


def redact(
    env_text: str,
    *,
    extra_keys: Optional[List[str]] = None,
    partial: bool = False,
) -> RedactResult:
    """Return a RedactResult with sensitive values masked.

    Args:
        env_text:   Raw contents of a .env file.
        extra_keys: Additional key names to redact (case-insensitive).
        partial:    If True, show a few chars at each end instead of full mask.
    """
    sensitive: frozenset[str] = _ALWAYS_REDACT
    if extra_keys:
        sensitive = sensitive | frozenset(k.upper() for k in extra_keys)

    masked_keys: List[str] = []
    output_lines: List[str] = []

    for line in env_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            output_lines.append(line)
            continue

        key, _, value = stripped.partition("=")
        key_upper = key.strip().upper()

        # Also redact any key that *contains* a sensitive word.
        should_redact = key_upper in sensitive or any(
            s in key_upper for s in sensitive
        )

        if should_redact:
            mask = _partial_mask(value) if partial else _MASK
            output_lines.append(f"{key.strip()}={mask}")
            masked_keys.append(key.strip())
        else:
            output_lines.append(line)

    redacted_text = "\n".join(output_lines)
    if env_text.endswith("\n"):
        redacted_text += "\n"

    return RedactResult(
        original=env_text,
        redacted=redacted_text,
        masked_keys=masked_keys,
    )
