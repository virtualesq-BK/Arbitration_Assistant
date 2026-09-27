from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from schemas.common import TimestampedResponse

FindingLabel = Literal[
    "FACT",
    "SOURCE_BASED_INFO",
    "AI_SUMMARY",
    "POTENTIAL_ISSUE",
    "POTENTIAL_EVIDENCE_GAP",
    "REQUIRES_HUMAN_REVIEW",
]

AI_DISCLAIMER = (
    "AI-assisted analysis. Final legal judgment must be performed by qualified legal professionals."
)


class FindingSchema(BaseModel):
    label: FindingLabel
    content: str
    citations: list[str] = []


class AgentResponseSchema(BaseModel):
    summary: str
    findings: list[FindingSchema] = []
    evidence_gaps: list[str] = []
    requires_human_review: list[str] = []
    sources: list[dict[str, Any]] = []
    model: str
    agent: str
    disclaimer: str = AI_DISCLAIMER
    analysis_id: uuid.UUID | None = None


class ResearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=4000)
    institution: str | None = None
    case_id: uuid.UUID | None = None


class ProcedureQuery(BaseModel):
    institution: str
    stage: str | None = None


class AIAnalysisResponse(TimestampedResponse):
    case_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None
    agent: str
    model_name: str
    prompt_version: str
    query: str | None = None
    retrieved_sources_json: list[dict[str, Any]] | None = None
    output_json: dict[str, Any] | None = None


class AIAnalysisListItem(BaseModel):
    id: uuid.UUID
    agent: str
    model_name: str
    created_at: datetime
    summary: str | None = None
