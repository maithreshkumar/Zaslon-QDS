"""
Audit Service.
Records tamper-evident security events, session transitions, and verifications.
"""
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
import logging

from ..models.audit_event import AuditEventModel

logger = logging.getLogger("zaslon.services.audit")


class AuditService:
    @staticmethod
    def log_event(
        db: Session,
        event_type: str,
        actor: str,
        details: Dict[str, Any],
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> AuditEventModel:
        audit = AuditEventModel(
            session_id=session_id,
            event_type=event_type,
            actor=actor,
            ip_address=ip_address,
            details=details
        )
        db.add(audit)
        db.commit()
        db.refresh(audit)
        logger.info(f"AUDIT_EVENT [{event_type}] by '{actor}' for session '{session_id}'")
        return audit

    @staticmethod
    def get_events(
        db: Session,
        session_id: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 100
    ) -> List[AuditEventModel]:
        query = db.query(AuditEventModel)
        if session_id:
            query = query.filter(AuditEventModel.session_id == session_id)
        if event_type:
            query = query.filter(AuditEventModel.event_type == event_type)
        return query.order_by(AuditEventModel.timestamp.desc()).limit(limit).all()
