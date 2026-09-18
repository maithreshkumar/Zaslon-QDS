"""
Teleportation Orchestration Service.
Coordinates 4,096 3-qubit teleportation operations across batched executions,
persists measurement records, and tracks granular execution metrics and batch progress.
"""
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Dict, Any, Optional
import uuid
import time
import logging

from ..core.datetime_utils import utc_now

from ..db.session import SessionLocal
from ..models.quantum_run import QuantumRunModel
from ..models.measurement import MeasurementModel
from ..models.hash_record import HashRecordModel
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
        Validates prerequisites, allocates a new QuantumRunModel record in PENDING state,
        and transitions the session to TELEPORTING.
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
            status="PENDING",
            completed_operations=0,
            failed_operations=0,
            current_batch=0,
            total_batches=num_batches
        )
        db.add(quantum_run)
        SessionService.update_status(db, session_id, "TELEPORTING", actor=actor)
        db.commit()
        db.refresh(quantum_run)

        AuditService.log_event(
            db,
            event_type="TELEPORTATION_INITIALIZED",
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
    def execute_quantum_pipeline(run_id: str, actor: str, db_session: Optional[Session] = None) -> None:
        """
        Executes the batch pipeline for a given QuantumRun.
        If db_session is provided (e.g. synchronous execution or testing), it uses it directly.
        Otherwise creates a new session from SessionLocal for background execution.
        """
        db = db_session if db_session is not None else SessionLocal()
        close_on_finish = (db_session is None)
        try:
            quantum_run = db.query(QuantumRunModel).filter(QuantumRunModel.id == run_id).first()
            if not quantum_run:
                logger.error(f"Quantum run '{run_id}' not found for execution.")
                return

            session_id = quantum_run.session_id
            hash_record = db.query(HashRecordModel).filter(HashRecordModel.session_id == session_id).first()
            if not hash_record:
                quantum_run.status = "FAILED"
                quantum_run.error_message = "SHA-512 hash record missing during execution."
                db.commit()
                return

            quantum_run.status = "RUNNING"
            db.commit()

            start_time = time.perf_counter()
            total_count = quantum_run.teleportation_count
            batch_size = quantum_run.batch_size
            num_batches = quantum_run.total_batches or ((total_count + batch_size - 1) // batch_size)

            for b in range(num_batches):
                start_idx = b * batch_size
                current_batch_size = min(batch_size, total_count - start_idx)

                # Update current batch progress
                quantum_run.current_batch = b + 1
                db.commit()

                batch_res = QuantumService.execute_teleportation_batch(
                    sha512_digest=hash_record.sha512_digest,
                    start_index=start_idx,
                    batch_size=current_batch_size,
                    total_count=total_count
                )

                batch_meas = []
                for item in batch_res["measurements"]:
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

                # Persist batch measurements and update completed count
                db.bulk_save_objects(batch_meas)
                quantum_run.completed_operations = start_idx + len(batch_meas)
                db.commit()

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            quantum_run.status = "COMPLETED"
            quantum_run.execution_duration_ms = elapsed_ms
            quantum_run.completed_at = utc_now()

            SessionService.update_status(db, session_id, "TELEPORTED", actor=actor)
            db.commit()

            AuditService.log_event(
                db,
                event_type="TELEPORTATION_COMPLETED",
                actor=actor,
                session_id=session_id,
                details={
                    "quantum_run_id": quantum_run.id,
                    "duration_ms": elapsed_ms,
                    "total_measurements": quantum_run.completed_operations
                }
            )
            logger.info(
                f"Quantum run '{run_id}' COMPLETED: {quantum_run.completed_operations} operations in {elapsed_ms:.2f}ms."
            )

        except Exception as e:
            logger.exception(f"Quantum run '{run_id}' FAILED: {str(e)}")
            try:
                quantum_run = db.query(QuantumRunModel).filter(QuantumRunModel.id == run_id).first()
                if quantum_run:
                    quantum_run.status = "FAILED"
                    quantum_run.error_message = str(e)
                    quantum_run.failed_operations = quantum_run.teleportation_count - (quantum_run.completed_operations or 0)
                    SessionService.update_status(db, quantum_run.session_id, "FAILED", actor=actor)
                    db.commit()

                    AuditService.log_event(
                        db,
                        event_type="TELEPORTATION_FAILED",
                        actor=actor,
                        session_id=quantum_run.session_id,
                        details={"error": str(e), "run_id": run_id}
                    )
            except Exception as inner_e:
                logger.error(f"Failed to persist failure state for run '{run_id}': {inner_e}")
        finally:
            if close_on_finish:
                db.close()

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
        Coordinates either synchronous or asynchronous execution of the teleportation run.
        """
        quantum_run = TeleportationService.initiate_quantum_run(
            db=db,
            session_id=session_id,
            actor=actor,
            teleportation_count=teleportation_count,
            batch_size=batch_size
        )

        if background and background_tasks:
            background_tasks.add_task(TeleportationService.execute_quantum_pipeline, quantum_run.id, actor)
            return quantum_run

        # Otherwise execute synchronously using the caller's db session
        TeleportationService.execute_quantum_pipeline(quantum_run.id, actor, db_session=db)
        db.refresh(quantum_run)
        return quantum_run

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

