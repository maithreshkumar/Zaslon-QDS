"""
Master API v1 Router.
"""
from fastapi import APIRouter

from .routes import sessions, qds, quantum, declarations, verification, attacks, audit, health, auth, alice, eve, bob

api_router = APIRouter(prefix="/api/v1")

# Mount authentication and role-specific portals
api_router.include_router(auth.router, prefix="/auth")
api_router.include_router(alice.router, prefix="/alice")
api_router.include_router(eve.router, prefix="/eve")
api_router.include_router(bob.router, prefix="/bob")

# Mount foundational system and research endpoints
api_router.include_router(health.router)
api_router.include_router(sessions.router, prefix="/sessions", tags=["Sessions"])
api_router.include_router(qds.router, prefix="/sessions", tags=["QDS Cryptography"])
api_router.include_router(quantum.router, prefix="/sessions", tags=["Quantum Teleportation"])
api_router.include_router(declarations.router, prefix="/sessions", tags=["Public Declarations"])
api_router.include_router(verification.router, prefix="/sessions", tags=["Verification & Statistics"])
api_router.include_router(attacks.router, prefix="/sessions", tags=["Attack Simulation"])
api_router.include_router(audit.router, prefix="/audit-trail", tags=["Audit Trail"])
api_router.include_router(audit.router, prefix="/audit", tags=["Audit Trail"])
