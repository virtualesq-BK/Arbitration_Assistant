"""Orchestrates per-institution crawl: BFS queue, dedup, output writing."""

import asyncio
import logging
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .config import INSTITUTIONS, InstitutionConfig
from .fetcher import Fetcher
from .models import CrawlRecord
from .parser import (
    canonicalize_url,
    extract_links,
    is_pdf,
    parse_page,
    should_skip_mime,
)
from .pdf_handler import extract_pdf_text, save_pdf, sha256_of

logger = logging.getLogger(__name__)


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


class Pipeline:
    def __init__(
        self,
        institution: str,
        out_dir: Path,
        max_pages: Optional[int] = None,
        dry_run: bool = False,
        dry_run_limit: int = 5,
    ) -> None:
        if institution not in INSTITUTIONS:
            raise ValueError(f"Unknown institution: {institution!r}")
        self.config: InstitutionConfig = INSTITUTIONS[institution]
        if max_pages is not None:
            self.config.max_pages = max_pages
        self.out_dir = out_dir
        self.dry_run = dry_run
        self.dry_run_limit = dry_run_limit

        self._visited: set[str] = set()
        self._pdf_hashes: set[str] = set()
        self._count = 0

    async def run(self) -> None:
        out_dir = self.out_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        jsonl_path = out_dir / "records.jsonl"

        # BFS queue: (url, depth)
        queue: deque[tuple[str, int]] = deque(
            (canonicalize_url(s), 0) for s in self.config.seeds
        )

        async with Fetcher(self.config) as fetcher:
            with jsonl_path.open("a", encoding="utf-8") as fh:
                while queue:
                    if self._count >= self.config.max_pages:
                        logger.info("Reached max_pages=%d, stopping.", self.config.max_pages)
                        break
                    if self.dry_run and self._count >= self.dry_run_limit:
                        logger.info("Dry-run limit reached.")
                        break

                    url, depth = queue.popleft()
                    if url in self._visited:
                        continue
                    self._visited.add(url)

                    result = await fetcher.fetch(url)
                    if result is None:
                        continue

                    content_type = result.content_type
                    final_url = canonicalize_url(result.final_url)

                    # Deduplicate after redirect
                    if final_url in self._visited and final_url != url:
                        continue
                    self._visited.add(final_url)

                    if should_skip_mime(content_type):
                        logger.debug("Skipping MIME %s for %s", content_type, url)
                        continue

                    record: Optional[CrawlRecord] = None

                    if is_pdf(content_type, final_url):
                        record = await self._handle_pdf(result.content, final_url)
                    else:
                        # HTML / text
                        try:
                            html = result.content.decode("utf-8", errors="replace")
                        except Exception as exc:
                            logger.warning("Decode error for %s: %s", url, exc)
                            continue

                        parsed = parse_page(html, final_url, self.config)
                        if parsed is None:
                            # Extract links even from skipped pages so we don't miss deeper content
                            if depth < self.config.max_depth:
                                for link in extract_links(
                                    html, final_url, self.config.allowed_domains,
                                    self.config.max_depth, depth,
                                ):
                                    if link not in self._visited:
                                        queue.append((link, depth + 1))
                            continue

                        record = CrawlRecord(
                            institution=self.config.name,
                            url=parsed["url"],
                            content_type="html",
                            title=parsed["title"],
                            published_date=parsed["published_date"],
                            text=parsed["text"],
                            crawled_at=_now_utc(),
                        )

                        # Enqueue outbound links
                        if depth < self.config.max_depth:
                            for link in extract_links(
                                html, final_url, self.config.allowed_domains,
                                self.config.max_depth, depth,
                            ):
                                if link not in self._visited:
                                    queue.append((link, depth + 1))

                    if record is not None:
                        self._count += 1
                        line = record.model_dump_jsonl()
                        if self.dry_run:
                            print(line)
                        else:
                            fh.write(line + "\n")
                            fh.flush()
                        logger.info("[%d] %s %s", self._count, record.content_type.upper(), record.url)

        logger.info("Crawl complete. Records written: %d", self._count)

    async def _handle_pdf(self, data: bytes, url: str) -> Optional[CrawlRecord]:
        sha256 = sha256_of(data)
        if sha256 in self._pdf_hashes:
            logger.debug("Duplicate PDF (sha256 match): %s", url)
            return None
        self._pdf_hashes.add(sha256)

        pdf_path = save_pdf(data, self.config.name, sha256, self.out_dir)
        extraction = extract_pdf_text(data)

        return CrawlRecord(
            institution=self.config.name,
            url=url,
            content_type="pdf",
            title=url.split("/")[-1],  # filename as fallback title
            text=extraction["text"],
            pdf_path=str(pdf_path),
            pdf_sha256=sha256,
            pdf_pages=extraction["pdf_pages"],
            needs_ocr=extraction["needs_ocr"],
            crawled_at=_now_utc(),
        )
