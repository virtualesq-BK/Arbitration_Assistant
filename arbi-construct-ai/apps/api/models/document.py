from __future__ import annotations

import uuid
from datetime import date
from enum import Enum
from typing import Any

from sqlalchemy import BigInteger, Date, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, JSONType, TimestampMixin, enum_column


class DocumentType(str, Enum):
    CONTRACT = "CONTRACT"
    AMENDMENT = "AMENDMENT"
    VARIATION_ORDER = "VARIATION_ORDER"
    NOTICE = "NOTICE"
    LETTER = "LETTER"
    EMAIL = "EMAIL"
    MEETING_MINUTES = "MEETING_MINUTES"
    DAILY_REPORT = "DAILY_REPORT"
    PROGRAMME = "PROGRAMME"
    PAYMENT_CERTIFICATE = "PAYMENT_CERTIFICATE"
    INVOICE = "INVOICE"
    CHANGE_ORDER = "CHANGE_ORDER"
    SITE_INSTRUCTION = "SITE_INSTRUCTION"
    TECHNICAL_REPORT = "TECHNICAL_REPORT"
    EXPERT_REPORT = "EXPERT_REPORT"
    WITNESS_STATEMENT = "WITNESS_STATEMENT"
    PHOTOGRAPH = "PHOTOGRAPH"
    DRAWING = "DRAWING"
    SPECIFICATION = "SPECIFICATION"
    CLAIM_SUBMISSION = "CLAIM_SUBMISSION"
    RESPONSE = "RESPONSE"
    ARBITRATION_FILING = "ARBITRATION_FILING"
    PROCEDURAL_ORDER = "PROCEDURAL_ORDER"
    AWARD = "AWARD"
    OTHER = "OTHER"


class ConfidentialityLevel(str, Enum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    HIGHLY_CONFIDENTIAL = "HIGHLY_CONFIDENTIAL"
    PRIVILEGED = "PRIVILEGED"
    ATTORNEY_WORK_PRODUCT = "ATTORNEY_WORK_PRODUCT"


class ProcessingStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    NOT_REQUIRED = "NOT_REQUIRED"


class PrivilegeStatus(str, Enum):
    """User-classified privilege status. The AI may only ever suggest POTENTIALLY_PRIVILEGED."""

    NOT_PRIVILEGED = "NOT_PRIVILEGED"
    POTENTIALLY_PRIVILEGED = "POTENTIALLY_PRIVILEGED"
    PRIVILEGED = "PRIVILEGED"
    UNREVIEWED = "UNREVIEWED"


class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    org_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    s3_key: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    document_type: Mapped[DocumentType] = mapped_column(
        enum_column(DocumentType, "documenttype"), nullable=False, default=DocumentType.OTHER
    )
    author: Mapped[str | None] = mapped_column(String(500), nullable=True)
    recipient: Mapped[str | None] = mapped_column(String(500), nullable=True)
    doc_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    language: Mapped[str | None] = mapped_column(String(50), nullable=True, default="en")
    confidentiality_level: Mapped[ConfidentialityLevel] = mapped_column(
        enum_column(ConfidentialityLevel, "confidentialitylevel"), nullable=False, default=ConfidentialityLevel.CONFIDENTIAL
    )
    privilege_status: Mapped[PrivilegeStatus] = mapped_column(
        enum_column(PrivilegeStatus, "privilegestatus"), nullable=False, default=PrivilegeStatus.UNREVIEWED
    )
    evidence_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_status: Mapped[ProcessingStatus] = mapped_column(
        enum_column(ProcessingStatus, "processingstatus"), nullable=False, default=ProcessingStatus.PENDING
    )
    classification_status: Mapped[ProcessingStatus] = mapped_column(
        enum_column(ProcessingStatus, "processingstatus"), nullable=False, default=ProcessingStatus.PENDING
    )
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)
