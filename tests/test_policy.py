"""Tests for envault.policy."""
import json
import pytest

from envault.policy import Policy, PolicyError, PolicyRule, check


# ---------------------------------------------------------------------------
# PolicyRule
# ---------------------------------------------------------------------------

class TestPolicyRule:
    def test_to_dict_roundtrip(self):
        rule = PolicyRule(principal="alice", actions=["push", "pull"], allow=True)
        assert PolicyRule.from_dict(rule.to_dict()).principal == "alice"

    def test_unknown_action_raises(self):
        with pytest.raises(PolicyError, match="Unknown action"):
            PolicyRule(principal="bob", actions=["delete"])

    def test_from_dict_missing_field_raises(self):
        with pytest.raises(PolicyError, match="Missing policy rule field"):
            PolicyRule.from_dict({"actions": ["push"]})

    def test_allow_defaults_to_true(self):
        rule = PolicyRule.from_dict({"principal": "alice", "actions": ["pull"]})
        assert rule.allow is True


# ---------------------------------------------------------------------------
# Policy
# ---------------------------------------------------------------------------

class TestPolicy:
    def _make(self) -> Policy:
        return Policy(
            env="production",
            rules=[
                PolicyRule(principal="alice", actions=["push", "pull"], allow=True),
                PolicyRule(principal="bob", actions=["pull"], allow=True),
                PolicyRule(principal="bob", actions=["push"], allow=False),
            ],
        )

    def test_allowed_action_returns_true(self):
        policy = self._make()
        assert policy.is_allowed("alice", "push") is True

    def test_denied_action_returns_false(self):
        policy = self._make()
        assert policy.is_allowed("bob", "push") is False

    def test_unknown_principal_returns_false(self):
        policy = self._make()
        assert policy.is_allowed("charlie", "pull") is False

    def test_wildcard_principal_matches_anyone(self):
        policy = Policy(
            env="staging",
            rules=[PolicyRule(principal="*", actions=["pull"], allow=True)],
        )
        assert policy.is_allowed("anyone", "pull") is True

    def test_to_dict_roundtrip(self):
        policy = self._make()
        restored = Policy.from_dict(policy.to_dict())
        assert restored.env == policy.env
        assert len(restored.rules) == len(policy.rules)

    def test_to_json_is_valid_json(self):
        policy = self._make()
        data = json.loads(policy.to_json())
        assert data["env"] == "production"

    def test_from_json_roundtrip(self):
        policy = self._make()
        restored = Policy.from_json(policy.to_json())
        assert restored.env == policy.env

    def test_from_json_invalid_raises(self):
        with pytest.raises(PolicyError, match="Invalid policy JSON"):
            Policy.from_json("not-json")

    def test_from_dict_missing_env_raises(self):
        with pytest.raises(PolicyError, match="Missing policy field"):
            Policy.from_dict({"rules": []})

    def test_from_dict_missing_rules_raises(self):
        with pytest.raises(PolicyError, match="Missing policy field"):
            Policy.from_dict({"env": "production"})
