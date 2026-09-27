from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr, Field

from models.user import UserRole
from schemas.common import TimestampedResponse


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    organization_name: str | None = Field(default=None, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(TimestampedResponse):
    email: str
    full_name: str
    is_active: bool
    role: UserRole
    org_id: uuid.UUID


class OrganizationResponse(TimestampedResponse):
    name: str
    slug: str | None = None
    country: str | None = None
