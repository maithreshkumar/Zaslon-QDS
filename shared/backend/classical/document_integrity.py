import hmac

from zaslon_shared.crypto import sha512_hex


def hash_matches(document: bytes, expected_hex: str) -> bool:
    return hmac.compare_digest(sha512_hex(document), expected_hex)

