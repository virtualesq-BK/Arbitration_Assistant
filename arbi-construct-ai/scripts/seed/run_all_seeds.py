"""Run all seed scripts in order: institutions/rules/knowledge, then the synthetic demo case.

Usage (from the repository root, after `cd apps/api && alembic upgrade head`):
    python scripts/seed/run_all_seeds.py
"""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _common  # noqa: E402,F401
import seed_institutions  # noqa: E402
import seed_synthetic_case  # noqa: E402
from core.database import AsyncSessionLocal, engine  # noqa: E402
from services.llm_service import LLMService  # noqa: E402


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    llm = LLMService()  # one instance: if embeddings are unavailable we only probe once
    async with AsyncSessionLocal() as session:
        await seed_institutions.seed(session, llm)
    async with AsyncSessionLocal() as session:
        await seed_synthetic_case.seed(session, llm)
    await engine.dispose()
    print("\nSeeding complete. Demo login: demo@arbiconstruct.ai / Demo1234!")


if __name__ == "__main__":
    asyncio.run(main())
