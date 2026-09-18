"""
Participant Entity Model.
"""
from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from ..db.base import Base
from ..core.datetime_utils import utc_now


class ParticipantModel(Base):
    __tablename__ = "participants"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(64), nullable=False)
    role = Column(
        Enum('Signer', 'Verifier', 'Administrator', name='participant_role_enum'),
        nullable=False
    )
    public_key_fingerprint = Column(String(128), nullable=False)
    auth_token_hash = Column(String(128), nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    session = relationship("SessionModel", back_populates="participants")

    __table_args__ = (
        UniqueConstraint("session_id", "name", name="uq_session_participant"),
    )
