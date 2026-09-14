from __future__ import annotations

from collections.abc import Callable
import secrets
from typing import Annotated, Literal

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

from .config import settings


Role = Literal["ALICE", "BOB", "ATTACK"]
API_KEY_HEADER_NAME = "X-ZASLON-API-Key"
_api_key_header = APIKeyHeader(name=API_KEY_HEADER_NAME, auto_error=False)


def _configured_keys() -> dict[Role, str]:
    return {
        "ALICE": settings.alice_api_key,
        "BOB": settings.bob_api_key,
        "ATTACK": settings.attack_api_key,
    }


def validate_auth_configuration() -> None:
    keys = _configured_keys()
    invalid = [
        role for role, key in keys.items()
        if len(key) < 32 or key.startswith("replace-with-")
    ]
    if invalid:
        raise RuntimeError(
            "Missing or weak role API keys: " + ", ".join(invalid) + ". "
            "Configure unique non-template ZASLON_<ROLE>_API_KEY values of at least 32 characters."
        )
    if len(set(keys.values())) != len(keys):
        raise RuntimeError("Alice, Bob, and Attack API keys must be different.")


def authenticated_role(
    presented_key: Annotated[str | None, Depends(_api_key_header)],
) -> Role:
    if not presented_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing role API credential.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    matched_role: Role | None = None
    for role, configured_key in _configured_keys().items():
        if configured_key and secrets.compare_digest(presented_key, configured_key):
            matched_role = role
    if matched_role is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid role API credential.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return matched_role


def require_roles(*allowed_roles: Role) -> Callable[[Role], Role]:
    allowed = frozenset(allowed_roles)

    def authorize(role: Annotated[Role, Depends(authenticated_role)]) -> Role:
        if role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"The {role} role is not authorized for this endpoint.",
            )
        return role

    return authorize
