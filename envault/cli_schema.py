"""CLI commands for env schema validation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from envault.config import ConfigError, load_config
from envault.env_schema import SchemaError, SchemaRule, validate_env
from envault.pull import PullError, pull
from envault.keystore import KeystoreError, load_keypair


@click.group("schema")
def schema_cmd() -> None:
    """Validate .env files against a schema."""


@schema_cmd.command("check")
@click.argument("schema_file", type=click.Path(exists=True))
@click.option("--env-file", type=click.Path(), default=None,
              help="Local .env file to validate (skips pull).")
@click.option("--config", "config_path", default="envault.toml",
              show_default=True)
def check_schema_cmd(
    schema_file: str, env_file: str | None, config_path: str
) -> None:
    """Validate a .env file against SCHEMA_FILE (JSON array of rules)."""
    try:
        rules_raw = json.loads(Path(schema_file).read_text())
        rules = [SchemaRule.from_dict(r) for r in rules_raw]
    except (json.JSONDecodeError, SchemaError) as exc:
        click.echo(f"Error loading schema: {exc}", err=True)
        sys.exit(1)

    if env_file:
        raw = Path(env_file).read_text()
    else:
        try:
            cfg = load_config(config_path)
            kp = load_keypair(cfg.identity)
        except (ConfigError, KeystoreError) as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)
        try:
            tmp = Path(".envault_schema_tmp")
            pull(cfg, kp, tmp)
            raw = tmp.read_text()
            tmp.unlink(missing_ok=True)
        except PullError as exc:
            click.echo(f"Pull failed: {exc}", err=True)
            sys.exit(1)

    env = _parse_env(raw)
    result = validate_env(env, rules)
    click.echo(str(result))
    if not result.ok:
        sys.exit(1)


def _parse_env(text: str) -> dict[str, str]:
    env: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip()
    return env
