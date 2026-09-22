"""
Authentication & Role Management API Routes.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from typing import List, Optional

from ...db.session import get_db
from ...models.user import UserModel
from ...core.auth import hash_password, verify_password, create_access_token, decode_access_token
from ...schemas.auth import (
    UserRegisterRequest,
    RoleLockedRegisterRequest,
    UserLoginRequest,
    UserResponse,
    TokenResponse,
    DemoSeedResponse,
    DemoSeedUser,
    PortalSessionRequest
)
from ..deps import get_current_user

router = APIRouter(tags=["Authentication & Roles"])


def _register_user_internal(
    username: str,
    email: str,
    password: str,
    role: str,
    public_identity: str | None,
    db: Session
) -> TokenResponse:
    normalized_role = role.upper().strip()
    if normalized_role not in ["ALICE", "EVE", "BOB", "ADMIN"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role '{role}'. Allowed roles: ALICE, EVE, BOB, ADMIN"
        )

    # Check for existing username or email
    existing_user = db.query(UserModel).filter(
        (UserModel.username == username) | (UserModel.email == email)
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already registered"
        )

    public_id = public_identity
    if not public_id:
        role_labels = {
            "ALICE": "Alice (Signer)",
            "EVE": "Eve (Attacker / Adversary)",
            "BOB": "Bob (Verifier)",
            "ADMIN": "Security Auditor / Admin"
        }
        public_id = role_labels.get(normalized_role, f"{username} ({normalized_role})")

    new_user = UserModel(
        username=username.strip(),
        email=email.strip().lower(),
        password_hash=hash_password(password),
        role=normalized_role,
        public_identity=public_id,
        status="ACTIVE"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_access_token({
        "sub": new_user.id,
        "username": new_user.username,
        "role": new_user.role,
        "public_identity": new_user.public_identity
    })

    return TokenResponse(access_token=token, token_type="bearer", user=new_user)


@router.post("/register/alice", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register_alice(request: RoleLockedRegisterRequest, db: Session = Depends(get_db)):
    """Registers a new user strictly locked to role ALICE (Signer Portal)."""
    return _register_user_internal(
        username=request.username,
        email=request.email,
        password=request.password,
        role="ALICE",
        public_identity=request.public_identity or "Alice (Signer)",
        db=db
    )


@router.post("/register/eve", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register_eve(request: RoleLockedRegisterRequest, db: Session = Depends(get_db)):
    """Registers a new user strictly locked to role EVE (Adversary Lab)."""
    return _register_user_internal(
        username=request.username,
        email=request.email,
        password=request.password,
        role="EVE",
        public_identity=request.public_identity or "Eve (Attacker / Adversary)",
        db=db
    )


@router.post("/register/bob", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register_bob(request: RoleLockedRegisterRequest, db: Session = Depends(get_db)):
    """Registers a new user strictly locked to role BOB (Verifier Portal)."""
    return _register_user_internal(
        username=request.username,
        email=request.email,
        password=request.password,
        role="BOB",
        public_identity=request.public_identity or "Bob (Verifier)",
        db=db
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register_user(request: UserRegisterRequest, db: Session = Depends(get_db)):
    """Registers a new user with dedicated protocol role (ALICE, EVE, BOB, ADMIN)."""
    return _register_user_internal(
        username=request.username,
        email=request.email,
        password=request.password,
        role=request.role,
        public_identity=request.public_identity,
        db=db
    )


@router.post("/login", response_model=TokenResponse)
def login_user(request: UserLoginRequest, db: Session = Depends(get_db)):
    """Authenticates user credentials and issues an HS256 JWT access token."""
    identifier = request.username.strip()
    user = db.query(UserModel).filter(
        (UserModel.username == identifier) | (UserModel.email == identifier.lower())
    ).first()

    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials or account does not exist"
        )

    if user.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is suspended or deactivated"
        )

    token = create_access_token({
        "sub": user.id,
        "username": user.username,
        "role": user.role,
        "public_identity": user.public_identity
    })

    return TokenResponse(access_token=token, token_type="bearer", user=user)


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(user: UserModel = Depends(get_current_user)):
    """Fetches the authenticated user's profile and active role."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Provide Bearer token."
        )
    return user


