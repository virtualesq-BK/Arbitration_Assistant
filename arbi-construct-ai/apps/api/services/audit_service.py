"""Helpers to persist AuditLog and AIAnalysis records."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from models.ai_analysis import AIAnalysis
from models.audit_log import AuditLog
from models.user import User
from services.agent_service import PROMPT_VERSION, AgentResponse


def client_ip(request: Request | None) -> str | None:
    if request is None:
        return None
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def audit(
    db: AsyncSession,
    *,
    user: User | None,
    action: str,
    resource_type: str,
    resource_id: str | uuid.UUID | None = None,
    details: dict[str, Any] | None = None,
    request: Request | None = None,
    org_id: uuid.UUID | None = None,
) -> AuditLog:
    entry = AuditLog(
        org_id=org_id or (user.org_id if user else None),
        user_id=user.id if user else None,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        details_json=details,
        ip_address=client_ip(request),
    )
    db.add(entry)
    return entry


def record_analysis(
    db: AsyncSession,
    *,
    response: AgentResponse,
    user: User,
    case_id: uuid.UUID | None,
    query: str | None,
) -> AIAnalysis:
    analysis = AIAnalysis(
        id=uuid.uuid4(),
        case_id=case_id,
        user_id=user.id,
        agent=response.agent,
        model_name=response.model,
        prompt_version=PROMPT_VERSION,
        query=query,
        retrieved_sources_json=response.sources,
        output_json=response.to_dict(),
    )
    db.add(analysis)
    return analysis
