from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field

from services.rag_service import Corpus


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    corpus: Corpus = Corpus.CASE
    case_id: uuid.UUID | None = None
    institution: str | None = None
    mode: Literal["keyword", "semantic", "hybrid"] = "hybrid"
    top_k: int = Field(default=10, ge=1, le=50)


class SearchHit(BaseModel):
    text: str
    source_name: str
    source_url: str | None = None
    institution: str | None = None
    rule_version: str | None = None
    document_id: str | None = None
    chunk_index: int | None = None
    confidence: float


class SearchResponse(BaseModel):
    query: str
    corpus: Corpus
    mode: str
    results: list[SearchHit]
    source_not_found: bool
