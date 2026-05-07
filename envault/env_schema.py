"""Schema validation for .env files — check required keys, types, and patterns."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from envault.exceptions import EnvaultError


class SchemaError(EnvaultError):
    """Raised when schema operations fail."""


@dataclass
class SchemaRule:
    key: str
    required: bool = True
    pattern: Optional[str] = None
    description: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "required": self.required,
            "pattern": self.pattern,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SchemaRule":
        for f in ("key",):
            if f not in data:
                raise SchemaError(f"SchemaRule missing field: {f!r}")
        return cls(
            key=data["key"],
            required=data.get("required", True),
            pattern=data.get("pattern"),
            description=data.get("description"),
        )


@dataclass
class SchemaViolation:
    key: str
    message: str

    def __str__(self) -> str:
        return f"{self.key}: {self.message}"


@dataclass
class SchemaResult:
    violations: List[SchemaViolation] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return len(self.violations) == 0

    def __str__(self) -> str:
        if self.ok:
            return "Schema OK — no violations found."
        lines = [f"Schema violations ({len(self.violations)}):"] + [
            f"  - {v}" for v in self.violations
        ]
        return "\n".join(lines)


def validate_env(
    env: Dict[str, str], rules: List[SchemaRule]
) -> SchemaResult:
    """Validate a parsed env dict against a list of SchemaRules."""
    violations: List[SchemaViolation] = []
    for rule in rules:
        value = env.get(rule.key)
        if value is None:
            if rule.required:
                violations.append(
                    SchemaViolation(rule.key, "required key is missing")
                )
            continue
        if rule.pattern and not re.fullmatch(rule.pattern, value):
            violations.append(
                SchemaViolation(
                    rule.key,
                    f"value does not match pattern {rule.pattern!r}",
                )
            )
    return SchemaResult(violations=violations)
