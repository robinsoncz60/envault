"""CLI commands for importing and exporting envault bundles."""

from __future__ import annotations

from pathlib import Path

import click

from envault.bundle import decode_bundle
from envault.config import ConfigError, load_config
from envault.import_export import ImportExportError, export_bundle, import_bundle
from envault.storage import S3Storage, StorageError
from envault.versioning import latest_version


@click.command("export")
@click.option("--config", "config_path", default="envault.toml", show_default=True)
@click.option("--version", "version_tag", default=None, help="Version to export (default: latest)")
@click.option("--output", "-o", required=True, help="Output file path for the export")
def export_cmd(
    config_path: str,
    version_tag: str | None,
    output: str,
) -> None:
    """Export an encrypted bundle to a portable file."""
    try:
        cfg = load_config(config_path)
    except ConfigError as exc:
        raise click.ClickException(str(exc)) from exc

    storage = S3Storage(
        bucket=cfg.bucket,
        prefix=cfg.prefix,
        endpoint_url=cfg.endpoint_url,
    )

    try:
        tag = version_tag or latest_version(storage, cfg.env_name)
        if tag is None:
            raise click.ClickException("No versions found to export.")

        raw = storage.download(cfg.env_name, tag)
        bundle = decode_bundle(raw)
        dest = export_bundle(bundle, output)
    except (StorageError, ImportExportError) as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"Exported version {tag} to {dest}")


@click.command("import")
@click.option("--config", "config_path", default="envault.toml", show_default=True)
@click.argument("input_file")
def import_cmd(
    config_path: str,
    input_file: str,
) -> None:
    """Import an encrypted bundle from a portable export file and push it to storage."""
    try:
        cfg = load_config(config_path)
    except ConfigError as exc:
        raise click.ClickException(str(exc)) from exc

    storage = S3Storage(
        bucket=cfg.bucket,
        prefix=cfg.prefix,
        endpoint_url=cfg.endpoint_url,
    )

    try:
        bundle = import_bundle(input_file)
    except ImportExportError as exc:
        raise click.ClickException(str(exc)) from exc

    from envault.push import _make_version
    from envault.bundle import encode_bundle

    version_tag = _make_version()
    try:
        key = storage.upload(cfg.env_name, version_tag, encode_bundle(bundle))
    except StorageError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"Imported bundle as version {version_tag} -> {key}")
