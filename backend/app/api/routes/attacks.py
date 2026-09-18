"""
Cyberattack Simulation and Demonstration Routes.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List

from ...db.session import get_db
from ...services.attack_service import AttackService
from ...models.attack_event import AttackEventModel
from ...schemas.attack import AttackSimulationRequest, AttackEventResponse
from ...schemas.common import StandardResponse

router = APIRouter()


@router.post("/{session_id}/simulate-attack", response_model=StandardResponse[AttackEventResponse], status_code=status.HTTP_201_CREATED)
def trigger_attack_simulation(
    session_id: str,
    req: AttackSimulationRequest,
    db: Session = Depends(get_db)
):
    event = AttackService.simulate_attack(
        db=db,
        session_id=session_id,
        attack_type=req.attack_type,
        payload_params=req.tamper_payload
    )
    return StandardResponse(data=event)


@router.get("/{session_id}/attack-events", response_model=StandardResponse[List[AttackEventResponse]])
def list_attack_events(session_id: str, db: Session = Depends(get_db)):
    events = AttackService.get_attack_events(db=db, session_id=session_id)
    return StandardResponse(data=events)
