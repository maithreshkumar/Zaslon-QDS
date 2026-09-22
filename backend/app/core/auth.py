"""
Authentication & Security Utilities.
Provides PBKDF2-HMAC-SHA256 password hashing and HS256 JWT token generation.
Zero third-party binary dependency issues; uses standard library hashlib, hmac, secrets.
"""
import base64
import json
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from .config import settings
from .datetime_utils import utc_now


def _b64_encode(data: bytes) -> str:
    """Encodes bytes to URL-safe base64 string without padding."""
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64_decode(data: str) -> bytes:
    """Decodes URL-safe base64 string with proper padding."""
    padding = 4 - (len(data) % 4)
    if padding and padding < 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data.encode("utf-8"))


def hash_password(password: str) -> str:
    """Hashes a password using PBKDF2-HMAC-SHA256 with 100,000 rounds and random salt."""
    salt = secrets.token_bytes(16)
    iterations = 100000
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${derived.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a stored PBKDF2-HMAC-SHA256 hash."""
    try:
        parts = hashed_password.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False
        iterations = int(parts[1])
        salt = bytes.fromhex(parts[2])
        expected_derived = bytes.fromhex(parts[3])
        actual_derived = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, iterations)
        return secrets.compare_digest(expected_derived, actual_derived)
    except Exception:
        return False


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Creates a signed HS256 JWT access token."""
    to_encode = data.copy()
    expire = utc_now() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES if hasattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES") else 120))
    to_encode.update({"exp": int(expire.timestamp()), "iat": int(utc_now().timestamp())})

    header = {"alg": "HS256", "typ": "JWT"}
    header_json = json.dumps(header, separators=(",", ":")).encode("utf-8")
    payload_json = json.dumps(to_encode, separators=(",", ":")).encode("utf-8")

    header_b64 = _b64_encode(header_json)
    payload_b64 = _b64_encode(payload_json)

    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    secret_key = (getattr(settings, "SECRET_KEY", None) or "zaslon_qds_cryptographic_master_secret_2026").encode("utf-8")
    signature = hmac.new(secret_key, signing_input, hashlib.sha256).digest()
    signature_b64 = _b64_encode(signature)

    return f"{header_b64}.{payload_b64}.{signature_b64}"


def decode_access_token(token: str, verify_exp: bool = True) -> Dict[str, Any]:
    """Decodes and validates a signed HS256 JWT access token."""
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT token format")

    header_b64, payload_b64, signature_b64 = parts
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    secret_key = (getattr(settings, "SECRET_KEY", None) or "zaslon_qds_cryptographic_master_secret_2026").encode("utf-8")

    expected_signature = hmac.new(secret_key, signing_input, hashlib.sha256).digest()
    actual_signature = _b64_decode(signature_b64)

    if not secrets.compare_digest(expected_signature, actual_signature):
        raise ValueError("Invalid JWT signature")

    payload_bytes = _b64_decode(payload_b64)
    payload = json.loads(payload_bytes.decode("utf-8"))

    if verify_exp:
        exp = payload.get("exp")
        if exp is not None:
            now_ts = int(utc_now().timestamp())
            if now_ts > exp:
                raise ValueError("JWT token has expired")

    return payload
