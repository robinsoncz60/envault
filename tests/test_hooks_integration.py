"""Integration tests for hooks executed in a real subprocess environment."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from envault.hooks import HookConfig, HookError, run_hooks


def test_successful_hook_writes_file(tmp_path: Path) -> None:
    sentinel = tmp_path / "hook_ran"
    run_hooks([f"touch {sentinel}"], cwd=tmp_path)
    assert sentinel.exists()


def test_multiple_hooks_all_execute(tmp_path: Path) -> None:
    a = tmp_path / "a"
    b = tmp_path / "b"
    run_hooks([f"touch {a}", f"touch {b}"], cwd=tmp_path)
    assert a.exists()
    assert b.exists()


def test_hook_failure_prevents_later_hooks(tmp_path: Path) -> None:
    sentinel = tmp_path / "should_not_exist"
    with pytest.raises(HookError):
        run_hooks(["exit 1", f"touch {sentinel}"], cwd=tmp_path)
    assert not sentinel.exists()


def test_hook_config_roundtrip_and_execution(tmp_path: Path) -> None:
    data = {
        "pre_push": [f"touch {tmp_path / 'pre'}"],
        "post_push": [f"touch {tmp_path / 'post'}"],
        "pre_pull": [],
        "post_pull": [],
    }
    cfg = HookConfig.from_dict(data)
    run_hooks(cfg.pre_push, cwd=tmp_path)
    run_hooks(cfg.post_push, cwd=tmp_path)
    assert (tmp_path / "pre").exists()
    assert (tmp_path / "post").exists()


def test_env_vars_passed_to_hook(tmp_path: Path) -> None:
    import os

    out_file = tmp_path / "env_out"
    env = {**os.environ, "MY_HOOK_VAR": "envault-test"}
    run_hooks([f"printenv MY_HOOK_VAR > {out_file}"], cwd=tmp_path, env=env)
    assert out_file.read_text().strip() == "envault-test"
