from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from models.claim import ClaimStatus, ClaimType
from models.document import DocumentType
from models.issue import IssueSeverity, IssueStatus
from schemas.common import TimestampedResponse


class ClaimCreate(BaseModel):
    claim_ref: str = Field(min_length=1, max_length=100)
    claim_type: ClaimType
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    quantum: Decimal | None = None
    currency: str | None = Field(default=None, max_length=3)
    status: ClaimStatus = ClaimStatus.DRAFT
    contract_clause: str | None = None


class ClaimUpdate(BaseModel):
    claim_ref: str | None = None
    claim_type: ClaimType | None = None
    title: str | None = None
    description: str | None = None
    quantum: Decimal | None = None
    currency: str | None = Field(default=None, max_length=3)
    status: ClaimStatus | None = None
    contract_clause: str | None = None


class ClaimResponse(TimestampedResponse):
    case_id: uuid.UUID
    claim_ref: str
    claim_type: ClaimType
    title: str
    description: str | None = None
    quantum: Decimal | None = None
    currency: str | None = None
    status: ClaimStatus
    contract_clause: str | None = None
    evidence_count: int = 0


class ClaimEvidenceCreate(BaseModel):
    document_id: uuid.UUID
    relevance_note: str | None = None


class ClaimEvidenceResponse(TimestampedResponse):
    claim_id: uuid.UUID
    document_id: uuid.UUID
    relevance_note: str | None = None
    added_by_ai: bool
    document_filename: str | None = None
    document_type: DocumentType | None = None
    document_date: date | None = None
    evidence_number: str | None = None


class EvidenceMatrixRow(BaseModel):
    document_id: uuid.UUID
    filename: str
    document_type: DocumentType
    doc_date: date | None = None
    evidence_number: str | None = None
    claim_links: dict[str, str | None]  # claim_id -> relevance note (None = not linked)


class EvidenceMatrix(BaseModel):
    claims: list[ClaimResponse]
    rows: list[EvidenceMatrixRow]


class EvidenceGap(BaseModel):
    claim_id: uuid.UUID
    claim_ref: str
    claim_type: ClaimType
    missing_document_types: list[DocumentType]
    message: str


class EvidenceOverview(BaseModel):
    evidence: list[ClaimEvidenceResponse]
    gaps: list[EvidenceGap]
    unlinked_documents: int


class IssueCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    category: str | None = None
    severity: IssueSeverity = IssueSeverity.MEDIUM
    status: IssueStatus = IssueStatus.OPEN


class IssueResponse(TimestampedResponse):
    case_id: uuid.UUID
    title: str
    description: str | None = None
    category: str | None = None
    severity: IssueSeverity
    status: IssueStatus
