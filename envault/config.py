"""Load and validate envault project configuration from envault.toml."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]


CONFIG_FILENAME = "envault.toml"


class ConfigError(Exception):
    """Raised when configuration is missing or invalid."""


@dataclass
class EnvaultConfig:
    project: str
    bucket: str
    prefix: str = "envault"
    endpoint_url: Optional[str] = None
    region: str = "us-east-1"
    env_file: str = ".env"
    recipients: list[str] = field(default_factory=list)


def _find_config(start: Path) -> Path:
    """Walk up from *start* looking for envault.toml."""
    for directory in (start, *start.parents):
        candidate = directory / CONFIG_FILENAME
        if candidate.is_file():
            return candidate
    raise ConfigError(
        f"No '{CONFIG_FILENAME}' found in '{start}' or any parent directory."
    )


def load_config(start: Optional[Path] = None) -> EnvaultConfig:
    """Find, parse, and validate the nearest envault.toml.

    Environment variables override file values:
      ENVAULT_BUCKET, ENVAULT_PREFIX, ENVAULT_S3_ENDPOINT
    """
    config_path = _find_config(start or Path.cwd())

    with config_path.open("rb") as fh:
        raw = tomllib.load(fh)

    try:
        project = raw["project"]
        bucket = os.getenv("ENVAULT_BUCKET") or raw["storage"]["bucket"]
    except KeyError as exc:
        raise ConfigError(f"Missing required config key: {exc}") from exc

    storage = raw.get("storage", {})

    return EnvaultConfig(
        project=project,
        bucket=bucket,
        prefix=os.getenv("ENVAULT_PREFIX") or storage.get("prefix", "envault"),
        endpoint_url=os.getenv("ENVAULT_S3_ENDPOINT") or storage.get("endpoint_url"),
        region=storage.get("region", "us-east-1"),
        env_file=raw.get("env_file", ".env"),
        recipients=raw.get("recipients", []),
    )
