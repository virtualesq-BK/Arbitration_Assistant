from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.deps import get_case_for_user, get_current_user
from models.document import Document
from models.timeline_event import TimelineEvent
from models.user import User
from schemas.timeline import TimelineEventCreate, TimelineEventResponse
from services.audit_service import audit

router = APIRouter(tags=["timeline"])


@router.get("/cases/{case_id}/timeline", response_model=list[TimelineEventResponse])
async def get_timeline(
    case_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[TimelineEventResponse]:
    case = await get_case_for_user(case_id, user, db)
    rows = (
        await db.execute(
            select(TimelineEvent, Document.filename)
            .outerjoin(Document, (Document.id == TimelineEvent.source_document_id) & (Document.case_id == case.id))
            .where(TimelineEvent.case_id == case.id)
            .order_by(TimelineEvent.event_date, TimelineEvent.created_at)
        )
    ).all()
    return [
        TimelineEventResponse(
            **{k: getattr(ev, k) for k in TimelineEventResponse.model_fields if hasattr(ev, k)},
            source_document_filename=filename,
        )
        for ev, filename in rows
    ]


@router.post("/cases/{case_id}/timeline", response_model=TimelineEventResponse, status_code=status.HTTP_201_CREATED)
async def add_timeline_event(
    case_id: str,
    body: TimelineEventCreate,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TimelineEventResponse:
    case = await get_case_for_user(case_id, user, db)
    filename: str | None = None
    if body.source_document_id is not None:
        doc = (
            await db.execute(select(Document).where(Document.id == body.source_document_id, Document.case_id == case.id))
        ).scalar_one_or_none()
        if doc is None:
            raise HTTPException(status_code=400, detail="source_document_id does not belong to this case")
        filename = doc.filename
    ev = TimelineEvent(id=uuid.uuid4(), case_id=case.id, is_ai_extracted=False, **body.model_dump())
    db.add(ev)
    audit(db, user=user, action="timeline.create", resource_type="timeline_event", resource_id=ev.id, request=request)
    await db.commit()
    await db.refresh(ev)
    return TimelineEventResponse(
        **{k: getattr(ev, k) for k in TimelineEventResponse.model_fields if hasattr(ev, k)},
        source_document_filename=filename,
    )
