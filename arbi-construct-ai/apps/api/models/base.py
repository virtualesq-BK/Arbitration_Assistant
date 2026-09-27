"""Declarative base, common column types and the TimestampMixin."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, DateTime, Enum as SAEnum, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

try:  # pgvector is required in production; tests on SQLite fall back gracefully.
    from pgvector.sqlalchemy import Vector as _PgVector

    def VectorType(dim: int) -> Any:  # noqa: N802 - mimic a type constructor
        return _PgVector(dim)

except ImportError:  # pragma: no cover - only when pgvector is not installed
    def VectorType(dim: int) -> Any:  # noqa: N802
        return JSON()


# JSON that becomes JSONB on PostgreSQL but still works on SQLite for tests.
JSONType = JSON().with_variant(JSONB(), "postgresql")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def enum_column(enum_cls: type[enum.Enum], name: str) -> SAEnum:
    """Store enums as VARCHAR (non-native) so new members never need an ALTER TYPE migration."""
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=False,
        length=40,
        values_callable=lambda e: [m.value for m in e],
        validate_strings=True,
    )


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now(), onupdate=utcnow
    )
