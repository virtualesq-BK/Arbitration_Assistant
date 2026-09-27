# ArbiConstruct AI

ArbiConstruct AI is an AI-assisted case management platform for international construction arbitration. It covers:

- document management with per-case RAG search
- a chronology of case events
- a claim–evidence matrix with evidence-gap detection
- procedural checklists, with comparison of institutional rules (ICC, SIAC and LCIA)
- seven labelled AI agents

> **Product boundary:** ArbiConstruct AI provides AI-assisted information management and research.
> It does not provide legal advice or legal representation. AI outputs must be reviewed by qualified
> legal professionals. See [`docs/legal/product-boundary.md`](docs/legal/product-boundary.md).

## Repository layout

```
arbi-construct-ai/
├── apps/
│   ├── api/            FastAPI + SQLAlchemy 2.0 (async) + pgvector + Alembic
│   └── web/            Next.js 14 App Router + TypeScript + Tailwind
├── packages/shared/    shared Python types (labels, corpora, stages, disclaimers)
├── crawler/            async crawler for ICC / SIAC / LCIA / HKIAC / ICSID / ICDR (see below)
├── data/               raw/ processed/ synthetic/ uploads/
├── docs/               architecture/ and legal/
├── scripts/
│   ├── seed/           seed_institutions.py, seed_synthetic_case.py, run_all_seeds.py
│   └── ingest/         ingest_crawler_records.py (crawler JSONL → RULES corpus)
├── tests/              pytest (in-memory SQLite + mock LLM)
├── docker/             optional Postgres init SQL
├── docker-compose.yml
└── .env.example
```

## Quick start

Prerequisites: Docker, Python 3.11, and Node 20 (only needed to run the web app outside Docker).

```bash
cp .env.example .env              # then set OPENAI_BASE_URL / OPENAI_API_KEY / OPENAI_MODEL / SECRET_KEY
pip install -r apps/api/requirements.txt

docker compose up db -d           # PostgreSQL 16 + pgvector on :5432
cd apps/api && alembic upgrade head && cd ../..
python scripts/seed/run_all_seeds.py
docker compose up                 # api on :8000, web on :3000
```

| What | URL |
|---|---|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000 |
| API docs (Swagger) | http://localhost:8000/docs |

**Demo login:** `demo@arbiconstruct.ai` / `Demo1234!`

### Running without Docker for the app tiers

```bash
# API (from apps/api)
uvicorn main:app --reload --port 8000
# Web (from apps/web)
npm install && npm run dev
```

