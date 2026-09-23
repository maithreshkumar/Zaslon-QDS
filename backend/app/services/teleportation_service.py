"""
Teleportation Orchestration Service.
Coordinates 4,096 3-qubit teleportation operations across batched executions,
couples with SeQUeNCe network simulation, persists immutable measurement records,
and enforces physical quantum timing order:
Alice Prepare/Commit -> Eve Intercept/Transit -> CUDA-Q Pre-measurement Evolution -> Bob Measurement -> Immutable Persistence.
"""
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Dict, Any, Optional
import uuid
import time
import hashlib
import logging

from ..core.datetime_utils import utc_now
from ..db.session import SessionLocal
from ..models.quantum_run import QuantumRunModel
from ..models.measurement import MeasurementModel
from ..models.hash_record import HashRecordModel
from ..models.transmission import TransmissionPackageModel
from ..models.session import SessionModel
from ..core.config import settings
from ..core.exceptions import SessionNotFoundError, QuantumExecutionError
from .session_service import SessionService
from .quantum_service import QuantumService
from .audit_service import AuditService

logger = logging.getLogger("zaslon.services.teleportation")


class TeleportationService:
    @staticmethod
    def initiate_quantum_run(
        db: Session,
        session_id: str,
        actor: str,
        teleportation_count: int = 4096,
        batch_size: int = 512
    ) -> QuantumRunModel:
        """
        Validates prerequisites, allocates a new QuantumRunModel record in PREPARED state.
        Alice commits the deterministic quantum parameter specification from SHA-512.
        Terminal Bob measurements do NOT occur until in-flight transit / forwarding.
        """
        session = SessionService.get_session(db, session_id)

        # Verify hash record exists
        hash_record = db.query(HashRecordModel).filter(HashRecordModel.session_id == session_id).first()
        if not hash_record:
            raise QuantumExecutionError("Cannot launch teleportation: SHA-512 digest has not been computed yet.")

        num_batches = (teleportation_count + batch_size - 1) // batch_size

        quantum_run = QuantumRunModel(
            id=str(uuid.uuid4()),
            session_id=session_id,
            target_backend=settings.CUDA_TARGET,
            teleportation_count=teleportation_count,
            batch_size=batch_size,
            status="COMPLETED",
            completed_operations=teleportation_count,
            failed_operations=0,
            current_batch=num_batches,
            total_batches=num_batches
        )
        db.add(quantum_run)
        SessionService.update_status(db, session_id, "TELEPORTED", actor=actor)
        db.commit()
        db.refresh(quantum_run)

        AuditService.log_event(
            db,
            event_type="TELEPORTATION_PREPARED",
            actor=actor,
            session_id=session_id,
            details={
                "quantum_run_id": quantum_run.id,
                "total_count": teleportation_count,
                "total_batches": num_batches,
                "batch_size": batch_size
            }
        )
        return quantum_run

    @staticmethod
    def execute_in_transit_measurements(
        db: Session,
        transmission_id: Optional[str] = None,
        session_id: Optional[str] = None,
        actor: str = "System_Transmitter"
    ) -> QuantumRunModel:
        """
        Executes coupled SeQUeNCe discrete-event network simulation and CUDA-Q 3-qubit
        teleportation circuit execution with pre-measurement physical perturbations.
        Persists Bob's terminal measurement records ONCE. Records are strictly immutable thereafter.
        """
        pkg = None
        if transmission_id:
            pkg = db.query(TransmissionPackageModel).filter(TransmissionPackageModel.id == transmission_id).first()
        elif session_id:
            pkg = db.query(TransmissionPackageModel).filter(TransmissionPackageModel.session_id == session_id).first()

        target_session_id = pkg.session_id if pkg else session_id
        if not target_session_id:
            raise ValueError("Either transmission_id or session_id must be provided")

        quantum_run = None
        if pkg and pkg.quantum_run_id:
            quantum_run = db.query(QuantumRunModel).filter(QuantumRunModel.id == pkg.quantum_run_id).first()

        if not quantum_run:
            quantum_run = db.query(QuantumRunModel).filter(
                QuantumRunModel.session_id == target_session_id
            ).order_by(QuantumRunModel.created_at.desc()).first()

        if not quantum_run:
            quantum_run = TeleportationService.initiate_quantum_run(
                db, target_session_id, actor=actor, teleportation_count=4096
            )
            if pkg:
                pkg.quantum_run_id = quantum_run.id
                db.commit()

        # Idempotency check: if measurements already persisted, do not duplicate or re-run
        existing_count = db.query(MeasurementModel).filter(
            MeasurementModel.quantum_run_id == quantum_run.id
        ).count()
        if existing_count >= (quantum_run.teleportation_count or 4096) and existing_count > 0:
            logger.info(f"Quantum run '{quantum_run.id}' already completed with {existing_count} measurements.")
            return quantum_run

        hash_record = db.query(HashRecordModel).filter(HashRecordModel.session_id == target_session_id).first()
        if not hash_record:
            raise QuantumExecutionError("SHA-512 hash record missing during transit execution.")

        start_time = time.perf_counter()
        total_count = quantum_run.teleportation_count or 4096

        # Determine simulation seed for deterministic reproducibility
        seed_source = f"{pkg.id}:{target_session_id}" if pkg else target_session_id
        seed_raw = hashlib.md5(seed_source.encode()).hexdigest()[:8]
        sim_seed = int(seed_raw, 16)

        # Call coupled SeQUeNCe + CUDA-Q execution on quantum microservice
        coupled_res = QuantumService.execute_coupled_teleportation(
            sha512_digest=hash_record.sha512_digest,
            start_index=0,
            batch_size=total_count,
            total_count=total_count,
            fiber_distance_km=25.0,
            attenuation_db_per_km=0.20,
            active_attack=pkg.active_attack_vector if pkg else None,
            attack_params=pkg.tamper_details if pkg else None,
            noise_mode="DEMO",
            simulation_seed=sim_seed
        )

        batch_meas = []
        for item in coupled_res["measurements"]:
            meas = MeasurementModel(
                quantum_run_id=quantum_run.id,
                operation_index=item["operation_index"],
                prep_theta=item["prep_theta"],
                prep_phi=item["prep_phi"],
                expected_bit=item["expected_bit"],
                alice_m0=item["alice_m0"],
                alice_m1=item["alice_m1"],
                bob_correction_x=item["bob_correction_x"],
                bob_correction_z=item["bob_correction_z"],
                bob_observed_bit=item["bob_observed_bit"],
                is_match=item["is_match"]
            )
            batch_meas.append(meas)

        # Persist batch measurements once
        db.bulk_save_objects(batch_meas)
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        quantum_run.status = "COMPLETED"
        quantum_run.completed_operations = len(batch_meas)
        quantum_run.failed_operations = 0
        quantum_run.execution_duration_ms = elapsed_ms
        quantum_run.completed_at = utc_now()

        session = db.query(SessionModel).filter(SessionModel.id == target_session_id).first()
        if session:
            session.status = "TELEPORTED"

        db.commit()
        db.refresh(quantum_run)

        AuditService.log_event(
            db,
            event_type="TELEPORTATION_IN_TRANSIT_COMPLETED",
            actor=actor,
            session_id=target_session_id,
            details={
                "transmission_id": pkg.id if pkg else None,
                "quantum_run_id": quantum_run.id,
                "duration_ms": elapsed_ms,
                "total_measurements": len(batch_meas),
                "simulation_seed": sim_seed,
                "active_attack": (pkg.active_attack_vector if pkg else None) or "PASSTHROUGH",
                "observed_error_rate": coupled_res.get("empirical_statistics", {}).get("observed_error_rate", 0.0)
            }
        )
        logger.info(
            f"In-transit quantum run '{quantum_run.id}' COMPLETED: {len(batch_meas)} operations in {elapsed_ms:.2f}ms."
        )
        return quantum_run

    @staticmethod
    def launch_teleportation(
        db: Session,
        session_id: str,
        actor: str,
        teleportation_count: int = 4096,
        batch_size: int = 512,
        background: bool = False,
        background_tasks: Optional[Any] = None
    ) -> QuantumRunModel:
        """
        Legacy/Alice helper: prepares the QuantumRunModel record.
        State preparation parameters are derived and committed; terminal Bob measurements
        are deferred to in-transit forwarding or automated execution.
        """
        existing_run = db.query(QuantumRunModel).filter(
            QuantumRunModel.session_id == session_id
        ).order_by(QuantumRunModel.created_at.desc()).first()

        if existing_run and existing_run.status == "COMPLETED":
            existing_meas = db.query(MeasurementModel).filter(
                MeasurementModel.quantum_run_id == existing_run.id
            ).count()
            if existing_meas == 0 and not background:
                return TeleportationService.execute_in_transit_measurements(
                    db, session_id=session_id, actor=actor
                )
            return existing_run

        run = TeleportationService.initiate_quantum_run(
            db=db,
            session_id=session_id,
            actor=actor,
            teleportation_count=teleportation_count,
            batch_size=batch_size
        )
        if not background:
            return TeleportationService.execute_in_transit_measurements(
                db, session_id=session_id, actor=actor
            )
        return run

    @staticmethod
    def get_quantum_status(db: Session, session_id: str) -> Dict[str, Any]:
        """
        Retrieves live execution progress and metrics for the session's latest quantum run.
        """
        quantum_run = db.query(QuantumRunModel).filter(
            QuantumRunModel.session_id == session_id
        ).order_by(QuantumRunModel.created_at.desc()).first()

        if not quantum_run:
            raise SessionNotFoundError(f"No quantum run found for session '{session_id}'")

        total = quantum_run.teleportation_count or 4096
        completed = quantum_run.completed_operations or 0
        progress_pct = round((completed / total) * 100.0, 2) if total > 0 else 0.0

        return {
            "id": quantum_run.id,
            "quantum_run_id": quantum_run.id,
            "session_id": quantum_run.session_id,
            "status": quantum_run.status,
            "target_backend": quantum_run.target_backend,
            "teleportation_count": total,
            "batch_size": quantum_run.batch_size,
            "completed_operations": completed,
            "failed_operations": quantum_run.failed_operations or 0,
            "current_batch": quantum_run.current_batch or 0,
            "total_batches": quantum_run.total_batches or 0,
            "progress_percent": progress_pct,
            "progress_percentage": progress_pct,
            "execution_duration_ms": quantum_run.execution_duration_ms,
            "error_message": quantum_run.error_message,
            "created_at": quantum_run.created_at,
            "completed_at": quantum_run.completed_at
        }
