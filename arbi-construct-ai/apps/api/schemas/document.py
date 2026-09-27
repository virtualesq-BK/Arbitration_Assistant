from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from pydantic import BaseModel

from models.document import ConfidentialityLevel, DocumentType, PrivilegeStatus, ProcessingStatus
from schemas.common import TimestampedResponse


class DocumentUpdate(BaseModel):
    document_type: DocumentType | None = None
    author: str | None = None
    recipient: str | None = None
    doc_date: date | None = None
    language: str | None = None
    confidentiality_level: ConfidentialityLevel | None = None
    privilege_status: PrivilegeStatus | None = None
    evidence_number: str | None = None
    summary: str | None = None


class DocumentResponse(TimestampedResponse):
    case_id: uuid.UUID
    org_id: uuid.UUID
    filename: str
    file_size: int | None = None
    mime_type: str | None = None
    document_type: DocumentType
    author: str | None = None
    recipient: str | None = None
    doc_date: date | None = None
    language: str | None = None
    confidentiality_level: ConfidentialityLevel
    privilege_status: PrivilegeStatus
    evidence_number: str | None = None
    file_hash: str | None = None
    ocr_status: ProcessingStatus
    classification_status: ProcessingStatus
    summary: str | None = None
    metadata_json: dict[str, Any] | None = None


class DocumentDetail(DocumentResponse):
    ocr_text: str | None = None
    download_url: str | None = None
    download_url_expires_in: int | None = None
    chunk_count: int = 0
