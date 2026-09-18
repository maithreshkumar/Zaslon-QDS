"""
Unit Tests for Role-Based Workflows (Alice -> Eve -> Bob), Authentication, and RBAC.
"""
import pytest
from datetime import timedelta

from backend.app.core.auth import hash_password, verify_password, create_access_token, decode_access_token
from backend.app.models.user import UserModel
from backend.app.models.transmission import TransmissionPackageModel
from backend.app.models.session import SessionModel
from backend.app.services.transmission_service import TransmissionService


def test_password_hashing_and_verification():
    raw_pwd = "SecureDefensePassword#2026"
    pwd_hash = hash_password(raw_pwd)
    assert pwd_hash.startswith("pbkdf2_sha256$100000$")
    assert verify_password(raw_pwd, pwd_hash) is True
    assert verify_password("WrongPassword!", pwd_hash) is False


def test_jwt_token_generation_and_decoding():
    payload = {"sub": "user_123", "username": "alice", "role": "ALICE"}
    token = create_access_token(payload, expires_delta=timedelta(minutes=15))
    decoded = decode_access_token(token)
    assert decoded["sub"] == "user_123"
    assert decoded["username"] == "alice"
    assert decoded["role"] == "ALICE"
    assert "exp" in decoded
    assert "iat" in decoded


def test_jwt_expired_token_rejected():
    payload = {"sub": "user_123", "username": "alice", "role": "ALICE"}
    token = create_access_token(payload, expires_delta=timedelta(seconds=-10))
    with pytest.raises(ValueError, match="expired"):
        decode_access_token(token)


def test_jwt_tampered_token_rejected():
    payload = {"sub": "user_123", "username": "alice", "role": "ALICE"}
    token = create_access_token(payload)
    tampered_token = token[:-4] + "abcd"
    with pytest.raises(ValueError, match="signature"):
        decode_access_token(tampered_token)


def test_transmission_tracking_number_generation():
    trk1 = TransmissionService.generate_tracking_number()
    trk2 = TransmissionService.generate_tracking_number()
    assert trk1.startswith("QDS-PKG-")
    assert trk2.startswith("QDS-PKG-")
    assert trk1 != trk2
