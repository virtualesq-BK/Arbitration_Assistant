"""CLI entry point for the arbitration crawler."""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from .config import INSTITUTIONS
from .pipeline import Pipeline


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m crawler.cli",
        description="Crawl international arbitration institution websites.",
    )
    p.add_argument(
        "--institution",
        choices=list(INSTITUTIONS.keys()) + ["ALL"],
        required=True,
        help="Institution to crawl, or ALL to crawl every institution sequentially.",
    )
    p.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Override max pages per institution (default from config).",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=Path("data"),
        help="Output directory (default: data/).",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch only 5 pages and print JSONL to stdout instead of writing files.",
    )
    p.add_argument(
        "--dry-run-limit",
        type=int,
        default=5,
        help="Number of pages to fetch in dry-run mode (default: 5).",
    )
    p.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    return p


async def _run_institution(
    name: str,
    out: Path,
    max_pages: int | None,
    dry_run: bool,
    dry_run_limit: int,
) -> None:
    pipeline = Pipeline(
        institution=name,
        out_dir=out,
        max_pages=max_pages,
        dry_run=dry_run,
        dry_run_limit=dry_run_limit,
    )
    await pipeline.run()


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        stream=sys.stderr,
    )

    institutions = list(INSTITUTIONS.keys()) if args.institution == "ALL" else [args.institution]

    for name in institutions:
        print(f"=== Starting crawl: {name} ===", file=sys.stderr)
        asyncio.run(
            _run_institution(
                name=name,
                out=args.out,
                max_pages=args.max_pages,
                dry_run=args.dry_run,
                dry_run_limit=args.dry_run_limit,
            )
        )


if __name__ == "__main__":
    main()
