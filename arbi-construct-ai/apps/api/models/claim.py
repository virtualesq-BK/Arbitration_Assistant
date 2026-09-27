from __future__ import annotations

import uuid
from decimal import Decimal
from enum import Enum

from sqlalchemy import ForeignKey, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin, enum_column


class ClaimType(str, Enum):
    EOT = "EOT"
    LD_DEFENCE = "LD_DEFENCE"
    VARIATION = "VARIATION"
    PAYMENT = "PAYMENT"
    DISRUPTION = "DISRUPTION"
    SUSPENSION = "SUSPENSION"
    TERMINATION = "TERMINATION"
    DEFECT = "DEFECT"
    OTHER = "OTHER"


class ClaimStatus(str, Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    DISPUTED = "DISPUTED"
    IN_ARBITRATION = "IN_ARBITRATION"
    SETTLED = "SETTLED"
    WITHDRAWN = "WITHDRAWN"


class Claim(Base, TimestampMixin):
    __tablename__ = "claims"

    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    claim_ref: Mapped[str] = mapped_column(String(100), nullable=False)
    claim_type: Mapped[ClaimType] = mapped_column(enum_column(ClaimType, "claimtype"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    quantum: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    status: Mapped[ClaimStatus] = mapped_column(enum_column(ClaimStatus, "claimstatus"), nullable=False, default=ClaimStatus.DRAFT)
    contract_clause: Mapped[str | None] = mapped_column(String(255), nullable=True)
