"""Tests for envault.cli_policy."""
import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from envault.cli_policy import policy_cmd
from envault.policy import Policy, PolicyRule


@pytest.fixture()
def runner():
    return CliRunner()


def _fake_config(has_policy: bool = True):
    cfg = MagicMock()
    if has_policy:
        cfg.extra = {
            "policy": {
                "env": "production",
                "rules": [
                    {"principal": "alice", "actions": ["push", "pull"], "allow": True}
                ],
            }
        }
    else:
        cfg.extra = {}
    return cfg


class TestShowPolicyCmd:
    def test_prints_policy_json(self, runner):
        with patch("envault.cli_policy.load_config", return_value=_fake_config()):
            result = runner.invoke(policy_cmd, ["show"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["env"] == "production"

    def test_no_policy_configured(self, runner):
        with patch("envault.cli_policy.load_config", return_value=_fake_config(False)):
            result = runner.invoke(policy_cmd, ["show"])
        assert result.exit_code == 0
        assert "No policy configured" in result.output


class TestCheckPolicyCmd:
    def test_allowed_principal_exits_zero(self, runner):
        with patch("envault.cli_policy.load_config", return_value=_fake_config()):
            result = runner.invoke(policy_cmd, ["check", "alice", "push"])
        assert result.exit_code == 0
        assert "may perform" in result.output

    def test_denied_principal_exits_nonzero(self, runner):
        with patch("envault.cli_policy.load_config", return_value=_fake_config()):
            result = runner.invoke(policy_cmd, ["check", "bob", "push"])
        assert result.exit_code == 1

    def test_no_policy_is_unrestricted(self, runner):
        with patch("envault.cli_policy.load_config", return_value=_fake_config(False)):
            result = runner.invoke(policy_cmd, ["check", "anyone", "pull"])
        assert result.exit_code == 0
        assert "unrestricted" in result.output


class TestAddRuleCmd:
    def test_adds_allow_rule(self, runner, tmp_path):
        policy = Policy(
            env="staging",
            rules=[PolicyRule(principal="alice", actions=["pull"], allow=True)],
        )
        policy_file = tmp_path / "policy.json"
        policy_file.write_text(policy.to_json())

        result = runner.invoke(
            policy_cmd,
            ["add-rule", "bob", "pull", "push", "--file", str(policy_file)],
        )
        assert result.exit_code == 0
        data = json.loads(policy_file.read_text())
        principals = [r["principal"] for r in data["rules"]]
        assert "bob" in principals

    def test_adds_deny_rule(self, runner, tmp_path):
        policy = Policy(env="staging", rules=[])
        policy_file = tmp_path / "policy.json"
        policy_file.write_text(policy.to_json())

        result = runner.invoke(
            policy_cmd,
            ["add-rule", "eve", "push", "--deny", "--file", str(policy_file)],
        )
        assert result.exit_code == 0
        data = json.loads(policy_file.read_text())
        rule = next(r for r in data["rules"] if r["principal"] == "eve")
        assert rule["allow"] is False

    def test_missing_file_exits_nonzero(self, runner, tmp_path):
        result = runner.invoke(
            policy_cmd,
            ["add-rule", "alice", "pull", "--file", str(tmp_path / "nope.json")],
        )
        assert result.exit_code == 1
