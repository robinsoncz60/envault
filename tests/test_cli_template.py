"""Tests for envault.cli_template."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from envault.cli_template import template_cmd
from envault.config import ConfigError
from envault.keystore import KeystoreError
from envault.pull import PullError
from envault.template import TemplateError, RenderResult


@pytest.fixture()
def runner():
    return CliRunner()


@pytest.fixture()
def _fake_config():
    cfg = MagicMock()
    cfg.environment = "dev"
    return cfg


@pytest.fixture()
def _fake_keypair():
    kp = MagicMock()
    kp.public_key = "age1abc"
    kp.private_key = "AGE-SECRET-KEY-1"
    return kp


_ENV_TEXT = "HOST=localhost\nPORT=5432\n"


def _invoke(runner, tmp_path, extra_args=None):
    tmpl = tmp_path / "app.conf.tmpl"
    tmpl.write_text("host={{ HOST }} port={{ PORT }}", encoding="utf-8")
    out = tmp_path / "app.conf"
    args = ["render", str(tmpl), str(out)] + (extra_args or [])
    return runner.invoke(template_cmd, args, catch_exceptions=False), out


class TestRenderCmd:
    def test_success_writes_file(self, runner, tmp_path, _fake_config, _fake_keypair):
        with (
            patch("envault.cli_template.load_config", return_value=_fake_config),
            patch("envault.cli_template.load_keypair", return_value=_fake_keypair),
            patch("envault.cli_template.pull", return_value=_ENV_TEXT),
            patch(
                "envault.cli_template.render_template_file",
                return_value=RenderResult(
                    output="host=localhost port=5432",
                    substituted=["HOST", "PORT"],
                    missing=[],
                ),
            ),
        ):
            result, _ = _invoke(runner, tmp_path)
        assert result.exit_code == 0
        assert "Rendered" in result.output
        assert "HOST" in result.output

    def test_exits_on_config_error(self, runner, tmp_path):
        with patch("envault.cli_template.load_config", side_effect=ConfigError("bad")):
            result, _ = _invoke(runner, tmp_path)
        assert result.exit_code == 1
        assert "Config error" in result.output

    def test_exits_on_keystore_error(self, runner, tmp_path, _fake_config):
        with (
            patch("envault.cli_template.load_config", return_value=_fake_config),
            patch("envault.cli_template.load_keypair", side_effect=KeystoreError("x")),
        ):
            result, _ = _invoke(runner, tmp_path)
        assert result.exit_code == 1
        assert "Keystore error" in result.output

    def test_exits_on_pull_error(self, runner, tmp_path, _fake_config, _fake_keypair):
        with (
            patch("envault.cli_template.load_config", return_value=_fake_config),
            patch("envault.cli_template.load_keypair", return_value=_fake_keypair),
            patch("envault.cli_template.pull", side_effect=PullError("oops")),
        ):
            result, _ = _invoke(runner, tmp_path)
        assert result.exit_code == 1
        assert "Pull error" in result.output

    def test_exits_on_template_error(self, runner, tmp_path, _fake_config, _fake_keypair):
        with (
            patch("envault.cli_template.load_config", return_value=_fake_config),
            patch("envault.cli_template.load_keypair", return_value=_fake_keypair),
            patch("envault.cli_template.pull", return_value=_ENV_TEXT),
            patch(
                "envault.cli_template.render_template_file",
                side_effect=TemplateError("missing key"),
            ),
        ):
            result, _ = _invoke(runner, tmp_path)
        assert result.exit_code == 1
        assert "Template error" in result.output

    def test_reports_unresolved_keys(self, runner, tmp_path, _fake_config, _fake_keypair):
        with (
            patch("envault.cli_template.load_config", return_value=_fake_config),
            patch("envault.cli_template.load_keypair", return_value=_fake_keypair),
            patch("envault.cli_template.pull", return_value=_ENV_TEXT),
            patch(
                "envault.cli_template.render_template_file",
                return_value=RenderResult(
                    output="host={{ UNKNOWN }}",
                    substituted=[],
                    missing=["UNKNOWN"],
                ),
            ),
        ):
            result, _ = _invoke(runner, tmp_path)
        assert result.exit_code == 0
        assert "UNKNOWN" in result.output
