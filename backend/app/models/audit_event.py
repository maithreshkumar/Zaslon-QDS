"""
Audit Event Entity Model.
"""
from sqlalchemy import Column, BigInteger, Integer, String, DateTime, JSON, Index
from datetime import datetime

from ..db.base import Base
from ..core.datetime_utils import utc_now


class AuditEventModel(Base):
    __tablename__ = "audit_events"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    session_id = Column(String(36), nullable=True, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    actor = Column(String(64), nullable=False)
    ip_address = Column(String(45), nullable=True)
    details = Column(JSON, nullable=False)
    timestamp = Column(DateTime, default=utc_now, nullable=False, index=True)
