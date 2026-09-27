from __future__ import annotations

import uuid
from decimal import Decimal

from pydantic import BaseModel, Field

from models.case import ArbitrationInstitutionEnum, CaseStatus
from models.case_party import PartyRole
from schemas.common import TimestampedResponse


class CaseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    institution: ArbitrationInstitutionEnum = ArbitrationInstitutionEnum.ICC
    seat: str | None = None
    governing_law: str | None = None
    language: str = "English"
    amount_in_dispute: Decimal | None = None
    currency: str | None = Field(default=None, max_length=3)
    case_ref: str | None = None


class CaseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = None
    institution: ArbitrationInstitutionEnum | None = None
    seat: str | None = None
    governing_law: str | None = None
    language: str | None = None
    status: CaseStatus | None = None
    amount_in_dispute: Decimal | None = None
    currency: str | None = Field(default=None, max_length=3)
    case_ref: str | None = None


class CaseResponse(TimestampedResponse):
    org_id: uuid.UUID
    title: str
    description: str | None = None
    institution: ArbitrationInstitutionEnum
    seat: str | None = None
    governing_law: str | None = None
    language: str
    status: CaseStatus
    amount_in_dispute: Decimal | None = None
    currency: str | None = None
    case_ref: str | None = None


class CaseStats(BaseModel):
    documents: int = 0
    claims: int = 0
    timeline_events: int = 0
    issues: int = 0
    open_procedural_events: int = 0


class CaseWithStats(CaseResponse):
    stats: CaseStats = CaseStats()


class CasePartyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=500)
    role: PartyRole
    counsel: str | None = None
    country: str | None = None
    notes: str | None = None


class CasePartyResponse(TimestampedResponse):
    case_id: uuid.UUID
    name: str
    role: PartyRole
    counsel: str | None = None
    country: str | None = None
    notes: str | None = None


class CaseDetail(CaseWithStats):
    parties: list[CasePartyResponse] = []
