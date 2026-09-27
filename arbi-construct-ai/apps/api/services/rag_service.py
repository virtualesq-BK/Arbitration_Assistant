"""Retrieval over the three separate corpora (RULES, CONSTRUCTION, CASE).

Tenant isolation contract
-------------------------
* CASE corpus queries MUST carry a case_id. A missing case_id raises ``TenantIsolationError``
  before any SQL is built, and every CASE query has ``DocumentChunk.case_id == :case_id`` in
  its WHERE clause (see ``_case_scope``).
* RULES / CONSTRUCTION corpora live in a separate table (knowledge_chunks) that never
  contains case documents.
"""
from __future__ import annotations

import logging
import math
import re
import uuid
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Literal

from sqlalchemy import Select, and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.document import Document
from models.document_chunk import DocumentChunk
from models.knowledge_chunk import KnowledgeChunk
from services.llm_service import LLMService, get_llm_service, is_zero_vector

logger = logging.getLogger(__name__)

SearchMode = Literal["keyword", "semantic", "hybrid"]

_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "what", "which", "when", "where", "who",
    "are", "was", "were", "has", "have", "had", "been", "into", "under", "does", "about", "any",
    "can", "will", "shall", "must", "may", "how", "why", "not", "our", "their", "there", "these",
    "those", "its", "his", "her", "per", "all", "out", "one", "two",
}


class Corpus(str, Enum):
    RULES = "rules"  # institution rules — tenant-independent
    CONSTRUCTION = "construction"  # general construction arb knowledge
    CASE = "case"  # per-case docs — MUST filter by case_id


class TenantIsolationError(ValueError):
    """Raised when a CASE-corpus retrieval is attempted without a case_id."""


@dataclass
class RetrievedChunk:
    text: str
    source_name: str
    source_url: str | None
    institution: str | None
    rule_version: str | None
    document_id: str | None
    chunk_index: int | None
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def citation_label(self) -> str:
        if self.document_id is not None:
            return f"{self.source_name} (chunk {self.chunk_index})"
        parts = [p for p in (self.institution, self.rule_version, self.source_name) if p]
        return " — ".join(parts)


def extract_terms(query: str) -> list[str]:
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9\-\.]*", query.lower())
    terms: list[str] = []
    for w in words:
        w = w.strip(".-")
        if len(w) < 3 and not w.isdigit():
            continue
        if w in _STOPWORDS or w in terms:
            continue
        terms.append(w)
    return terms[:12]


def keyword_score(text: str, terms: Sequence[str]) -> float:
    if not terms:
        return 0.0
    lowered = text.lower()
    hits = sum(1 for t in terms if t in lowered)
    return hits / len(terms)


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (math.sqrt(na) * math.sqrt(nb))


def _as_float_list(value: Any) -> list[float] | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip("[]")
        return [float(x) for x in stripped.split(",") if x.strip()] if stripped else []
    return [float(x) for x in value]


def _case_scope(stmt: Select[Any], case_id: uuid.UUID, org_id: uuid.UUID | None) -> Select[Any]:
    """The single place that applies tenant filters to CASE-corpus queries."""
    stmt = stmt.where(DocumentChunk.case_id == case_id)
    if org_id is not None:
        stmt = stmt.where(DocumentChunk.org_id == org_id)
    return stmt


