from __future__ import annotations

import uuid
from enum import Enum

from sqlalchemy import ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin, enum_column


class ProcedureStage(str, Enum):
    ARBITRATION_AGREEMENT = "ARBITRATION_AGREEMENT"
    PRE_ARBITRATION = "PRE_ARBITRATION"
    NOTICE_OF_ARBITRATION = "NOTICE_OF_ARBITRATION"
    RESPONSE = "RESPONSE"
    TRIBUNAL_CONSTITUTION = "TRIBUNAL_CONSTITUTION"
    PRELIMINARY_STAGE = "PRELIMINARY_STAGE"
    TERMS_OF_REFERENCE = "TERMS_OF_REFERENCE"
    PLEADINGS = "PLEADINGS"
    DOCUMENT_PRODUCTION = "DOCUMENT_PRODUCTION"
    WITNESS_STATEMENTS = "WITNESS_STATEMENTS"
    EXPERT_REPORTS = "EXPERT_REPORTS"
    PROCEDURAL_HEARINGS = "PROCEDURAL_HEARINGS"
    EVIDENTIARY_HEARING = "EVIDENTIARY_HEARING"
    POST_HEARING = "POST_HEARING"
    CLOSING = "CLOSING"
    AWARD = "AWARD"
    CORRECTION_INTERPRETATION = "CORRECTION_INTERPRETATION"
    RECOGNITION_ENFORCEMENT = "RECOGNITION_ENFORCEMENT"
    ANNULMENT = "ANNULMENT"


# Canonical ordering of stages, used for checklists and comparison tables.
STAGE_ORDER: list[ProcedureStage] = list(ProcedureStage)


class ArbitrationRule(Base, TimestampMixin):
    __tablename__ = "arbitration_rules"

    institution_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("arbitration_institutions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stage: Mapped[ProcedureStage] = mapped_column(enum_column(ProcedureStage, "procedurestage"), nullable=False, index=True)
    article_number: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    rule_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    typical_deadline_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
