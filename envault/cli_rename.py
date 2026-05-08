"""CLI command for renaming an env key in-place."""
from __future__ import annotations

import click

from envault.config import ConfigError, load_config
from envault.env_rename import RenameError, rename_key
from envault.keystore import KeystoreError, load_keypair
from envault.storage import S3Storage


@click.group("rename")
def rename_cmd() -> None:
    """Rename a key inside the latest (or specified) env version."""


@rename_cmd.command("run")
@click.argument("old_key")
@click.argument("new_key")
@click.option("--config", "config_path", default=None, help="Path to envault.toml")
@click.option("--version", default=None, help="Specific version key to rename from")
def run_rename_cmd(
    old_key: str,
    new_key: str,
    config_path: str | None,
    version: str | None,
) -> None:
    """Rename OLD_KEY to NEW_KEY and push a new version."""
    try:
        config = load_config(config_path)
    except ConfigError as exc:
        raise click.ClickException(str(exc)) from exc

    try:
        keypair = load_keypair()
    except KeystoreError as exc:
        raise click.ClickException(str(exc)) from exc

    storage = S3Storage(
        bucket=config.bucket,
        region=config.region,
        prefix=config.env,
    )

    try:
        result = rename_key(
            config=config,
            storage=storage,
            keypair=keypair,
            old_key=old_key,
            new_key=new_key,
            version=version,
        )
    except RenameError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(str(result))
