"""Bundle: pack/unpack encrypted .env payloads with metadata."""

from __future__ import annotations

import json
import base64
from dataclasses import dataclass, asdict
from typing import Optional


class BundleError(Exception):
    """Raised when bundle encoding/decoding fails."""


@dataclass
class EnvBundle:
    """An encrypted .env payload with associated metadata."""

    environment: str
    version: str
    ciphertext: bytes
    public_key: str
    comment: Optional[str] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["ciphertext"] = base64.b64encode(self.ciphertext).decode()
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "EnvBundle":
        try:
            data = dict(data)
            data["ciphertext"] = base64.b64decode(data["ciphertext"])
            return cls(**data)
        except (KeyError, TypeError, ValueError) as exc:
            raise BundleError(f"Invalid bundle data: {exc}") from exc


def encode_bundle(bundle: EnvBundle) -> bytes:
    """Serialize a bundle to JSON bytes."""
    try:
        return json.dumps(bundle.to_dict(), indent=2).encode()
    except (TypeError, ValueError) as exc:
        raise BundleError(f"Failed to encode bundle: {exc}") from exc


def decode_bundle(data: bytes) -> EnvBundle:
    """Deserialize a bundle from JSON bytes."""
    try:
        raw = json.loads(data.decode())
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise BundleError(f"Failed to decode bundle: {exc}") from exc
    return EnvBundle.from_dict(raw)
