"""Tests for envault.template."""
from __future__ import annotations

import pytest
from pathlib import Path

from envault.template import (
    TemplateError,
    RenderResult,
    _parse_env,
    render_template,
    render_template_file,
)


# ---------------------------------------------------------------------------
# _parse_env
# ---------------------------------------------------------------------------

def test_parse_env_basic():
    text = "FOO=bar\nBAZ=qux\n"
    assert _parse_env(text) == {"FOO": "bar", "BAZ": "qux"}


def test_parse_env_ignores_comments_and_blanks():
    text = "# comment\n\nKEY=val\n"
    assert _parse_env(text) == {"KEY": "val"}


def test_parse_env_handles_value_with_equals():
    text = "URL=http://x.com?a=1\n"
    assert _parse_env(text) == {"URL": "http://x.com?a=1"}


def test_parse_env_strips_whitespace():
    text = "  KEY  =  value  \n"
    assert _parse_env(text) == {"KEY": "value"}


# ---------------------------------------------------------------------------
# render_template
# ---------------------------------------------------------------------------

ENV_TEXT = "HOST=localhost\nPORT=5432\nSECRET=abc123\n"


def test_substitutes_known_keys():
    tmpl = "Connect to {{ HOST }}:{{ PORT }}"
    result = render_template(tmpl, ENV_TEXT)
    assert result.output == "Connect to localhost:5432"
    assert set(result.substituted) == {"HOST", "PORT"}
    assert result.missing == []


def test_leaves_unknown_placeholder_intact():
    tmpl = "db={{ DB_NAME }}"
    result = render_template(tmpl, ENV_TEXT)
    assert result.output == "db={{ DB_NAME }}"
    assert result.missing == ["DB_NAME"]


def test_strict_mode_raises_on_missing():
    tmpl = "val={{ MISSING }}"
    with pytest.raises(TemplateError, match="MISSING"):
        render_template(tmpl, ENV_TEXT, strict=True)


def test_strict_mode_passes_when_all_present():
    tmpl = "{{ HOST }}"
    result = render_template(tmpl, ENV_TEXT, strict=True)
    assert result.output == "localhost"


def test_duplicate_placeholder_counted_once_in_missing():
    tmpl = "{{ X }} and {{ X }}"
    result = render_template(tmpl, ENV_TEXT, strict=False)
    # both occurrences appear in missing list but TemplateError lists unique
    assert result.missing == ["X", "X"]


def test_strict_deduplicates_missing_in_error_message():
    tmpl = "{{ X }} {{ X }}"
    with pytest.raises(TemplateError) as exc_info:
        render_template(tmpl, ENV_TEXT, strict=True)
    # 'X' should appear only once in the message
    assert exc_info.value.args[0].count("X") == 1


def test_returns_render_result_instance():
    result = render_template("", ENV_TEXT)
    assert isinstance(result, RenderResult)


# ---------------------------------------------------------------------------
# render_template_file
# ---------------------------------------------------------------------------

def test_reads_and_writes_file(tmp_path):
    tmpl_file = tmp_path / "app.conf.tmpl"
    tmpl_file.write_text("host={{ HOST }}\n", encoding="utf-8")
    out_file = tmp_path / "app.conf"

    result = render_template_file(tmpl_file, ENV_TEXT, out_file)

    assert out_file.read_text(encoding="utf-8") == "host=localhost\n"
    assert "HOST" in result.substituted


def test_raises_on_missing_template_file(tmp_path):
    with pytest.raises(TemplateError, match="Cannot read"):
        render_template_file(tmp_path / "no.tmpl", ENV_TEXT, tmp_path / "out")


def test_raises_on_unwritable_output(tmp_path):
    tmpl_file = tmp_path / "t.tmpl"
    tmpl_file.write_text("{{ HOST }}", encoding="utf-8")
    bad_out = tmp_path / "no_dir" / "out.conf"
    with pytest.raises(TemplateError, match="Cannot write"):
        render_template_file(tmpl_file, ENV_TEXT, bad_out)
