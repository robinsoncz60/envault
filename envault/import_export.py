"""Import and export .env bundles as portable encrypted archives."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Union

from envault.bundle import EnvBundle, decode_bundle, encode_bundle
from envault.crypto import decrypt, encrypt
from envault.exceptions import EnvaultError


class ImportExportError(EnvaultError):
    """Raised when import or export operations fail."""


EXPORT_VERSION = 1
_MAGIC = "envault-export"


def export_bundle(
    bundle: EnvBundle,
    output_path: Union[str, Path],
    *,
    armor: bool = True,
) -> Path:
    """Serialize an EnvBundle to a portable JSON export file.

    Args:
        bundle: The encrypted bundle to export.
        output_path: Destination file path.
        armor: If True, base64-encode the ciphertext for readability.

    Returns:
        The resolved output path.
    """
    output_path = Path(output_path)
    payload = bundle.to_dict()
    if armor:
        payload["ciphertext"] = base64.b64encode(
            base64.b64decode(payload["ciphertext"])
        ).decode()

    export_doc = {
        "magic": _MAGIC,
        "version": EXPORT_VERSION,
        "payload": payload,
    }

    try:
        output_path.write_text(json.dumps(export_doc, indent=2))
    except OSError as exc:
        raise ImportExportError(f"Failed to write export file: {exc}") from exc

    return output_path.resolve()


def import_bundle(input_path: Union[str, Path]) -> EnvBundle:
    """Deserialize an EnvBundle from a portable JSON export file.

    Args:
        input_path: Path to the export file.

    Returns:
        The reconstructed EnvBundle.

    Raises:
        ImportExportError: If the file is missing, malformed, or has wrong magic.
    """
    input_path = Path(input_path)
    try:
        raw = input_path.read_text()
    except OSError as exc:
        raise ImportExportError(f"Cannot read import file: {exc}") from exc

    try:
        doc = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ImportExportError(f"Import file is not valid JSON: {exc}") from exc

    if doc.get("magic") != _MAGIC:
        raise ImportExportError("File does not look like an envault export.")

    supported = {1}
    if doc.get("version") not in supported:
        raise ImportExportError(
            f"Unsupported export version: {doc.get('version')}"
        )

    try:
        return EnvBundle.from_dict(doc["payload"])
    except Exception as exc:
        raise ImportExportError(f"Malformed bundle payload: {exc}") from exc
