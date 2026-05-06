"""Template rendering: substitute .env values into template files."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

TEMPLATE_VAR_RE = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}")


class TemplateError(Exception):
    """Raised when template rendering fails."""


@dataclass
class RenderResult:
    output: str
    substituted: List[str]
    missing: List[str]

    def __str__(self) -> str:  # pragma: no cover
        parts = [f"substituted={self.substituted}"]
        if self.missing:
            parts.append(f"missing={self.missing}")
        return f"RenderResult({', '.join(parts)})"


def _parse_env(text: str) -> Dict[str, str]:
    """Parse KEY=VALUE lines; skip comments and blanks."""
    env: Dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip()
    return env


def render_template(
    template_text: str,
    env_text: str,
    *,
    strict: bool = False,
) -> RenderResult:
    """Replace ``{{ KEY }}`` placeholders with values from *env_text*.

    Parameters
    ----------
    template_text:
        The raw template string.
    env_text:
        Contents of a decrypted .env file.
    strict:
        When *True*, raise :class:`TemplateError` if any placeholder has no
        corresponding key in *env_text*.
    """
    env = _parse_env(env_text)
    substituted: List[str] = []
    missing: List[str] = []

    def replacer(match: re.Match) -> str:
        key = match.group(1)
        if key in env:
            substituted.append(key)
            return env[key]
        missing.append(key)
        return match.group(0)  # leave placeholder intact

    output = TEMPLATE_VAR_RE.sub(replacer, template_text)

    if strict and missing:
        raise TemplateError(
            f"Template references undefined keys: {', '.join(sorted(set(missing)))}"
        )

    return RenderResult(output=output, substituted=substituted, missing=missing)


def render_template_file(
    template_path: Path,
    env_text: str,
    output_path: Path,
    *,
    strict: bool = False,
) -> RenderResult:
    """Read *template_path*, render it, and write to *output_path*."""
    try:
        template_text = template_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise TemplateError(f"Cannot read template file: {exc}") from exc

    result = render_template(template_text, env_text, strict=strict)

    try:
        output_path.write_text(result.output, encoding="utf-8")
    except OSError as exc:
        raise TemplateError(f"Cannot write output file: {exc}") from exc

    return result
