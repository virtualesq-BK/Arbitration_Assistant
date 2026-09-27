from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin, VectorType
from models.document_chunk import EMBEDDING_DIM


class KnowledgeChunk(Base, TimestampMixin):
    """Tenant-independent knowledge (RULES and CONSTRUCTION corpora).

    Kept in a separate table from DocumentChunk so that case documents can never
    leak into the shared corpora (and vice versa).
    corpus: "rules" | "construction"
    """

    __tablename__ = "knowledge_chunks"

    corpus: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    source_name: Mapped[str] = mapped_column(String(500), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    institution: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    rule_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    article_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    rule_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("arbitration_rules.id", ondelete="CASCADE"), nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Any | None] = mapped_column(VectorType(EMBEDDING_DIM), nullable=True)