class RAGService:
    def __init__(self, db: AsyncSession, llm: LLMService | None = None) -> None:
        self.db = db
        self.llm = llm or get_llm_service()

    @property
    def _is_postgres(self) -> bool:
        bind = self.db.get_bind()
        return bind.dialect.name == "postgresql"

    async def retrieve(
        self,
        query: str,
        corpus: Corpus,
        case_id: str | None = None,
        institution: str | None = None,
        top_k: int = 5,
        mode: SearchMode = "hybrid",
        org_id: str | None = None,
    ) -> list[RetrievedChunk]:
        """CASE corpus: mandatory case_id filter.
        RULES corpus: filter by institution if provided.
        Returns chunks ranked by cosine similarity (hybrid mode blends in keyword overlap)."""
        corpus = Corpus(corpus)
        case_uuid: uuid.UUID | None = None
        org_uuid: uuid.UUID | None = None
        if corpus is Corpus.CASE:
            if not case_id:
                raise TenantIsolationError("CASE corpus retrieval requires case_id")
            case_uuid = uuid.UUID(str(case_id))
            org_uuid = uuid.UUID(str(org_id)) if org_id else None

        inst = institution.upper() if institution else None
        terms = extract_terms(query)

        semantic: dict[str, tuple[RetrievedChunk, float]] = {}
        keyword: dict[str, tuple[RetrievedChunk, float]] = {}

        if mode in ("semantic", "hybrid"):
            qvec = (await self.llm.embed([query]))[0]
            if is_zero_vector(qvec):
                if mode == "semantic":
                    logger.info("Embeddings unavailable; semantic search falling back to keyword search")
                mode = "keyword"
            else:
                semantic = await self._semantic(qvec, corpus, case_uuid, org_uuid, inst, top_k * 3)

        if mode in ("keyword", "hybrid"):
            keyword = await self._keyword(terms, corpus, case_uuid, org_uuid, inst, top_k * 3)

        merged: dict[str, RetrievedChunk] = {}
        for key in set(semantic) | set(keyword):
            chunk = (semantic.get(key) or keyword[key])[0]
            sem = semantic[key][1] if key in semantic else 0.0
            kw = keyword[key][1] if key in keyword else 0.0
            if semantic and keyword:
                score = 0.7 * sem + 0.3 * kw
            else:
                score = sem if semantic else kw
            chunk.confidence = round(max(0.0, min(1.0, score)), 4)
            merged[key] = chunk

        ranked = sorted(merged.values(), key=lambda c: c.confidence, reverse=True)
        return [c for c in ranked if c.confidence > 0][:top_k]

    # ------------------------------------------------------------------ semantic
    async def _semantic(
        self,
        qvec: list[float],
        corpus: Corpus,
        case_id: uuid.UUID | None,
        org_id: uuid.UUID | None,
        institution: str | None,
        limit: int,
    ) -> dict[str, tuple[RetrievedChunk, float]]:
        out: dict[str, tuple[RetrievedChunk, float]] = {}
        if corpus is Corpus.CASE:
            assert case_id is not None
            if self._is_postgres:
                dist = DocumentChunk.embedding.cosine_distance(qvec).label("dist")
                stmt = select(DocumentChunk, Document.filename, dist).join(Document, Document.id == DocumentChunk.document_id)
                stmt = _case_scope(stmt, case_id, org_id).where(DocumentChunk.embedding.isnot(None)).order_by(dist).limit(limit)
                rows = (await self.db.execute(stmt)).all()
                for chunk, filename, distance in rows:
                    out[str(chunk.id)] = (self._case_chunk(chunk, filename), 1.0 - float(distance))
            else:
                stmt = select(DocumentChunk, Document.filename).join(Document, Document.id == DocumentChunk.document_id)
                stmt = _case_scope(stmt, case_id, org_id).where(DocumentChunk.embedding.isnot(None))
                rows = (await self.db.execute(stmt)).all()
                scored = []
                for chunk, filename in rows:
                    vec = _as_float_list(chunk.embedding)
                    if is_zero_vector(vec):
                        continue
                    scored.append((chunk, filename, cosine_similarity(qvec, vec or [])))
                scored.sort(key=lambda r: r[2], reverse=True)
                for chunk, filename, sim in scored[:limit]:
                    out[str(chunk.id)] = (self._case_chunk(chunk, filename), sim)
            return out

        conditions = [KnowledgeChunk.corpus == corpus.value, KnowledgeChunk.embedding.isnot(None)]
        if institution:
            conditions.append(KnowledgeChunk.institution == institution)
        if self._is_postgres:
            dist = KnowledgeChunk.embedding.cosine_distance(qvec).label("dist")
            stmt = select(KnowledgeChunk, dist).where(and_(*conditions)).order_by(dist).limit(limit)
            for kc, distance in (await self.db.execute(stmt)).all():
                out[str(kc.id)] = (self._knowledge_chunk(kc), 1.0 - float(distance))
        else:
            rows = (await self.db.execute(select(KnowledgeChunk).where(and_(*conditions)))).scalars().all()
            scored = []
            for kc in rows:
                vec = _as_float_list(kc.embedding)
                if is_zero_vector(vec):
                    continue
                scored.append((kc, cosine_similarity(qvec, vec or [])))
            scored.sort(key=lambda r: r[1], reverse=True)
            for kc, sim in scored[:limit]:
                out[str(kc.id)] = (self._knowledge_chunk(kc), sim)
        return out

    # ------------------------------------------------------------------ keyword
    async def _keyword(
        self,
        terms: list[str],
        corpus: Corpus,
        case_id: uuid.UUID | None,
        org_id: uuid.UUID | None,
        institution: str | None,
        limit: int,
    ) -> dict[str, tuple[RetrievedChunk, float]]:
        out: dict[str, tuple[RetrievedChunk, float]] = {}
        if not terms:
            return out
        if corpus is Corpus.CASE:
            assert case_id is not None
            stmt = select(DocumentChunk, Document.filename).join(Document, Document.id == DocumentChunk.document_id)
            stmt = _case_scope(stmt, case_id, org_id)
            stmt = stmt.where(or_(*[DocumentChunk.text.ilike(f"%{t}%") for t in terms])).limit(500)
            for chunk, filename in (await self.db.execute(stmt)).all():
                # Include the filename so a query like "Variation Order 3" matches by title too.
                score = keyword_score(f"{filename}\n{chunk.text}", terms)
                out[str(chunk.id)] = (self._case_chunk(chunk, filename), score)
        else:
            conditions = [KnowledgeChunk.corpus == corpus.value]
            if institution:
                conditions.append(KnowledgeChunk.institution == institution)
            text_match = or_(
                *[KnowledgeChunk.text.ilike(f"%{t}%") for t in terms],
                *[KnowledgeChunk.source_name.ilike(f"%{t}%") for t in terms],
            )
            stmt = select(KnowledgeChunk).where(and_(*conditions), text_match).limit(500)
            for kc in (await self.db.execute(stmt)).scalars().all():
                score = keyword_score(f"{kc.source_name}\n{kc.institution or ''}\n{kc.text}", terms)
                out[str(kc.id)] = (self._knowledge_chunk(kc), score)
        ranked = sorted(out.items(), key=lambda kv: kv[1][1], reverse=True)[:limit]
        return dict(ranked)

    # ------------------------------------------------------------------ mappers
    @staticmethod
    def _case_chunk(chunk: DocumentChunk, filename: str) -> RetrievedChunk:
        return RetrievedChunk(
            text=chunk.text,
            source_name=filename,
            source_url=None,
            institution=None,
            rule_version=None,
            document_id=str(chunk.document_id),
            chunk_index=chunk.chunk_index,
            confidence=0.0,
        )

    @staticmethod
    def _knowledge_chunk(kc: KnowledgeChunk) -> RetrievedChunk:
        name = kc.source_name
        if kc.article_number and kc.article_number not in name:
            name = f"{name} ({kc.article_number})"
        return RetrievedChunk(
            text=kc.text,
            source_name=name,
            source_url=kc.source_url,
            institution=kc.institution,
            rule_version=kc.rule_version,
            document_id=None,
            chunk_index=kc.chunk_index,
            confidence=0.0,
        )