@router.post("/seed-demo-users", response_model=DemoSeedResponse)
def seed_demo_users(db: Session = Depends(get_db)):
    """
    Provisions default demonstration accounts for evaluators:
    alice, eve, bob, admin (Password: 'zaslon2026').
    """
    demo_specs = [
        ("alice", "alice@zaslon.internal", "ALICE", "Alice (Signer)"),
        ("eve", "eve@zaslon.internal", "EVE", "Eve (Attacker / Adversary)"),
        ("bob", "bob@zaslon.internal", "BOB", "Bob (Verifier)"),
        ("admin", "admin@zaslon.internal", "ADMIN", "Security Auditor / Diagnostics"),
    ]

    seeded_list = []
    for username, email, role, public_id in demo_specs:
        user = db.query(UserModel).filter(UserModel.username == username).first()
        if not user:
            user = UserModel(
                username=username,
                email=email,
                password_hash=hash_password("zaslon2026"),
                role=role,
                public_identity=public_id,
                status="ACTIVE"
            )
            db.add(user)
        else:
            user.password_hash = hash_password("zaslon2026")
            user.role = role
            user.public_identity = public_id
            user.status = "ACTIVE"
        seeded_list.append(DemoSeedUser(
            username=username,
            role=role,
            public_identity=public_id,
            default_password="zaslon2026"
        ))

    db.commit()
    return DemoSeedResponse(
        message="Demo accounts seeded successfully",
        seeded_count=len(seeded_list),
        users=seeded_list
    )


@router.post("/portal-session", response_model=TokenResponse)
def get_portal_session(request: PortalSessionRequest, db: Session = Depends(get_db)):
    """
    Directly establishes a role-locked portal session based on active portal port or role.
    Port 5173 -> ALICE (Signer Portal)
    Port 5174 -> EVE (Adversary Lab)
    Port 5175 -> BOB (Verifier Portal)
    Port 3000 / other -> ADMIN / DIAGNOSTICS
    """
    target_username = None
    if request.port == 5173 or (request.role and request.role.upper() == "ALICE"):
        target_username = "alice"
    elif request.port == 5174 or (request.role and request.role.upper() == "EVE"):
        target_username = "eve"
    elif request.port == 5175 or (request.role and request.role.upper() == "BOB"):
        target_username = "bob"
    elif request.port == 3000 or (request.role and request.role.upper() == "ADMIN"):
        target_username = "admin"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown port {request.port} or role {request.role} for portal session"
        )

    user = db.query(UserModel).filter(UserModel.username == target_username).first()
    if not user:
        # Auto-seed if not yet present
        role_map = {
            "alice": ("alice@zaslon.internal", "ALICE", "Alice (Signer)"),
            "eve": ("eve@zaslon.internal", "EVE", "Eve (Attacker / Adversary)"),
            "bob": ("bob@zaslon.internal", "BOB", "Bob (Verifier)"),
            "admin": ("admin@zaslon.internal", "ADMIN", "Security Auditor / Diagnostics")
        }
        email, role, public_id = role_map[target_username]
        user = UserModel(
            username=target_username,
            email=email,
            password_hash=hash_password("zaslon2026"),
            role=role,
            public_identity=public_id,
            status="ACTIVE"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    token = create_access_token({
        "sub": user.id,
        "username": user.username,
        "role": user.role,
        "public_identity": user.public_identity
    })

    return TokenResponse(access_token=token, token_type="bearer", user=user)


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Refreshes an expiring or recently expired JWT access token.
    Cryptographically verifies the token signature and re-issues a new access token
    with the exact same user identity and role.
    """
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization Bearer token required for refresh",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # Cryptographically verifies signature, allows expired tokens for refresh
        payload = decode_access_token(token, verify_exp=False)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token signature: {str(e)}"
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload: missing sub"
        )

    user = db.query(UserModel).filter(
        (UserModel.id == user_id) | (UserModel.username == user_id)
    ).first()
    if not user or user.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account does not exist or is inactive"
        )

    new_token = create_access_token({
        "sub": user.id,
        "username": user.username,
        "role": user.role,
        "public_identity": user.public_identity
    })

    return TokenResponse(access_token=new_token, token_type="bearer", user=user)
