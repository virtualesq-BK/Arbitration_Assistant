"""Pytest fixtures: in-memory SQLite database and a deterministic mock LLM.

Run from the repository root:  pytest -q
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sys
import uuid
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio

ROOT = Path(__file__).resolve().parents[1]
API_DIR = ROOT / "apps" / "api"
sys.path.insert(0, str(API_DIR))

# Configure settings BEFORE any application module is imported.
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["OPENAI_API_KEY"] = "test-key"
os.environ["OPENAI_BASE_URL"] = "http://llm.invalid/v1"
os.environ["OPENAI_MODEL"] = "mock-model"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["LOCAL_STORAGE_PATH"] = str(ROOT / "data" / "uploads" / "_test")

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from models import Base  # noqa: E402
from services.llm_service import LLMService  # noqa: E402

DIM = 1536


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


class MockLLM(LLMService):
    """Deterministic stand-in for the gateway.

    embed(): hashed bag-of-words vectors, so texts sharing words have high cosine similarity.
    complete(): returns ``self.next_response`` (a dict serialised to JSON) and records the prompt.
    """

    def __init__(self) -> None:
        super().__init__(base_url="http://llm.invalid/v1", api_key="x", model="mock-model")
        self.calls: list[list[dict[str, Any]]] = []
        self.next_response: dict[str, Any] = {
            "summary": "Mock summary based on the supplied sources.",
            "findings": [{"label": "AI_SUMMARY", "content": "Mock finding.", "citations": []}],
            "evidence_gaps": [],
            "requires_human_review": [],
        }

    async def complete(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        max_tokens: int = 2000,
        temperature: float = 0.1,
    ) -> str:
        self.calls.append(messages)
        return json.dumps(self.next_response)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for text in texts:
            vec = [0.0] * DIM
            for tok in _tokens(text):
                h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
                vec[h % DIM] += 1.0
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            out.append([v / norm for v in vec])
        return out


@pytest.fixture
def mock_llm() -> MockLLM:
    return MockLLM()


@pytest_asyncio.fixture
async def engine() -> AsyncIterator[Any]:
    eng = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session_factory(engine: Any) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


@pytest_asyncio.fixture
async def db(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session


def new_id() -> uuid.UUID:
    return uuid.uuid4()
