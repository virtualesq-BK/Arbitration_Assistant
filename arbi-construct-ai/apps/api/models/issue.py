from __future__ import annotations

import uuid
from enum import Enum

from sqlalchemy import ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin, enum_column


class IssueSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class IssueStatus(str, Enum):
    OPEN = "OPEN"
    UNDER_REVIEW = "UNDER_REVIEW"
    RESOLVED = "RESOLVED"


class Issue(Base, TimestampMixin):
    __tablename__ = "issues"

    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    severity: Mapped[IssueSeverity] = mapped_column(enum_column(IssueSeverity, "issueseverity"), nullable=False, default=IssueSeverity.MEDIUM)
    status: Mapped[IssueStatus] = mapped_column(enum_column(IssueStatus, "issuestatus"), nullable=False, default=IssueStatus.OPEN)
