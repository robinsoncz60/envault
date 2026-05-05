"""CLI helpers for listing and testing configured hooks."""

from __future__ import annotations

import click

from envault.config import ConfigError, load_config
from envault.hooks import HookConfig, HookError, run_hooks


@click.group("hooks")
def hooks_cmd() -> None:
    """Manage and inspect envault hooks."""


@hooks_cmd.command("list")
@click.option("--config", "config_path", default=None, help="Path to envault.toml")
def list_hooks_cmd(config_path: str | None) -> None:
    """List all configured hooks from envault.toml."""
    try:
        cfg = load_config(config_path)
    except ConfigError as exc:
        raise click.ClickException(str(exc)) from exc

    raw_hooks: dict = getattr(cfg, "hooks", {}) or {}
    hook_cfg = HookConfig.from_dict(raw_hooks)

    phases = {
        "pre_push": hook_cfg.pre_push,
        "post_push": hook_cfg.post_push,
        "pre_pull": hook_cfg.pre_pull,
        "post_pull": hook_cfg.post_pull,
    }

    any_hooks = False
    for phase, commands in phases.items():
        if commands:
            any_hooks = True
            click.echo(f"[{phase}]")
            for cmd in commands:
                click.echo(f"  {cmd}")

    if not any_hooks:
        click.echo("No hooks configured.")


@hooks_cmd.command("run")
@click.argument("phase", type=click.Choice(["pre_push", "post_push", "pre_pull", "post_pull"]))
@click.option("--config", "config_path", default=None, help="Path to envault.toml")
def run_hooks_cmd(phase: str, config_path: str | None) -> None:
    """Manually trigger hooks for a given phase."""
    try:
        cfg = load_config(config_path)
    except ConfigError as exc:
        raise click.ClickException(str(exc)) from exc

    raw_hooks: dict = getattr(cfg, "hooks", {}) or {}
    hook_cfg = HookConfig.from_dict(raw_hooks)
    commands: list[str] = getattr(hook_cfg, phase)

    if not commands:
        click.echo(f"No hooks defined for phase '{phase}'.")
        return

    try:
        run_hooks(commands)
    except HookError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"All '{phase}' hooks completed successfully.")
