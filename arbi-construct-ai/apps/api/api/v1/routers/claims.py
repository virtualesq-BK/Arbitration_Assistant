from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.deps import get_case_for_user, get_current_user, parse_uuid
from models.case import Case
from models.claim import Claim
from models.claim_evidence import ClaimEvidence
from models.document import Document
from models.user import User
from schemas.claim import (
    ClaimCreate,
    ClaimEvidenceCreate,
    ClaimEvidenceResponse,
    ClaimResponse,
    ClaimUpdate,
    EvidenceGap,
    EvidenceMatrix,
    EvidenceMatrixRow,
    EvidenceOverview,
)
from services.audit_service import audit
from services.evidence_rules import compute_evidence_gaps

router = APIRouter(tags=["claims"])


async def _get_claim(case: Case, claim_id: str, db: AsyncSession) -> Claim:
    cid = parse_uuid(claim_id, "claim id")
    claim = (await db.execute(select(Claim).where(Claim.id == cid, Claim.case_id == case.id))).scalar_one_or_none()
    if claim is None:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claim


async def _evidence_counts(claim_ids: list[uuid.UUID], db: AsyncSession) -> dict[uuid.UUID, int]:
    if not claim_ids:
        return {}
    rows = (
        await db.execute(
            select(ClaimEvidence.claim_id, func.count()).where(ClaimEvidence.claim_id.in_(claim_ids)).group_by(ClaimEvidence.claim_id)
        )
    ).all()
    return {cid: n for cid, n in rows}


def _claim_response(claim: Claim, count: int) -> ClaimResponse:
    return ClaimResponse(**ClaimResponse.model_validate(claim).model_dump(exclude={"evidence_count"}), evidence_count=count)


async def _evidence_rows(case: Case, db: AsyncSession, claim_id: uuid.UUID | None = None) -> list[ClaimEvidenceResponse]:
    stmt = (
        select(ClaimEvidence, Document)
        .join(Document, Document.id == ClaimEvidence.document_id)
        .join(Claim, Claim.id == ClaimEvidence.claim_id)
        .where(Claim.case_id == case.id, Document.case_id == case.id)
    )
    if claim_id is not None:
        stmt = stmt.where(ClaimEvidence.claim_id == claim_id)
    rows = (await db.execute(stmt.order_by(Document.doc_date))).all()
    return [
        ClaimEvidenceResponse(
            id=link.id,
            created_at=link.created_at,
            updated_at=link.updated_at,
            claim_id=link.claim_id,
            document_id=link.document_id,
            relevance_note=link.relevance_note,
            added_by_ai=link.added_by_ai,
            document_filename=doc.filename,
            document_type=doc.document_type,
            document_date=doc.doc_date,
            evidence_number=doc.evidence_number,
        )
        for link, doc in rows
    ]


