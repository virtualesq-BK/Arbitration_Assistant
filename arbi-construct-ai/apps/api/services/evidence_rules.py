"""Deterministic evidence-gap heuristics per claim type.

These are checklists of document categories that construction arbitration practitioners
typically expect to see supporting a given claim head. A missing category is reported as a
POTENTIAL_EVIDENCE_GAP — never as a conclusion that the claim fails.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.claim import Claim, ClaimType
from models.claim_evidence import ClaimEvidence
from models.document import Document, DocumentType

EXPECTED_EVIDENCE: dict[ClaimType, list[tuple[DocumentType, str]]] = {
    ClaimType.EOT: [
        (DocumentType.NOTICE, "contemporaneous notice of delay / claim (time-bar compliance)"),
        (DocumentType.PROGRAMME, "baseline and updated programmes for delay analysis"),
        (DocumentType.DAILY_REPORT, "site records evidencing the delay events"),
        (DocumentType.CLAIM_SUBMISSION, "fully particularised EOT claim submission"),
    ],
    ClaimType.LD_DEFENCE: [
        (DocumentType.CONTRACT, "liquidated damages clause and completion dates"),
        (DocumentType.PROGRAMME, "programme evidence of employer-caused delay"),
        (DocumentType.NOTICE, "notices supporting entitlement to time"),
    ],
    ClaimType.VARIATION: [
        (DocumentType.VARIATION_ORDER, "instructed variation orders"),
        (DocumentType.SITE_INSTRUCTION, "site instructions changing the scope"),
        (DocumentType.CONTRACT, "variation / valuation clauses"),
    ],
    ClaimType.PAYMENT: [
        (DocumentType.PAYMENT_CERTIFICATE, "interim / final payment certificates"),
        (DocumentType.INVOICE, "invoices or payment applications"),
        (DocumentType.CONTRACT, "payment terms"),
    ],
    ClaimType.DISRUPTION: [
        (DocumentType.DAILY_REPORT, "resource / productivity records"),
        (DocumentType.PROGRAMME, "planned vs. as-built sequencing"),
        (DocumentType.EXPERT_REPORT, "disruption / productivity analysis"),
    ],
    ClaimType.SUSPENSION: [
        (DocumentType.NOTICE, "suspension notice"),
        (DocumentType.LETTER, "correspondence on the suspension"),
    ],
    ClaimType.TERMINATION: [
        (DocumentType.NOTICE, "termination notice(s)"),
        (DocumentType.CONTRACT, "termination clause"),
    ],
    ClaimType.DEFECT: [
        (DocumentType.TECHNICAL_REPORT, "defect inspection / technical report"),
        (DocumentType.PHOTOGRAPH, "photographic records of defects"),
    ],
    ClaimType.OTHER: [],
}


@dataclass
class ClaimGap:
    claim_id: uuid.UUID
    claim_ref: str
    claim_type: ClaimType
    missing: list[DocumentType]
    messages: list[str]


async def compute_evidence_gaps(case_id: uuid.UUID, db: AsyncSession, claim_id: uuid.UUID | None = None) -> list[ClaimGap]:
    stmt = select(Claim).where(Claim.case_id == case_id)
    if claim_id is not None:
        stmt = stmt.where(Claim.id == claim_id)
    claims = (await db.execute(stmt.order_by(Claim.claim_ref))).scalars().all()
    if not claims:
        return []

    link_rows = (
        await db.execute(
            select(ClaimEvidence.claim_id, Document.document_type)
            .join(Document, Document.id == ClaimEvidence.document_id)
            .where(ClaimEvidence.claim_id.in_([c.id for c in claims]), Document.case_id == case_id)
        )
    ).all()
    linked: dict[uuid.UUID, set[DocumentType]] = {}
    for cid, dtype in link_rows:
        linked.setdefault(cid, set()).add(dtype)

    gaps: list[ClaimGap] = []
    for claim in claims:
        have = linked.get(claim.id, set())
        missing: list[DocumentType] = []
        messages: list[str] = []
        if not have:
            messages.append(f"{claim.claim_ref}: no supporting documents are linked to this claim yet.")
        for dtype, why in EXPECTED_EVIDENCE.get(claim.claim_type, []):
            if dtype not in have:
                missing.append(dtype)
                messages.append(f"{claim.claim_ref}: no linked {dtype.value.replace('_', ' ').lower()} — {why}.")
        if missing or not have:
            gaps.append(ClaimGap(claim.id, claim.claim_ref, claim.claim_type, missing, messages))
    return gaps
