"""Tests for envault.cli_schema."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from envault.cli_schema import check_schema_cmd


@pytest.fixture()
def runner():
    return CliRunner()


def _write_schema(path: Path, rules: list) -> None:
    path.write_text(json.dumps(rules))


class TestCheckSchemaCmd:
    def test_valid_env_file_exits_zero(self, runner, tmp_path):
        schema = tmp_path / "schema.json"
        env_file = tmp_path / ".env"
        _write_schema(schema, [{"key": "FOO", "required": True}])
        env_file.write_text("FOO=bar\n")

        result = runner.invoke(
            check_schema_cmd,
            [str(schema), "--env-file", str(env_file)],
        )
        assert result.exit_code == 0
        assert "OK" in result.output

    def test_missing_required_key_exits_nonzero(self, runner, tmp_path):
        schema = tmp_path / "schema.json"
        env_file = tmp_path / ".env"
        _write_schema(schema, [{"key": "MISSING_KEY", "required": True}])
        env_file.write_text("OTHER=value\n")

        result = runner.invoke(
            check_schema_cmd,
            [str(schema), "--env-file", str(env_file)],
        )
        assert result.exit_code == 1
        assert "MISSING_KEY" in result.output

    def test_invalid_schema_json_exits_nonzero(self, runner, tmp_path):
        schema = tmp_path / "schema.json"
        env_file = tmp_path / ".env"
        schema.write_text("not valid json{")
        env_file.write_text("FOO=bar\n")

        result = runner.invoke(
            check_schema_cmd,
            [str(schema), "--env-file", str(env_file)],
        )
        assert result.exit_code == 1
        assert "Error loading schema" in result.output

    def test_pattern_violation_exits_nonzero(self, runner, tmp_path):
        schema = tmp_path / "schema.json"
        env_file = tmp_path / ".env"
        _write_schema(schema, [{"key": "PORT", "required": True, "pattern": r"\d+"}])
        env_file.write_text("PORT=not-a-port\n")

        result = runner.invoke(
            check_schema_cmd,
            [str(schema), "--env-file", str(env_file)],
        )
        assert result.exit_code == 1
        assert "PORT" in result.output

    def test_pull_path_config_error_exits_nonzero(self, runner, tmp_path):
        schema = tmp_path / "schema.json"
        _write_schema(schema, [{"key": "FOO"}])

        with patch("envault.cli_schema.load_config",
                   side_effect=Exception("no config")):
            result = runner.invoke(
                check_schema_cmd,
                [str(schema), "--config", str(tmp_path / "envault.toml")],
            )
        assert result.exit_code != 0
