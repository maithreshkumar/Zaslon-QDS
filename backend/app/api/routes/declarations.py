"""
Public Declaration Routes.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...services.declaration_service import DeclarationService
from ...schemas.declaration import DeclarationCreateRequest, DeclarationResponse
from ...schemas.common import StandardResponse

router = APIRouter()


@router.post("/{session_id}/declare", response_model=StandardResponse[DeclarationResponse], status_code=status.HTTP_201_CREATED)
def issue_declaration(
    session_id: str,
    req: DeclarationCreateRequest,
    db: Session = Depends(get_db)
):
    declaration = DeclarationService.create_declaration(
        db=db,
        session_id=session_id,
        signer_id=req.signer_id
    )
    return StandardResponse(data=declaration)


@router.get("/{session_id}/declaration", response_model=StandardResponse[DeclarationResponse])
def get_declaration(session_id: str, db: Session = Depends(get_db)):
    declaration = DeclarationService.get_declaration(db=db, session_id=session_id)
    return StandardResponse(data=declaration)
