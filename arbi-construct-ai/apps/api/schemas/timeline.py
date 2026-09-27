from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, Field

from schemas.common import TimestampedResponse


class TimelineEventCreate(BaseModel):
    event_date: date
    description: str = Field(min_length=1)
    event_type: str = "GENERAL"
    source_document_id: uuid.UUID | None = None
    source_page: int | None = None
    source_excerpt: str | None = None


class TimelineEventResponse(TimestampedResponse):
    case_id: uuid.UUID
    event_date: date
    description: str
    event_type: str
    source_document_id: uuid.UUID | None = None
    source_document_filename: str | None = None
    source_page: int | None = None
    source_excerpt: str | None = None
    is_ai_extracted: bool = False