## Configuration (`.env`)

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://…` (docker-compose overrides the host to `db` for the api container) |
| `SECRET_KEY` | JWT signing key and signed download links. **Change it in production.** |
| `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `OPENAI_MODEL` | OpenAI-compatible gateway. Calls go straight through httpx; no SDK or LangChain. |
| `EMBEDDING_MODEL` | Model for `/embeddings`. If the call fails, zero vectors are stored and search falls back to keyword mode. |
| `STORAGE_BACKEND`, `LOCAL_STORAGE_PATH` | Where uploaded files are stored (the MVP supports local disk only). |

`gpt-5*` and `o*` reasoning models are detected automatically: requests send `max_completion_tokens` and omit `temperature`.

## Seed data

- **`seed_institutions.py`** seeds:
  - the ICC 2021, SIAC 2016 and LCIA 2020 institutions
  - procedure-stage rule records with article numbers and official source URLs
  - the RULES knowledge corpus
  - a small CONSTRUCTION corpus (overviews of FIDIC 20.1/8.4/8.7, the SCL Protocol, quantum practice and the prevention principle)
- **`seed_synthetic_case.py`** seeds the fictitious "International Airport Expansion Arbitration" (ICC, seat Singapore, English law):
  - 30 documents, with text stored in `ocr_text` and paragraph-chunked into `document_chunks`
  - 5 claims: EOT-01, EOT-02, LD-DEFENCE, VAR-001 and PAYMENT-FINAL
  - evidence links and 30 timeline events
  - 3 issues: Notice Compliance, Concurrent Delay and Quantum Methodology
  - an ICC procedural checklist

Both scripts are idempotent.

## API surface (`/api/v1`)

| Area | Endpoints |
|---|---|
| Auth | `POST /auth/register`, `POST /auth/login`, `GET /auth/me` |
| Cases | `GET/POST /cases`, `GET/PATCH/DELETE /cases/{id}`, parties, issues |
| Documents | `POST /cases/{id}/documents` (multipart upload), `GET /cases/{id}/documents`, `GET /documents/{id}` (returns a pre-signed download URL), `GET /documents/{id}/download?token=` |
| Timeline | `GET/POST /cases/{id}/timeline` |
| Claims | CRUD `/cases/{id}/claims`, `GET/POST /cases/{id}/claims/{claim_id}/evidence`, `GET /cases/{id}/evidence-matrix`, `GET /cases/{id}/evidence` |
| Procedure | `GET/POST /cases/{id}/procedure`, `POST /cases/{id}/procedure/generate`, `PATCH /cases/{id}/procedure/{event_id}` |
| Institutions | `GET /institutions`, `GET /institutions/comparison`, `GET /institutions/{id}/rules`, `GET /institutions/{id}/procedure/{stage}?ai=true` |
| AI | `POST /cases/{id}/analyze`, `POST /research`, `POST /documents/{id}/analyze`, `POST /documents/{id}/contract-analyze`, `POST /cases/{id}/claims/{claim_id}/analyze`, `POST /cases/{id}/evidence/analyze`, `POST /procedure`, `GET /cases/{id}/analyses`, `GET /analyses/{id}` |
| Search | `POST /search` with body `{query, corpus: rules\|construction\|case, case_id?, institution?, mode: keyword\|semantic\|hybrid}` |

Every route requires a bearer token except `/auth/login`, `/auth/register` and the signed download link. Case and document lookups are scoped by `org_id` and return 404 across tenants. Every AI call is stored in `ai_analyses` and `audit_logs`.

## AI agents

The seven agents are DocumentAgent, ContractAgent, EvidenceAgent, ProcedureAgent, ConstructionClaimsAgent, ResearchAgent and CaseIntelligenceAgent.

Each agent returns `{summary, findings[{label, content, citations}], evidence_gaps, requires_human_review, sources, model, agent}`, where `label` is one of `FACT | SOURCE_BASED_INFO | AI_SUMMARY | POTENTIAL_ISSUE | POTENTIAL_EVIDENCE_GAP | REQUIRES_HUMAN_REVIEW`.

Before a response is returned:

- `legal_safety_validator` removes outcome predictions and advice phrasing.
- `citation_validator` flags article or rule numbers that are not present in the retrieved sources.

## Tests

```bash
pip install -r apps/api/requirements-dev.txt
pytest -q           # from the repository root
```

The suite covers:

- tenant isolation: the CASE corpus requires `case_id`, no cross-case chunks are returned, and the API returns 404 across orgs
- the legal safety validator
- the citation validator
- model instantiation and round-trips
- agent post-processing and graceful degradation when the LLM is unavailable

## Crawler (institution rule sources)

The async crawler collects English-language pages and PDFs from ICC, SIAC, LCIA, HKIAC, ICSID and ICDR.

```bash
pip install -r requirements.txt
python -m crawler.cli --institution SIAC --max-pages 200 --out data/   # one institution
python -m crawler.cli --institution SIAC --dry-run                      # 5 pages to stdout
python -m crawler.cli --institution ALL --out data/                     # all institutions
python scripts/ingest/ingest_crawler_records.py --file data/records.jsonl   # load into the RULES corpus
```

| Flag | Default | Description |
|---|---|---|
| `--institution` | required | `ICC`, `SIAC`, `LCIA`, `HKIAC`, `ICSID`, `ICDR` or `ALL` |
| `--max-pages` | per-config (2000) | Maximum HTML and PDF records per institution |
| `--out` | `data/` | Output directory |
| `--dry-run` | off | Fetch about 5 pages and print JSONL to stdout |
| `--dry-run-limit` | 5 | Pages to fetch in dry-run mode |
| `--log-level` | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |

The crawler writes one record per page or PDF to `data/records.jsonl`, and stores PDFs as `data/pdfs/<INSTITUTION>/<sha256>.pdf`. Each record has these fields: `institution, url, content_type, title, published_date, language, text, pdf_path, pdf_sha256, pdf_pages, needs_ocr, crawled_at`. `needs_ocr: true` marks a scanned PDF with no extractable text.

It follows these rules:

- respects `robots.txt`
- makes at most 1 request per 2 seconds per domain
- crawls to a maximum depth of 4
- skips paths in languages other than English
- deduplicates by canonical URL and PDF SHA-256
- retries up to 3 times with exponential backoff

## Known limitations (MVP)

- **Rule summaries are paraphrased, not official text.** Every record links to the official source and must be verified against it. SIAC is seeded with the 2016 Rules; the SIAC Rules 2025 apply to arbitrations commenced on or after 1 January 2025.
- **No OCR yet.** Scanned PDFs and images are stored, but no text is extracted from them. Text is extracted from txt, eml and PDF files that have a text layer.
- **Local storage only.** S3 is not implemented yet; the storage interface is ready for it.
- **Embeddings may be unavailable.** If the gateway denies `/embeddings`, search falls back to keyword mode. Re-run the seeds once embeddings are available to backfill the vectors.
- **Synchronous AI calls.** An AI request can take 20–60 seconds with reasoning models, and there is no background job queue yet.
- **Token storage.** The JWT is kept in `localStorage`, which is acceptable for an MVP. Move it to httpOnly cookies before production.
