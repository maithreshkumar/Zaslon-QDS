"""
User Entity Model for Role-Based Access Control (RBAC).
Supports ALICE (Signer), EVE (Attacker / Adversary), BOB (Verifier), and ADMIN (Auditor / Researcher).
"""
from sqlalchemy import Column, String, DateTime, Enum
from datetime import datetime
import uuid

from ..db.base import Base
from ..core.datetime_utils import utc_now


class UserModel(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(128), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    role = Column(
        Enum('ALICE', 'EVE', 'BOB', 'ADMIN', name='user_role_enum'),
        nullable=False,
        index=True
    )
    public_identity = Column(String(128), nullable=False)
    status = Column(
        Enum('ACTIVE', 'SUSPENDED', name='user_status_enum'),
        default='ACTIVE',
        nullable=False
    )
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
