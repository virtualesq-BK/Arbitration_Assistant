"""Shared FastAPI dependencies: authentication and tenant-scoped lookups."""
from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import TokenError, verify_access_token
from models.case import Case
from models.document import Document
from models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


def parse_uuid(value: str, what: str = "id") -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Invalid {what}") from exc


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized
    try:
        payload = verify_access_token(credentials.credentials)
        user_id = uuid.UUID(payload["sub"])
    except (TokenError, ValueError, KeyError) as exc:
        raise unauthorized from exc

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise unauthorized
    return user


async def get_case_for_user(case_id: str, user: User, db: AsyncSession) -> Case:
    """Fetch a case, enforcing org-level tenant isolation. 404 (not 403) to avoid leaking existence."""
    cid = parse_uuid(case_id, "case id")
    result = await db.execute(select(Case).where(Case.id == cid, Case.org_id == user.org_id))
    case = result.scalar_one_or_none()
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return case


async def get_document_for_user(document_id: str, user: User, db: AsyncSession) -> Document:
    did = parse_uuid(document_id, "document id")
    result = await db.execute(select(Document).where(Document.id == did, Document.org_id == user.org_id))
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return doc
