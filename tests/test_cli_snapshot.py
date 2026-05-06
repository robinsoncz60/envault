"""Tests for envault.cli_snapshot."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from envault.cli_snapshot import snapshot_cmd
from envault.snapshot import Snapshot, SnapshotError


@pytest.fixture()
def runner():
    return CliRunner()


def _fake_config():
    cfg = MagicMock()
    cfg.bucket = "my-bucket"
    cfg.prefix = "envault"
    cfg.endpoint_url = None
    cfg.env = "prod"
    cfg.identity = "bob"
    return cfg


def _fake_snapshot():
    return Snapshot(name="v2-stable", s3_key="envs/prod/20240601.bundle", created_by="bob")


class TestCreateSnapshotCmd:
    def test_success_prints_key(self, runner):
        with patch("envault.cli_snapshot.load_config", return_value=_fake_config()), \
             patch("envault.cli_snapshot.S3Storage"), \
             patch("envault.cli_snapshot.save_snapshot", return_value="snapshots/prod/v2-stable.json"):
            result = runner.invoke(snapshot_cmd, ["create", "v2-stable", "envs/prod/20240601.bundle"])
        assert result.exit_code == 0
        assert "v2-stable" in result.output
        assert "snapshots/prod/v2-stable.json" in result.output

    def test_exits_on_config_error(self, runner):
        from envault.config import ConfigError
        with patch("envault.cli_snapshot.load_config", side_effect=ConfigError("missing")):
            result = runner.invoke(snapshot_cmd, ["create", "x", "y"])
        assert result.exit_code == 1
        assert "Config error" in result.output

    def test_exits_on_snapshot_error(self, runner):
        with patch("envault.cli_snapshot.load_config", return_value=_fake_config()), \
             patch("envault.cli_snapshot.S3Storage"), \
             patch("envault.cli_snapshot.save_snapshot", side_effect=SnapshotError("boom")):
            result = runner.invoke(snapshot_cmd, ["create", "bad", "key"])
        assert result.exit_code == 1
        assert "boom" in result.output


class TestGetSnapshotCmd:
    def test_prints_snapshot_details(self, runner):
        snap = _fake_snapshot()
        with patch("envault.cli_snapshot.load_config", return_value=_fake_config()), \
             patch("envault.cli_snapshot.S3Storage"), \
             patch("envault.cli_snapshot.load_snapshot", return_value=snap):
            result = runner.invoke(snapshot_cmd, ["get", "v2-stable"])
        assert result.exit_code == 0
        assert "v2-stable" in result.output

    def test_exits_when_snapshot_missing(self, runner):
        with patch("envault.cli_snapshot.load_config", return_value=_fake_config()), \
             patch("envault.cli_snapshot.S3Storage"), \
             patch("envault.cli_snapshot.load_snapshot", side_effect=SnapshotError("not found")):
            result = runner.invoke(snapshot_cmd, ["get", "ghost"])
        assert result.exit_code == 1
        assert "not found" in result.output


class TestListSnapshotsCmd:
    def test_prints_each_snapshot(self, runner):
        snaps = [_fake_snapshot(), Snapshot("a-snap", "envs/prod/old.bundle", "alice")]
        with patch("envault.cli_snapshot.load_config", return_value=_fake_config()), \
             patch("envault.cli_snapshot.S3Storage"), \
             patch("envault.cli_snapshot.list_snapshots", return_value=snaps):
            result = runner.invoke(snapshot_cmd, ["list"])
        assert result.exit_code == 0
        assert "v2-stable" in result.output
        assert "a-snap" in result.output

    def test_shows_no_snapshots_message(self, runner):
        with patch("envault.cli_snapshot.load_config", return_value=_fake_config()), \
             patch("envault.cli_snapshot.S3Storage"), \
             patch("envault.cli_snapshot.list_snapshots", return_value=[]):
            result = runner.invoke(snapshot_cmd, ["list"])
        assert result.exit_code == 0
        assert "No snapshots found" in result.output

    def test_exits_on_snapshot_error(self, runner):
        with patch("envault.cli_snapshot.load_config", return_value=_fake_config()), \
             patch("envault.cli_snapshot.S3Storage"), \
             patch("envault.cli_snapshot.list_snapshots", side_effect=SnapshotError("s3 down")):
            result = runner.invoke(snapshot_cmd, ["list"])
        assert result.exit_code == 1
        assert "s3 down" in result.output