@router.get("/cases/{case_id}/claims", response_model=list[ClaimResponse])
async def list_claims(case_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[ClaimResponse]:
    case = await get_case_for_user(case_id, user, db)
    claims = (await db.execute(select(Claim).where(Claim.case_id == case.id).order_by(Claim.claim_ref))).scalars().all()
    counts = await _evidence_counts([c.id for c in claims], db)
    return [_claim_response(c, counts.get(c.id, 0)) for c in claims]


@router.post("/cases/{case_id}/claims", response_model=ClaimResponse, status_code=status.HTTP_201_CREATED)
async def create_claim(
    case_id: str, body: ClaimCreate, request: Request, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> ClaimResponse:
    case = await get_case_for_user(case_id, user, db)
    claim = Claim(id=uuid.uuid4(), case_id=case.id, **body.model_dump())
    db.add(claim)
    audit(db, user=user, action="claim.create", resource_type="claim", resource_id=claim.id, request=request)
    await db.commit()
    await db.refresh(claim)
    return _claim_response(claim, 0)


@router.get("/cases/{case_id}/claims/{claim_id}", response_model=ClaimResponse)
async def get_claim(
    case_id: str, claim_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> ClaimResponse:
    case = await get_case_for_user(case_id, user, db)
    claim = await _get_claim(case, claim_id, db)
    counts = await _evidence_counts([claim.id], db)
    return _claim_response(claim, counts.get(claim.id, 0))


@router.patch("/cases/{case_id}/claims/{claim_id}", response_model=ClaimResponse)
async def update_claim(
    case_id: str,
    claim_id: str,
    body: ClaimUpdate,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ClaimResponse:
    case = await get_case_for_user(case_id, user, db)
    claim = await _get_claim(case, claim_id, db)
    changes = body.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(claim, key, value)
    audit(db, user=user, action="claim.update", resource_type="claim", resource_id=claim.id, details={"fields": list(changes)}, request=request)
    await db.commit()
    await db.refresh(claim)
    counts = await _evidence_counts([claim.id], db)
    return _claim_response(claim, counts.get(claim.id, 0))


@router.delete("/cases/{case_id}/claims/{claim_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_claim(
    case_id: str, claim_id: str, request: Request, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> Response:
    case = await get_case_for_user(case_id, user, db)
    claim = await _get_claim(case, claim_id, db)
    await db.delete(claim)
    audit(db, user=user, action="claim.delete", resource_type="claim", resource_id=claim.id, request=request)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/cases/{case_id}/claims/{claim_id}/evidence", response_model=list[ClaimEvidenceResponse])
async def get_claim_evidence(
    case_id: str, claim_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[ClaimEvidenceResponse]:
    case = await get_case_for_user(case_id, user, db)
    claim = await _get_claim(case, claim_id, db)
    return await _evidence_rows(case, db, claim.id)


@router.post("/cases/{case_id}/claims/{claim_id}/evidence", response_model=ClaimEvidenceResponse, status_code=status.HTTP_201_CREATED)
async def link_evidence(
    case_id: str,
    claim_id: str,
    body: ClaimEvidenceCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ClaimEvidenceResponse:
    case = await get_case_for_user(case_id, user, db)
    claim = await _get_claim(case, claim_id, db)
    doc = (
        await db.execute(select(Document).where(Document.id == body.document_id, Document.case_id == case.id))
    ).scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=400, detail="Document does not belong to this case")
    link = ClaimEvidence(id=uuid.uuid4(), claim_id=claim.id, document_id=doc.id, relevance_note=body.relevance_note, added_by_ai=False)
    db.add(link)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Document already linked to this claim") from exc
    rows = await _evidence_rows(case, db, claim.id)
    return next(r for r in rows if r.id == link.id)


@router.delete("/cases/{case_id}/claims/{claim_id}/evidence/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unlink_evidence(
    case_id: str, claim_id: str, evidence_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> Response:
    case = await get_case_for_user(case_id, user, db)
    claim = await _get_claim(case, claim_id, db)
    eid = parse_uuid(evidence_id, "evidence id")
    link = (
        await db.execute(select(ClaimEvidence).where(ClaimEvidence.id == eid, ClaimEvidence.claim_id == claim.id))
    ).scalar_one_or_none()
    if link is not None:
        await db.delete(link)
        await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/cases/{case_id}/evidence-matrix", response_model=EvidenceMatrix)
async def evidence_matrix(case_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> EvidenceMatrix:
    """Claim × document matrix: rows are documents linked to at least one claim."""
    case = await get_case_for_user(case_id, user, db)
    claims = (await db.execute(select(Claim).where(Claim.case_id == case.id).order_by(Claim.claim_ref))).scalars().all()
    counts = await _evidence_counts([c.id for c in claims], db)
    links = await _evidence_rows(case, db)
    rows: dict[uuid.UUID, EvidenceMatrixRow] = {}
    for link in links:
        row = rows.get(link.document_id)
        if row is None:
            row = EvidenceMatrixRow(
                document_id=link.document_id,
                filename=link.document_filename or "",
                document_type=link.document_type,  # type: ignore[arg-type]
                doc_date=link.document_date,
                evidence_number=link.evidence_number,
                claim_links={},
            )
            rows[link.document_id] = row
        row.claim_links[str(link.claim_id)] = link.relevance_note or "linked"
    ordered = sorted(rows.values(), key=lambda r: (r.doc_date is None, r.doc_date, r.filename))
    return EvidenceMatrix(claims=[_claim_response(c, counts.get(c.id, 0)) for c in claims], rows=ordered)


@router.get("/cases/{case_id}/evidence", response_model=EvidenceOverview)
async def evidence_overview(case_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> EvidenceOverview:
    case = await get_case_for_user(case_id, user, db)
    evidence = await _evidence_rows(case, db)
    gaps = await compute_evidence_gaps(case.id, db)
    total_docs = (await db.execute(select(func.count()).select_from(Document).where(Document.case_id == case.id))).scalar_one()
    linked_docs = len({e.document_id for e in evidence})
    return EvidenceOverview(
        evidence=evidence,
        gaps=[
            EvidenceGap(
                claim_id=g.claim_id,
                claim_ref=g.claim_ref,
                claim_type=g.claim_type,
                missing_document_types=g.missing,
                message=" ".join(g.messages),
            )
            for g in gaps
        ],
        unlinked_documents=total_docs - linked_docs,
    )
