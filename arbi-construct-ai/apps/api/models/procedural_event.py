from __future__ import annotations

import uuid
from datetime import date
from enum import Enum

from sqlalchemy import Boolean, Date, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin, enum_column


class ProceduralEventStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    OVERDUE = "OVERDUE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ProceduralEvent(Base, TimestampMixin):
    __tablename__ = "procedural_events"

    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)  # usually a ProcedureStage value
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_rule: Mapped[str | None] = mapped_column(String(255), nullable=True)  # e.g. "ICC Rules 2021"
    rule_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)  # e.g. "Art. 23"
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[ProceduralEventStatus] = mapped_column(
        enum_column(ProceduralEventStatus, "proceduraleventstatus"), nullable=False, default=ProceduralEventStatus.PENDING
    )
    responsible_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_ai_suggested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_confirmation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
