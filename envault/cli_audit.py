"""CLI sub-commands for the audit log (exposed via cli.py)."""

from __future__ import annotations

from pathlib import Path

import click

from envault.audit import AuditError, read_log


@click.command("log")
@click.option(
    "--log-file",
    default=None,
    type=click.Path(path_type=Path),
    help="Path to audit log file (defaults to ~/.envault/audit.log).",
)
@click.option(
    "--env",
    "filter_env",
    default=None,
    help="Filter entries by environment name.",
)
@click.option(
    "--action",
    "filter_action",
    default=None,
    type=click.Choice(["push", "pull"]),
    help="Filter entries by action.",
)
@click.option(
    "-n",
    "limit",
    default=20,
    show_default=True,
    help="Maximum number of entries to show (most recent first).",
)
def audit_log_cmd(
    log_file: Path | None,
    filter_env: str | None,
    filter_action: str | None,
    limit: int,
) -> None:
    """Show the local audit log of push/pull operations."""
    try:
        entries = read_log(log_file=log_file)
    except AuditError as exc:
        raise click.ClickException(str(exc)) from exc

    if filter_env:
        entries = [e for e in entries if e.env == filter_env]
    if filter_action:
        entries = [e for e in entries if e.action == filter_action]

    # most recent first
    entries = list(reversed(entries))[:limit]

    if not entries:
        click.echo("No audit log entries found.")
        return

    for entry in entries:
        click.echo(str(entry))
