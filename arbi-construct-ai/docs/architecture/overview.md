# Architecture overview

```
 Browser (Next.js 14, apps/web)
   │  JWT in localStorage → Authorization: Bearer
   ▼
 FastAPI (apps/api)  /api/v1/*
   ├─ routers/        auth · cases · documents · timeline · claims · procedure · institutions · ai · search
   ├─ core/           settings · async DB session · JWT/bcrypt · get_current_user + tenant-scoped lookups
   ├─ services/
   │   ├─ llm_service.py        httpx → {OPENAI_BASE_URL}/chat/completions, /embeddings (zero-vector fallback)
   │   ├─ rag_service.py        3 corpora; CASE corpus hard-requires case_id (TenantIsolationError)
   │   ├─ agent_service.py      7 agents → deterministic findings + LLM JSON → safety + citation validation
   │   ├─ legal_safety_validator.py / citation_validator.py
   │   ├─ evidence_rules.py     claim-type → expected document types (evidence gaps)
   │   ├─ ingest_service.py     text extraction (txt/pdf), paragraph chunking, embeddings
   │   └─ storage_service.py    local disk + signed, expiring download URLs
   └─ models/         SQLAlchemy 2.0 (UUID PKs, non-native enums, JSONB, pgvector Vector(1536))
   ▼
 PostgreSQL 16 + pgvector   (HNSW cosine indexes on document_chunks / knowledge_chunks)
```

## RAG corpora

| Corpus | Table | Scope | Filter |
|---|---|---|---|
| `rules` | `knowledge_chunks` (corpus='rules') | shared | optional `institution` |
| `construction` | `knowledge_chunks` (corpus='construction') | shared | — |
| `case` | `document_chunks` | one case | **mandatory** `case_id` (+ `org_id` when known) |

Case documents and shared knowledge are kept in separate tables, so a shared-corpus query can
never return case data. Retrieval modes are `keyword` (ILIKE term overlap), `semantic`
(cosine distance via pgvector) and `hybrid` (0.7 semantic + 0.3 keyword). If the gateway
returns no embeddings, semantic mode falls back to keyword mode.

## Agent pipeline

1. Gather context scoped to the tenant: database records plus RAG results. Each source gets an id: `[D#]` for case documents, `[S#]` for rules/reference material, `C1`/`T1` for the case record and timeline.
2. Build deterministic findings that don't need the LLM, such as facts from records, rule citations and evidence gaps.
3. Call the LLM with a system prompt that sets the product boundary and asks for a labelled JSON response.
4. Post-process the response:
   - Drop citations to unknown source ids.
   - Downgrade an uncited FACT or SOURCE_BASED_INFO finding to REQUIRES_HUMAN_REVIEW.
   - Run the legal-safety validator on all text.
   - Run the citation validator on generated text.
5. Persist the result as an `AIAnalysis` record and an `AuditLog` entry.

If the LLM is unavailable, the response contains the deterministic findings plus verbatim source excerpts, labelled `SOURCE_BASED_INFO`.
