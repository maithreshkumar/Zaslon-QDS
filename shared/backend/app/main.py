from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

PROJECT_ROOT = Path(__file__).resolve().parents[3]
for relative in ("Alice/backend", "Bob/backend", "Attack/backend"):
    path = str(PROJECT_ROOT / relative)
    if path not in sys.path:
        sys.path.insert(0, path)

from alice_service.router import router as alice_router
from attacker_service.router import router as attack_router
from bob_service.router import router as bob_router
from zaslon_shared.config import settings
from zaslon_shared.auth import authenticated_role, require_roles, validate_auth_configuration
from zaslon_shared.attacks import get_experiment
from zaslon_shared.db import init_db
from zaslon_shared.dispatch import qiskit_validation
from zaslon_shared.job_queue import (
    JobFailed,
    JobTimedOut,
    job_status,
    validate_job_queue_configuration,
    worker_readiness,
)
from zaslon_shared.migrations import verify_schema
from zaslon_shared.runtime import (
    AdmissionRejected,
    database_readiness,
    initialize_quantum_runtime,
    quantum_readiness,
)
from zaslon_shared.protocol import (
    get_session_quantum_status,
    get_session_summary,
    list_sessions,
    load_qds_session,
    serialize_signature_artifact,
    signature_artifact_filename,
)
from zaslon_shared.schemas import HealthResponse, QiskitValidationRequest

@asynccontextmanager
async def lifespan(_: FastAPI):
    validate_auth_configuration()
    validate_job_queue_configuration()
    if settings.execution_mode == "worker_queue":
        if not verify_schema():
            raise RuntimeError("Database migrations are incomplete")
    else:
        init_db()
        initialize_quantum_runtime()
    yield


app = FastAPI(
    title="ZASLON-QDS Research API",
    version="0.2.0",
    description="Teleportation-based QDS research laboratory; not a standardized QDS implementation.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(alice_router)
app.include_router(bob_router)
app.include_router(attack_router)


@app.get("/api/v1/health", response_model=HealthResponse)
def health() -> HealthResponse:
    metadata = (
        worker_readiness()
        if settings.execution_mode == "worker_queue"
        else quantum_readiness()
    )
    db_ready = database_readiness()
    database_kind = "sqlite-development" if settings.database_url.startswith("sqlite") else "mysql"
    return HealthResponse(
        status="ok" if metadata.get("available") and db_ready else "degraded",
        protocol=settings.protocol_name,
        protocol_version=settings.protocol_version,
        quantum=metadata,
        database=f"{database_kind}:ready" if db_ready else f"{database_kind}:unavailable",
    )


@app.get(
    "/api/v1/sessions",
    dependencies=[Depends(require_roles("ALICE", "ATTACK"))],
)
def sessions():
    return {"items": list_sessions()}


@app.get(
    "/api/v1/sessions/{session_id}",
    dependencies=[Depends(require_roles("ALICE"))],
)
def session(session_id: str):
    try:
        return get_session_summary(session_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.get(
    "/api/v1/sessions/{session_id}/quantum-status",
    dependencies=[Depends(require_roles("ALICE", "BOB"))],
)
def session_quantum_status(session_id: str):
    try:
        return get_session_quantum_status(session_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.get(
    "/api/v1/sessions/{session_id}/signature",
    dependencies=[Depends(require_roles("ALICE", "BOB"))],
)
def signature_artifact(session_id: str) -> Response:
    try:
        row, signature, _ = load_qds_session(session_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    filename = signature_artifact_filename(row.document_name)
    return Response(
        content=serialize_signature_artifact(signature),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@app.post(
    "/api/v1/validate/qiskit",
    dependencies=[Depends(require_roles("ALICE"))],
)
def validate_with_qiskit(request: QiskitValidationRequest):
    try:
        primary = settings.quantum_engine if request.primary_engine == "configured" else request.primary_engine
        return qiskit_validation({
            "primary_engine_name": primary,
            "shots": request.shots,
            "seed": request.seed,
            "tolerance": request.tolerance,
        })
    except JobTimedOut as exc:
        raise HTTPException(202, {"job_id": exc.job_id, "status": "RUNNING"}) from exc
    except JobFailed as exc:
        raise HTTPException(503, {"job_id": exc.job_id, "code": exc.code}) from exc
    except AdmissionRejected as exc:
        raise HTTPException(429, str(exc), headers={"Retry-After": "2"}) from exc
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(503, str(exc)) from exc


@app.get("/api/v1/jobs/{job_id}")
def queued_job(job_id: str, role=Depends(authenticated_role)):
    try:
        return job_status(job_id, role=role)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.get(
    "/api/v1/results/{experiment_id}",
    dependencies=[Depends(require_roles("ATTACK"))],
)
def result(experiment_id: str):
    try:
        return get_experiment(experiment_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
