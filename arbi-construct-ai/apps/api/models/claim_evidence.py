from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin


class ClaimEvidence(Base, TimestampMixin):
    __tablename__ = "claim_evidence"
    __table_args__ = (UniqueConstraint("claim_id", "document_id", name="uq_claim_document"),)

    claim_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("claims.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    relevance_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    added_by_ai: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
