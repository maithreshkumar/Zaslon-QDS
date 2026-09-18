"""
QDS Cryptographic Hashing and Workflow Routes.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import Dict, Any

from ...db.session import get_db
from ...services.hashing_service import HashingService
from ...services.qds_service import QdsService
from ...schemas.qds import HashCreateRequest, HashResponse
from ...schemas.common import StandardResponse

router = APIRouter()


@router.post("/{session_id}/hash", response_model=StandardResponse[HashResponse], status_code=status.HTTP_201_CREATED)
def compute_hash(
    session_id: str,
    req: HashCreateRequest,
    db: Session = Depends(get_db)
):
    hash_record = HashingService.process_message_hash(
        db=db,
        session_id=session_id,
        raw_message=req.raw_message,
        actor=req.actor
    )
    return StandardResponse(data=hash_record)


@router.get("/{session_id}/workflow", response_model=StandardResponse[Dict[str, Any]])
def get_workflow_overview(session_id: str, db: Session = Depends(get_db)):
    overview = QdsService.get_full_session_status(db, session_id)
    return StandardResponse(data=overview)
