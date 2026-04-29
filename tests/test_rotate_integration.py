"""Light integration test: rotate calls the right chain of operations."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

import pytest

from envault.rotate import RotateError, rotate


def _config(env="staging"):
    return SimpleNamespace(env=env, bucket="bucket")


def _kp(pub="age1pub", priv="/k/priv.key"):
    return SimpleNamespace(public_key=pub, private_key_path=priv)


@patch("envault.rotate.encode_bundle", return_value=b"encoded")
@patch("envault.rotate.encrypt", return_value=b"new-ct")
@patch("envault.rotate.decrypt", return_value=b"plain")
@patch("envault.rotate.decode_bundle")
@patch("envault.rotate._make_version", return_value="20990101T120000Z")
@patch("envault.rotate.latest_version")
def test_full_rotate_chain(mock_lv, mock_mv, mock_decode, mock_dec, mock_enc, mock_encode):
    mock_lv.return_value = SimpleNamespace(s3_key="staging/old.bundle")
    mock_decode.return_value = SimpleNamespace(ciphertext=b"old-ct")

    storage = MagicMock()
    storage.download.return_value = b"raw-bundle"

    old_kp = _kp("age1old", "/keys/old.key")
    new_kp = _kp("age1new", "/keys/new.key")

    result = rotate(_config(), storage, old_kp, new_kp, "bob")

    # correct S3 key shape
    assert result == "staging/20990101T120000Z.bundle"

    # decrypt called with old private key
    mock_dec.assert_called_once_with(b"old-ct", "/keys/old.key")

    # encrypt called with new public key
    mock_enc.assert_called_once_with(b"plain", "age1new")

    # encode_bundle called with new ciphertext and identity
    mock_encode.assert_called_once_with(b"new-ct", "bob")

    # upload called once with correct key
    storage.upload.assert_called_once_with("staging/20990101T120000Z.bundle", b"encoded")
