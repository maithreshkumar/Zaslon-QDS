"""
Public Declaration Entity Model.
"""
from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from ..db.base import Base
from ..core.datetime_utils import utc_now


class PublicDeclarationModel(Base):
    __tablename__ = "public_declarations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), unique=True, nullable=False)
    signer_id = Column(String(64), nullable=False, index=True)
    signature_token = Column(String(256), nullable=False)
    declaration_payload_hash = Column(String(128), nullable=False)
    declared_at = Column(DateTime, default=utc_now, nullable=False)
    status = Column(
        Enum('ACTIVE', 'TAMPERED', 'REVOKED', name='declaration_status_enum'),
        default='ACTIVE',
        nullable=False
    )
    is_consumed = Column(Boolean, default=False, nullable=False)
    consumed_at = Column(DateTime, nullable=True)
    consumed_in_verification_id = Column(String(36), nullable=True)

    session = relationship("SessionModel", back_populates="declaration")
