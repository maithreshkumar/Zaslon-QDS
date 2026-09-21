"""
Transmission Service.
Orchestrates the in-flight lifecycle of QDS packages:
Alice Dispatches (IN_TRANSIT) -> Eve Intercepts (INTERCEPTED) -> Eve Mutates (MODIFIED) or Passes Through (PASSTHROUGH) -> Eve Forwards (FORWARDED -> RECEIVED) -> Bob Verifies.
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime
import uuid
import secrets

from ..models.transmission import TransmissionPackageModel
from ..models.session import SessionModel
from ..models.declaration import PublicDeclarationModel
from ..models.hash_record import HashRecordModel
from ..models.measurement import MeasurementModel
from ..models.quantum_run import QuantumRunModel
from ..models.audit_event import AuditEventModel
from ..models.attack_event import AttackEventModel
from ..core.datetime_utils import utc_now
from .file_service import FileService
from .attack_simulation_service import AttackSimulationService


class TransmissionService:

    @staticmethod
    def generate_tracking_number() -> str:
        date_str = utc_now().strftime("%Y%m%d")
        rand_suffix = secrets.token_hex(4).upper()
        return f"QDS-PKG-{date_str}-{rand_suffix}"

    @classmethod
    def dispatch_package(
        cls,
        db: Session,
        session_id: str,
        sender_id: str,
        recipient_id: str
    ) -> TransmissionPackageModel:
        """Alice seals and dispatches a signed QDS package into the transmission channel."""
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            raise ValueError(f"Session '{session_id}' not found")

        hash_record = db.query(HashRecordModel).filter(HashRecordModel.session_id == session_id).first()
        if not hash_record:
            raise ValueError("Message hash record not found. Sign session before dispatching.")

        declaration = db.query(PublicDeclarationModel).filter(PublicDeclarationModel.session_id == session_id).first()
        if not declaration:
            raise ValueError("Public declaration not found. Sign session before dispatching.")

        quantum_run = db.query(QuantumRunModel).filter(QuantumRunModel.session_id == session_id).order_by(QuantumRunModel.created_at.desc()).first()

        filename = hash_record.file_name or "directive_payload.txt"
        file_size = hash_record.file_size_bytes or hash_record.message_bytes_len
        mime_type = hash_record.file_mime_type or "text/plain"

        # Check if already dispatched
        existing_pkg = db.query(TransmissionPackageModel).filter(
            TransmissionPackageModel.session_id == session_id
        ).first()
        if existing_pkg:
            return existing_pkg

        tracking_no = cls.generate_tracking_number()

        # Build portable .qds.json signature package
        qds_manifest = FileService.build_qds_json_manifest(
            package_tracking_no=tracking_no,
            session_id=session_id,
            filename=filename,
            file_size_bytes=file_size,
            mime_type=mime_type,
            sha512_digest=hash_record.sha512_digest,
            signer_id=sender_id,
            verifier_id=recipient_id,
            declaration_id=declaration.id,
            signature_token=declaration.signature_token,
            declaration_payload_hash=declaration.declaration_payload_hash,
            quantum_run_id=quantum_run.id if quantum_run else "simulated_quantum_run",
            teleportation_count=quantum_run.teleportation_count if quantum_run else 4096,
            declared_at=declaration.declared_at
        )

        pkg = TransmissionPackageModel(
            package_tracking_no=tracking_no,
            session_id=session_id,
            sender_id=sender_id,
            recipient_id=recipient_id,
            status="IN_TRANSIT",
            message_payload=hash_record.raw_message,
            committed_digest=hash_record.sha512_digest,
            declaration_id=declaration.id,
            signature_token=declaration.signature_token,
            declaration_payload_hash=declaration.declaration_payload_hash,
            quantum_run_id=quantum_run.id if quantum_run else None,
            file_name=filename,
            file_mime_type=mime_type,
            file_size_bytes=file_size,
            storage_path=hash_record.storage_path,
            qds_manifest_json=qds_manifest,
            classical_channel_status="NORMAL",
            quantum_channel_status="COHERENT",
            tampered_channel=None,
            active_attack_vector=None
        )
        db.add(pkg)

        session.status = "IN_TRANSIT"

        # Record audit event
        audit = AuditEventModel(
            session_id=session_id,
            actor=sender_id,
            event_type="ALICE_PACKAGE_DISPATCHED",
            details={
                "tracking_no": pkg.package_tracking_no,
                "recipient_id": recipient_id,
                "file_name": filename,
                "committed_digest": hash_record.sha512_digest,
                "token_prefix": declaration.signature_token[:16] + "..."
            }
        )
        db.add(audit)
        db.commit()
        db.refresh(pkg)
        return pkg

    @classmethod
    def get_interceptable_transmissions(cls, db: Session) -> List[TransmissionPackageModel]:
        """Eve views transmissions currently in transit, intercepted, or completed."""
        return db.query(TransmissionPackageModel).filter(
            TransmissionPackageModel.status.in_([
                "IN_TRANSIT", "INTERCEPTED", "MODIFIED", "PASSTHROUGH",
                "RECEIVED", "FORWARDED", "VERIFIED", "REJECTED"
            ])
        ).order_by(TransmissionPackageModel.created_at.desc()).all()

    @classmethod
    def intercept_transmission(
        cls,
        db: Session,
        transmission_id: str,
        actor: str = "Eve_Attacker"
    ) -> TransmissionPackageModel:
        """Eve intercepts an in-flight transmission."""
        try:
            pkg = db.query(TransmissionPackageModel).filter(
                TransmissionPackageModel.id == transmission_id
            ).with_for_update().first()
        except Exception:
            pkg = db.query(TransmissionPackageModel).filter(
                TransmissionPackageModel.id == transmission_id
            ).first()

        if not pkg:
            raise ValueError(f"Transmission package '{transmission_id}' not found")

        if pkg.status != "IN_TRANSIT":
            raise ValueError(
                f"Invalid state transition: Cannot intercept package in status '{pkg.status}'. "
                f"Package must be 'IN_TRANSIT' and not already intercepted."
            )

        pkg.status = "INTERCEPTED"
        pkg.intercepted_by = actor
        pkg.intercepted_at = utc_now()

        session = db.query(SessionModel).filter(SessionModel.id == pkg.session_id).first()
        if session:
            session.status = "INTERCEPTED"

        audit = AuditEventModel(
            session_id=pkg.session_id,
            actor=actor,
            event_type="EVE_PACKAGE_INTERCEPTED",
            details={
                "tracking_no": pkg.package_tracking_no,
                "sender": pkg.sender_id,
                "recipient": pkg.recipient_id
            }
        )
        db.add(audit)
        db.commit()
        db.refresh(pkg)
        return pkg

    @classmethod
    def mutate_transmission(
        cls,
        db: Session,
        transmission_id: str,
        attack_type: str,
        mutation_params: Dict[str, Any],
        actor: str = "Eve_Attacker"
    ) -> TransmissionPackageModel:
        """Eve injects a controlled cyber/quantum attack mutation into the intercepted package."""
        try:
            pkg = db.query(TransmissionPackageModel).filter(
                TransmissionPackageModel.id == transmission_id
            ).with_for_update().first()
        except Exception:
            pkg = db.query(TransmissionPackageModel).filter(
                TransmissionPackageModel.id == transmission_id
            ).first()

        if not pkg:
            raise ValueError(f"Transmission package '{transmission_id}' not found")

        if pkg.status in ["MODIFIED", "ATTACKED"] or pkg.is_tampered:
            raise ValueError(
                f"An attack has already been executed on this transmission package (#{pkg.package_tracking_no}). "
                f"Only one attack is permitted per transmission."
            )

        if pkg.status in ["RECEIVED", "FORWARDED", "VERIFIED", "REJECTED"]:
            raise ValueError(
                f"Transmission package has already been forwarded to Bob (status: '{pkg.status}'). "
                f"Mutations cannot be applied to forwarded or delivered transmissions."
            )

        if pkg.status != "INTERCEPTED":
            raise ValueError(
                f"Cannot mutate package in status '{pkg.status}'. "
                f"Package must be intercepted from transit first."
            )

        AttackSimulationService.execute_mutation(
            db=db,
            transmission_id=transmission_id,
            attack_type=attack_type,
            params=mutation_params,
            actor=actor
        )
        pkg = db.query(TransmissionPackageModel).filter(TransmissionPackageModel.id == transmission_id).first()
        pkg.status = "MODIFIED"
        pkg.is_tampered = True
        pkg.attack_type = attack_type
        pkg.active_attack_vector = attack_type
        db.commit()
        db.refresh(pkg)
        return pkg

    @classmethod
    def passthrough_transmission(
        cls,
        db: Session,
        transmission_id: str,
        actor: str = "Eve_Attacker"
    ) -> TransmissionPackageModel:
        """Eve elects not to tamper with the transmission, forwarding it untouched directly to Bob."""
        try:
            pkg = db.query(TransmissionPackageModel).filter(
                TransmissionPackageModel.id == transmission_id
            ).with_for_update().first()
        except Exception:
            pkg = db.query(TransmissionPackageModel).filter(
                TransmissionPackageModel.id == transmission_id
            ).first()

        if not pkg:
            raise ValueError(f"Transmission package '{transmission_id}' not found")

        if pkg.status in ["MODIFIED", "ATTACKED"] or pkg.is_tampered:
            raise ValueError(
                f"Cannot passthrough an already attacked transmission (#{pkg.package_tracking_no})."
            )

        if pkg.status in ["RECEIVED", "FORWARDED", "VERIFIED", "REJECTED"]:
            raise ValueError(
                f"Transmission package has already been forwarded (status: '{pkg.status}')."
            )

        if pkg.status != "INTERCEPTED":
            raise ValueError(
                f"Cannot passthrough package in status '{pkg.status}'. Package must be intercepted first."
            )

        # Terminal passthrough: package arrives in Bob's inbox untouched
        pkg.status = "RECEIVED"
        pkg.is_tampered = False
        pkg.attack_type = None
        pkg.active_attack_vector = None
        pkg.tamper_details = None
        pkg.classical_channel_status = "NORMAL"
        pkg.quantum_channel_status = "COHERENT"
        pkg.tampered_channel = None
        pkg.forwarded_at = utc_now()
        pkg.delivered_at = utc_now()

        session = db.query(SessionModel).filter(SessionModel.id == pkg.session_id).first()
        if session:
            session.status = "FORWARDED"

        audit = AuditEventModel(
            session_id=pkg.session_id,
            actor=actor,
            event_type="EVE_PACKAGE_PASSED_THROUGH",
            details={"tracking_no": pkg.package_tracking_no, "action": "UNTOUCHED_FORWARD"}
        )
        db.add(audit)
        db.commit()
        db.refresh(pkg)
        return pkg

    @classmethod
    def get_channel_telemetry(
        cls,
        db: Session,
        transmission_id: str
    ) -> Dict[str, Any]:
        """Provides Eve's sniffer with detailed split-screen Classical and Quantum channel telemetry."""
        pkg = db.query(TransmissionPackageModel).filter(TransmissionPackageModel.id == transmission_id).first()
        if not pkg:
            raise ValueError(f"Transmission package '{transmission_id}' not found")

        # Classical channel stream
        classical_stream = {
            "channel_status": pkg.classical_channel_status,
            "file_name": pkg.file_name or "directive_payload.txt",
            "file_size_bytes": pkg.file_size_bytes or len(pkg.message_payload.encode()),
            "file_mime_type": pkg.file_mime_type or "text/plain",
            "committed_digest": pkg.committed_digest,
            "signature_token": pkg.signature_token,
            "declaration_payload_hash": pkg.declaration_payload_hash,
            "sender_id": pkg.sender_id,
            "recipient_id": pkg.recipient_id,
            "transport_security": "Application-Level Classical Transmission"
        }

        # Quantum channel stream
        sample_ops = []
        basis_counts = {"Z": 0, "X": 0}
        total_ops = 0
        run_id = pkg.quantum_run_id
        if run_id:
            measurements = db.query(MeasurementModel).filter(
                MeasurementModel.quantum_run_id == run_id
            ).limit(20).all()
            for m in measurements:
                basis = "X" if abs(m.prep_theta - 1.570796) < 0.1 else "Z"
                basis_counts[basis] = basis_counts.get(basis, 0) + 1
                sample_ops.append({
                    "op_index": m.operation_index,
                    "theta": round(m.prep_theta, 4),
                    "phi": round(m.prep_phi, 4),
                    "expected_bit": m.expected_bit,
                    "observed_bit": m.bob_observed_bit,
                    "is_match": m.is_match
                })
            total_ops = db.query(MeasurementModel).filter(MeasurementModel.quantum_run_id == run_id).count()

        quantum_stream = {
            "channel_status": pkg.quantum_channel_status,
            "quantum_run_id": run_id,
            "total_teleportation_operations": total_ops or 4096,
            "simulated_qubits_total": (total_ops or 4096) * 3,
            "sample_teleportation_operations": sample_ops,
            "network_parameters": {
                "fiber_distance_km": 25.0,
                "attenuation_db_per_km": 0.20,
                "propagation_delay_us": 122.5,
                "entanglement_fidelity": 0.99 if pkg.quantum_channel_status == "COHERENT" else 0.72
            }
        }

        return {
            "package_tracking_no": pkg.package_tracking_no,
            "session_id": pkg.session_id,
            "status": pkg.status,
            "is_tampered": pkg.is_tampered,
            "attack_type": pkg.attack_type,
            "tampered_channel": pkg.tampered_channel,
            "classical_channel": classical_stream,
            "quantum_channel": quantum_stream
        }

    @classmethod
    def forward_transmission(
        cls,
        db: Session,
        transmission_id: str,
        actor: str = "Eve_Attacker"
    ) -> TransmissionPackageModel:
        """Eve dispatches the package onwards to Bob's inbox."""
        try:
            pkg = db.query(TransmissionPackageModel).filter(
                TransmissionPackageModel.id == transmission_id
            ).with_for_update().first()
        except Exception:
            pkg = db.query(TransmissionPackageModel).filter(
                TransmissionPackageModel.id == transmission_id
            ).first()

        if not pkg:
            raise ValueError(f"Transmission package '{transmission_id}' not found")

        if pkg.status in ["RECEIVED", "FORWARDED", "VERIFIED", "REJECTED"]:
            raise ValueError(
                f"Transmission package has already been forwarded to Bob (status: '{pkg.status}'). "
                f"Cannot forward multiple times."
            )

        if pkg.status not in ["MODIFIED", "INTERCEPTED"]:
            raise ValueError(
                f"Cannot forward package in status '{pkg.status}'. "
                f"Package must be intercepted or modified before forwarding."
            )

        pkg.status = "RECEIVED"  # Arrives in Bob's inbox
        pkg.forwarded_at = utc_now()
        pkg.delivered_at = utc_now()

        session = db.query(SessionModel).filter(SessionModel.id == pkg.session_id).first()
        if session:
            session.status = "FORWARDED"

        audit = AuditEventModel(
            session_id=pkg.session_id,
            actor=actor,
            event_type="EVE_PACKAGE_FORWARDED",
            details={
                "tracking_no": pkg.package_tracking_no,
                "recipient_id": pkg.recipient_id,
                "tampered": pkg.is_tampered
            }
        )
        db.add(audit)
        db.commit()
        db.refresh(pkg)
        return pkg

    @classmethod
    def get_bob_inbox(
        cls,
        db: Session,
        recipient_id: Optional[str] = None
    ) -> List[TransmissionPackageModel]:
        """Lists packages that have reached Bob's inbox ready for verification."""
        query = db.query(TransmissionPackageModel).filter(
            TransmissionPackageModel.status.in_(["RECEIVED", "VERIFIED", "REJECTED"])
        )
        if recipient_id:
            query = query.filter(TransmissionPackageModel.recipient_id == recipient_id)
        return query.order_by(
            TransmissionPackageModel.delivered_at.desc(),
            TransmissionPackageModel.created_at.desc()
        ).all()
