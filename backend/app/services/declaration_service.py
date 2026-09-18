"""
Public Declaration Service.
Manages generation, persistence, cryptographic binding, and single-use consumption of public QDS declarations.
"""
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Tuple, Optional
import uuid
import logging

from ..core.datetime_utils import utc_now

from ..models.declaration import PublicDeclarationModel
from ..models.hash_record import HashRecordModel
from ..models.quantum_run import QuantumRunModel
from ..core.security import compute_sha512, generate_secure_token, ThreatCategories
from ..core.config import settings
from ..core.exceptions import SessionNotFoundError, VerificationStateError, UnauthorizedError
from .session_service import SessionService
from .audit_service import AuditService

logger = logging.getLogger("zaslon.services.declaration")


class DeclarationService:
    @staticmethod
    def create_declaration(
        db: Session,
        session_id: str,
        signer_id: str
    ) -> PublicDeclarationModel:
        session = SessionService.get_session(db, session_id)

        # Enforce signer authorization barrier: only the session's designated signer can declare
        if signer_id != session.signer_id:
            logger.warning(
                f"IMPERSONATION_ATTEMPT: Actor '{signer_id}' attempted to create declaration "
                f"for session '{session_id}' designated to signer '{session.signer_id}'."
            )
            raise UnauthorizedError(
                f"Actor '{signer_id}' is not the authorized signer '{session.signer_id}' for this session."
            )

        # Verify quantum run completed
        quantum_run = db.query(QuantumRunModel).filter(
            QuantumRunModel.session_id == session_id,
            QuantumRunModel.status == "COMPLETED"
        ).first()
        if not quantum_run:
            raise VerificationStateError(session.status, "TELEPORTED")

        # Verify hash record exists
        hash_record = db.query(HashRecordModel).filter(HashRecordModel.session_id == session_id).first()
        if not hash_record:
            raise VerificationStateError(session.status, "HASHED")

        # Generate cryptographic signature token and commitment
        token = generate_secure_token(prefix="sig_qds_")
        now_dt = utc_now()
        now_ts = int(now_dt.timestamp())
        payload_material = (
            f"{session_id}:{signer_id}:{hash_record.sha512_digest}:"
            f"{quantum_run.id}:{token}:{now_ts}"
        )
        payload_hash = compute_sha512(payload_material.encode("utf-8"))

        # Check existing declaration
        existing = db.query(PublicDeclarationModel).filter(PublicDeclarationModel.session_id == session_id).first()
        if existing:
            declaration = existing
            declaration.signer_id = signer_id
            declaration.signature_token = token
            declaration.declaration_payload_hash = payload_hash
            declaration.status = "ACTIVE"
            declaration.is_consumed = False
            declaration.consumed_at = None
            declaration.consumed_in_verification_id = None
            declaration.declared_at = now_dt
        else:
            declaration = PublicDeclarationModel(
                id=str(uuid.uuid4()),
                session_id=session_id,
                signer_id=signer_id,
                signature_token=token,
                declaration_payload_hash=payload_hash,
                status="ACTIVE",
                is_consumed=False,
                consumed_at=None,
                consumed_in_verification_id=None,
                declared_at=now_dt
            )
            db.add(declaration)

        SessionService.update_status(db, session_id, "DECLARATION_READY", actor=signer_id)
        db.commit()
        db.refresh(declaration)

        AuditService.log_event(
            db,
            event_type="DECLARATION_CREATED",
            actor=signer_id,
            session_id=session_id,
            details={
                "declaration_id": declaration.id,
                "token_prefix": token[:16],
                "payload_hash": payload_hash
            }
        )
        return declaration

    @staticmethod
    def get_declaration(db: Session, session_id: str) -> PublicDeclarationModel:
        declaration = db.query(PublicDeclarationModel).filter(
            PublicDeclarationModel.session_id == session_id
        ).first()
        if not declaration:
            raise SessionNotFoundError(f"Declaration for session {session_id}")
        return declaration

    @staticmethod
    def verify_declaration_status(
        declaration: PublicDeclarationModel,
        replay_window: Optional[int] = None
    ) -> tuple[bool, Optional[str], str]:
        """
        Verifies whether a public declaration is valid, active, and has not been replayed.
        """
        if replay_window is None:
            replay_window = settings.REPLAY_WINDOW_SECONDS

        if declaration.status != "ACTIVE":
            return (
                False,
                ThreatCategories.INTEGRITY_TAMPERING,
                f"Declaration is in invalid state: '{declaration.status}'."
            )

        if declaration.is_consumed:
            return (
                False,
                ThreatCategories.REPLAY,
                f"Signature token '{declaration.signature_token}' has already been consumed in verification '{declaration.consumed_in_verification_id}' at {declaration.consumed_at}."
            )

        if declaration.declared_at:
            decl_dt = declaration.declared_at
            now_dt = utc_now()
            # Normalize timezone awareness for comparison
            if decl_dt.tzinfo is None:
                decl_ts = decl_dt.timestamp()
                now_ts = now_dt.replace(tzinfo=None).timestamp()
            else:
                decl_ts = decl_dt.timestamp()
                now_ts = now_dt.timestamp()
            age_seconds = now_ts - decl_ts
            if age_seconds > replay_window:
                return (
                    False,
                    ThreatCategories.REPLAY,
                    f"Signature declaration expired: age {age_seconds:.1f}s exceeds replay window of {replay_window}s."
                )

        return True, None, "Declaration is active, unconsumed, and fresh."

    @staticmethod
    def consume_declaration(
        db: Session,
        declaration_id: str,
        verification_id: str
    ) -> PublicDeclarationModel:
        """Atomically marks a declaration token as consumed upon successful verification."""
        declaration = db.query(PublicDeclarationModel).filter(PublicDeclarationModel.id == declaration_id).first()
        if not declaration:
            raise SessionNotFoundError(f"Declaration {declaration_id}")

        declaration.is_consumed = True
        declaration.consumed_at = utc_now()
        declaration.consumed_in_verification_id = verification_id
        db.commit()
        db.refresh(declaration)

        AuditService.log_event(
            db,
            event_type="DECLARATION_CONSUMED",
            actor="system",
            session_id=declaration.session_id,
            details={
                "declaration_id": declaration.id,
                "consumed_in_verification_id": verification_id,
                "consumed_at": declaration.consumed_at.isoformat()
            }
        )
        return declaration

