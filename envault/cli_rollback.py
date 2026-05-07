"""CLI commands for rolling back .env versions."""
from __future__ import annotations

from typing import Optional

import click

from envault.config import ConfigError, load_config
from envault.env_rollback import RollbackError, rollback
from envault.keystore import KeystoreError, load_keypair
from envault.storage import S3Storage


@click.group("rollback")
def rollback_cmd() -> None:
    """Roll back to a previous .env version."""


@rollback_cmd.command("run")
@click.option(
    "--config",
    "config_path",
    default=None,
    help="Path to envault.toml (auto-detected if omitted).",
)
@click.option(
    "--version",
    "target_version",
    default=None,
    help="Specific version to roll back to. Defaults to the previous version.",
)
@click.option(
    "--profile",
    default="default",
    show_default=True,
    help="Key profile to use from the keystore.",
)
def run_rollback_cmd(
    config_path: Optional[str],
    target_version: Optional[str],
    profile: str,
) -> None:
    """Re-push a previous version as the new latest version."""
    try:
        config = load_config(config_path)
    except ConfigError as exc:
        raise click.ClickException(str(exc)) from exc

    try:
        keypair = load_keypair(profile)
    except KeystoreError as exc:
        raise click.ClickException(str(exc)) from exc

    storage = S3Storage(
        bucket=config.bucket,
        endpoint_url=config.endpoint_url,
        region=config.region,
    )

    try:
        result = rollback(
            config=config,
            storage=storage,
            keypair=keypair,
            target_version=target_version,
        )
    except RollbackError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(str(result))
    click.echo(f"New S3 key: {result.new_version}")
