from __future__ import annotations

from contextlib import contextmanager
import threading
from typing import Iterator

from sqlalchemy import text

from .config import settings
from .db import engine as database_engine
from .quantum import create_quantum_engine


class AdmissionRejected(RuntimeError):
    pass


if settings.max_parallel_quantum_jobs < 1:
    raise RuntimeError("ZASLON_MAX_PARALLEL_QUANTUM_JOBS must be at least 1")

_quantum_job_slots = threading.BoundedSemaphore(settings.max_parallel_quantum_jobs)
_runtime_lock = threading.Lock()
_quantum_readiness: dict | None = None


def initialize_quantum_runtime() -> dict:
    """Initialize the configured engine once during controlled application startup."""
    global _quantum_readiness
    with _runtime_lock:
        try:
            metadata = create_quantum_engine(settings.quantum_engine, 0).metadata.model_dump()
            _quantum_readiness = {
                **metadata,
                "available": True,
                "initialized_at_startup": True,
                "health_check_mutates_configuration": False,
                "max_parallel_quantum_jobs": settings.max_parallel_quantum_jobs,
            }
        except Exception:
            _quantum_readiness = {
                "engine": settings.quantum_engine,
                "available": False,
                "initialized_at_startup": True,
                "health_check_mutates_configuration": False,
                "fallback_used": False,
                "error_code": "QUANTUM_ENGINE_INITIALIZATION_FAILED",
                "max_parallel_quantum_jobs": settings.max_parallel_quantum_jobs,
            }
        return dict(_quantum_readiness)


def quantum_readiness() -> dict:
    with _runtime_lock:
        if _quantum_readiness is None:
            return {
                "engine": settings.quantum_engine,
                "available": False,
                "initialized_at_startup": False,
                "health_check_mutates_configuration": False,
                "error_code": "QUANTUM_RUNTIME_NOT_INITIALIZED",
            }
        return dict(_quantum_readiness)


def database_readiness() -> bool:
    try:
        with database_engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


@contextmanager
def quantum_job_slot(job_type: str) -> Iterator[None]:
    acquired = _quantum_job_slots.acquire(blocking=False)
    if not acquired:
        raise AdmissionRejected(
            f"Quantum job capacity is busy; retry the {job_type} request later."
        )
    try:
        yield
    finally:
        _quantum_job_slots.release()

