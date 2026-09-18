"""
Cryptographic Hashing Service.
Performs standard SHA-512 digest computation and links hash records to sessions.
"""
from sqlalchemy.orm import Session
import uuid
import logging

from ..models.hash_record import HashRecordModel
from ..core.security import compute_sha512
from ..core.exceptions import SessionNotFoundError
from .session_service import SessionService
from .audit_service import AuditService

logger = logging.getLogger("zaslon.services.hashing")


class HashingService:
    @staticmethod
    def process_message_hash(
        db: Session,
        session_id: str,
        raw_message: str,
        actor: str
    ) -> HashRecordModel:
        # Validate session exists
        session = SessionService.get_session(db, session_id)

        # Compute SHA-512
        message_bytes = raw_message.encode("utf-8")
        digest = compute_sha512(message_bytes)

        # Check for existing hash record
        existing = db.query(HashRecordModel).filter(HashRecordModel.session_id == session_id).first()
        if existing:
            existing.raw_message = raw_message
            existing.message_bytes_len = len(message_bytes)
            existing.sha512_digest = digest
            record = existing
        else:
            record = HashRecordModel(
                id=str(uuid.uuid4()),
                session_id=session_id,
                raw_message=raw_message,
                message_bytes_len=len(message_bytes),
                sha512_digest=digest,
                hash_encoding_format="hex"
            )
            db.add(record)

        # Update session status
        SessionService.update_status(db, session_id, "HASHED", actor=actor)
        db.commit()
        db.refresh(record)

        AuditService.log_event(
            db,
            event_type="HASH_GENERATED",
            actor=actor,
            session_id=session_id,
            details={
                "message_bytes_len": len(message_bytes),
                "sha512_digest": digest
            }
        )
        return record
