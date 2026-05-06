"""CLI commands for managing access policies."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from envault.config import load_config
from envault.policy import Policy, PolicyError, PolicyRule, check


@click.group("policy")
def policy_cmd() -> None:
    """Manage access policies for an environment."""


@policy_cmd.command("show")
@click.option("--config", "config_path", default=None, help="Path to envault.toml")
def show_policy_cmd(config_path: str | None) -> None:
    """Print the current policy for the active environment."""
    try:
        cfg = load_config(config_path)
        raw = cfg.extra.get("policy")
        if not raw:
            click.echo("No policy configured for this environment.")
            return
        policy = Policy.from_dict(raw)
        click.echo(policy.to_json())
    except PolicyError as exc:
        click.echo(f"Policy error: {exc}", err=True)
        sys.exit(1)


@policy_cmd.command("check")
@click.argument("principal")
@click.argument("action")
@click.option("--config", "config_path", default=None, help="Path to envault.toml")
def check_policy_cmd(principal: str, action: str, config_path: str | None) -> None:
    """Check whether PRINCIPAL is allowed to perform ACTION."""
    try:
        cfg = load_config(config_path)
        raw = cfg.extra.get("policy")
        if not raw:
            click.echo("No policy configured — access is unrestricted.", err=True)
            return
        policy = Policy.from_dict(raw)
        check(policy, principal, action)
        click.echo(f"✓ '{principal}' may perform '{action}' on '{policy.env}'.")
    except PolicyError as exc:
        click.echo(f"✗ {exc}", err=True)
        sys.exit(1)


@policy_cmd.command("add-rule")
@click.argument("principal")
@click.argument("actions", nargs=-1, required=True)
@click.option("--deny", is_flag=True, default=False, help="Create a deny rule instead of allow.")
@click.option("--file", "policy_file", required=True, help="Path to policy JSON file.")
def add_rule_cmd(principal: str, actions: tuple, deny: bool, policy_file: str) -> None:
    """Append a rule to an existing policy JSON file."""
    path = Path(policy_file)
    try:
        if path.exists():
            policy = Policy.from_json(path.read_text())
        else:
            click.echo(f"Policy file not found: {policy_file}", err=True)
            sys.exit(1)

        rule = PolicyRule(principal=principal, actions=list(actions), allow=not deny)
        policy.rules.append(rule)
        path.write_text(policy.to_json())
        verb = "Deny" if deny else "Allow"
        click.echo(f"{verb} rule for '{principal}' added ({', '.join(actions)}).")
    except PolicyError as exc:
        click.echo(f"Policy error: {exc}", err=True)
        sys.exit(1)
