from __future__ import annotations

import base64
import hashlib
import os
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt


def sha512_hex(data: bytes) -> str:
    return hashlib.sha512(data).hexdigest()


def canonical_json_hash(payload: bytes) -> str:
    return hashlib.sha512(payload).hexdigest()


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    kdf = Scrypt(salt=salt, length=32, n=2**15, r=8, p=1)
    return kdf.derive(passphrase.encode("utf-8"))


def encrypt_payload(data: bytes, passphrase: str, filename: str) -> dict[str, Any]:
    salt = os.urandom(16)
    nonce = os.urandom(12)
    key = _derive_key(passphrase, salt)
    aad = f"ZASLON-QDS|{filename}|AES-256-GCM|v1".encode("utf-8")
    ciphertext = AESGCM(key).encrypt(nonce, data, aad)
    return {
        "format": "zaslon.encrypted.v1",
        "algorithm": "AES-256-GCM",
        "kdf": {
            "algorithm": "scrypt",
            "n": 32768,
            "r": 8,
            "p": 1,
            "salt_b64": base64.b64encode(salt).decode("ascii"),
        },
        "nonce_b64": base64.b64encode(nonce).decode("ascii"),
        "aad_b64": base64.b64encode(aad).decode("ascii"),
        "ciphertext_b64": base64.b64encode(ciphertext).decode("ascii"),
        "original_filename": filename,
        "plaintext_sha512": sha512_hex(data),
    }


def decrypt_payload(package: dict[str, Any], passphrase: str) -> tuple[str, bytes]:
    if package.get("format") != "zaslon.encrypted.v1":
        raise ValueError("Unsupported encrypted package format")
    if package.get("algorithm") != "AES-256-GCM":
        raise ValueError("Unsupported encryption algorithm")
    try:
        salt = base64.b64decode(package["kdf"]["salt_b64"], validate=True)
        nonce = base64.b64decode(package["nonce_b64"], validate=True)
        aad = base64.b64decode(package["aad_b64"], validate=True)
        ciphertext = base64.b64decode(package["ciphertext_b64"], validate=True)
    except (KeyError, ValueError) as exc:
        raise ValueError("Malformed encrypted package") from exc
    key = _derive_key(passphrase, salt)
    try:
        plaintext = AESGCM(key).decrypt(nonce, ciphertext, aad)
    except InvalidTag as exc:
        raise ValueError("Decryption failed: wrong passphrase or modified package") from exc
    if sha512_hex(plaintext) != package.get("plaintext_sha512"):
        raise ValueError("Decrypted payload integrity check failed")
    return str(package.get("original_filename", "decrypted.bin")), plaintext
