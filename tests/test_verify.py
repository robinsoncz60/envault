"""Tests for envault.verify."""

from __future__ import annotations

import hashlib

import pytest

from envault.bundle import EnvBundle
from envault.verify import VerifyError, VerifyResult, compute_bundle_digest, verify_bundle


def _make_bundle(ciphertext: bytes = b"secret-cipher", version: str = "20240101T000000Z") -> EnvBundle:
    return EnvBundle(ciphertext=ciphertext, version=version, recipient="age1abc")


# ---------------------------------------------------------------------------
# compute_bundle_digest
# ---------------------------------------------------------------------------

class TestComputeBundleDigest:
    def test_returns_hex_string(self):
        digest = compute_bundle_digest(_make_bundle())
        assert isinstance(digest, str)
        assert len(digest) == 64  # sha256 hex

    def test_deterministic(self):
        b = _make_bundle()
        assert compute_bundle_digest(b) == compute_bundle_digest(b)

    def test_changes_with_ciphertext(self):
        d1 = compute_bundle_digest(_make_bundle(ciphertext=b"aaa"))
        d2 = compute_bundle_digest(_make_bundle(ciphertext=b"bbb"))
        assert d1 != d2

    def test_matches_manual_sha256(self):
        ct = b"hello world"
        expected = hashlib.sha256(ct).hexdigest()
        assert compute_bundle_digest(_make_bundle(ciphertext=ct)) == expected


# ---------------------------------------------------------------------------
# verify_bundle — no expected digest
# ---------------------------------------------------------------------------

class TestVerifyBundleNoExpected:
    def test_returns_ok_result(self):
        result = verify_bundle(_make_bundle())
        assert isinstance(result, VerifyResult)
        assert result.ok is True

    def test_version_propagated(self):
        b = _make_bundle(version="20991231T235959Z")
        result = verify_bundle(b)
        assert result.version == "20991231T235959Z"

    def test_digest_in_result(self):
        b = _make_bundle()
        result = verify_bundle(b)
        assert result.sha256 == compute_bundle_digest(b)


# ---------------------------------------------------------------------------
# verify_bundle — with expected digest
# ---------------------------------------------------------------------------

class TestVerifyBundleWithExpected:
    def test_ok_when_digest_matches(self):
        b = _make_bundle()
        good = compute_bundle_digest(b)
        result = verify_bundle(b, expected_digest=good)
        assert result.ok is True

    def test_fail_when_digest_mismatches(self):
        b = _make_bundle()
        result = verify_bundle(b, expected_digest="deadbeef" * 8)
        assert result.ok is False

    def test_fail_message_mentions_mismatch(self):
        b = _make_bundle()
        result = verify_bundle(b, expected_digest="deadbeef" * 8)
        assert "mismatch" in result.message


# ---------------------------------------------------------------------------
# VerifyResult.__str__
# ---------------------------------------------------------------------------

class TestVerifyResultStr:
    def test_ok_str_contains_ok(self):
        r = VerifyResult(ok=True, version="v1", sha256="a" * 64, message="fine")
        assert "OK" in str(r)

    def test_fail_str_contains_fail(self):
        r = VerifyResult(ok=False, version="v1", sha256="b" * 64, message="bad")
        assert "FAIL" in str(r)

    def test_str_contains_version(self):
        r = VerifyResult(ok=True, version="myver", sha256="c" * 64, message="")
        assert "myver" in str(r)
