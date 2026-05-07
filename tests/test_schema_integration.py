"""Integration tests: schema rules round-trip through JSON and validate real envs."""

from __future__ import annotations

import json

from envault.env_schema import SchemaRule, validate_env


def _rules_to_json(rules: list[SchemaRule]) -> str:
    return json.dumps([r.to_dict() for r in rules])


def _rules_from_json(raw: str) -> list[SchemaRule]:
    return [SchemaRule.from_dict(d) for d in json.loads(raw)]


def test_schema_roundtrip_through_json():
    rules = [
        SchemaRule(key="APP_ENV", required=True, pattern=r"(dev|staging|production)"),
        SchemaRule(key="SECRET_KEY", required=True, pattern=r".{16,}"),
        SchemaRule(key="DEBUG", required=False),
    ]
    restored = _rules_from_json(_rules_to_json(rules))
    assert restored == rules


def test_full_validate_chain_passes():
    rules = [
        SchemaRule(key="APP_ENV", required=True, pattern=r"(dev|staging|production)"),
        SchemaRule(key="PORT", required=True, pattern=r"\d+"),
    ]
    env = {"APP_ENV": "production", "PORT": "443"}
    result = validate_env(env, rules)
    assert result.ok


def test_full_validate_chain_catches_all_violations():
    rules = [
        SchemaRule(key="APP_ENV", required=True, pattern=r"(dev|staging|production)"),
        SchemaRule(key="PORT", required=True, pattern=r"\d+"),
        SchemaRule(key="DATABASE_URL", required=True),
    ]
    env = {"APP_ENV": "unknown", "PORT": "abc"}  # DATABASE_URL missing
    result = validate_env(env, rules)
    assert not result.ok
    keys = {v.key for v in result.violations}
    assert keys == {"APP_ENV", "PORT", "DATABASE_URL"}


def test_optional_keys_never_cause_violations_when_absent():
    rules = [
        SchemaRule(key="SENTRY_DSN", required=False, pattern=r"https://.+"),
    ]
    result = validate_env({}, rules)
    assert result.ok


def test_optional_key_with_bad_pattern_still_violates():
    rules = [SchemaRule(key="SENTRY_DSN", required=False, pattern=r"https://.+")]
    result = validate_env({"SENTRY_DSN": "not-a-url"}, rules)
    assert not result.ok
    assert result.violations[0].key == "SENTRY_DSN"
