"""Generate human-readable diff reports between two .env versions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


class DiffReportError(Exception):
    pass


@dataclass
class DiffReportEntry:
    key: str
    status: str  # 'added' | 'removed' | 'changed' | 'unchanged'
    old_value: Optional[str] = None
    new_value: Optional[str] = None

    def __str__(self) -> str:
        if self.status == "added":
            return f"+ {self.key}={self.new_value}"
        if self.status == "removed":
            return f"- {self.key}={self.old_value}"
        if self.status == "changed":
            return f"~ {self.key}: {self.old_value!r} -> {self.new_value!r}"
        return f"  {self.key}={self.new_value}"


@dataclass
class DiffReport:
    from_version: str
    to_version: str
    entries: List[DiffReportEntry] = field(default_factory=list)

    @property
    def added(self) -> List[DiffReportEntry]:
        return [e for e in self.entries if e.status == "added"]

    @property
    def removed(self) -> List[DiffReportEntry]:
        return [e for e in self.entries if e.status == "removed"]

    @property
    def changed(self) -> List[DiffReportEntry]:
        return [e for e in self.entries if e.status == "changed"]

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.removed or self.changed)

    def __str__(self) -> str:
        lines = [
            f"diff {self.from_version} -> {self.to_version}",
            f"  {len(self.added)} added, {len(self.removed)} removed, {len(self.changed)} changed",
        ]
        for entry in sorted(self.entries, key=lambda e: e.key):
            if entry.status != "unchanged":
                lines.append(f"  {entry}")
        return "\n".join(lines)


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


def build_report(from_version: str, to_version: str, old_text: str, new_text: str) -> DiffReport:
    """Compare two plaintext .env blobs and return a structured DiffReport."""
    old = _parse_env(old_text)
    new = _parse_env(new_text)
    all_keys = sorted(set(old) | set(new))
    entries: List[DiffReportEntry] = []
    for key in all_keys:
        if key in old and key not in new:
            entries.append(DiffReportEntry(key=key, status="removed", old_value=old[key]))
        elif key not in old and key in new:
            entries.append(DiffReportEntry(key=key, status="added", new_value=new[key]))
        elif old[key] != new[key]:
            entries.append(DiffReportEntry(key=key, status="changed", old_value=old[key], new_value=new[key]))
        else:
            entries.append(DiffReportEntry(key=key, status="unchanged", new_value=new[key]))
    return DiffReport(from_version=from_version, to_version=to_version, entries=entries)
