"""CLI command for copying an env bundle between environment prefixes."""
from __future__ import annotations

import click

from .config import load_config, ConfigError
from .env_copy import copy_env, CopyError
from .storage import S3Storage, StorageError


@click.group("copy")
def copy_cmd() -> None:
    """Copy env bundles between environment prefixes."""


@copy_cmd.command("run")
@click.argument("dest_prefix")
@click.option(
    "--version",
    "source_version",
    default=None,
    help="Specific source version to copy (default: latest).",
)
@click.option(
    "--config",
    "config_path",
    default=None,
    help="Path to envault.toml (auto-detected if omitted).",
)
def run_copy_cmd(
    dest_prefix: str,
    source_version: str | None,
    config_path: str | None,
) -> None:
    """Copy a bundle from the configured prefix to DEST_PREFIX."""
    try:
        config = load_config(config_path)
    except ConfigError as exc:
        raise click.ClickException(str(exc)) from exc

    try:
        storage = S3Storage(
            bucket=config.bucket,
            endpoint_url=config.endpoint_url,
            aws_access_key_id=config.aws_access_key_id,
            aws_secret_access_key=config.aws_secret_access_key,
        )
    except StorageError as exc:
        raise click.ClickException(str(exc)) from exc

    try:
        result = copy_env(
            config=config,
            storage=storage,
            dest_prefix=dest_prefix,
            source_version=source_version,
        )
    except CopyError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(str(result))
