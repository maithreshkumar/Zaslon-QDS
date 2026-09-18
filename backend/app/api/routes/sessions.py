"""
Session Management API Routes.
"""
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from typing import List

from ...db.session import get_db
from ...services.session_service import SessionService
from ...schemas.session import SessionCreate, SessionResponse
from ...schemas.common import StandardResponse

router = APIRouter()


@router.post("", response_model=StandardResponse[SessionResponse], status_code=status.HTTP_201_CREATED)
def create_session(req: SessionCreate, db: Session = Depends(get_db)):
    session = SessionService.create_session(
        db=db,
        session_name=req.session_name,
        created_by=req.created_by,
        verifier_id=req.verifier_id
    )
    return StandardResponse(data=session)


@router.get("", response_model=StandardResponse[List[SessionResponse]])
def list_sessions(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    sessions = SessionService.list_sessions(db, limit=limit, offset=offset)
    return StandardResponse(data=sessions)


@router.get("/{session_id}", response_model=StandardResponse[SessionResponse])
def get_session(session_id: str, db: Session = Depends(get_db)):
    session = SessionService.get_session(db, session_id)
    return StandardResponse(data=session)
