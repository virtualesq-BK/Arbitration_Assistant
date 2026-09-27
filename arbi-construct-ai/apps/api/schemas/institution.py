from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel

from models.arbitration_rule import ProcedureStage
from models.procedural_event import ProceduralEventStatus
from schemas.ai import AgentResponseSchema
from schemas.common import TimestampedResponse


class InstitutionResponse(TimestampedResponse):
    name: str
    short_name: str
    website: str | None = None
    rules_version: str | None = None
    rules_effective_date: date | None = None
    rules_url: str | None = None
    source_tier: str


class RuleResponse(TimestampedResponse):
    institution_id: uuid.UUID
    stage: ProcedureStage
    article_number: str
    title: str
    summary: str
    source_url: str | None = None
    rule_version: str | None = None
    notes: str | None = None
    typical_deadline_days: int | None = None


class InstitutionWithRules(InstitutionResponse):
    rules: list[RuleResponse] = []


class ProcedureStageResponse(BaseModel):
    institution: InstitutionResponse
    stage: ProcedureStage
    rules: list[RuleResponse]
    source_not_found: bool
    ai_guidance: AgentResponseSchema | None = None
    disclaimer: str


class ComparisonCell(BaseModel):
    article_number: str
    title: str
    source_url: str | None = None
    rule_version: str | None = None


class ComparisonRow(BaseModel):
    stage: ProcedureStage
    cells: dict[str, list[ComparisonCell]]  # institution short_name -> rules


class ComparisonTable(BaseModel):
    institutions: list[InstitutionResponse]
    rows: list[ComparisonRow]


class ProceduralEventCreate(BaseModel):
    event_type: str
    title: str | None = None
    due_date: date | None = None
    source_rule: str | None = None
    rule_reference: str | None = None
    source_url: str | None = None
    notes: str | None = None
    responsible_user_id: uuid.UUID | None = None


class ProceduralEventUpdate(BaseModel):
    status: ProceduralEventStatus | None = None
    due_date: date | None = None
    notes: str | None = None
    responsible_user_id: uuid.UUID | None = None
    requires_confirmation: bool | None = None


class ProceduralEventResponse(TimestampedResponse):
    case_id: uuid.UUID
    event_type: str
    title: str | None = None
    due_date: date | None = None
    source_rule: str | None = None
    rule_reference: str | None = None
    source_url: str | None = None
    status: ProceduralEventStatus
    responsible_user_id: uuid.UUID | None = None
    notes: str | None = None
    is_ai_suggested: bool
    requires_confirmation: bool
