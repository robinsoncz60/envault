"""Bundle: serialise/deserialise encrypted .env payloads for storage."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Any, Dict


class BundleError(Exception):
    """Raised when bundle encoding/decoding fails."""


@dataclass
class EnvBundle:
    ciphertext: bytes
    env_name: str
    version: str

    # ------------------------------------------------------------------
    # serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "env_name": self.env_name,
            "version": self.version,
            "ciphertext": base64.b64encode(self.ciphertext).decode(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EnvBundle":
        try:
            return cls(
                env_name=data["env_name"],
                version=data["version"],
                ciphertext=base64.b64decode(data["ciphertext"]),
            )
        except KeyError as exc:
            raise BundleError(f"Missing field in bundle: {exc}") from exc
        except Exception as exc:
            raise BundleError(f"Invalid bundle data: {exc}") from exc


def encode_bundle(bundle: EnvBundle) -> bytes:
    """Serialise *bundle* to JSON bytes."""
    try:
        return json.dumps(bundle.to_dict()).encode()
    except Exception as exc:
        raise BundleError(f"Failed to encode bundle: {exc}") from exc


def decode_bundle(raw: bytes) -> EnvBundle:
    """Deserialise *raw* JSON bytes into an :class:`EnvBundle`."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise BundleError(f"Bundle is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise BundleError(
            f"Bundle must be a JSON object, got {type(data).__name__}"
        )
    return EnvBundle.from_dict(data)
