"""
Attack Event Entity Model.
"""
from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from ..db.base import Base
from ..core.datetime_utils import utc_now


class AttackEventModel(Base):
    __tablename__ = "attack_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    attack_type = Column(String(64), nullable=False, index=True)
    simulated = Column(Boolean, default=False, nullable=False)
    detected = Column(Boolean, default=True, nullable=False)
    payload_manipulation = Column(JSON, nullable=True)
    detection_evidence = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    session = relationship("SessionModel", back_populates="attack_events")
