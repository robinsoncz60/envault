"""CLI command: envault verify — check a bundle's integrity before use."""

from __future__ import annotations

import sys

import click

from envault.config import ConfigError, load_config
from envault.keystore import KeystoreError, load_keypair
from envault.storage import S3Storage, StorageError
from envault.versioning import latest_version
from envault.bundle import decode_bundle
from envault.verify import VerifyError, verify_bundle


@click.command("verify")
@click.option("--env", "env_name", default="default", show_default=True, help="Environment name.")
@click.option("--version", "version_id", default=None, help="Specific version to verify (default: latest).")
@click.option("--digest", "expected_digest", default=None, help="Expected SHA-256 digest to compare against.")
@click.pass_context
def verify_cmd(ctx: click.Context, env_name: str, version_id: str | None, expected_digest: str | None) -> None:
    """Verify the integrity of an encrypted bundle stored in S3."""
    try:
        cfg = load_config()
    except ConfigError as exc:
        click.echo(f"config error: {exc}", err=True)
        sys.exit(1)

    try:
        storage = S3Storage(
            bucket=cfg.bucket,
            prefix=cfg.prefix,
            region=cfg.region,
            endpoint_url=cfg.endpoint_url,
        )
    except StorageError as exc:
        click.echo(f"storage error: {exc}", err=True)
        sys.exit(1)

    try:
        if version_id is None:
            version_id = latest_version(storage, env_name)
        if version_id is None:
            click.echo(f"no versions found for environment '{env_name}'", err=True)
            sys.exit(1)

        raw = storage.download(env_name, version_id)
        bundle = decode_bundle(raw)
    except (StorageError, Exception) as exc:
        click.echo(f"failed to fetch bundle: {exc}", err=True)
        sys.exit(1)

    try:
        result = verify_bundle(bundle, expected_digest=expected_digest)
    except VerifyError as exc:
        click.echo(f"verify error: {exc}", err=True)
        sys.exit(1)

    click.echo(str(result))

    if not result.ok:
        sys.exit(2)
