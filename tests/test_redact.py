"""Tests for envault.redact."""

from __future__ import annotations

import pytest

from envault.redact import (
    RedactResult,
    _MASK,
    _partial_mask,
    redact,
)


# ---------------------------------------------------------------------------
# _partial_mask
# ---------------------------------------------------------------------------

def test_partial_mask_short_value_returns_full_mask():
    assert _partial_mask("abc") == _MASK


def test_partial_mask_long_value_shows_edges():
    result = _partial_mask("abcdefghijklmnop")
    assert result.startswith("abcd")
    assert result.endswith("mnop")
    assert "****" in result


# ---------------------------------------------------------------------------
# redact — basic masking
# ---------------------------------------------------------------------------

ENV_TEXT = """\
APP_NAME=myapp
SECRET_KEY=supersecretvalue
DATABASE_URL=postgres://user:pass@host/db
DEBUG=true
API_KEY=abc123xyz
"""


def test_masks_secret_key():
    result = redact(ENV_TEXT)
    assert "supersecretvalue" not in result.redacted
    assert f"SECRET_KEY={_MASK}" in result.redacted


def test_masks_database_url():
    result = redact(ENV_TEXT)
    assert "postgres://" not in result.redacted
    assert f"DATABASE_URL={_MASK}" in result.redacted


def test_masks_api_key():
    result = redact(ENV_TEXT)
    assert "abc123xyz" not in result.redacted
    assert f"API_KEY={_MASK}" in result.redacted


def test_does_not_mask_safe_keys():
    result = redact(ENV_TEXT)
    assert "APP_NAME=myapp" in result.redacted
    assert "DEBUG=true" in result.redacted


def test_masked_keys_list_populated():
    result = redact(ENV_TEXT)
    assert "SECRET_KEY" in result.masked_keys
    assert "DATABASE_URL" in result.masked_keys
    assert "API_KEY" in result.masked_keys
    assert "APP_NAME" not in result.masked_keys


def test_original_is_preserved():
    result = redact(ENV_TEXT)
    assert result.original == ENV_TEXT


# ---------------------------------------------------------------------------
# redact — extra keys
# ---------------------------------------------------------------------------

def test_extra_keys_are_masked():
    env = "STRIPE_KEY=sk_live_abc\nAPP_NAME=myapp\n"
    result = redact(env, extra_keys=["STRIPE_KEY"])
    assert f"STRIPE_KEY={_MASK}" in result.redacted
    assert "APP_NAME=myapp" in result.redacted


def test_extra_keys_case_insensitive():
    env = "MY_SECRET_THING=hunter2\n"
    result = redact(env, extra_keys=["my_secret_thing"])
    assert "hunter2" not in result.redacted


# ---------------------------------------------------------------------------
# redact — partial masking
# ---------------------------------------------------------------------------

def test_partial_mask_shows_edges():
    env = "API_KEY=abcdefghijklmnop\n"
    result = redact(env, partial=True)
    assert result.redacted.startswith("API_KEY=abcd")
    assert "mnop" in result.redacted


# ---------------------------------------------------------------------------
# redact — edge cases
# ---------------------------------------------------------------------------

def test_blank_and_comment_lines_preserved():
    env = "# comment\n\nAPP=foo\n"
    result = redact(env)
    assert "# comment" in result.redacted
    assert "APP=foo" in result.redacted


def test_trailing_newline_preserved():
    env = "APP=foo\n"
    result = redact(env)
    assert result.redacted.endswith("\n")


def test_no_trailing_newline_not_added():
    env = "APP=foo"
    result = redact(env)
    assert not result.redacted.endswith("\n")


def test_key_containing_sensitive_word_is_masked():
    env = "MY_PASSWORD_HASH=abc123\n"
    result = redact(env)
    assert "abc123" not in result.redacted
