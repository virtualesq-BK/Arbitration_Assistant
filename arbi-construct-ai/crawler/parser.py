"""HTML parser: extract cleaned text, metadata, and outbound links."""

import json
import logging
import re
from typing import Optional
from urllib.parse import urljoin, urlparse, urlunparse, urlencode, parse_qsl

import tldextract
from bs4 import BeautifulSoup, Tag

from .config import (
    SKIP_LANG_PREFIXES,
    SKIP_MIME_PREFIXES,
    STRIP_PATTERN,
    STRIP_SELECTORS,
    InstitutionConfig,
)

logger = logging.getLogger(__name__)

# UTM and tracking params to strip from URLs
_UTM_PARAMS: frozenset[str] = frozenset({
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "msclkid", "mc_cid", "mc_eid",
})

_STRIP_RE = re.compile(STRIP_PATTERN, re.IGNORECASE)


def canonicalize_url(url: str) -> str:
    """Strip fragments and known tracking params; lowercase scheme+host."""
    parsed = urlparse(url)
    clean_params = [
        (k, v) for k, v in parse_qsl(parsed.query) if k not in _UTM_PARAMS
    ]
    return urlunparse((
        parsed.scheme.lower(),
        parsed.netloc.lower(),
        parsed.path,
        parsed.params,
        urlencode(clean_params),
        "",  # drop fragment
    ))


def is_english_url(url: str) -> bool:
    """Return False if the URL path starts with a non-English language segment."""
    path = urlparse(url).path
    parts = [p for p in path.split("/") if p]
    if parts and parts[0].lower() in SKIP_LANG_PREFIXES:
        return False
    return True


def is_same_domain(url: str, allowed_domains: list[str]) -> bool:
    """Return True if the URL's registrable domain is in allowed_domains."""
    extracted = tldextract.extract(url)
    reg_domain = f"{extracted.domain}.{extracted.suffix}"
    return any(
        reg_domain == d or reg_domain.endswith(f".{d}") or d == reg_domain
        for d in allowed_domains
    )


def should_skip_mime(content_type: str) -> bool:
    """Return True for binary/non-text MIME types other than PDF."""
    if "application/pdf" in content_type:
        return False
    return any(content_type.startswith(prefix) for prefix in SKIP_MIME_PREFIXES)


def is_pdf(content_type: str, url: str) -> bool:
    return "application/pdf" in content_type or url.lower().rstrip("/").endswith(".pdf")


def _strip_noise(soup: BeautifulSoup) -> None:
    """Remove script, style, nav, footer, and pattern-matched elements in place."""
    for tag in STRIP_SELECTORS:
        for el in soup.find_all(tag):
            el.decompose()

    for el in soup.find_all(True):
        el_id = el.get("id", "") or ""
        el_cls = " ".join(el.get("class", []) or [])
        if _STRIP_RE.search(el_id) or _STRIP_RE.search(el_cls):
            el.decompose()


def _get_text_container(soup: BeautifulSoup, selectors: list[str]) -> Tag:
    """Return the best content container from the soup."""
    for sel in selectors:
        el = soup.select_one(sel)
        if el:
            return el
    return soup.body or soup  # type: ignore[return-value]


def extract_text(html: str, selectors: list[str]) -> str:
    """Extract and clean body text from HTML."""
    soup = BeautifulSoup(html, "html.parser")
    _strip_noise(soup)
    container = _get_text_container(soup, selectors)
    # Get text preserving block-level newlines
    chunks: list[str] = []
    for el in container.descendants:
        if isinstance(el, str):
            stripped = el.strip()
            if stripped:
                chunks.append(stripped)
        elif hasattr(el, "name") and el.name in {
            "p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6",
            "br", "tr", "blockquote",
        }:
            chunks.append("\n")
    text = " ".join(chunks)
    # Collapse multiple spaces/newlines
    text = re.sub(r" {2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_title(soup: BeautifulSoup) -> str:
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        return str(og_title["content"]).strip()
    title_tag = soup.find("title")
    if title_tag:
        return title_tag.get_text(strip=True)
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)
    return ""


def extract_published_date(soup: BeautifulSoup, meta_names: list[str]) -> Optional[str]:
    # Try <meta> tags
    for name in meta_names:
        for attr in ("name", "property", "itemprop"):
            tag = soup.find("meta", {attr: name})
            if tag and tag.get("content"):
                return str(tag["content"]).strip()

    # Try JSON-LD
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            if isinstance(data, list):
                data = data[0] if data else {}
            date = data.get("datePublished") or data.get("dateCreated")
            if date:
                return str(date).strip()
        except (json.JSONDecodeError, AttributeError):
            pass

    # Try <time datetime="...">
    time_tag = soup.find("time", datetime=True)
    if time_tag:
        return str(time_tag["datetime"]).strip()

    return None


def extract_canonical(soup: BeautifulSoup, base_url: str) -> str:
    """Return canonical URL if present, else base_url."""
    link = soup.find("link", rel="canonical")
    if link and link.get("href"):
        href = str(link["href"]).strip()
        if href.startswith("http"):
            return href
        return urljoin(base_url, href)
    return base_url


def is_english_page(soup: BeautifulSoup) -> bool:
    """Check hreflang tags: if present, keep only en / x-default pages."""
    hreflang_tags = soup.find_all("link", rel="alternate", hreflang=True)
    if not hreflang_tags:
        return True  # no hreflang means assume English
    langs = {str(t["hreflang"]).lower() for t in hreflang_tags}
    # If any en or x-default tag exists, treat this as an English page
    return bool(langs & {"en", "x-default", "en-us", "en-gb", "en-au"})


def extract_links(
    html: str,
    base_url: str,
    allowed_domains: list[str],
    max_depth: int,
    current_depth: int,
) -> list[str]:
    """Return canonicalized same-domain links suitable for further crawling."""
    if current_depth >= max_depth:
        return []
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    for a in soup.find_all("a", href=True):
        href = str(a["href"]).strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        full = urljoin(base_url, href)
        canonical = canonicalize_url(full)
        if not canonical.startswith(("http://", "https://")):
            continue
        if not is_same_domain(canonical, allowed_domains):
            continue
        if not is_english_url(canonical):
            continue
        links.append(canonical)
    return links


def parse_page(
    html: str,
    url: str,
    config: InstitutionConfig,
) -> Optional[dict]:
    """Parse HTML page and return a dict ready for CrawlRecord, or None to skip."""
    soup = BeautifulSoup(html, "html.parser")

    if not is_english_page(soup):
        logger.debug("Skipping non-English page: %s", url)
        return None

    canonical = extract_canonical(soup, url)
    title = extract_title(soup)
    published_date = extract_published_date(soup, config.date_meta_names)
    text = extract_text(html, config.content_selectors)

    if len(text) < 200:
        logger.debug("Dropping short page (%d chars): %s", len(text), url)
        return None

    return {
        "url": canonical,
        "title": title,
        "published_date": published_date,
        "text": text,
    }
