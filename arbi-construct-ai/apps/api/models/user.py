from __future__ import annotations

import uuid
from enum import Enum

from sqlalchemy import Boolean, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin, enum_column


class UserRole(str, Enum):
    ORG_ADMIN = "ORG_ADMIN"
    CASE_MANAGER = "CASE_MANAGER"
    LAWYER = "LAWYER"
    LEGAL_TEAM = "LEGAL_TEAM"
    CLAIMS_TEAM = "CLAIMS_TEAM"
    VIEWER = "VIEWER"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    role: Mapped[UserRole] = mapped_column(enum_column(UserRole, "userrole"), nullable=False, default=UserRole.VIEWER)
    org_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
