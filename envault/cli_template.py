"""CLI commands for template rendering."""
from __future__ import annotations

import sys
from pathlib import Path

import click

from envault.config import ConfigError, load_config
from envault.crypto import CryptoError
from envault.keystore import KeystoreError, load_keypair
from envault.pull import PullError, pull
from envault.template import TemplateError, render_template_file


@click.group("template")
def template_cmd() -> None:
    """Render config templates using decrypted .env values."""


@template_cmd.command("render")
@click.argument("template_file", type=click.Path(exists=True, path_type=Path))
@click.argument("output_file", type=click.Path(path_type=Path))
@click.option(
    "--config", "config_path",
    default="envault.toml",
    show_default=True,
    help="Path to envault config file.",
)
@click.option(
    "--version", "version_id",
    default=None,
    help="Specific version to pull (defaults to latest).",
)
@click.option(
    "--strict",
    is_flag=True,
    default=False,
    help="Fail if any template placeholder has no matching key.",
)
def render_cmd(
    template_file: Path,
    output_file: Path,
    config_path: str,
    version_id: str | None,
    strict: bool,
) -> None:
    """Pull the latest .env and render TEMPLATE_FILE into OUTPUT_FILE."""
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
        env_text = pull(
            config=cfg,
            keypair=keypair,
            version_id=version_id,
            output_path=None,  # return plaintext instead of writing
        )
    except (PullError, CryptoError) as exc:
        click.echo(f"Pull error: {exc}", err=True)
        sys.exit(1)

    try:
        result = render_template_file(
            template_file,
            env_text,
            output_file,
            strict=strict,
        )
    except TemplateError as exc:
        click.echo(f"Template error: {exc}", err=True)
        sys.exit(1)

    click.echo(f"Rendered {template_file} -> {output_file}")
    click.echo(f"  substituted: {', '.join(result.substituted) or '(none)'}")
    if result.missing:
        click.echo(f"  unresolved:  {', '.join(result.missing)}", err=True)
