"""Crawler configuration: seed URLs, per-institution selectors, rate limits."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class InstitutionConfig:
    name: str
    seeds: list[str]
    allowed_domains: list[str]
    max_pages: int = 2000
    requests_per_second: float = 0.5  # 1 req / 2 sec
    max_depth: int = 4
    # CSS selectors tried in order; first match wins
    content_selectors: list[str] = field(default_factory=lambda: [
        "main", "article", '[role="main"]', "#content", ".content",
        ".entry-content", ".page-content", "body",
    ])
    date_meta_names: list[str] = field(default_factory=lambda: [
        "article:published_time", "datePublished", "date",
        "DC.date", "pubdate", "publishdate",
    ])


INSTITUTIONS: dict[str, InstitutionConfig] = {
    "ICC": InstitutionConfig(
        name="ICC",
        seeds=["https://iccwbo.org/"],
        allowed_domains=["iccwbo.org"],
        content_selectors=["main", ".field--type-text-long", "article", "body"],
    ),
    "SIAC": InstitutionConfig(
        name="SIAC",
        seeds=["https://siac.org.sg/"],
        allowed_domains=["siac.org.sg"],
    ),
    "LCIA": InstitutionConfig(
        name="LCIA",
        seeds=["https://www.lcia.org/"],
        allowed_domains=["lcia.org"],
    ),
    "HKIAC": InstitutionConfig(
        name="HKIAC",
        seeds=["https://hkiac.org/"],
        allowed_domains=["hkiac.org"],
    ),
    "ICSID": InstitutionConfig(
        name="ICSID",
        seeds=["https://icsid.worldbank.org/"],
        allowed_domains=["icsid.worldbank.org"],
    ),
    "ICDR": InstitutionConfig(
        name="ICDR",
        seeds=["https://icdr.org/"],
        allowed_domains=["icdr.org"],
    ),
}

# Language path prefixes to skip (case-insensitive match against URL path segments)
SKIP_LANG_PREFIXES: set[str] = {
    "fr", "es", "zh", "ko", "ar", "ru", "de", "ja", "pt", "it",
}

# MIME types to skip entirely (not PDF, not HTML/text)
SKIP_MIME_PREFIXES: tuple[str, ...] = (
    "image/", "video/", "audio/", "application/zip",
    "application/x-zip", "application/octet-stream",
    "application/msword",  # old .doc — skip; .docx also skipped
    "application/vnd.",
)

# Elements to strip before text extraction
STRIP_SELECTORS: list[str] = [
    "script", "style", "nav", "footer", "header", "aside",
    "noscript", "iframe", "figure",
]

# Class/id patterns whose elements are stripped (regex applied case-insensitively)
STRIP_PATTERN: str = r"cookie|banner|nav|menu|sidebar|footer|header|popup|modal|overlay"

USER_AGENT: str = (
    "ArbitrationCrawler/1.0 (research; contact: virtual.esq@gmail.com)"
)

CONNECT_TIMEOUT: float = 30.0
READ_TIMEOUT: float = 60.0
MAX_RETRIES: int = 3
MIN_TEXT_LENGTH: int = 200      # drop pages with fewer cleaned chars
MIN_PDF_TEXT_LENGTH: int = 100  # fallback to PyMuPDF if below this
