"""
Health and Runtime Capability Endpoints.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from ...db.session import get_db
from ...services.quantum_service import QuantumService

router = APIRouter()


@router.get("/health", tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    # 1. DB Health
    db_status = "HEALTHY"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"UNHEALTHY: {str(e)}"

    # 2. Quantum Service Health
    quantum_status = QuantumService.check_health()

    return {
        "status": "HEALTHY" if db_status == "HEALTHY" else "DEGRADED",
        "components": {
            "backend": "HEALTHY",
            "database": db_status,
            "quantum_service": quantum_status
        }
    }
