"""CLI sub-command: rotate — re-encrypt env bundle under a new keypair."""

from __future__ import annotations

import click

from envault.config import ConfigError, load_config
from envault.crypto import CryptoError, generate_keypair
from envault.keystore import KeystoreError, keypair_exists, load_keypair, save_keypair
from envault.rotate import RotateError, rotate
from envault.storage import S3Storage, StorageError


@click.command("rotate")
@click.option("--config", "config_path", default=None, help="Path to envault.toml")
@click.option("--pushed-by", default=None, help="Identity tag for audit log")
@click.pass_context
def rotate_cmd(ctx: click.Context, config_path: str | None, pushed_by: str | None) -> None:
    """Rotate encryption keys: generate a new keypair and re-encrypt the latest bundle."""

    # --- load config ---
    try:
        cfg = load_config(config_path)
    except ConfigError as exc:
        click.echo(f"Config error: {exc}", err=True)
        ctx.exit(1)
        return

    # --- load old keypair ---
    try:
        old_kp = load_keypair(cfg.env)
    except KeystoreError as exc:
        click.echo(f"Keystore error (old keypair): {exc}", err=True)
        ctx.exit(1)
        return

    # --- generate new keypair ---
    try:
        new_pub, new_priv = generate_keypair()
    except CryptoError as exc:
        click.echo(f"Key generation failed: {exc}", err=True)
        ctx.exit(1)
        return

    # --- rotate ---
    storage = S3Storage(
        bucket=cfg.bucket,
        endpoint_url=cfg.endpoint_url,
        region=cfg.region,
    )

    identity = pushed_by or old_kp.public_key[:16]

    try:
        s3_key = rotate(cfg, storage, old_kp, _kp_from_raw(new_pub, new_priv, cfg.env), identity)
    except (RotateError, StorageError) as exc:
        click.echo(f"Rotation failed: {exc}", err=True)
        ctx.exit(1)
        return

    # --- persist new keypair (overwrites old) ---
    try:
        save_keypair(cfg.env, new_pub, new_priv)
    except KeystoreError as exc:
        click.echo(f"Warning: rotation succeeded but keypair not saved: {exc}", err=True)

    click.echo(f"Rotated successfully → {s3_key}")


def _kp_from_raw(public_key: str, private_key: str, env: str):
    """Build a transient keypair namespace without persisting to disk."""
    import tempfile, os
    from types import SimpleNamespace

    tmp = tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".key")
    tmp.write(private_key)
    tmp.close()
    os.chmod(tmp.name, 0o600)
    return SimpleNamespace(public_key=public_key, private_key_path=tmp.name)
