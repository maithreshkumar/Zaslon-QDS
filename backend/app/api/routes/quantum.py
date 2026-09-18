"""
Quantum Teleportation Orchestration and Measurement Routes.
"""
from fastapi import APIRouter, Depends, Query, BackgroundTasks, status
from sqlalchemy.orm import Session
from typing import List

from ...db.session import get_db
from ...services.teleportation_service import TeleportationService
from ...models.quantum_run import QuantumRunModel
from ...models.measurement import MeasurementModel
from ...schemas.quantum import (
    TeleportationLaunchRequest,
    QuantumRunResponse,
    MeasurementResponse,
    QuantumStatusResponse
)
from ...schemas.common import StandardResponse, PaginatedResponse

router = APIRouter()


@router.post("/{session_id}/teleport", response_model=StandardResponse[QuantumRunResponse], status_code=status.HTTP_202_ACCEPTED)
def launch_teleportation(
    session_id: str,
    req: TeleportationLaunchRequest,
    background_tasks: BackgroundTasks,
    background: bool = Query(False, description="Execute quantum teleportation asynchronously in background"),
    db: Session = Depends(get_db)
):
    quantum_run = TeleportationService.launch_teleportation(
        db=db,
        session_id=session_id,
        actor=req.actor,
        teleportation_count=req.teleportation_count or 4096,
        batch_size=req.batch_size or 512,
        background=background,
        background_tasks=background_tasks
    )
    return StandardResponse(data=quantum_run)


@router.get("/{session_id}/quantum-status", response_model=StandardResponse[QuantumStatusResponse])
def get_quantum_status(session_id: str, db: Session = Depends(get_db)):
    status_data = TeleportationService.get_quantum_status(db, session_id)
    return StandardResponse(data=status_data)


@router.get("/{session_id}/quantum-runs", response_model=StandardResponse[List[QuantumRunResponse]])
def get_quantum_runs(session_id: str, db: Session = Depends(get_db)):
    runs = db.query(QuantumRunModel).filter(QuantumRunModel.session_id == session_id).all()
    return StandardResponse(data=runs)


@router.get("/{session_id}/measurements", response_model=StandardResponse[PaginatedResponse[MeasurementResponse]])
def get_measurements(
    session_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    offset = (page - 1) * page_size
    query = db.query(MeasurementModel).join(QuantumRunModel).filter(QuantumRunModel.session_id == session_id)
    total = query.count()
    items = query.order_by(MeasurementModel.operation_index.asc()).offset(offset).limit(page_size).all()

    return StandardResponse(
        data=PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size
        )
    )

