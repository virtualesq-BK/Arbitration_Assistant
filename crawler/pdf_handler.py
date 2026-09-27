"""PDF download, storage, and text extraction."""

import hashlib
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def save_pdf(data: bytes, institution: str, sha256: str, base_dir: Path) -> Path:
    """Save PDF bytes to data/pdfs/<institution>/<sha256>.pdf and return the path."""
    dest_dir = base_dir / "pdfs" / institution
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{sha256}.pdf"
    if not dest.exists():
        dest.write_bytes(data)
        logger.debug("Saved PDF: %s", dest)
    return dest


def _extract_with_pdfplumber(data: bytes) -> tuple[str, int]:
    """Return (text, page_count). Raises on import or extraction error."""
    import pdfplumber  # type: ignore[import]
    import io

    text_parts: list[str] = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        page_count = len(pdf.pages)
        for page in pdf.pages:
            extracted = page.extract_text()
            if extracted:
                text_parts.append(extracted)
    return "\n\n".join(text_parts), page_count


def _extract_with_pymupdf(data: bytes) -> tuple[str, int]:
    """Return (text, page_count) using PyMuPDF (fitz)."""
    import fitz  # type: ignore[import]

    doc = fitz.open(stream=data, filetype="pdf")
    page_count = doc.page_count
    parts = [page.get_text() for page in doc]
    return "\n\n".join(parts), page_count


def extract_pdf_text(data: bytes) -> dict:
    """Extract text from PDF bytes. Returns dict with keys: text, pdf_pages, needs_ocr."""
    text = ""
    page_count: Optional[int] = None
    needs_ocr = False

    try:
        text, page_count = _extract_with_pdfplumber(data)
    except Exception as exc:
        logger.debug("pdfplumber failed: %s", exc)

    if len(text.strip()) < 100:
        logger.debug("pdfplumber yielded < 100 chars, trying PyMuPDF")
        try:
            text, page_count = _extract_with_pymupdf(data)
        except Exception as exc:
            logger.debug("PyMuPDF failed: %s", exc)

    if len(text.strip()) < 100:
        logger.info("PDF appears to be scanned (no extractable text)")
        needs_ocr = True
        text = ""

    return {
        "text": text,
        "pdf_pages": page_count,
        "needs_ocr": needs_ocr,
    }
