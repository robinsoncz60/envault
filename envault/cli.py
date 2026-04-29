"""CLI entry point for envault using Click."""

import sys
from pathlib import Path

import click

from envault.config import ConfigError, load_config
from envault.crypto import CryptoError, generate_keypair
from envault.keystore import KeystoreError, keypair_exists, load_keypair, save_keypair
from envault.pull import PullError, pull
from envault.push import PushError, push
from envault.storage import StorageError, S3Storage
from envault.versioning import VersioningError, list_versions


@click.group()
def cli() -> None:
    """envault — encrypt, version, and sync .env files."""


@cli.command()
@click.option("--name", default="default", show_default=True, help="Key pair name.")
def keygen(name: str) -> None:
    """Generate a new age key pair and save it to the keystore."""
    if keypair_exists(name):
        click.echo(f"Key pair '{name}' already exists. Use --name to specify a different name.")
        sys.exit(1)
    try:
        keypair = generate_keypair()
        save_keypair(name, keypair)
        click.echo(f"Key pair '{name}' generated and saved.")
        click.echo(f"Public key: {keypair.public_key}")
    except (CryptoError, KeystoreError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("env_file", default=".env", type=click.Path(exists=True))
@click.option("--name", default="default", show_default=True, help="Key pair name.")
@click.option("--config", "config_path", default=None, type=click.Path(), help="Config file path.")
def push_cmd(env_file: str, name: str, config_path: str | None) -> None:
    """Encrypt and push an .env file to remote storage."""
    try:
        cfg = load_config(config_path)
        keypair = load_keypair(name)
        storage = S3Storage(cfg.bucket, cfg.endpoint, cfg.access_key, cfg.secret_key)
        version = push(Path(env_file), keypair, storage, cfg)
        click.echo(f"Pushed version: {version}")
    except (ConfigError, KeystoreError, PushError, StorageError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--version", "version_id", default=None, help="Version to pull (default: latest).")
@click.option("--output", default=".env", show_default=True, type=click.Path(), help="Output file path.")
@click.option("--name", default="default", show_default=True, help="Key pair name.")
@click.option("--config", "config_path", default=None, type=click.Path(), help="Config file path.")
def pull_cmd(version_id: str | None, output: str, name: str, config_path: str | None) -> None:
    """Pull and decrypt an .env file from remote storage."""
    try:
        cfg = load_config(config_path)
        keypair = load_keypair(name)
        storage = S3Storage(cfg.bucket, cfg.endpoint, cfg.access_key, cfg.secret_key)
        pull(version_id, Path(output), keypair, storage, cfg)
        click.echo(f"Written to {output}")
    except (ConfigError, KeystoreError, PullError, StorageError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@cli.command(name="versions")
@click.option("--config", "config_path", default=None, type=click.Path(), help="Config file path.")
@click.option("--limit", default=10, show_default=True, help="Max versions to display.")
def versions_cmd(config_path: str | None, limit: int) -> None:
    """List available versions in remote storage."""
    try:
        cfg = load_config(config_path)
        storage = S3Storage(cfg.bucket, cfg.endpoint, cfg.access_key, cfg.secret_key)
        vers = list_versions(storage, cfg.prefix)
        if not vers:
            click.echo("No versions found.")
            return
        for v in vers[:limit]:
            click.echo(str(v))
    except (ConfigError, VersioningError, StorageError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
