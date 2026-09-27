from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.deps import get_case_for_user, get_current_user, parse_uuid
from models.case import Case, CaseStatus
from models.case_party import CaseParty
from models.claim import Claim
from models.document import Document
from models.issue import Issue
from models.procedural_event import ProceduralEvent, ProceduralEventStatus
from models.timeline_event import TimelineEvent
from models.user import User
from schemas.case import (
    CaseCreate,
    CaseDetail,
    CasePartyCreate,
    CasePartyResponse,
    CaseResponse,
    CaseStats,
    CaseUpdate,
    CaseWithStats,
)
from schemas.claim import IssueCreate, IssueResponse
from services.audit_service import audit

router = APIRouter(prefix="/cases", tags=["cases"])


async def _stats_for(case_ids: list[uuid.UUID], db: AsyncSession) -> dict[uuid.UUID, CaseStats]:
    stats = {cid: CaseStats() for cid in case_ids}
    if not case_ids:
        return stats

    async def count_by(model: type, attr: str, extra: list | None = None) -> None:  # type: ignore[type-arg]
        col = model.case_id
        stmt = select(col, func.count()).where(col.in_(case_ids))
        for cond in extra or []:
            stmt = stmt.where(cond)
        for cid, n in (await db.execute(stmt.group_by(col))).all():
            setattr(stats[cid], attr, n)

    await count_by(Document, "documents")
    await count_by(Claim, "claims")
    await count_by(TimelineEvent, "timeline_events")
    await count_by(Issue, "issues")
    await count_by(
        ProceduralEvent,
        "open_procedural_events",
        [ProceduralEvent.status.in_([ProceduralEventStatus.PENDING, ProceduralEventStatus.IN_PROGRESS, ProceduralEventStatus.OVERDUE])],
    )
    return stats


@router.get("", response_model=list[CaseWithStats])
async def list_cases(
    status_filter: CaseStatus | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CaseWithStats]:
    stmt = select(Case).where(Case.org_id == user.org_id)
    if status_filter is not None:
        stmt = stmt.where(Case.status == status_filter)
    cases = (await db.execute(stmt.order_by(Case.created_at.desc()))).scalars().all()
    stats = await _stats_for([c.id for c in cases], db)
    return [CaseWithStats(**CaseResponse.model_validate(c).model_dump(), stats=stats[c.id]) for c in cases]


@router.post("", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
async def create_case(
    body: CaseCreate, request: Request, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> Case:
    case = Case(id=uuid.uuid4(), org_id=user.org_id, status=CaseStatus.ACTIVE, **body.model_dump())
    db.add(case)
    audit(db, user=user, action="case.create", resource_type="case", resource_id=case.id, request=request)
    await db.commit()
    await db.refresh(case)
    return case


@router.get("/{case_id}", response_model=CaseDetail)
async def get_case(case_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> CaseDetail:
    case = await get_case_for_user(case_id, user, db)
    stats = (await _stats_for([case.id], db))[case.id]
    parties = (await db.execute(select(CaseParty).where(CaseParty.case_id == case.id))).scalars().all()
    return CaseDetail(
        **CaseResponse.model_validate(case).model_dump(),
        stats=stats,
        parties=[CasePartyResponse.model_validate(p) for p in parties],
    )


@router.patch("/{case_id}", response_model=CaseResponse)
async def update_case(
    case_id: str,
    body: CaseUpdate,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Case:
    case = await get_case_for_user(case_id, user, db)
    changes = body.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(case, key, value)
    audit(db, user=user, action="case.update", resource_type="case", resource_id=case.id, details={"fields": list(changes)}, request=request)
    await db.commit()
    await db.refresh(case)
    return case


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_case(
    case_id: str, request: Request, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> Response:
    """Soft delete: cases are archived, never hard-deleted (records retention)."""
    case = await get_case_for_user(case_id, user, db)
    case.status = CaseStatus.ARCHIVED
    audit(db, user=user, action="case.archive", resource_type="case", resource_id=case.id, request=request)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ----------------------------------------------------------------- parties
@router.get("/{case_id}/parties", response_model=list[CasePartyResponse])
async def list_parties(case_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[CaseParty]:
    case = await get_case_for_user(case_id, user, db)
    return list((await db.execute(select(CaseParty).where(CaseParty.case_id == case.id))).scalars().all())


@router.post("/{case_id}/parties", response_model=CasePartyResponse, status_code=status.HTTP_201_CREATED)
async def add_party(
    case_id: str, body: CasePartyCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> CaseParty:
    case = await get_case_for_user(case_id, user, db)
    party = CaseParty(id=uuid.uuid4(), case_id=case.id, **body.model_dump())
    db.add(party)
    await db.commit()
    await db.refresh(party)
    return party


# ----------------------------------------------------------------- issues
@router.get("/{case_id}/issues", response_model=list[IssueResponse])
async def list_issues(case_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[Issue]:
    case = await get_case_for_user(case_id, user, db)
    return list((await db.execute(select(Issue).where(Issue.case_id == case.id).order_by(Issue.created_at))).scalars().all())


@router.post("/{case_id}/issues", response_model=IssueResponse, status_code=status.HTTP_201_CREATED)
async def create_issue(
    case_id: str, body: IssueCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> Issue:
    case = await get_case_for_user(case_id, user, db)
    issue = Issue(id=uuid.uuid4(), case_id=case.id, **body.model_dump())
    db.add(issue)
    await db.commit()
    await db.refresh(issue)
    return issue


@router.delete("/{case_id}/issues/{issue_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_issue(
    case_id: str, issue_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> Response:
    case = await get_case_for_user(case_id, user, db)
    iid = parse_uuid(issue_id, "issue id")
    issue = (await db.execute(select(Issue).where(Issue.id == iid, Issue.case_id == case.id))).scalar_one_or_none()
    if issue is not None:
        await db.delete(issue)
        await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
