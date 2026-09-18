"""
High-Level QDS Workflow Coordinator Service.
Coordinates the multi-stage pipeline: Message -> SHA-512 -> Teleportation -> Declaration -> Verification.
"""
from sqlalchemy.orm import Session
from typing import Dict, Any
import logging

from .session_service import SessionService
from .hashing_service import HashingService
from .teleportation_service import TeleportationService
from .declaration_service import DeclarationService
from .verification_service import VerificationService

logger = logging.getLogger("zaslon.services.qds")


class QdsService:
    @staticmethod
    def get_full_session_status(db: Session, session_id: str) -> Dict[str, Any]:
        """Collects complete workflow state for dashboard and inspection."""
        session = SessionService.get_session(db, session_id)
        
        has_hash = session.hash_record is not None
        has_runs = len(session.quantum_runs) > 0
        has_declaration = session.declaration is not None
        has_verification = len(session.verification_results) > 0

        latest_run = session.quantum_runs[-1] if has_runs else None
        latest_result = session.verification_results[-1] if has_verification else None

        return {
            "session_id": session.id,
            "session_name": session.session_name,
            "status": session.status,
            "created_by": session.created_by,
            "verifier_id": session.verifier_id,
            "stages": {
                "hash_stage": {
                    "completed": has_hash,
                    "sha512_digest": session.hash_record.sha512_digest if has_hash else None,
                    "message_len": session.hash_record.message_bytes_len if has_hash else None
                },
                "quantum_stage": {
                    "completed": latest_run.status == "COMPLETED" if latest_run else False,
                    "teleportation_count": latest_run.teleportation_count if latest_run else 0,
                    "duration_ms": latest_run.execution_duration_ms if latest_run else None,
                    "status": latest_run.status if latest_run else "NOT_STARTED"
                },
                "declaration_stage": {
                    "completed": has_declaration,
                    "token": session.declaration.signature_token if has_declaration else None,
                    "status": session.declaration.status if has_declaration else None
                },
                "verification_stage": {
                    "completed": has_verification,
                    "decision": latest_result.security_decision if latest_result else None,
                    "mismatch_ratio": latest_result.mismatch_ratio if latest_result else None,
                    "fisher_p_value": latest_result.fisher_p_value if latest_result else None,
                    "attack_detected": latest_result.attack_detected if latest_result else False
                }
            }
        }
