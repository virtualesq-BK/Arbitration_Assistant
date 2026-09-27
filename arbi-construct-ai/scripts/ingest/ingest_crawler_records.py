"""Load crawler output (data/records.jsonl) into the RULES knowledge corpus.

The crawler (python -m crawler.cli --institution ALL --out data/) writes one JSON record per
page/PDF. This script chunks each record's text and stores it as KnowledgeChunk(corpus="rules")
tagged with the institution and source URL, so the Research and Procedure agents can cite it.

Usage (from the repository root):
    python scripts/ingest/ingest_crawler_records.py --file data/records.jsonl [--institution SIAC] [--limit 500]

Re-running skips URLs that are already ingested.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from sqlalchemy import select  # noqa: E402

from core.database import AsyncSessionLocal, engine  # noqa: E402
from models.knowledge_chunk import KnowledgeChunk  # noqa: E402
from services.ingest_service import index_knowledge  # noqa: E402
from services.llm_service import LLMService  # noqa: E402

logger = logging.getLogger("ingest_crawler_records")
MIN_TEXT_CHARS = 200


async def ingest(path: Path, institution: str | None, limit: int | None) -> None:
    llm = LLMService()
    async with AsyncSessionLocal() as session:
        existing = set((await session.execute(select(KnowledgeChunk.source_url).where(KnowledgeChunk.corpus == "rules"))).scalars())
        added = skipped = 0
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                if limit is not None and added >= limit:
                    break
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    skipped += 1
                    continue
                inst = str(rec.get("institution") or "").upper() or None
                if institution and inst != institution.upper():
                    continue
                url = rec.get("url")
                text = (rec.get("text") or "").strip()
                if not url or url in existing or len(text) < MIN_TEXT_CHARS or rec.get("language", "en") != "en":
                    skipped += 1
                    continue
                n = await index_knowledge(
                    session,
                    corpus="rules",
                    source_name=(rec.get("title") or url)[:480],
                    text=text,
                    source_url=url,
                    institution=inst,
                    rule_version=None,  # crawled pages carry a publish date, not a rules version
                    llm=llm,
                )
                existing.add(url)
                added += 1
                logger.info("Indexed %s (%d chunks)", url, n)
                if added % 25 == 0:
                    await session.commit()
        await session.commit()
    await engine.dispose()
    logger.info("Done: %d records ingested, %d skipped", added, skipped)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", default=str(ROOT / "data" / "records.jsonl"))
    parser.add_argument("--institution", default=None)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    path = Path(args.file)
    if not path.exists():
        raise SystemExit(f"{path} not found — run the crawler first: python -m crawler.cli --institution ALL --out data/")
    asyncio.run(ingest(path, args.institution, args.limit))


if __name__ == "__main__":
    main()
