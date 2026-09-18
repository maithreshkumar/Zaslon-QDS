"""
Security Event Entity Model for Zaslon-QDS.
Tracks intrusion attempts, unauthorized access probes, and verification policy violations.
"""
from sqlalchemy import Column, String, DateTime, JSON
from datetime import datetime
import uuid

from ..db.base import Base
from ..core.datetime_utils import utc_now


class SecurityEventModel(Base):
    __tablename__ = "security_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), nullable=True, index=True)
    event_type = Column(String(64), nullable=False, index=True)  # UNAUTHORIZED_PROBE, UNAUTHORIZED_VERIFICATION
    severity = Column(String(32), default="HIGH", nullable=False)
    actor = Column(String(64), nullable=False, index=True)
    resource = Column(String(255), nullable=False)
    ip_address = Column(String(45), nullable=True)
    details = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)
