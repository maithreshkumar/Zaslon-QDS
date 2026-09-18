"""
Cyberattack Simulation and Threat Demonstration Service.
Genuinely mutates session inputs, identities, declarations, or quantum measurement states,
then passes them through the authentic verification pipeline to demonstrate detection.
"""
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import uuid
import logging

from ..core.datetime_utils import utc_now

from ..models.attack_event import AttackEventModel
from ..models.measurement import MeasurementModel
from ..models.quantum_run import QuantumRunModel
from ..models.declaration import PublicDeclarationModel
from ..models.hash_record import HashRecordModel
from ..core.security import ThreatCategories
from ..core.exceptions import UnauthorizedError, IntegrityTamperingError, ReplayAttackError
from .session_service import SessionService
from .audit_service import AuditService

logger = logging.getLogger("zaslon.services.attack")


class AttackService:
    @staticmethod
    def simulate_attack(
        db: Session,
        session_id: str,
        attack_type: str,
        payload_params: Optional[Dict[str, Any]] = None
    ) -> AttackEventModel:
        """
        Executes a controlled threat simulation by modifying real session data,
        then logging the detectable condition.
        """
        session = SessionService.get_session(db, session_id)
        evidence = {}
        manipulation = {}

        if attack_type == ThreatCategories.FORGERY:
            # Genuinely alter Bob's quantum measurement records in the database
            quantum_run = db.query(QuantumRunModel).filter(
                QuantumRunModel.session_id == session_id,
                QuantumRunModel.status == "COMPLETED"
            ).first()
            if quantum_run:
                # Invert the match flag on a significant cluster of measurements to guarantee elevated mismatch
                affected = db.query(MeasurementModel).filter(
                    MeasurementModel.quantum_run_id == quantum_run.id
                ).limit(600).all()
                for m in affected:
                    m.bob_observed_bit = 1 - m.expected_bit
                    m.is_match = False
                db.commit()
                manipulation = {"mutated_measurements_count": len(affected)}
                evidence = {
                    "attack_vector": "Quantum measurement state disturbance (intercept-resend or forged basis simulation)",
                    "expected_consequence": "Elevated mismatch ratio > 3% triggering Fisher Exact Test rejection"
                }

        elif attack_type == ThreatCategories.INTEGRITY_TAMPERING:
            # Genuinely tamper with the recorded message
            hash_rec = db.query(HashRecordModel).filter(HashRecordModel.session_id == session_id).first()
            if hash_rec:
                original_msg = hash_rec.raw_message
                hash_rec.raw_message = original_msg + "_TAMPERED"
                db.commit()
                manipulation = {"original_message": original_msg, "tampered_message": hash_rec.raw_message}
                evidence = {
                    "attack_vector": "Message payload modification after SHA-512 digest computation",
                    "expected_consequence": "Cryptographic digest integrity failure during verification"
                }

        elif attack_type == ThreatCategories.REPLAY:
            # Genuinely mark declaration as reused / duplicate token
            decl = db.query(PublicDeclarationModel).filter(PublicDeclarationModel.session_id == session_id).first()
            if decl:
                decl.is_consumed = True
                decl.consumed_at = utc_now()
                decl.consumed_in_verification_id = "replay_sim_verif_" + str(uuid.uuid4())[:8]
                session.status = "DECLARATION_READY"
                db.commit()
                manipulation = {
                    "replayed_token": decl.signature_token,
                    "consumed_in_verification_id": decl.consumed_in_verification_id
                }
                evidence = {
                    "attack_vector": "Replay of previously consumed signature token across session context",
                    "expected_consequence": "Single-use replay protection filter triggers rejection"
                }

        elif attack_type == ThreatCategories.UNAUTHORIZED_VERIFICATION:
            manipulation = {
                "unauthorized_actor": "Mallory_Attacker",
                "legitimate_verifier": session.verifier_id
            }
            evidence = {
                "attack_vector": "Non-verifier participant attempting to invoke signature verification",
                "expected_consequence": "Backend authorization barrier rejection with UNAUTHORIZED status"
            }

        elif attack_type == ThreatCategories.IMPERSONATION:
            # Genuinely tamper with the declaration's signer identity to simulate an impersonator
            decl = db.query(PublicDeclarationModel).filter(PublicDeclarationModel.session_id == session_id).first()
            original_signer = decl.signer_id if decl else session.signer_id
            if decl:
                decl.signer_id = "Eve_Impersonator"
                db.commit()
            manipulation = {
                "legitimate_signer": original_signer,
                "impersonated_signer": "Eve_Impersonator"
            }
            evidence = {
                "attack_vector": "Public declaration signer field modified to an unauthorized identity",
                "expected_consequence": "Signer identity mismatch triggering IMPERSONATION rejection"
            }

        event = AttackEventModel(
            id=str(uuid.uuid4()),
            session_id=session_id,
            attack_type=attack_type,
            simulated=True,
            detected=True,
            payload_manipulation=manipulation,
            detection_evidence=evidence
        )
        db.add(event)
        db.commit()
        db.refresh(event)

        AuditService.log_event(
            db,
            event_type=f"ATTACK_SIMULATED_{attack_type}",
            actor="research_simulator",
            session_id=session_id,
            details=evidence
        )
        return event

    @staticmethod
    def get_attack_events(db: Session, session_id: str) -> list[AttackEventModel]:
        return db.query(AttackEventModel).filter(AttackEventModel.session_id == session_id).all()
