from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import time
import uuid
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select, update

from .config import settings
from .db import QuantumJob, QuantumWorkerStatus, session_scope


TERMINAL_JOB_STATES = frozenset({"SUCCEEDED", "FAILED"})


class JobQueueError(RuntimeError):
    pass


class JobTimedOut(JobQueueError):
    def __init__(self, job_id: str):
        super().__init__(f"Quantum job {job_id} is still running; retrieve it by job id.")
        self.job_id = job_id


class JobFailed(JobQueueError):
    def __init__(self, job_id: str, code: str, message: str):
        super().__init__(message)
        self.job_id = job_id
        self.code = code


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _cipher() -> Fernet:
    if not settings.job_payload_key:
        raise RuntimeError(
            "ZASLON_JOB_PAYLOAD_KEY is required in worker_queue mode; generate a Fernet key."
        )
    try:
        return Fernet(settings.job_payload_key.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise RuntimeError(
            "ZASLON_JOB_PAYLOAD_KEY must be one URL-safe base64 Fernet key."
        ) from exc


def validate_job_queue_configuration() -> None:
    if settings.execution_mode not in {"direct", "worker_queue"}:
        raise RuntimeError("ZASLON_EXECUTION_MODE must be direct or worker_queue")
    if settings.execution_mode == "worker_queue":
        _cipher()
    if settings.job_wait_timeout_seconds <= 0 or settings.job_poll_interval_seconds <= 0:
        raise RuntimeError("Quantum job wait and poll intervals must be positive")
    if settings.worker_max_attempts < 1:
        raise RuntimeError("ZASLON_WORKER_MAX_ATTEMPTS must be at least 1")


def submit_job(*, role: str, job_type: str, payload: dict[str, Any]) -> str:
    job_id = f"JOB-{uuid.uuid4().hex.upper()}"
    serialized = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    encrypted = _cipher().encrypt(serialized).decode("ascii")
    with session_scope() as db:
        db.add(
            QuantumJob(
                id=job_id,
                role=role,
                job_type=job_type,
                status="QUEUED",
                payload_ciphertext=encrypted,
                attempts=0,
                created_at=_utcnow(),
            )
        )
    return job_id


def job_status(job_id: str, *, role: str) -> dict[str, Any]:
    with session_scope() as db:
        row = db.get(QuantumJob, job_id)
        if row is None or row.role != role:
            raise LookupError("Quantum job not found")
        result = json.loads(row.result_json) if row.result_json else None
        return {
            "job_id": row.id,
            "job_type": row.job_type,
            "status": row.status,
            "attempts": row.attempts,
            "created_at": row.created_at.isoformat(),
            "started_at": row.started_at.isoformat() if row.started_at else None,
            "completed_at": row.completed_at.isoformat() if row.completed_at else None,
            "error_code": row.error_code,
            "error_message": row.error_message,
            "result": result,
            "encrypted_payload_retained": row.payload_ciphertext is not None,
        }


def wait_for_job(job_id: str, *, role: str) -> dict[str, Any]:
    deadline = time.monotonic() + settings.job_wait_timeout_seconds
    while time.monotonic() < deadline:
        status = job_status(job_id, role=role)
        if status["status"] == "SUCCEEDED":
            assert isinstance(status["result"], dict)
            result = dict(status["result"])
            result["worker_job"] = {
                "job_id": job_id,
                "status": "SUCCEEDED",
                "attempts": status["attempts"],
            }
            return result
        if status["status"] == "FAILED":
            raise JobFailed(
                job_id,
                status["error_code"] or "QUANTUM_JOB_FAILED",
                status["error_message"] or "The quantum worker failed this job.",
            )
        time.sleep(settings.job_poll_interval_seconds)
    raise JobTimedOut(job_id)


def submit_and_wait(*, role: str, job_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    return wait_for_job(submit_job(role=role, job_type=job_type, payload=payload), role=role)


def recover_stale_jobs() -> int:
    stale_before = _utcnow() - timedelta(seconds=settings.worker_stale_seconds)
    recovered = 0
    with session_scope() as db:
        rows = list(
            db.scalars(
                select(QuantumJob).where(
                    QuantumJob.status == "RUNNING",
                    QuantumJob.heartbeat_at < stale_before,
                )
            )
        )
        for row in rows:
            if row.attempts >= settings.worker_max_attempts:
                row.status = "FAILED"
                row.error_code = "STALE_JOB_MAX_ATTEMPTS"
                row.error_message = "Worker stopped before completing the job."
                row.payload_ciphertext = None
                row.completed_at = _utcnow()
            else:
                row.status = "QUEUED"
                row.claimed_by = None
                row.started_at = None
                row.heartbeat_at = None
            recovered += 1
    return recovered


def claim_next_job(*, worker_id: str) -> dict[str, Any] | None:
    with session_scope() as db:
        statement = (
            select(QuantumJob)
            .where(QuantumJob.status == "QUEUED")
            .order_by(QuantumJob.created_at.asc())
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        row = db.scalar(statement)
        if row is None:
            return None
        now = _utcnow()
        row.status = "RUNNING"
        row.claimed_by = worker_id
        row.attempts += 1
        row.started_at = now
        row.heartbeat_at = now
        encrypted = row.payload_ciphertext
        identity = {"job_id": row.id, "role": row.role, "job_type": row.job_type}
    if encrypted is None:
        raise JobQueueError(f"Quantum job {identity['job_id']} has no encrypted payload")
    try:
        payload = json.loads(_cipher().decrypt(encrypted.encode("ascii")).decode("utf-8"))
    except (InvalidToken, UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail_job(
            identity["job_id"],
            worker_id=worker_id,
            code="JOB_PAYLOAD_AUTHENTICATION_FAILED",
            message="Encrypted quantum job payload could not be authenticated.",
        )
        return None
    return {**identity, "payload": payload}


def heartbeat_job(job_id: str, *, worker_id: str) -> None:
    with session_scope() as db:
        db.execute(
            update(QuantumJob)
            .where(
                QuantumJob.id == job_id,
                QuantumJob.status == "RUNNING",
                QuantumJob.claimed_by == worker_id,
            )
            .values(heartbeat_at=_utcnow())
        )


def complete_job(job_id: str, *, worker_id: str, result: dict[str, Any]) -> None:
    encoded = json.dumps(result, separators=(",", ":"), ensure_ascii=False)
    with session_scope() as db:
        changed = db.execute(
            update(QuantumJob)
            .where(
                QuantumJob.id == job_id,
                QuantumJob.status == "RUNNING",
                QuantumJob.claimed_by == worker_id,
            )
            .values(
                status="SUCCEEDED",
                result_json=encoded,
                payload_ciphertext=None,
                completed_at=_utcnow(),
                heartbeat_at=_utcnow(),
                error_code=None,
                error_message=None,
            )
        )
        if changed.rowcount != 1:
            raise JobQueueError(f"Quantum job {job_id} was not owned by {worker_id}")


def fail_job(job_id: str, *, worker_id: str, code: str, message: str) -> None:
    safe_message = " ".join(str(message).split())[:512]
    with session_scope() as db:
        db.execute(
            update(QuantumJob)
            .where(
                QuantumJob.id == job_id,
                QuantumJob.status == "RUNNING",
                QuantumJob.claimed_by == worker_id,
            )
            .values(
                status="FAILED",
                payload_ciphertext=None,
                completed_at=_utcnow(),
                heartbeat_at=_utcnow(),
                error_code=code[:64],
                error_message=safe_message or "Quantum worker failed the job.",
            )
        )


def update_worker_status(status: dict[str, Any]) -> None:
    now = _utcnow()
    worker_id = str(status["worker_id"])
    values = {
        "process_status": status["worker"],
        "cudaq_status": status["cudaq"],
        "gpu_status": status["gpu"],
        "engine": status.get("engine", "CUDA-Q"),
        "requested_target": status.get("requested_target", "nvidia"),
        "execution_target": status.get("execution_target"),
        "engine_version": status.get("cudaq_version"),
        "gpu_name": status.get("gpu_name"),
        "fallback_used": int(bool(status.get("fallback_used"))),
        "fallback_reason": status.get("fallback_reason"),
        "health_result_json": json.dumps(status, separators=(",", ":")),
        "updated_at": now,
    }
    with session_scope() as db:
        row = db.get(QuantumWorkerStatus, worker_id)
        if row is None:
            db.add(QuantumWorkerStatus(worker_id=worker_id, **values))
        else:
            for name, value in values.items():
                setattr(row, name, value)


def worker_readiness() -> dict[str, Any]:
    try:
        with session_scope() as db:
            row = db.scalar(
                select(QuantumWorkerStatus)
                .order_by(QuantumWorkerStatus.updated_at.desc())
                .limit(1)
            )
    except Exception:
        # Health endpoints must fail closed and remain machine-readable during a
        # transient database outage; they must not manufacture a healthy worker.
        return {
            "engine": "CUDA-Q",
            "available": False,
            "worker": "UNKNOWN",
            "cudaq": "UNKNOWN",
            "gpu": "UNKNOWN",
            "error_code": "QUANTUM_WORKER_STATUS_UNAVAILABLE",
        }
    if row is None:
        return {
            "engine": "CUDA-Q",
            "available": False,
            "worker": "UNAVAILABLE",
            "cudaq": "UNKNOWN",
            "gpu": "UNKNOWN",
            "error_code": "QUANTUM_WORKER_NOT_REGISTERED",
        }
    age = (_utcnow() - _aware(row.updated_at)).total_seconds()
    fresh = age <= max(settings.worker_stale_seconds, 15)
    result = json.loads(row.health_result_json or "{}")
    result.update(
        {
            "available": bool(
                fresh
                and row.process_status == "HEALTHY"
                and row.cudaq_status == "HEALTHY"
            ),
            "heartbeat_age_seconds": round(max(age, 0.0), 3),
            "worker_fresh": fresh,
        }
    )
    if not fresh:
        result["error_code"] = "QUANTUM_WORKER_HEARTBEAT_STALE"
    return result
