from __future__ import annotations

import pytest

from zaslon_shared.crypto import decrypt_payload, encrypt_payload


def test_aes_gcm_round_trip_and_tamper_detection():
    package = encrypt_payload(b"classified payload", "correct horse battery", "memo.txt")
    filename, plaintext = decrypt_payload(package, "correct horse battery")
    assert filename == "memo.txt"
    assert plaintext == b"classified payload"
    with pytest.raises(ValueError):
        decrypt_payload(package, "incorrect passphrase")
