"""Filter .env keys by prefix, pattern, or explicit list."""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


class FilterError(Exception):
    """Raised when filtering fails."""


@dataclass
class FilterResult:
    matched: Dict[str, str]
    excluded: Dict[str, str]

    def __str__(self) -> str:
        return (
            f"FilterResult(matched={len(self.matched)}, "
            f"excluded={len(self.excluded)})"
        )


def _parse_env(text: str) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        result[key.strip()] = value.strip()
    return result


def filter_env(
    plaintext: str,
    *,
    prefixes: Optional[List[str]] = None,
    patterns: Optional[List[str]] = None,
    keys: Optional[List[str]] = None,
    invert: bool = False,
) -> FilterResult:
    """Filter env vars by prefix, glob pattern, or explicit key list.

    At least one of *prefixes*, *patterns*, or *keys* must be supplied.
    If *invert* is True the match logic is flipped (exclude matched keys).
    """
    if not any([prefixes, patterns, keys]):
        raise FilterError(
            "At least one of 'prefixes', 'patterns', or 'keys' must be provided."
        )

    env = _parse_env(plaintext)

    def _matches(k: str) -> bool:
        if prefixes and any(k.startswith(p) for p in prefixes):
            return True
        if patterns and any(fnmatch.fnmatch(k, p) for p in patterns):
            return True
        if keys and k in keys:
            return True
        return False

    matched: Dict[str, str] = {}
    excluded: Dict[str, str] = {}

    for k, v in env.items():
        hit = _matches(k)
        if hit ^ invert:
            matched[k] = v
        else:
            excluded[k] = v

    return FilterResult(matched=matched, excluded=excluded)
