"""Tests for envault.env_schema."""

from __future__ import annotations

import pytest

from envault.env_schema import (
    SchemaError,
    SchemaResult,
    SchemaRule,
    SchemaViolation,
    validate_env,
)


# ---------------------------------------------------------------------------
# SchemaRule
# ---------------------------------------------------------------------------

class TestSchemaRule:
    def test_to_dict_roundtrip(self):
        rule = SchemaRule(key="DATABASE_URL", required=True, pattern=r"postgres://.+",
                          description="main db")
        assert SchemaRule.from_dict(rule.to_dict()) == rule

    def test_from_dict_missing_key_raises(self):
        with pytest.raises(SchemaError, match="missing field"):
            SchemaRule.from_dict({"required": True})

    def test_defaults(self):
        rule = SchemaRule.from_dict({"key": "FOO"})
        assert rule.required is True
        assert rule.pattern is None
        assert rule.description is None


# ---------------------------------------------------------------------------
# SchemaViolation / SchemaResult
# ---------------------------------------------------------------------------

def test_violation_str():
    v = SchemaViolation(key="FOO", message="required key is missing")
    assert "FOO" in str(v)
    assert "required" in str(v)


def test_schema_result_ok_when_empty():
    r = SchemaResult()
    assert r.ok is True
    assert "OK" in str(r)


def test_schema_result_not_ok_with_violations():
    r = SchemaResult(violations=[SchemaViolation("X", "bad")])
    assert r.ok is False
    assert "violations" in str(r).lower()


# ---------------------------------------------------------------------------
# validate_env
# ---------------------------------------------------------------------------

class TestValidateEnv:
    def _rules(self):
        return [
            SchemaRule(key="APP_ENV", required=True),
            SchemaRule(key="PORT", required=True, pattern=r"\d+"),
            SchemaRule(key="OPTIONAL_KEY", required=False),
        ]

    def test_valid_env_returns_no_violations(self):
        env = {"APP_ENV": "production", "PORT": "8080"}
        result = validate_env(env, self._rules())
        assert result.ok

    def test_missing_required_key(self):
        env = {"PORT": "8080"}
        result = validate_env(env, self._rules())
        assert not result.ok
        assert any(v.key == "APP_ENV" for v in result.violations)

    def test_pattern_mismatch(self):
        env = {"APP_ENV": "prod", "PORT": "not-a-number"}
        result = validate_env(env, self._rules())
        assert not result.ok
        assert any(v.key == "PORT" for v in result.violations)

    def test_optional_missing_key_not_a_violation(self):
        env = {"APP_ENV": "dev", "PORT": "3000"}
        result = validate_env(env, self._rules())
        assert result.ok

    def test_multiple_violations_collected(self):
        result = validate_env({}, self._rules())
        required_keys = {v.key for v in result.violations}
        assert "APP_ENV" in required_keys
        assert "PORT" in required_keys

    def test_pattern_match_passes(self):
        rule = SchemaRule(key="SECRET", pattern=r"[A-Z0-9]{32}")
        env = {"SECRET": "A" * 32}
        result = validate_env(env, [rule])
        assert result.ok
