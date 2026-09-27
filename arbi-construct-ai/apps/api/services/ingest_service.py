"""Text extraction, paragraph chunking and embedding of case documents and knowledge sources."""
from __future__ import annotations

import asyncio
import io
import logging
import re
import uuid

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from models.document import Document, ProcessingStatus
from models.document_chunk import DocumentChunk
from models.knowledge_chunk import KnowledgeChunk
from services.llm_service import LLMService, get_llm_service, is_zero_vector

logger = logging.getLogger(__name__)

MAX_CHUNK_CHARS = 1500
MIN_CHUNK_CHARS = 200


def chunk_text(text: str, max_chars: int = MAX_CHUNK_CHARS, min_chars: int = MIN_CHUNK_CHARS) -> list[str]:
    """Split on blank lines (paragraphs); merge short paragraphs and hard-split very long ones."""
    if not text or not text.strip():
        return []
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text.replace("\r\n", "\n")) if p.strip()]
    chunks: list[str] = []
    buffer = ""
    for para in paragraphs:
        while len(para) > max_chars:
            cut = para.rfind(". ", 0, max_chars)
            cut = cut + 1 if cut > max_chars // 2 else max_chars
            head, para = para[:cut].strip(), para[cut:].strip()
            if buffer:
                chunks.append(buffer)
                buffer = ""
            chunks.append(head)
        if not buffer:
            buffer = para
        elif len(buffer) < min_chars or len(buffer) + len(para) + 2 <= max_chars // 2:
            buffer = f"{buffer}\n\n{para}"
        else:
            chunks.append(buffer)
            buffer = para
    if buffer:
        chunks.append(buffer)
    return chunks


def _extract_pdf_text(data: bytes) -> str:
    try:
        from pypdf import PdfReader
        from pypdf.errors import PdfReadError
    except ImportError:
        logger.warning("pypdf not installed; PDF text extraction skipped")
        return ""
    try:
        reader = PdfReader(io.BytesIO(data))
        pages = [(page.extract_text() or "") for page in reader.pages]
    except (PdfReadError, ValueError, KeyError) as exc:
        logger.warning("PDF text extraction failed: %s", exc)
        return ""
    return "\n\n".join(p.strip() for p in pages if p.strip())


async def extract_text(data: bytes, mime_type: str | None, filename: str) -> str:
    """Best-effort text extraction. Scanned PDFs / images return '' (OCR is out of MVP scope)."""
    name = filename.lower()
    mime = (mime_type or "").lower()
    if mime.startswith("text/") or name.endswith((".txt", ".md", ".csv", ".eml", ".json", ".xml", ".html")):
        return data.decode("utf-8", errors="replace")
    if mime == "application/pdf" or name.endswith(".pdf"):
        return await asyncio.to_thread(_extract_pdf_text, data)
    return ""


async def index_document(db: AsyncSession, document: Document, llm: LLMService | None = None) -> int:
    """(Re)build DocumentChunk rows for a document from its ocr_text. Returns chunk count."""
    llm = llm or get_llm_service()
    await db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
    pieces = chunk_text(document.ocr_text or "")
    if not pieces:
        return 0
    header = f"[{document.document_type.value}] {document.filename}"
    vectors = await llm.embed([f"{header}\n{p}" for p in pieces])
    for idx, (piece, vec) in enumerate(zip(pieces, vectors)):
        db.add(
            DocumentChunk(
                id=uuid.uuid4(),
                document_id=document.id,
                chunk_index=idx,
                text=piece,
                embedding=None if is_zero_vector(vec) else vec,
                case_id=document.case_id,
                org_id=document.org_id,
            )
        )
    document.ocr_status = ProcessingStatus.COMPLETED
    return len(pieces)


async def index_knowledge(
    db: AsyncSession,
    *,
    corpus: str,
    source_name: str,
    text: str,
    source_url: str | None = None,
    institution: str | None = None,
    rule_version: str | None = None,
    article_number: str | None = None,
    rule_id: uuid.UUID | None = None,
    llm: LLMService | None = None,
) -> int:
    llm = llm or get_llm_service()
    pieces = chunk_text(text)
    if not pieces:
        return 0
    header = " ".join(p for p in (institution, rule_version, source_name, article_number) if p)
    vectors = await llm.embed([f"{header}\n{p}" for p in pieces])
    for idx, (piece, vec) in enumerate(zip(pieces, vectors)):
        db.add(
            KnowledgeChunk(
                id=uuid.uuid4(),
                corpus=corpus,
                source_name=source_name,
                source_url=source_url,
                institution=institution,
                rule_version=rule_version,
                article_number=article_number,
                rule_id=rule_id,
                chunk_index=idx,
                text=piece,
                embedding=None if is_zero_vector(vec) else vec,
            )
        )
    return len(pieces)
