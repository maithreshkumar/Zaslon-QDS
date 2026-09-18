"""
Audit Trail API Routes.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from ...db.session import get_db
from ...services.audit_service import AuditService
from ...schemas.audit import AuditEventResponse
from ...schemas.common import StandardResponse

router = APIRouter()


@router.get("", response_model=StandardResponse[List[AuditEventResponse]])
@router.get("/trail", response_model=StandardResponse[List[AuditEventResponse]])
def get_audit_trail(
    session_id: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    events = AuditService.get_events(db=db, session_id=session_id, event_type=event_type, limit=limit)
    return StandardResponse(data=events)
