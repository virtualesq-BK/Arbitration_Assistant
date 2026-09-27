"""Tenant isolation: CASE-corpus retrieval must be scoped to exactly one case (and org)."""
from __future__ import annotations

import uuid
from typing import Any

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.security import create_access_token, hash_password
from models import (
    Case,
    Document,
    DocumentChunk,
    DocumentType,
    Organization,
    User,
    UserRole,
)
from services.ingest_service import index_document
from services.rag_service import Corpus, RAGService, TenantIsolationError, _case_scope

SECRET_A = "Case A secret: concrete pour delayed by late design drawings for Terminal 2 apron."
SECRET_B = "Case B record: steel delivery for the bridge deck was delayed by customs clearance."


async def _seed_two_tenants(db: AsyncSession, llm: Any) -> dict[str, Any]:
    org_a = Organization(id=uuid.uuid4(), name="Org A")
    org_b = Organization(id=uuid.uuid4(), name="Org B")
    db.add_all([org_a, org_b])
    await db.flush()
    case_a = Case(id=uuid.uuid4(), org_id=org_a.id, title="Case A")
    case_b = Case(id=uuid.uuid4(), org_id=org_b.id, title="Case B")
    db.add_all([case_a, case_b])
    await db.flush()
    doc_a = Document(id=uuid.uuid4(), case_id=case_a.id, org_id=org_a.id, filename="a.txt",
                     document_type=DocumentType.DAILY_REPORT, ocr_text=SECRET_A)
    doc_b = Document(id=uuid.uuid4(), case_id=case_b.id, org_id=org_b.id, filename="b.txt",
                     document_type=DocumentType.DAILY_REPORT, ocr_text=SECRET_B)
    db.add_all([doc_a, doc_b])
    await db.flush()
    await index_document(db, doc_a, llm)
    await index_document(db, doc_b, llm)
    user_a = User(id=uuid.uuid4(), email="a@example.com", hashed_password=hash_password("Password1!"),
                  full_name="A", role=UserRole.LAWYER, org_id=org_a.id)
    user_b = User(id=uuid.uuid4(), email="b@example.com", hashed_password=hash_password("Password1!"),
                  full_name="B", role=UserRole.LAWYER, org_id=org_b.id)
    db.add_all([user_a, user_b])
    await db.commit()
    return {"org_a": org_a, "org_b": org_b, "case_a": case_a, "case_b": case_b,
            "doc_a": doc_a, "doc_b": doc_b, "user_a": user_a, "user_b": user_b}


@pytest.mark.asyncio
async def test_case_corpus_requires_case_id(db: AsyncSession, mock_llm: Any) -> None:
    rag = RAGService(db, mock_llm)
    with pytest.raises(TenantIsolationError):
        await rag.retrieve("delay", Corpus.CASE)
    with pytest.raises(TenantIsolationError):
        await rag.retrieve("delay", Corpus.CASE, case_id=None, mode="keyword")


def test_case_scope_always_adds_case_id_filter() -> None:
    cid = uuid.uuid4()
    stmt = _case_scope(select(DocumentChunk), cid, None)
    sql = str(stmt.compile(compile_kwargs={"literal_binds": False}))
    assert "document_chunks.case_id = :case_id_1" in sql
    stmt2 = _case_scope(select(DocumentChunk), cid, uuid.uuid4())
    sql2 = str(stmt2.compile())
    assert "document_chunks.case_id" in sql2 and "document_chunks.org_id" in sql2


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["semantic", "keyword", "hybrid"])
async def test_chunk_from_case_a_not_returned_for_case_b(db: AsyncSession, mock_llm: Any, mode: str) -> None:
    data = await _seed_two_tenants(db, mock_llm)
    rag = RAGService(db, mock_llm)

    # Query text deliberately matches case A's content.
    hits_b = await rag.retrieve("concrete pour delayed design drawings Terminal apron", Corpus.CASE,
                                case_id=str(data["case_b"].id), top_k=10, mode=mode)  # type: ignore[arg-type]
    assert all(h.document_id == str(data["doc_b"].id) for h in hits_b)
    assert not any("Case A secret" in h.text for h in hits_b)

    hits_a = await rag.retrieve("concrete pour delayed design drawings Terminal apron", Corpus.CASE,
                                case_id=str(data["case_a"].id), top_k=10, mode=mode)  # type: ignore[arg-type]
    assert hits_a, "the owning case should find its own chunk"
    assert all(h.document_id == str(data["doc_a"].id) for h in hits_a)


@pytest.mark.asyncio
async def test_org_filter_blocks_mismatched_org(db: AsyncSession, mock_llm: Any) -> None:
    data = await _seed_two_tenants(db, mock_llm)
    rag = RAGService(db, mock_llm)
    hits = await rag.retrieve("concrete pour", Corpus.CASE, case_id=str(data["case_a"].id),
                              org_id=str(data["org_b"].id), mode="keyword")
    assert hits == []


@pytest.mark.asyncio
async def test_api_denies_cross_org_case_access(
    session_factory: async_sessionmaker[AsyncSession], mock_llm: Any
) -> None:
    from core.database import get_db
    from main import app

    async with session_factory() as s:
        data = await _seed_two_tenants(s, mock_llm)

    async def override_db() -> Any:
        async with session_factory() as s:
            yield s

    app.dependency_overrides[get_db] = override_db
    try:
        token_b = create_access_token(str(data["user_b"].id))
        headers = {"Authorization": f"Bearer {token_b}"}
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get(f"/api/v1/cases/{data['case_a'].id}", headers=headers)
            assert r.status_code == 404
            r = await client.get(f"/api/v1/cases/{data['case_a'].id}/documents", headers=headers)
            assert r.status_code == 404
            r = await client.post("/api/v1/search", headers=headers,
                                  json={"query": "concrete", "corpus": "case", "case_id": str(data["case_a"].id), "mode": "keyword"})
            assert r.status_code == 404
            r = await client.get("/api/v1/cases", headers=headers)
            assert r.status_code == 200
            assert [c["id"] for c in r.json()] == [str(data["case_b"].id)]
            r = await client.get("/api/v1/cases")
            assert r.status_code == 401
    finally:
        app.dependency_overrides.clear()
