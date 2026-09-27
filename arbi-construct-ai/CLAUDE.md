# ArbiConstruct AI — CLAUDE.md

## Project Purpose
AI-powered International Construction Arbitration Case Management platform.

## CRITICAL: AI Product Boundary
AI ASSISTS humans. AI does NOT:
- Provide final legal advice
- Provide legal representation
- Make definitive outcome predictions
- Replace qualified legal professionals

All AI output must be labeled (FACT / SOURCE_BASED_INFO / AI_SUMMARY / POTENTIAL_ISSUE / REQUIRES_HUMAN_REVIEW).

## Architecture
- Backend: FastAPI + PostgreSQL + pgvector (apps/api/)
- Frontend: Next.js 14 + TypeScript + Tailwind (apps/web/)
- Crawler: Python httpx crawler (crawler/)
- RAG: 3 separate corpora (RULES, CONSTRUCTION, CASE)

## Coding Standards
### Python
- Type hints on all functions
- No bare except clauses (always except SpecificError)
- Async I/O throughout (no blocking in async functions)
- All DB queries filtered by org_id or case_id (tenant isolation)

### TypeScript
- Strict mode
- No any types
- API calls only through lib/api.ts

## RAG Rules
1. CASE corpus: ALWAYS filter by case_id. Never return chunks from another case.
2. RULES corpus: cite institution name, rule version, article number, source URL
3. Never fabricate citations. If source not found, say "Source not found."

## Security Rules
1. All routes require authentication except /auth/login and /auth/register
2. All case/document queries must include org_id filter
3. Audit all AI analysis calls (AIAnalysis table)

## Git
- Conventional commits: feat:, fix:, docs:, test:
- Feature branches from main
