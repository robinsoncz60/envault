"""CLI command for watching a .env file and auto-pushing on change."""

from __future__ import annotations

from pathlib import Path

import click

from envault.config import ConfigError, load_config
from envault.keystore import KeystoreError, load_keypair
from envault.push import PushError, push
from envault.watch import WatchError, watch


@click.command("watch")
@click.argument("env_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--interval",
    default=2.0,
    show_default=True,
    help="Polling interval in seconds.",
)
@click.option(
    "--config",
    "config_path",
    default=None,
    type=click.Path(path_type=Path),
    help="Path to envault.toml (auto-detected if omitted).",
)
def watch_cmd(env_file: Path, interval: float, config_path: Path | None) -> None:
    """Watch ENV_FILE and push to S3 automatically whenever it changes."""
    try:
        cfg = load_config(config_path)
    except ConfigError as exc:
        raise click.ClickException(str(exc)) from exc

    try:
        keypair = load_keypair(cfg.environment)
    except KeystoreError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"Watching {env_file} every {interval}s — press Ctrl+C to stop.")

    def on_change(path: Path) -> None:
        click.echo(f"  change detected in {path.name}, pushing…")
        try:
            s3_key = push(
                env_path=path,
                config=cfg,
                keypair=keypair,
            )
            click.echo(f"  pushed → {s3_key}")
        except PushError as exc:
            click.echo(f"  push failed: {exc}", err=True)

    try:
        watch(env_file, on_change=on_change, interval=interval)
    except KeyboardInterrupt:
        click.echo("\nStopped watching.")
    except WatchError as exc:
        raise click.ClickException(str(exc)) from exc
