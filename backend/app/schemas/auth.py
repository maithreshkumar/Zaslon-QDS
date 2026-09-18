"""
Pydantic Schemas for Authentication and Role Authorization.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime


class UserRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64, description="Unique username")
    email: str = Field(..., min_length=3, max_length=128, description="Valid email address")
    password: str = Field(..., min_length=6, description="Plaintext password")
    role: str = Field(..., description="Role: ALICE, EVE, BOB, or ADMIN")
    public_identity: Optional[str] = Field(None, description="Human-readable participant designation")


class RoleLockedRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64, description="Unique username")
    email: str = Field(..., min_length=3, max_length=128, description="Valid email address")
    password: str = Field(..., min_length=6, description="Plaintext password")
    public_identity: Optional[str] = Field(None, description="Human-readable participant designation")


class UserLoginRequest(BaseModel):
    username: str = Field(..., description="Username or email")
    password: str = Field(..., description="Password")


class PortalSessionRequest(BaseModel):
    port: Optional[int] = Field(None, description="Frontend port: 5173, 5174, 5175, or 3000")
    role: Optional[str] = Field(None, description="Direct role request: ALICE, EVE, BOB, or ADMIN")


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str
    public_identity: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class DemoSeedUser(BaseModel):
    username: str
    role: str
    public_identity: str
    default_password: str


class DemoSeedResponse(BaseModel):
    message: str
    seeded_count: int
    users: List[DemoSeedUser]
