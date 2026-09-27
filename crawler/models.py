"""Pydantic models for crawl output records."""

from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field, HttpUrl, field_validator


class CrawlRecord(BaseModel):
    institution: Literal["ICC", "SIAC", "LCIA", "HKIAC", "ICSID", "ICDR"]
    url: str
    content_type: Literal["html", "pdf"]
    title: str
    published_date: Optional[str] = None  # ISO8601 string or null
    language: str = "en"
    text: str
    pdf_path: Optional[str] = None
    pdf_sha256: Optional[str] = None
    pdf_pages: Optional[int] = None
    needs_ocr: bool = False
    crawled_at: str  # ISO8601 UTC

    @field_validator("url")
    @classmethod
    def url_must_be_http(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError(f"URL must start with http/https: {v!r}")
        return v

    @field_validator("crawled_at", "published_date", mode="before")
    @classmethod
    def coerce_datetime(cls, v: object) -> Optional[str]:
        if v is None:
            return None
        if isinstance(v, datetime):
            return v.isoformat()
        return str(v)

    def model_dump_jsonl(self) -> str:
        """Return a single-line JSON string suitable for JSONL output."""
        return self.model_dump_json()
