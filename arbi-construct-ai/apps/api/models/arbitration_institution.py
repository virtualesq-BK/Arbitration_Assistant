from __future__ import annotations

from datetime import date

from sqlalchemy import Date, String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin


class ArbitrationInstitution(Base, TimestampMixin):
    __tablename__ = "arbitration_institutions"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    short_name: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    rules_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    rules_effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    rules_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    source_tier: Mapped[str] = mapped_column(String(20), nullable=False, default="official")  # official | institutional | secondary
