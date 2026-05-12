"""cli_inject.py – CLI surface for `envault inject`."""
from __future__ import annotations

import sys

import click

from envault.config import ConfigError, load_config
from envault.env_inject import InjectError, inject
from envault.keystore import KeystoreError, load_keypair
from envault.storage import StorageError, S3Storage
from envault.versioning import VersioningError, latest_version
from envault.bundle import decode_bundle


@click.group("inject")
def inject_cmd() -> None:  # pragma: no cover
    """Inject decrypted env vars into a subprocess."""


@inject_cmd.command("run")
@click.argument("command", nargs=-1, required=True)
@click.option("--config", "config_path", default=None, help="Path to envault.toml")
@click.option("--version", "version_key", default=None, help="S3 key of the bundle to inject")
@click.option("--no-override", is_flag=True, default=False, help="Do not override existing env vars")
def run_inject_cmd(
    command: tuple,
    config_path: str | None,
    version_key: str | None,
    no_override: bool,
) -> None:
    """Decrypt the latest (or specified) bundle and run COMMAND with env vars injected."""
    try:
        cfg = load_config(config_path)
    except ConfigError as exc:
        click.echo(f"Config error: {exc}", err=True)
        sys.exit(1)

    try:
        keypair = load_keypair(cfg.environment)
    except KeystoreError as exc:
        click.echo(f"Keystore error: {exc}", err=True)
        sys.exit(1)

    try:
        storage = S3Storage(
            bucket=cfg.bucket,
            prefix=cfg.environment,
            endpoint_url=cfg.endpoint_url,
        )
        if version_key is None:
            ver = latest_version(storage, cfg.environment)
            if ver is None:
                click.echo("No versions found.", err=True)
                sys.exit(1)
            version_key = ver.s3_key

        bundle_bytes = storage.download(version_key)
    except (StorageError, VersioningError) as exc:
        click.echo(f"Storage error: {exc}", err=True)
        sys.exit(1)

    bundle = decode_bundle(bundle_bytes)

    try:
        result = inject(
            command=list(command),
            ciphertext=bundle.ciphertext,
            private_key_path=keypair.private_key_path,
            override=not no_override,
        )
    except InjectError as exc:
        click.echo(f"Inject error: {exc}", err=True)
        sys.exit(1)

    sys.exit(result.returncode)
