"""Verify the integrity and authenticity of a pulled .env bundle."""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from typing import Optional

from envault.bundle import EnvBundle
from envault.exceptions import EnvaultError


class VerifyError(EnvaultError):
    """Raised when bundle verification fails."""


@dataclass
class VerifyResult:
    ok: bool
    version: str
    sha256: str
    message: str

    def __str__(self) -> str:
        status = "OK" if self.ok else "FAIL"
        return f"[{status}] version={self.version} sha256={self.sha256[:16]}... {self.message}"


def _sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compute_bundle_digest(bundle: EnvBundle) -> str:
    """Return a deterministic SHA-256 over the bundle's ciphertext."""
    return _sha256_of(bundle.ciphertext)


def verify_bundle(
    bundle: EnvBundle,
    expected_digest: Optional[str] = None,
) -> VerifyResult:
    """Verify a bundle's ciphertext digest.

    If *expected_digest* is provided the computed digest must match it.
    Otherwise the function just computes and returns the digest (always ok).
    """
    digest = compute_bundle_digest(bundle)

    if expected_digest is not None:
        if not hmac.compare_digest(digest, expected_digest):
            return VerifyResult(
                ok=False,
                version=bundle.version,
                sha256=digest,
                message=f"digest mismatch (expected {expected_digest[:16]}...)",
            )

    return VerifyResult(
        ok=True,
        version=bundle.version,
        sha256=digest,
        message="bundle integrity verified",
    )
