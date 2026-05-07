"""Access policy enforcement for envault environments."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import List, Optional

from envault.exceptions import EnvaultError


class PolicyError(EnvaultError):
    """Raised when a policy operation fails."""


_VALID_ACTIONS = frozenset({"push", "pull", "rotate", "share", "audit"})


@dataclass
class PolicyRule:
    """A single allow/deny rule binding a principal to a set of actions."""

    principal: str
    actions: List[str]
    allow: bool = True

    def __post_init__(self) -> None:
        invalid = [a for a in self.actions if a not in _VALID_ACTIONS]
        if invalid:
            raise PolicyError(f"Unknown action(s): {', '.join(invalid)}")

    def to_dict(self) -> dict:
        return {"principal": self.principal, "actions": self.actions, "allow": self.allow}

    @classmethod
    def from_dict(cls, data: dict) -> "PolicyRule":
        try:
            return cls(
                principal=data["principal"],
                actions=data["actions"],
                allow=data.get("allow", True),
            )
        except KeyError as exc:
            raise PolicyError(f"Missing policy rule field: {exc}") from exc


@dataclass
class Policy:
    """Collection of rules for an environment."""

    env: str
    rules: List[PolicyRule] = field(default_factory=list)

    def is_allowed(self, principal: str, action: str) -> bool:
        """Return True if *principal* is permitted to perform *action*.

        Rules are evaluated in order; the first matching rule wins.
        A wildcard principal (``"*"``) matches any principal.
        """
        for rule in self.rules:
            if rule.principal in (principal, "*") and action in rule.actions:
                return rule.allow
        return False

    def add_rule(self, rule: PolicyRule) -> None:
        """Append *rule* to the policy, replacing any existing rule for the same principal.

        If a rule already exists for *rule.principal*, it is removed before
        appending the new one so that the latest definition always takes effect.
        """
        self.rules = [r for r in self.rules if r.principal != rule.principal]
        self.rules.append(rule)

    def to_dict(self) -> dict:
        return {"env": self.env, "rules": [r.to_dict() for r in self.rules]}

    @classmethod
    def from_dict(cls, data: dict) -> "Policy":
        try:
            rules = [PolicyRule.from_dict(r) for r in data.get("rules", [])]
            return cls(env=data["env"], rules=rules)
        except KeyError as exc:
            raise PolicyError(f"Missing policy field: {exc}") from exc

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, raw: str) -> "Policy":
        try:
            return cls.from_dict(json.loads(raw))
        except json.JSONDecodeError as exc:
            raise PolicyError(f"Invalid policy JSON: {exc}") from exc


def check(policy: Policy, principal: str, action: str) -> None:
    """Raise *PolicyError* if *principal* cannot perform *action*."""
    if not policy.is_allowed(principal, action):
        raise PolicyError(
            f"Principal '{principal}' is not allowed to perform '{action}' "
            f"on env '{policy.env}'."
        )
