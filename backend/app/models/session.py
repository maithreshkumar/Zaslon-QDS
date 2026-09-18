"""
Session Entity Model.
"""
from sqlalchemy import Column, String, DateTime, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from ..db.base import Base
from ..core.datetime_utils import utc_now


class SessionModel(Base):
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_name = Column(String(128), nullable=False)
    status = Column(
        Enum(
            'CREATED',
            'HASHING',
            'HASHED',
            'STATE_PREPARATION',
            'TELEPORTING',
            'TELEPORTED',
            'DECLARATION_READY',
            'IN_TRANSIT',
            'INTERCEPTED',
            'FORWARDED',
            'SAMPLING',
            'VERIFYING',
            'VERIFIED',
            'REJECTED',
            'FAILED',
            name='session_status_enum'
        ),
        nullable=False,
        default='CREATED'
    )
    created_by = Column(String(64), nullable=False)
    verifier_id = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    participants = relationship("ParticipantModel", back_populates="session", cascade="all, delete-orphan")
    hash_record = relationship("HashRecordModel", back_populates="session", uselist=False, cascade="all, delete-orphan")
    quantum_runs = relationship("QuantumRunModel", back_populates="session", cascade="all, delete-orphan")
    declaration = relationship("PublicDeclarationModel", back_populates="session", uselist=False, cascade="all, delete-orphan")
    verification_samples = relationship("VerificationSampleModel", back_populates="session", cascade="all, delete-orphan")
    verification_results = relationship("VerificationResultModel", back_populates="session", cascade="all, delete-orphan")
    attack_events = relationship("AttackEventModel", back_populates="session", cascade="all, delete-orphan")
    transmissions = relationship("TransmissionPackageModel", back_populates="session", cascade="all, delete-orphan")

    @property
    def signer_id(self) -> str:
        return self.created_by

