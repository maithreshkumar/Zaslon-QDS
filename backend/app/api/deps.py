"""
API Dependencies and Common Injections.
Provides DB session, JWT user authentication, and RBAC role enforcement.
"""
from typing import Generator, Optional, List, Callable
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..core.exceptions import UnauthorizedError
from ..core.auth import decode_access_token
from ..models.user import UserModel


def get_current_actor(x_participant_id: Optional[str] = Header(None)) -> str:
    """Extracts participant actor identity from request header (legacy compatibility)."""
    return x_participant_id or "anonymous"


def get_current_user(
    authorization: Optional[str] = Header(None),
    x_participant_id: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Optional[UserModel]:
    """
    Extracts and authenticates user from JWT Bearer token.
    Falls back to looking up username by x_participant_id if bearer token is not provided.
    """
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()

    if token:
        try:
            payload = decode_access_token(token)
            user_id = payload.get("sub")
            if user_id:
                user = db.query(UserModel).filter(UserModel.id == user_id).first()
                if user and user.status == "ACTIVE":
                    return user
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid or expired authentication token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # Fallback to x_participant_id for backwards compatibility
    if x_participant_id:
        user = db.query(UserModel).filter(
            (UserModel.username == x_participant_id) | (UserModel.public_identity == x_participant_id)
        ).first()
        if user:
            return user

    return None


def require_role(allowed_roles: List[str]) -> Callable:
    """
    Enforces Role-Based Access Control (RBAC).
    Raises HTTP 401 if unauthenticated, or HTTP 403 if user role is not in allowed_roles.
    """
    def role_dependency(
        user: Optional[UserModel] = Depends(get_current_user)
    ) -> UserModel:
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required. Please provide a valid Bearer token.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if user.role not in allowed_roles and user.role != "ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {allowed_roles}. Your authenticated role: {user.role}"
            )
        return user

    return role_dependency
