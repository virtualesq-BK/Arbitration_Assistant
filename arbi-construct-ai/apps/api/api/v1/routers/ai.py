"""AI agent endpoints. Every call is audited in the AIAnalysis table."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.deps import get_case_for_user, get_current_user, get_document_for_user, parse_uuid
from models.ai_analysis import AIAnalysis
from models.claim import Claim
from models.document import ProcessingStatus
from models.user import User
from schemas.ai import AgentResponseSchema, AIAnalysisListItem, AIAnalysisResponse, ProcedureQuery, ResearchRequest
from services.agent_service import (
    AgentResponse,
    CaseIntelligenceAgent,
    ConstructionClaimsAgent,
    ContractAgent,
    DocumentAgent,
    EvidenceAgent,
    ProcedureAgent,
    ResearchAgent,
)
from services.audit_service import audit, record_analysis

router = APIRouter(tags=["ai"])


async def _persist(
    db: AsyncSession,
    resp: AgentResponse,
    user: User,
    case_id: uuid.UUID | None,
    query: str | None,
    request: Request,
) -> AgentResponseSchema:
    analysis = record_analysis(db, response=resp, user=user, case_id=case_id, query=query)
    audit(
        db,
        user=user,
        action="ai.analysis",
        resource_type="ai_analysis",
        resource_id=analysis.id,
        details={"agent": resp.agent, "model": resp.model, "case_id": str(case_id) if case_id else None},
        request=request,
    )
    await db.commit()
    return AgentResponseSchema(**resp.to_dict(), analysis_id=analysis.id)


@router.post("/cases/{case_id}/analyze", response_model=AgentResponseSchema)
async def analyze_case(
    case_id: str, request: Request, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> AgentResponseSchema:
    case = await get_case_for_user(case_id, user, db)
    resp = await CaseIntelligenceAgent().analyze_case(str(case.id), db)
    return await _persist(db, resp, user, case.id, "case intelligence briefing", request)


@router.post("/cases/{case_id}/evidence/analyze", response_model=AgentResponseSchema)
async def analyze_evidence(
    case_id: str, request: Request, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> AgentResponseSchema:
    case = await get_case_for_user(case_id, user, db)
    resp = await EvidenceAgent().analyze_case(str(case.id), db)
    return await _persist(db, resp, user, case.id, "evidence review", request)


@router.post("/cases/{case_id}/claims/{claim_id}/analyze", response_model=AgentResponseSchema)
async def analyze_claim(
    case_id: str, claim_id: str, request: Request, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> AgentResponseSchema:
    case = await get_case_for_user(case_id, user, db)
    cid = parse_uuid(claim_id, "claim id")
    claim = (await db.execute(select(Claim).where(Claim.id == cid, Claim.case_id == case.id))).scalar_one_or_none()
    if claim is None:
        raise HTTPException(status_code=404, detail="Claim not found")
    resp = await ConstructionClaimsAgent().analyze_claim(str(claim.id), db)
    return await _persist(db, resp, user, case.id, f"claim analysis {claim.claim_ref}", request)


@router.post("/documents/{document_id}/analyze", response_model=AgentResponseSchema)
async def analyze_document(
    document_id: str, request: Request, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> AgentResponseSchema:
    doc = await get_document_for_user(document_id, user, db)
    resp = await DocumentAgent().analyze(str(doc.id), db)
    if resp.summary and not resp.model.endswith("(unavailable)"):
        doc.summary = resp.summary
        doc.classification_status = ProcessingStatus.COMPLETED
    return await _persist(db, resp, user, doc.case_id, f"document analysis {doc.filename}", request)


@router.post("/documents/{document_id}/contract-analyze", response_model=AgentResponseSchema)
async def analyze_contract(
    document_id: str, request: Request, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> AgentResponseSchema:
    doc = await get_document_for_user(document_id, user, db)
    resp = await ContractAgent().analyze(str(doc.id), db)
    return await _persist(db, resp, user, doc.case_id, f"contract analysis {doc.filename}", request)


@router.post("/research", response_model=AgentResponseSchema)
async def research(
    body: ResearchRequest, request: Request, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> AgentResponseSchema:
    case_id: uuid.UUID | None = None
    if body.case_id is not None:
        case = await get_case_for_user(str(body.case_id), user, db)
        case_id = case.id
    resp = await ResearchAgent().research(
        body.query,
        body.institution,
        db=db,
        case_id=str(case_id) if case_id else None,
        org_id=str(user.org_id),
    )
    return await _persist(db, resp, user, case_id, body.query, request)


@router.post("/procedure", response_model=AgentResponseSchema)
async def procedure_guidance(
    body: ProcedureQuery, request: Request, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> AgentResponseSchema:
    resp = await ProcedureAgent().get_procedure(body.institution, body.stage, db=db)
    return await _persist(db, resp, user, None, f"{body.institution} {body.stage or ''}".strip(), request)


@router.get("/cases/{case_id}/analyses", response_model=list[AIAnalysisListItem])
async def list_analyses(
    case_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[AIAnalysisListItem]:
    case = await get_case_for_user(case_id, user, db)
    rows = (
        await db.execute(select(AIAnalysis).where(AIAnalysis.case_id == case.id).order_by(AIAnalysis.created_at.desc()).limit(50))
    ).scalars().all()
    return [
        AIAnalysisListItem(
            id=a.id,
            agent=a.agent,
            model_name=a.model_name,
            created_at=a.created_at,
            summary=(a.output_json or {}).get("summary"),
        )
        for a in rows
    ]


@router.get("/analyses/{analysis_id}", response_model=AIAnalysisResponse)
async def get_analysis(
    analysis_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> AIAnalysis:
    aid = parse_uuid(analysis_id, "analysis id")
    analysis = await db.get(AIAnalysis, aid)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    if analysis.case_id is not None:
        await get_case_for_user(str(analysis.case_id), user, db)  # tenant check
    elif analysis.user_id != user.id:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis
