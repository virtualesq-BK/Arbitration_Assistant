"""Case-level procedural checklist (ProceduralEvent) derived from institutional rules."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.deps import get_case_for_user, get_current_user, parse_uuid
from models.arbitration_institution import ArbitrationInstitution
from models.arbitration_rule import STAGE_ORDER, ArbitrationRule, ProcedureStage
from models.procedural_event import ProceduralEvent, ProceduralEventStatus
from models.user import User
from schemas.institution import ProceduralEventCreate, ProceduralEventResponse, ProceduralEventUpdate
from services.audit_service import audit

router = APIRouter(tags=["procedure"])


def _stage_rank(event_type: str) -> int:
    try:
        return STAGE_ORDER.index(ProcedureStage(event_type))
    except ValueError:
        return len(STAGE_ORDER)


@router.get("/cases/{case_id}/procedure", response_model=list[ProceduralEventResponse])
async def list_procedural_events(
    case_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[ProceduralEvent]:
    case = await get_case_for_user(case_id, user, db)
    events = (await db.execute(select(ProceduralEvent).where(ProceduralEvent.case_id == case.id))).scalars().all()
    return sorted(events, key=lambda e: (_stage_rank(e.event_type), e.due_date is None, e.due_date, e.created_at))


@router.post("/cases/{case_id}/procedure", response_model=ProceduralEventResponse, status_code=status.HTTP_201_CREATED)
async def create_procedural_event(
    case_id: str, body: ProceduralEventCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> ProceduralEvent:
    case = await get_case_for_user(case_id, user, db)
    ev = ProceduralEvent(id=uuid.uuid4(), case_id=case.id, is_ai_suggested=False, requires_confirmation=False, **body.model_dump())
    db.add(ev)
    await db.commit()
    await db.refresh(ev)
    return ev


@router.post("/cases/{case_id}/procedure/generate", response_model=list[ProceduralEventResponse])
async def generate_checklist(
    case_id: str, request: Request, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[ProceduralEvent]:
    """Create a suggested checklist from the seeded rules of the case's institution.

    Items are marked is_ai_suggested / requires_confirmation: a human must confirm each step
    and its deadline against the arbitration agreement and procedural orders.
    """
    case = await get_case_for_user(case_id, user, db)
    inst = (
        await db.execute(select(ArbitrationInstitution).where(ArbitrationInstitution.short_name == case.institution.value))
    ).scalar_one_or_none()
    if inst is None:
        raise HTTPException(status_code=404, detail=f"No seeded rules for {case.institution.value}. Source not found.")
    rules = (await db.execute(select(ArbitrationRule).where(ArbitrationRule.institution_id == inst.id))).scalars().all()
    existing = (await db.execute(select(ProceduralEvent).where(ProceduralEvent.case_id == case.id))).scalars().all()
    existing_keys = {(e.event_type, e.rule_reference) for e in existing}
    created = 0
    for rule in sorted(rules, key=lambda r: STAGE_ORDER.index(r.stage)):
        key = (rule.stage.value, rule.article_number)
        if key in existing_keys:
            continue
        db.add(
            ProceduralEvent(
                id=uuid.uuid4(),
                case_id=case.id,
                event_type=rule.stage.value,
                title=rule.title,
                due_date=None,
                source_rule=f"{inst.short_name} Rules {rule.rule_version or inst.rules_version}",
                rule_reference=rule.article_number,
                source_url=rule.source_url or inst.rules_url,
                status=ProceduralEventStatus.PENDING,
                notes=(f"Typical period: {rule.typical_deadline_days} days. " if rule.typical_deadline_days else "")
                + "Confirm against the arbitration agreement and procedural orders.",
                is_ai_suggested=True,
                requires_confirmation=True,
            )
        )
        created += 1
    audit(db, user=user, action="procedure.generate", resource_type="case", resource_id=case.id, details={"created": created}, request=request)
    await db.commit()
    return await list_procedural_events(case_id, user, db)


@router.patch("/cases/{case_id}/procedure/{event_id}", response_model=ProceduralEventResponse)
async def update_procedural_event(
    case_id: str,
    event_id: str,
    body: ProceduralEventUpdate,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProceduralEvent:
    case = await get_case_for_user(case_id, user, db)
    eid = parse_uuid(event_id, "event id")
    ev = (
        await db.execute(select(ProceduralEvent).where(ProceduralEvent.id == eid, ProceduralEvent.case_id == case.id))
    ).scalar_one_or_none()
    if ev is None:
        raise HTTPException(status_code=404, detail="Procedural event not found")
    changes = body.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(ev, key, value)
    audit(db, user=user, action="procedure.update", resource_type="procedural_event", resource_id=ev.id, details={"fields": list(changes)}, request=request)
    await db.commit()
    await db.refresh(ev)
    return ev
