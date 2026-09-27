from __future__ import annotations

import uuid
from decimal import Decimal
from enum import Enum

from sqlalchemy import ForeignKey, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin, enum_column


class CaseStatus(str, Enum):
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"
    ARCHIVED = "ARCHIVED"


class ArbitrationInstitutionEnum(str, Enum):
    ICC = "ICC"
    SIAC = "SIAC"
    LCIA = "LCIA"
    HKIAC = "HKIAC"
    ICDR = "ICDR"
    UNCITRAL = "UNCITRAL"
    ICSID = "ICSID"
    OTHER = "OTHER"


class Case(Base, TimestampMixin):
    __tablename__ = "cases"

    org_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    institution: Mapped[ArbitrationInstitutionEnum] = mapped_column(
        enum_column(ArbitrationInstitutionEnum, "arbitrationinstitutionenum"),
        nullable=False,
        default=ArbitrationInstitutionEnum.ICC,
    )
    seat: Mapped[str | None] = mapped_column(String(255), nullable=True)
    governing_law: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language: Mapped[str] = mapped_column(String(50), nullable=False, default="English")
    status: Mapped[CaseStatus] = mapped_column(enum_column(CaseStatus, "casestatus"), nullable=False, default=CaseStatus.ACTIVE)
    amount_in_dispute: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    case_ref: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
