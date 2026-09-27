from __future__ import annotations

import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.deps import get_current_user
from core.security import create_access_token, hash_password, verify_password
from models.organization import Organization, OrganizationMember
from models.user import User, UserRole
from schemas.auth import LoginRequest, OrganizationResponse, RegisterRequest, TokenResponse, UserResponse
from services.audit_service import audit

router = APIRouter(prefix="/auth", tags=["auth"])


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:200] or "org"


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    email = body.email.lower()
    existing = await db.execute(select(User).where(func.lower(User.email) == email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    org_name = body.organization_name or f"{body.full_name}'s Organization"
    org = Organization(id=uuid.uuid4(), name=org_name, slug=f"{_slugify(org_name)}-{uuid.uuid4().hex[:6]}")
    db.add(org)
    await db.flush()

    user = User(
        id=uuid.uuid4(),
        email=email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        is_active=True,
        role=UserRole.ORG_ADMIN,  # creator of a new organisation administers it
        org_id=org.id,
    )
    db.add(user)
    await db.flush()
    db.add(OrganizationMember(org_id=org.id, user_id=user.id, role=UserRole.ORG_ADMIN))
    audit(db, user=user, action="user.register", resource_type="user", resource_id=user.id, request=request)
    await db.commit()
    return TokenResponse(access_token=create_access_token(str(user.id), {"org": str(org.id)}))


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    result = await db.execute(select(User).where(func.lower(User.email) == body.email.lower()))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(body.password, user.hashed_password) or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    audit(db, user=user, action="user.login", resource_type="user", resource_id=user.id, request=request)
    await db.commit()
    return TokenResponse(access_token=create_access_token(str(user.id), {"org": str(user.org_id)}))


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.get("/me/organization", response_model=OrganizationResponse)
async def my_org(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> Organization:
    org = await db.get(Organization, user.org_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org
