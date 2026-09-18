"""
Authorization and Role Enforcement Service.
Guarantees strict backend verification of participants, preventing unauthorized access.
"""
from sqlalchemy.orm import Session
from typing import Optional, List
import logging

from ..models.participant import ParticipantModel
from ..models.session import SessionModel
from ..core.exceptions import UnauthorizedError
from .audit_service import AuditService

logger = logging.getLogger("zaslon.services.authorization")


class AuthorizationService:
    @staticmethod
    def verify_participant_role(
        db: Session,
        session_id: str,
        actor: str,
        allowed_roles: List[str]
    ) -> ParticipantModel:
        """
        Validates that the actor is a registered participant in the session
        with one of the specified allowed roles.
        """
        participant = db.query(ParticipantModel).filter(
            ParticipantModel.session_id == session_id,
            ParticipantModel.name == actor
        ).first()

        if not participant:
            AuditService.log_event(
                db,
                event_type="UNAUTHORIZED_ACCESS_ATTEMPT",
                actor=actor,
                session_id=session_id,
                details={"reason": "Unknown participant identity", "required_roles": allowed_roles}
            )
            raise UnauthorizedError(f"Participant '{actor}' is not registered for session '{session_id}'.", actor=actor)

        if participant.role not in allowed_roles:
            AuditService.log_event(
                db,
                event_type="PRIVILEGE_VIOLATION_ATTEMPT",
                actor=actor,
                session_id=session_id,
                details={"role": participant.role, "required_roles": allowed_roles}
            )
            raise UnauthorizedError(
                f"Participant '{actor}' has role '{participant.role}', required: {allowed_roles}.",
                actor=actor
            )

        return participant

    @staticmethod
    def verify_can_verify(db: Session, session_id: str, actor: str) -> None:
        """Enforces that only designated Verifiers can execute verification."""
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if session and session.verifier_id != actor:
            raise UnauthorizedError(
                f"Actor '{actor}' is not the designated verifier ('{session.verifier_id}') for this session.",
                actor=actor
            )
        AuthorizationService.verify_participant_role(db, session_id, actor, ["Verifier", "Administrator"])
