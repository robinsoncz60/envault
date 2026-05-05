"""Tests for envault.import_export."""

from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from envault.bundle import EnvBundle
from envault.import_export import (
    EXPORT_VERSION,
    ImportExportError,
    export_bundle,
    import_bundle,
)


def _make_bundle() -> EnvBundle:
    ciphertext = base64.b64encode(b"fake-ciphertext-data").decode()
    return EnvBundle(
        ciphertext=ciphertext,
        recipient="age1testrecipient",
        version="20240101T000000Z",
    )


class TestExportBundle:
    def test_creates_file(self, tmp_path: Path) -> None:
        bundle = _make_bundle()
        out = tmp_path / "export.json"
        result = export_bundle(bundle, out)
        assert result == out.resolve()
        assert out.exists()

    def test_file_contains_magic(self, tmp_path: Path) -> None:
        out = tmp_path / "export.json"
        export_bundle(_make_bundle(), out)
        doc = json.loads(out.read_text())
        assert doc["magic"] == "envault-export"

    def test_file_contains_version(self, tmp_path: Path) -> None:
        out = tmp_path / "export.json"
        export_bundle(_make_bundle(), out)
        doc = json.loads(out.read_text())
        assert doc["version"] == EXPORT_VERSION

    def test_payload_has_expected_keys(self, tmp_path: Path) -> None:
        out = tmp_path / "export.json"
        export_bundle(_make_bundle(), out)
        doc = json.loads(out.read_text())
        assert {"ciphertext", "recipient", "version"} <= set(doc["payload"].keys())

    def test_raises_on_unwritable_path(self, tmp_path: Path) -> None:
        bad = tmp_path / "no_such_dir" / "export.json"
        with pytest.raises(ImportExportError, match="Failed to write"):
            export_bundle(_make_bundle(), bad)


class TestImportBundle:
    def test_roundtrip(self, tmp_path: Path) -> None:
        bundle = _make_bundle()
        out = tmp_path / "export.json"
        export_bundle(bundle, out)
        recovered = import_bundle(out)
        assert recovered.ciphertext == bundle.ciphertext
        assert recovered.recipient == bundle.recipient
        assert recovered.version == bundle.version

    def test_raises_on_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(ImportExportError, match="Cannot read"):
            import_bundle(tmp_path / "nonexistent.json")

    def test_raises_on_invalid_json(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text("not json at all")
        with pytest.raises(ImportExportError, match="not valid JSON"):
            import_bundle(bad)

    def test_raises_on_wrong_magic(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text(json.dumps({"magic": "something-else", "version": 1, "payload": {}}))
        with pytest.raises(ImportExportError, match="does not look like"):
            import_bundle(bad)

    def test_raises_on_unsupported_version(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text(json.dumps({"magic": "envault-export", "version": 99, "payload": {}}))
        with pytest.raises(ImportExportError, match="Unsupported export version"):
            import_bundle(bad)

    def test_raises_on_malformed_payload(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text(
            json.dumps({"magic": "envault-export", "version": 1, "payload": {"broken": True}})
        )
        with pytest.raises(ImportExportError, match="Malformed bundle payload"):
            import_bundle(bad)
