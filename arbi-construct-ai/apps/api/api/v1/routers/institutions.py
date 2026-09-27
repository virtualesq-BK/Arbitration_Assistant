from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.deps import get_current_user
from models.arbitration_institution import ArbitrationInstitution
from models.arbitration_rule import STAGE_ORDER, ArbitrationRule, ProcedureStage
from models.user import User
from schemas.ai import AI_DISCLAIMER, AgentResponseSchema
from schemas.institution import (
    ComparisonCell,
    ComparisonRow,
    ComparisonTable,
    InstitutionResponse,
    ProcedureStageResponse,
    RuleResponse,
)
from services.agent_service import ProcedureAgent
from services.audit_service import record_analysis

router = APIRouter(prefix="/institutions", tags=["institutions"])


async def _resolve_institution(institution_id: str, db: AsyncSession) -> ArbitrationInstitution:
    """Accept either the UUID or the short name (ICC, SIAC, ...)."""
    stmt = select(ArbitrationInstitution)
    try:
        stmt = stmt.where(ArbitrationInstitution.id == uuid.UUID(institution_id))
    except ValueError:
        stmt = stmt.where(ArbitrationInstitution.short_name == institution_id.upper())
    inst = (await db.execute(stmt)).scalar_one_or_none()
    if inst is None:
        raise HTTPException(status_code=404, detail="Institution not found")
    return inst


def _sort_rules(rules: list[ArbitrationRule]) -> list[ArbitrationRule]:
    return sorted(rules, key=lambda r: (STAGE_ORDER.index(r.stage), r.article_number))


@router.get("", response_model=list[InstitutionResponse])
async def list_institutions(_: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[ArbitrationInstitution]:
    return list((await db.execute(select(ArbitrationInstitution).order_by(ArbitrationInstitution.short_name))).scalars().all())


@router.get("/stages", response_model=list[str])
async def list_stages(_: User = Depends(get_current_user)) -> list[str]:
    return [s.value for s in STAGE_ORDER]


@router.get("/comparison", response_model=ComparisonTable)
async def comparison(
    institutions: str = Query("ICC,SIAC,LCIA", description="Comma-separated short names"),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ComparisonTable:
    names = [n.strip().upper() for n in institutions.split(",") if n.strip()]
    insts = (await db.execute(select(ArbitrationInstitution).where(ArbitrationInstitution.short_name.in_(names)))).scalars().all()
    insts = sorted(insts, key=lambda i: names.index(i.short_name))
    rules = (
        await db.execute(select(ArbitrationRule).where(ArbitrationRule.institution_id.in_([i.id for i in insts])))
    ).scalars().all()
    by_id = {i.id: i for i in insts}
    rows: list[ComparisonRow] = []
    for stage in STAGE_ORDER:
        stage_rules = [r for r in rules if r.stage == stage]
        if not stage_rules:
            continue
        cells: dict[str, list[ComparisonCell]] = {i.short_name: [] for i in insts}
        for r in sorted(stage_rules, key=lambda r: r.article_number):
            inst = by_id[r.institution_id]
            cells[inst.short_name].append(
                ComparisonCell(
                    article_number=r.article_number,
                    title=r.title,
                    source_url=r.source_url or inst.rules_url,
                    rule_version=r.rule_version or inst.rules_version,
                )
            )
        rows.append(ComparisonRow(stage=stage, cells=cells))
    return ComparisonTable(institutions=[InstitutionResponse.model_validate(i) for i in insts], rows=rows)


@router.get("/{institution_id}", response_model=InstitutionResponse)
async def get_institution(institution_id: str, _: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> ArbitrationInstitution:
    return await _resolve_institution(institution_id, db)


@router.get("/{institution_id}/rules", response_model=list[RuleResponse])
async def list_rules(
    institution_id: str,
    stage: ProcedureStage | None = None,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ArbitrationRule]:
    inst = await _resolve_institution(institution_id, db)
    stmt = select(ArbitrationRule).where(ArbitrationRule.institution_id == inst.id)
    if stage is not None:
        stmt = stmt.where(ArbitrationRule.stage == stage)
    return _sort_rules(list((await db.execute(stmt)).scalars().all()))


@router.get("/{institution_id}/procedure/{stage}", response_model=ProcedureStageResponse)
async def get_procedure_stage(
    institution_id: str,
    stage: str,
    ai: bool = Query(False, description="Also run the ProcedureAgent for an AI explanation"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProcedureStageResponse:
    inst = await _resolve_institution(institution_id, db)
    try:
        stage_enum = ProcedureStage(stage.upper())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Unknown stage '{stage}'") from exc
    rules = _sort_rules(
        list(
            (
                await db.execute(
                    select(ArbitrationRule).where(ArbitrationRule.institution_id == inst.id, ArbitrationRule.stage == stage_enum)
                )
            ).scalars().all()
        )
    )
    guidance: AgentResponseSchema | None = None
    if ai:
        resp = await ProcedureAgent().get_procedure(inst.short_name, stage_enum.value, db=db)
        analysis = record_analysis(db, response=resp, user=user, case_id=None, query=f"{inst.short_name} {stage_enum.value}")
        await db.commit()
        guidance = AgentResponseSchema(**resp.to_dict(), analysis_id=analysis.id)
    return ProcedureStageResponse(
        institution=InstitutionResponse.model_validate(inst),
        stage=stage_enum,
        rules=[RuleResponse.model_validate(r) for r in rules],
        source_not_found=not rules,
        ai_guidance=guidance,
        disclaimer=AI_DISCLAIMER,
    )
