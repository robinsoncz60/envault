"""Tests for envault.cli_import_export."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from envault.bundle import EnvBundle
from envault.cli_import_export import export_cmd, import_cmd
from envault.import_export import EXPORT_VERSION


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


def _fake_config() -> MagicMock:
    cfg = MagicMock()
    cfg.bucket = "test-bucket"
    cfg.prefix = "envs"
    cfg.endpoint_url = None
    cfg.env_name = "myapp"
    return cfg


def _fake_bundle() -> EnvBundle:
    return EnvBundle(
        ciphertext=base64.b64encode(b"ciphertext").decode(),
        recipient="age1abc",
        version="20240601T120000Z",
    )


class TestExportCmd:
    def test_success_writes_file(self, runner: CliRunner, tmp_path: Path) -> None:
        out_file = str(tmp_path / "out.json")
        bundle = _fake_bundle()

        with (
            patch("envault.cli_import_export.load_config", return_value=_fake_config()),
            patch("envault.cli_import_export.S3Storage"),
            patch("envault.cli_import_export.latest_version", return_value="20240601T120000Z"),
            patch("envault.cli_import_export.decode_bundle", return_value=bundle),
            patch("envault.cli_import_export.export_bundle", return_value=Path(out_file)) as mock_export,
            patch.object(MagicMock, "download", return_value=b"raw"),
        ):
            result = runner.invoke(export_cmd, ["--output", out_file])

        assert result.exit_code == 0
        assert "Exported" in result.output

    def test_exits_when_no_versions(self, runner: CliRunner, tmp_path: Path) -> None:
        with (
            patch("envault.cli_import_export.load_config", return_value=_fake_config()),
            patch("envault.cli_import_export.S3Storage"),
            patch("envault.cli_import_export.latest_version", return_value=None),
        ):
            result = runner.invoke(export_cmd, ["--output", str(tmp_path / "out.json")])

        assert result.exit_code != 0
        assert "No versions" in result.output

    def test_exits_on_config_error(self, runner: CliRunner, tmp_path: Path) -> None:
        from envault.config import ConfigError

        with patch("envault.cli_import_export.load_config", side_effect=ConfigError("bad config")):
            result = runner.invoke(export_cmd, ["--output", str(tmp_path / "out.json")])

        assert result.exit_code != 0
        assert "bad config" in result.output


class TestImportCmd:
    def test_success_prints_key(self, runner: CliRunner, tmp_path: Path) -> None:
        import_file = tmp_path / "import.json"
        bundle = _fake_bundle()
        doc = {"magic": "envault-export", "version": EXPORT_VERSION, "payload": bundle.to_dict()}
        import_file.write_text(json.dumps(doc))

        with (
            patch("envault.cli_import_export.load_config", return_value=_fake_config()),
            patch("envault.cli_import_export.S3Storage") as MockStorage,
            patch("envault.cli_import_export._make_version", return_value="20240701T000000Z"),
            patch("envault.cli_import_export.encode_bundle", return_value=b"encoded"),
        ):
            mock_storage_instance = MockStorage.return_value
            mock_storage_instance.upload.return_value = "envs/myapp/20240701T000000Z.age"
            result = runner.invoke(import_cmd, [str(import_file)])

        assert result.exit_code == 0
        assert "Imported" in result.output

    def test_exits_on_bad_import_file(self, runner: CliRunner, tmp_path: Path) -> None:
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not json")

        with patch("envault.cli_import_export.load_config", return_value=_fake_config()):
            result = runner.invoke(import_cmd, [str(bad_file)])

        assert result.exit_code != 0
