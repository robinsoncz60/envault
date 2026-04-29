"""Tests for envault.bundle."""

import json
import base64
import pytest

from envault.bundle import (
    BundleError,
    EnvBundle,
    encode_bundle,
    decode_bundle,
)


SAMPLE_CIPHERTEXT = b"\x00\x01\x02encrypted-bytes\xff"


@pytest.fixture()
def bundle() -> EnvBundle:
    return EnvBundle(
        environment="staging",
        version="20240101T120000Z",
        ciphertext=SAMPLE_CIPHERTEXT,
        public_key="age1abcdef",
        comment="initial push",
    )


class TestEnvBundle:
    def test_to_dict_base64_encodes_ciphertext(self, bundle):
        d = bundle.to_dict()
        assert d["ciphertext"] == base64.b64encode(SAMPLE_CIPHERTEXT).decode()

    def test_from_dict_roundtrip(self, bundle):
        restored = EnvBundle.from_dict(bundle.to_dict())
        assert restored == bundle

    def test_from_dict_missing_key_raises(self):
        with pytest.raises(BundleError, match="Invalid bundle data"):
            EnvBundle.from_dict({"environment": "prod"})

    def test_from_dict_bad_base64_raises(self, bundle):
        d = bundle.to_dict()
        d["ciphertext"] = "!!!not-base64!!!"
        with pytest.raises(BundleError):
            EnvBundle.from_dict(d)

    def test_comment_is_optional(self):
        b = EnvBundle(
            environment="prod",
            version="v1",
            ciphertext=b"data",
            public_key="age1xyz",
        )
        assert b.comment is None


class TestEncodeBundle:
    def test_returns_bytes(self, bundle):
        result = encode_bundle(bundle)
        assert isinstance(result, bytes)

    def test_result_is_valid_json(self, bundle):
        raw = json.loads(encode_bundle(bundle))
        assert raw["environment"] == "staging"


class TestDecodeBundle:
    def test_roundtrip(self, bundle):
        restored = decode_bundle(encode_bundle(bundle))
        assert restored == bundle

    def test_raises_on_invalid_json(self):
        with pytest.raises(BundleError, match="Failed to decode"):
            decode_bundle(b"{not valid json}")

    def test_raises_on_missing_fields(self):
        payload = json.dumps({"environment": "dev"}).encode()
        with pytest.raises(BundleError):
            decode_bundle(payload)

    def test_raises_on_non_utf8_bytes(self):
        with pytest.raises(BundleError):
            decode_bundle(b"\xff\xfe")
