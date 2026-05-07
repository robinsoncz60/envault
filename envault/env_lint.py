"""Lint .env files for common issues like duplicate keys, empty values, and suspicious patterns."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


class LintError(Exception):
    """Raised when the linter itself fails (not for lint findings)."""


@dataclass
class LintIssue:
    line: int
    key: str
    code: str
    message: str

    def __str__(self) -> str:
        return f"line {self.line}: [{self.code}] {self.key!r} — {self.message}"


@dataclass
class LintResult:
    issues: List[LintIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return len(self.issues) == 0

    def __str__(self) -> str:
        if self.ok:
            return "No issues found."
        return "\n".join(str(i) for i in self.issues)


_SUSPICIOUS_KEYS = re.compile(
    r"(password|secret|token|key|api_key|private)", re.IGNORECASE
)
_PLACEHOLDER = re.compile(r"^(todo|fixme|changeme|xxx|<[^>]+>|\$\{[^}]+\})$", re.IGNORECASE)


def lint(source: str) -> LintResult:
    """Lint the contents of a .env file and return a LintResult."""
    issues: List[LintIssue] = []
    seen: dict[str, int] = {}

    for lineno, raw in enumerate(source.splitlines(), start=1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if "=" not in stripped:
            issues.append(LintIssue(lineno, stripped, "E001", "Line is not a valid KEY=VALUE pair"))
            continue

        key, _, value = stripped.partition("=")
        key = key.strip()
        value = value.strip()

        if not key:
            issues.append(LintIssue(lineno, "", "E002", "Empty key name"))
            continue

        if key in seen:
            issues.append(LintIssue(lineno, key, "W001", f"Duplicate key (first seen on line {seen[key]})"))
        else:
            seen[key] = lineno

        if value == "":
            issues.append(LintIssue(lineno, key, "W002", "Empty value"))

        if _SUSPICIOUS_KEYS.search(key) and _PLACEHOLDER.match(value):
            issues.append(LintIssue(lineno, key, "W003", "Sensitive key appears to have a placeholder value"))

        if value.startswith(("'", '"')) and not (
            (value.startswith("'") and value.endswith("'")) or
            (value.startswith('"') and value.endswith('"'))
        ):
            issues.append(LintIssue(lineno, key, "W004", "Value has unmatched quote"))

    return LintResult(issues=issues)


def lint_file(path: Path) -> LintResult:
    """Read a .env file from disk and lint it."""
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise LintError(f"Cannot read {path}: {exc}") from exc
    return lint(source)
