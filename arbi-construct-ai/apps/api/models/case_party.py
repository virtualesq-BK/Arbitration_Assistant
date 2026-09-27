from __future__ import annotations

import uuid
from enum import Enum

from sqlalchemy import ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin, enum_column


class PartyRole(str, Enum):
    EMPLOYER = "EMPLOYER"
    CONTRACTOR = "CONTRACTOR"
    SUBCONTRACTOR = "SUBCONTRACTOR"
    TRIBUNAL_MEMBER = "TRIBUNAL_MEMBER"
    RESPONDENT = "RESPONDENT"
    CLAIMANT = "CLAIMANT"


class CaseParty(Base, TimestampMixin):
    __tablename__ = "case_parties"

    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    role: Mapped[PartyRole] = mapped_column(enum_column(PartyRole, "partyrole"), nullable=False)
    counsel: Mapped[str | None] = mapped_column(String(500), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
