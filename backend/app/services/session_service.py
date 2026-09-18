"""
Session Management Service.
Handles session creation, state machine transitions, and participant management.
"""
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
import logging

from ..models.session import SessionModel
from ..models.participant import ParticipantModel
from ..core.exceptions import SessionNotFoundError, VerificationStateError
from .audit_service import AuditService

logger = logging.getLogger("zaslon.services.session")


class SessionService:
    @staticmethod
    def create_session(
        db: Session,
        session_name: str,
        created_by: str,
        verifier_id: str
    ) -> SessionModel:
        session = SessionModel(
            id=str(uuid.uuid4()),
            session_name=session_name,
            status="CREATED",
            created_by=created_by,
            verifier_id=verifier_id
        )
        db.add(session)
        
        # Add default participants (Signer and Verifier)
        signer = ParticipantModel(
            id=str(uuid.uuid4()),
            session_id=session.id,
            name=created_by,
            role="Signer",
            public_key_fingerprint=f"fp_signer_{uuid.uuid4().hex[:16]}",
            auth_token_hash=f"tok_{uuid.uuid4().hex}"
        )
        verifier = ParticipantModel(
            id=str(uuid.uuid4()),
            session_id=session.id,
            name=verifier_id,
            role="Verifier",
            public_key_fingerprint=f"fp_verifier_{uuid.uuid4().hex[:16]}",
            auth_token_hash=f"tok_{uuid.uuid4().hex}"
        )
        db.add(signer)
        db.add(verifier)
        db.commit()
        db.refresh(session)

        AuditService.log_event(
            db,
            event_type="SESSION_CREATED",
            actor=created_by,
            session_id=session.id,
            details={"session_name": session_name, "verifier_id": verifier_id}
        )
        return session

    @staticmethod
    def get_session(db: Session, session_id: str) -> SessionModel:
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            raise SessionNotFoundError(session_id)
        return session

    @staticmethod
    def list_sessions(db: Session, limit: int = 50, offset: int = 0) -> List[SessionModel]:
        return db.query(SessionModel).order_by(SessionModel.created_at.desc()).offset(offset).limit(limit).all()

    @staticmethod
    def update_status(db: Session, session_id: str, new_status: str, actor: str) -> SessionModel:
        session = SessionService.get_session(db, session_id)
        old_status = session.status
        session.status = new_status
        db.commit()
        db.refresh(session)

        AuditService.log_event(
            db,
            event_type="SESSION_STATUS_TRANSITION",
            actor=actor,
            session_id=session.id,
            details={"from": old_status, "to": new_status}
        )
        return session
