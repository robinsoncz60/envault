"""CLI commands for snapshot management."""

from __future__ import annotations

import sys

import click

from envault.config import ConfigError, load_config
from envault.snapshot import Snapshot, SnapshotError, list_snapshots, load_snapshot, save_snapshot
from envault.storage import S3Storage, StorageError


@click.group("snapshot")
def snapshot_cmd() -> None:
    """Tag and manage named snapshots of env versions."""


@snapshot_cmd.command("create")
@click.argument("name")
@click.argument("s3_key")
@click.option("--note", default="", help="Optional description for this snapshot.")
@click.option("--config", "config_path", default=None, help="Path to envault config file.")
def create_snapshot_cmd(name: str, s3_key: str, note: str, config_path: str | None) -> None:
    """Create a named snapshot pointing to S3_KEY."""
    try:
        cfg = load_config(config_path)
    except ConfigError as exc:
        click.echo(f"Config error: {exc}", err=True)
        sys.exit(1)

    try:
        storage = S3Storage(
            bucket=cfg.bucket,
            prefix=cfg.prefix,
            endpoint_url=cfg.endpoint_url,
        )
        snap = Snapshot(name=name, s3_key=s3_key, created_by=cfg.identity, note=note)
        key = save_snapshot(storage, cfg.env, snap)
        click.echo(f"Snapshot '{name}' saved: {key}")
    except (SnapshotError, StorageError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@snapshot_cmd.command("get")
@click.argument("name")
@click.option("--config", "config_path", default=None)
def get_snapshot_cmd(name: str, config_path: str | None) -> None:
    """Print details of a named snapshot."""
    try:
        cfg = load_config(config_path)
    except ConfigError as exc:
        click.echo(f"Config error: {exc}", err=True)
        sys.exit(1)

    try:
        storage = S3Storage(
            bucket=cfg.bucket,
            prefix=cfg.prefix,
            endpoint_url=cfg.endpoint_url,
        )
        snap = load_snapshot(storage, cfg.env, name)
        click.echo(str(snap))
    except SnapshotError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@snapshot_cmd.command("list")
@click.option("--config", "config_path", default=None)
def list_snapshots_cmd(config_path: str | None) -> None:
    """List all snapshots for the current env."""
    try:
        cfg = load_config(config_path)
    except ConfigError as exc:
        click.echo(f"Config error: {exc}", err=True)
        sys.exit(1)

    try:
        storage = S3Storage(
            bucket=cfg.bucket,
            prefix=cfg.prefix,
            endpoint_url=cfg.endpoint_url,
        )
        snaps = list_snapshots(storage, cfg.env)
        if not snaps:
            click.echo("No snapshots found.")
            return
        for snap in snaps:
            click.echo(str(snap))
    except SnapshotError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
