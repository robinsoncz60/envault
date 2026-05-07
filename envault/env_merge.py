"""Merge two .env file contents with configurable conflict resolution."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class MergeError(Exception):
    """Raised when a merge operation fails."""


class ConflictStrategy(str, Enum):
    OURS = "ours"       # keep value from base
    THEIRS = "theirs"   # keep value from incoming
    ERROR = "error"     # raise on any conflict


@dataclass
class MergeConflict:
    key: str
    base_value: str
    incoming_value: str

    def __str__(self) -> str:
        return f"CONFLICT {self.key!r}: {self.base_value!r} vs {self.incoming_value!r}"


@dataclass
class MergeResult:
    merged: str
    conflicts: List[MergeConflict] = field(default_factory=list)
    added: List[str] = field(default_factory=list)
    removed: List[str] = field(default_factory=list)

    @property
    def has_conflicts(self) -> bool:
        return bool(self.conflicts)

    def __str__(self) -> str:
        lines = []
        if self.added:
            lines.append(f"Added: {', '.join(self.added)}")
        if self.removed:
            lines.append(f"Removed: {', '.join(self.removed)}")
        if self.conflicts:
            lines.append(f"Conflicts: {', '.join(c.key for c in self.conflicts)}")
        return " | ".join(lines) if lines else "Clean merge"


def _parse_env(text: str) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        result[key.strip()] = value.strip()
    return result


def _render_env(pairs: Dict[str, str]) -> str:
    return "\n".join(f"{k}={v}" for k, v in pairs.items()) + "\n"


def merge_envs(
    base: str,
    incoming: str,
    strategy: ConflictStrategy = ConflictStrategy.THEIRS,
) -> MergeResult:
    """Merge two env strings, returning a MergeResult."""
    base_map = _parse_env(base)
    incoming_map = _parse_env(incoming)

    conflicts: List[MergeConflict] = []
    added = [k for k in incoming_map if k not in base_map]
    removed = [k for k in base_map if k not in incoming_map]

    merged: Dict[str, str] = dict(base_map)

    for key, inc_val in incoming_map.items():
        if key not in base_map:
            merged[key] = inc_val
        elif base_map[key] != inc_val:
            conflict = MergeConflict(key=key, base_value=base_map[key], incoming_value=inc_val)
            conflicts.append(conflict)
            if strategy == ConflictStrategy.ERROR:
                raise MergeError(f"Conflict on key {key!r} and strategy is 'error'")
            elif strategy == ConflictStrategy.THEIRS:
                merged[key] = inc_val
            # OURS: keep existing value in merged

    for key in list(merged):
        if key not in incoming_map:
            del merged[key]

    return MergeResult(
        merged=_render_env(merged),
        conflicts=conflicts,
        added=added,
        removed=removed,
    )
