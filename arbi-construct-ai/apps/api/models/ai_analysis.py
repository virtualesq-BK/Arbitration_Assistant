from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, JSONType, TimestampMixin


class AIAnalysis(Base, TimestampMixin):
    """Audit record of every AI agent invocation (prompt version, sources, output)."""

    __tablename__ = "ai_analyses"

    case_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("cases.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    agent: Mapped[str] = mapped_column(String(100), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    query: Mapped[str | None] = mapped_column(Text, nullable=True)
    retrieved_sources_json: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONType, nullable=True)
    output_json: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)
