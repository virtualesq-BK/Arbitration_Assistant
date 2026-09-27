"""The seven ArbiConstruct AI agents.

Every agent follows the same pipeline:
  1. Gather tenant-scoped context from the database and RAG (CASE corpus always case-filtered).
  2. Produce deterministic, source-based findings that do not depend on the LLM.
  3. Ask the LLM for a labelled JSON analysis grounded ONLY in the supplied context.
  4. Post-process: legal-safety validation (no outcome predictions / legal advice) and
     citation validation (no references absent from retrieved sources).
If the LLM is unreachable the agent still returns the deterministic findings, flagged for review.
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.arbitration_institution import ArbitrationInstitution
from models.arbitration_rule import STAGE_ORDER, ArbitrationRule, ProcedureStage
from models.case import Case
from models.case_party import CaseParty
from models.claim import Claim
from models.claim_evidence import ClaimEvidence
from models.document import Document, DocumentType
from models.issue import Issue
from models.procedural_event import ProceduralEvent, ProceduralEventStatus
from models.timeline_event import TimelineEvent
from services import legal_safety_validator
from services.citation_validator import validate_many
from services.evidence_rules import compute_evidence_gaps
from services.llm_service import LLMError, LLMService, get_llm_service
from services.rag_service import Corpus, RAGService, RetrievedChunk

logger = logging.getLogger(__name__)

PROMPT_VERSION = "2026-09.v1"

LABELS = (
    "FACT",
    "SOURCE_BASED_INFO",
    "AI_SUMMARY",
    "POTENTIAL_ISSUE",
    "POTENTIAL_EVIDENCE_GAP",
    "REQUIRES_HUMAN_REVIEW",
)

SOURCE_NOT_FOUND = "Source not found."

SYSTEM_PROMPT = """You are an AI assistant inside ArbiConstruct AI, a case-management tool used by qualified \
lawyers and claims professionals working on international construction arbitrations.

PRODUCT BOUNDARY (mandatory):
- You ASSIST qualified professionals. You do NOT give legal advice, legal representation, or legal conclusions.
- Never predict outcomes, never estimate chances/probabilities of success, never say a party "will win" or is "liable".
- Use cautious language: "potentially", "may", "appears to", "the record suggests".
- Use ONLY the CONTEXT provided. Never invent facts, documents, dates, rule numbers or article numbers.
- Cite sources for every factual statement using the bracketed source ids given in the CONTEXT, e.g. [S1], [D3].
- If the context does not contain the information, say exactly "Source not found." rather than guessing.
- Anything that needs legal judgment must be labelled REQUIRES_HUMAN_REVIEW.

OUTPUT: respond with a single JSON object and nothing else:
{
  "summary": "2-5 sentence neutral summary",
  "findings": [
    {"label": "FACT|SOURCE_BASED_INFO|AI_SUMMARY|POTENTIAL_ISSUE|POTENTIAL_EVIDENCE_GAP|REQUIRES_HUMAN_REVIEW",
     "content": "one finding", "citations": ["S1", "D2"]}
  ],
  "evidence_gaps": ["..."],
  "requires_human_review": ["..."]
}
Label meanings: FACT = stated verbatim in a case document; SOURCE_BASED_INFO = drawn from institutional rules or \
reference sources; AI_SUMMARY = your synthesis; POTENTIAL_ISSUE = a point a lawyer may wish to examine; \
POTENTIAL_EVIDENCE_GAP = supporting material that appears to be missing; REQUIRES_HUMAN_REVIEW = needs legal judgment."""


@dataclass
class Finding:
    label: str  # FACT | SOURCE_BASED_INFO | AI_SUMMARY | POTENTIAL_ISSUE | POTENTIAL_EVIDENCE_GAP | REQUIRES_HUMAN_REVIEW
    content: str
    citations: list[str] = field(default_factory=list)


@dataclass
class AgentResponse:
    summary: str
    findings: list[Finding]
    evidence_gaps: list[str]
    requires_human_review: list[str]
    sources: list[dict[str, Any]]
    model: str
    agent: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# --------------------------------------------------------------------------- helpers
@dataclass
class _Source:
    sid: str
    label: str
    text: str
    meta: dict[str, Any]


class _ContextBuilder:
    """Collects numbered sources ([S#] reference sources, [D#] case documents) for the prompt."""

    def __init__(self) -> None:
        self.sources: list[_Source] = []
        self.retrieved: list[RetrievedChunk] = []
        self._doc_n = 0
        self._ref_n = 0

    def add_document(self, doc: Document, text: str | None = None, chunk_index: int | None = None) -> str:
        self._doc_n += 1
        sid = f"D{self._doc_n}"
        label = f"{doc.filename} ({doc.document_type.value}{', ' + doc.doc_date.isoformat() if doc.doc_date else ''})"
        self.sources.append(
            _Source(
                sid,
                label,
                text if text is not None else (doc.ocr_text or ""),
                {
                    "id": sid,
                    "type": "case_document",
                    "document_id": str(doc.id),
                    "filename": doc.filename,
                    "document_type": doc.document_type.value,
                    "doc_date": doc.doc_date.isoformat() if doc.doc_date else None,
                    "chunk_index": chunk_index,
                },
            )
        )
        return sid

    def add_chunk(self, chunk: RetrievedChunk) -> str:
        self.retrieved.append(chunk)
        if chunk.document_id is not None:
            self._doc_n += 1
            sid = f"D{self._doc_n}"
            kind = "case_document"
        else:
            self._ref_n += 1
            sid = f"S{self._ref_n}"
            kind = "rule" if chunk.institution else "reference"
        meta = {"id": sid, "type": kind, **chunk.to_dict()}
        self.sources.append(_Source(sid, chunk.citation_label(), chunk.text, meta))
        return sid

    def add_rule(self, rule: ArbitrationRule, inst: ArbitrationInstitution) -> str:
        chunk = RetrievedChunk(
            text=f"{rule.article_number} — {rule.title}: {rule.summary}",
            source_name=f"{inst.short_name} Rules {rule.rule_version or inst.rules_version or ''} {rule.article_number}".strip(),
            source_url=rule.source_url or inst.rules_url,
            institution=inst.short_name,
            rule_version=rule.rule_version or inst.rules_version,
            document_id=None,
            chunk_index=None,
            confidence=1.0,
        )
        return self.add_chunk(chunk)

    def render(self, max_chars_per_source: int = 2500, max_total: int = 40000) -> str:
        if not self.sources:
            return "(no sources were retrieved)"
        parts: list[str] = []
        total = 0
        for s in self.sources:
            body = s.text[:max_chars_per_source]
            block = f"[{s.sid}] {s.label}\n{body}"
            if total + len(block) > max_total:
                parts.append(f"[{s.sid}] {s.label}\n(truncated for length)")
                continue
            parts.append(block)
            total += len(block)
        return "\n\n---\n\n".join(parts)

    def source_dicts(self) -> list[dict[str, Any]]:
        return [s.meta for s in self.sources]

    def valid_ids(self) -> set[str]:
        return {s.sid for s in self.sources}


def _parse_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1).strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("No JSON object in model output")
    data = json.loads(cleaned[start : end + 1])
    if not isinstance(data, dict):
        raise ValueError("Model output is not a JSON object")
    return data


def _as_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(v).strip() for v in value if str(v).strip()]


class _BaseAgent:
    name = "BaseAgent"
    max_tokens = 2000

    def __init__(self, llm: LLMService | None = None) -> None:
        self.llm = llm or get_llm_service()

    async def _run(
        self,
        task: str,
        ctx: _ContextBuilder,
        deterministic: list[Finding] | None = None,
        gaps: list[str] | None = None,
        review: list[str] | None = None,
        fallback_summary: str | None = None,
    ) -> AgentResponse:
        deterministic = deterministic or []
        gaps = list(gaps or [])
        review = list(review or [])
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"TASK:\n{task}\n\nCONTEXT:\n{ctx.render()}"},
        ]

        llm_summary: str | None = None
        llm_findings: list[Finding] = []
        model_name = self.llm.model
        try:
            raw = await self.llm.complete(messages, max_tokens=self.max_tokens)
            data = _parse_json(raw)
            llm_summary = str(data.get("summary") or "").strip() or None
            valid_ids = ctx.valid_ids()
            for item in data.get("findings") or []:
                if not isinstance(item, dict) or not str(item.get("content") or "").strip():
                    continue
                label = str(item.get("label") or "AI_SUMMARY").upper().strip()
                if label not in LABELS:
                    label = "AI_SUMMARY"
                cites = _as_str_list(item.get("citations"))
                cleaned_cites = [c.strip("[] ") for c in cites]
                unknown = [c for c in cleaned_cites if c not in valid_ids]
                if unknown:
                    review.append(
                        f"Finding cites unknown source id(s) {', '.join(unknown)} — {SOURCE_NOT_FOUND} Verify manually."
                    )
                    cleaned_cites = [c for c in cleaned_cites if c in valid_ids]
                if label in ("FACT", "SOURCE_BASED_INFO") and not cleaned_cites:
                    # An uncited "fact" is not a fact: downgrade it.
                    label = "REQUIRES_HUMAN_REVIEW"
                llm_findings.append(Finding(label, str(item["content"]).strip(), cleaned_cites))
            for g in _as_str_list(data.get("evidence_gaps")):
                if g not in gaps:
                    gaps.append(g)
            for r in _as_str_list(data.get("requires_human_review")):
                if r not in review:
                    review.append(r)
        except LLMError as exc:
            model_name = f"{self.llm.model} (unavailable)"
            review.append(f"AI model call failed ({exc}); only deterministic, source-based findings are shown.")
        except (ValueError, json.JSONDecodeError) as exc:
            logger.warning("%s: could not parse model output: %s", self.name, exc)
            review.append("AI model returned an unstructured response; only deterministic findings are shown.")

        if llm_summary is None:
            # Without a model answer, surface the top retrieved passages verbatim so the user still
            # gets source-based information (never synthesised text).
            already = {c for f in deterministic for c in f.citations}
            for src in ctx.sources:
                if src.meta.get("type") in ("rule", "reference", "case_document") and src.sid not in already:
                    excerpt = src.text[:400] + ("…" if len(src.text) > 400 else "")
                    deterministic.append(Finding("SOURCE_BASED_INFO", f"{src.label}: {excerpt}", [src.sid]))
                    already.add(src.sid)
                if len(already) >= 8:
                    break

        summary = llm_summary or fallback_summary or SOURCE_NOT_FOUND
        return self._finalize(summary, deterministic, llm_findings, gaps, review, ctx, model_name, summary_generated=llm_summary is not None)

    def _finalize(
        self,
        summary: str,
        deterministic: list[Finding],
        generated: list[Finding],
        gaps: list[str],
        review: list[str],
        ctx: _ContextBuilder,
        model_name: str,
        summary_generated: bool = True,
    ) -> AgentResponse:
        findings = deterministic + generated
        # 1) Legal-safety validation over every piece of generated text.
        safe_summary, w = legal_safety_validator.validate(summary)
        warnings = list(w)
        safe_findings: list[Finding] = []
        for f in findings:
            content, fw = legal_safety_validator.validate(f.content)
            warnings.extend(fw)
            label = "REQUIRES_HUMAN_REVIEW" if fw else f.label
            safe_findings.append(Finding(label, content, f.citations))
        safe_gaps = []
        for g in gaps:
            sg, gw = legal_safety_validator.validate(g)
            warnings.extend(gw)
            safe_gaps.append(sg)

        # 2) Citation validation: rule/article numbers in MODEL-GENERATED text must appear in retrieved
        #    sources. Deterministic findings quote database records verbatim and are not re-checked.
        generated_texts = [f.content for f in safe_findings[len(deterministic):]]
        if summary_generated:
            generated_texts.insert(0, safe_summary)
        _, cite_warnings = validate_many(generated_texts, ctx.retrieved)

        review_out: list[str] = []
        for item in [*review, *warnings, *cite_warnings]:
            if item not in review_out:
                review_out.append(item)

        return AgentResponse(
            summary=safe_summary,
            findings=safe_findings,
            evidence_gaps=safe_gaps,
            requires_human_review=review_out,
            sources=ctx.source_dicts(),
            model=model_name,
            agent=self.name,
        )


_DATE_RE = re.compile(
    r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})\b"
)
_PRIVILEGE_RE = re.compile(
    r"\b(privileged|without prejudice|legal advice|attorney[- ]client|solicitor[- ]client|prepared at the request of counsel)\b",
    re.IGNORECASE,
)
_CLAUSE_RE = re.compile(r"\b(?:Sub-Clause|Clause)\s+(\d+(?:\.\d+)*)", re.IGNORECASE)
_CONTRACT_TOPICS: dict[str, str] = {
    "notice": r"\bnotice\b|\bnotify\b",
    "time bar": r"time[- ]bar|within\s+\d+\s+days|28\s+days",
    "liquidated damages": r"liquidated damages|delay damages",
    "extension of time": r"extension of time|\bEOT\b",
    "variation": r"\bvariation",
    "payment": r"\bpayment|interim payment|payment certificate",
    "dispute resolution": r"\barbitration\b|dispute (?:adjudication|avoidance)|\bDAAB\b|\bDAB\b",
    "termination": r"\bterminat",
}


async def _load_case(case_id: uuid.UUID, db: AsyncSession) -> Case:
    case = await db.get(Case, case_id)
    if case is None:
        raise LookupError("Case not found")
    return case


async def _load_institution(short_name: str, db: AsyncSession) -> ArbitrationInstitution | None:
    return (
        await db.execute(select(ArbitrationInstitution).where(ArbitrationInstitution.short_name == short_name.upper()))
    ).scalar_one_or_none()


# --------------------------------------------------------------------------- agents
class DocumentAgent(_BaseAgent):
    name = "DocumentAgent"

    async def analyze(self, document_id: str, db: AsyncSession) -> AgentResponse:
        doc = await db.get(Document, uuid.UUID(str(document_id)))
        if doc is None:
            raise LookupError("Document not found")
        ctx = _ContextBuilder()
        text = (doc.ocr_text or "")[:12000]
        sid = ctx.add_document(doc, text)

        det: list[Finding] = [
            Finding("FACT", f"Document type recorded as {doc.document_type.value}.", [sid]),
        ]
        if doc.doc_date:
            det.append(Finding("FACT", f"Document dated {doc.doc_date.isoformat()}.", [sid]))
        if doc.author:
            det.append(Finding("FACT", f"Author: {doc.author}" + (f"; recipient: {doc.recipient}" if doc.recipient else ""), [sid]))
        dates = list(dict.fromkeys(_DATE_RE.findall(text)))[:10]
        if dates:
            det.append(Finding("FACT", f"Dates mentioned in the document: {', '.join(dates)}.", [sid]))
        review: list[str] = []
        if _PRIVILEGE_RE.search(text):
            det.append(
                Finding(
                    "REQUIRES_HUMAN_REVIEW",
                    "POTENTIALLY_PRIVILEGED: the text contains privilege-related wording. "
                    "Privilege status must be determined by a qualified lawyer.",
                    [sid],
                )
            )
            review.append("Document flagged POTENTIALLY_PRIVILEGED — confirm privilege status before any disclosure.")
        if not text.strip():
            review.append("No extracted text available (scanned or unsupported file); OCR / manual review required.")

        task = (
            "Analyse this single case document for an arbitration team. Identify: its purpose, key facts "
            "(parties, dates, amounts, instructions), any notices or time-sensitive statements, and points a "
            "lawyer may wish to examine. Cite the document id for every fact."
        )
        resp = await self._run(task, ctx, det, review=review, fallback_summary=f"Document {doc.filename} ({doc.document_type.value}).")
        return resp


class ContractAgent(_BaseAgent):
    name = "ContractAgent"

    async def analyze(self, document_id: str, db: AsyncSession) -> AgentResponse:
        doc = await db.get(Document, uuid.UUID(str(document_id)))
        if doc is None:
            raise LookupError("Document not found")
        case = await db.get(Case, doc.case_id)
        ctx = _ContextBuilder()
        text = (doc.ocr_text or "")[:15000]
        sid = ctx.add_document(doc, text)

        det: list[Finding] = []
        review: list[str] = []
        if doc.document_type not in (DocumentType.CONTRACT, DocumentType.AMENDMENT):
            review.append(f"Document is typed {doc.document_type.value}, not CONTRACT — contract analysis may be incomplete.")
        clauses = list(dict.fromkeys(_CLAUSE_RE.findall(text)))
        if clauses:
            det.append(Finding("FACT", f"Clauses referenced: {', '.join(clauses[:25])}.", [sid]))
        for topic, pattern in _CONTRACT_TOPICS.items():
            if re.search(pattern, text, re.IGNORECASE):
                det.append(Finding("AI_SUMMARY", f"The contract text addresses {topic}.", [sid]))
            elif topic in ("notice", "dispute resolution", "liquidated damages"):
                det.append(
                    Finding("POTENTIAL_ISSUE", f"No {topic} provision was located in the extracted text — verify against the full contract.", [sid])
                )

        if case is not None:
            rag = RAGService(db, self.llm)
            for chunk in await rag.retrieve(
                "arbitration agreement seat governing law notice of arbitration",
                Corpus.RULES,
                institution=case.institution.value,
                top_k=3,
            ):
                ctx.add_chunk(chunk)

        task = (
            "Review this construction contract for an arbitration team. Extract: contract price and dates, "
            "notice and time-bar provisions, extension of time and liquidated damages mechanisms, variation "
            "and payment provisions, and the dispute resolution / arbitration clause (institution, seat, law). "
            "Quote clause numbers exactly as they appear. Flag ambiguities as POTENTIAL_ISSUE."
        )
        return await self._run(task, ctx, det, review=review, fallback_summary=f"Contract review of {doc.filename}.")


class EvidenceAgent(_BaseAgent):
    name = "EvidenceAgent"

    async def analyze_case(self, case_id: str, db: AsyncSession) -> AgentResponse:
        cid = uuid.UUID(str(case_id))
        case = await _load_case(cid, db)
        ctx = _ContextBuilder()

        claims = (await db.execute(select(Claim).where(Claim.case_id == cid).order_by(Claim.claim_ref))).scalars().all()
        links = (
            await db.execute(
                select(ClaimEvidence, Document)
                .join(Document, Document.id == ClaimEvidence.document_id)
                .join(Claim, Claim.id == ClaimEvidence.claim_id)
                .where(Claim.case_id == cid, Document.case_id == cid)
            )
        ).all()
        doc_sid: dict[uuid.UUID, str] = {}
        by_claim: dict[uuid.UUID, list[str]] = {}
        for link, doc in links:
            if doc.id not in doc_sid:
                doc_sid[doc.id] = ctx.add_document(doc, (doc.ocr_text or "")[:800])
            by_claim.setdefault(link.claim_id, []).append(doc_sid[doc.id])

        det: list[Finding] = []
        for claim in claims:
            sids = by_claim.get(claim.id, [])
            det.append(
                Finding(
                    "FACT",
                    f"{claim.claim_ref} ({claim.claim_type.value}) has {len(sids)} linked supporting document(s).",
                    sids,
                )
            )

        gaps_struct = await compute_evidence_gaps(cid, db)
        gaps = [m for g in gaps_struct for m in g.messages]
        for g in gaps_struct:
            det.append(Finding("POTENTIAL_EVIDENCE_GAP", " ".join(g.messages), []))

        all_docs = (await db.execute(select(Document).where(Document.case_id == cid))).scalars().all()
        unlinked = [d for d in all_docs if d.id not in doc_sid]
        if unlinked:
            det.append(
                Finding(
                    "AI_SUMMARY",
                    f"{len(unlinked)} of {len(all_docs)} case documents are not linked to any claim "
                    f"(e.g. {', '.join(d.filename for d in unlinked[:5])}).",
                    [],
                )
            )

        task = (
            f"Case: {case.title}. Review the evidence linked to each claim (below). Identify which claims appear "
            "well supported by contemporaneous records, where supporting evidence appears thin, and what kinds "
            "of additional records a claims team may wish to locate. Do not assess the merits."
        )
        return await self._run(
            task, ctx, det, gaps=gaps, fallback_summary=f"Evidence review for {len(claims)} claim(s); {len(gaps_struct)} with potential gaps."
        )


class ProcedureAgent(_BaseAgent):
    name = "ProcedureAgent"

    async def get_procedure(
        self, institution: str, stage: str | None = None, *, db: AsyncSession
    ) -> AgentResponse:
        ctx = _ContextBuilder()
        det: list[Finding] = []
        review: list[str] = []
        inst = await _load_institution(institution, db)
        stage_enum: ProcedureStage | None = None
        if stage:
            try:
                stage_enum = ProcedureStage(stage.upper())
            except ValueError:
                review.append(f"Unknown procedure stage '{stage}'.")

        rules: list[ArbitrationRule] = []
        if inst is not None:
            stmt = select(ArbitrationRule).where(ArbitrationRule.institution_id == inst.id)
            if stage_enum is not None:
                stmt = stmt.where(ArbitrationRule.stage == stage_enum)
            rules = list((await db.execute(stmt)).scalars().all())
            rules.sort(key=lambda r: STAGE_ORDER.index(r.stage))
            for rule in rules:
                sid = ctx.add_rule(rule, inst)
                det.append(
                    Finding(
                        "SOURCE_BASED_INFO",
                        f"{inst.short_name} Rules {rule.rule_version or inst.rules_version}, {rule.article_number} — "
                        f"{rule.title}: {rule.summary}",
                        [sid],
                    )
                )
        if inst is None or not rules:
            det.append(Finding("REQUIRES_HUMAN_REVIEW", f"{SOURCE_NOT_FOUND} No seeded rule for {institution} / {stage or 'all stages'}.", []))

        rag = RAGService(db, self.llm)
        query = f"{institution} {stage_enum.value.replace('_', ' ').lower() if stage_enum else 'arbitration procedure'}"
        for chunk in await rag.retrieve(query, Corpus.RULES, institution=institution, top_k=3):
            if not any(chunk.text == r.text for r in ctx.retrieved):
                ctx.add_chunk(chunk)

        review.append(
            "Procedural deadlines depend on the arbitration agreement, procedural orders and the tribunal's "
            "directions — confirm against the official rules text and the case file."
        )
        task = (
            f"Explain the {institution.upper()} arbitration procedure"
            + (f" for the stage {stage_enum.value}" if stage_enum else "")
            + ". Describe what typically happens, who acts, and any time limits, citing ONLY the rule sources given "
            "(institution, rule version, article number). If a detail is not in the sources, say 'Source not found.'"
        )
        return await self._run(task, ctx, det, review=review, fallback_summary=f"{institution.upper()} procedure summary from seeded rule records.")


class ConstructionClaimsAgent(_BaseAgent):
    name = "ConstructionClaimsAgent"

    async def analyze_claim(self, claim_id: str, db: AsyncSession) -> AgentResponse:
        claim = await db.get(Claim, uuid.UUID(str(claim_id)))
        if claim is None:
            raise LookupError("Claim not found")
        case = await _load_case(claim.case_id, db)
        ctx = _ContextBuilder()

        links = (
            await db.execute(
                select(ClaimEvidence, Document)
                .join(Document, Document.id == ClaimEvidence.document_id)
                .where(ClaimEvidence.claim_id == claim.id, Document.case_id == case.id)
            )
        ).all()
        det: list[Finding] = [
            Finding(
                "FACT",
                f"{claim.claim_ref} — {claim.title} ({claim.claim_type.value})"
                + (f", quantum {claim.currency or ''} {claim.quantum:,.2f}" if claim.quantum is not None else "")
                + (f", contract clause {claim.contract_clause}" if claim.contract_clause else "")
                + ".",
                [],
            )
        ]
        for link, doc in links:
            sid = ctx.add_document(doc, (doc.ocr_text or "")[:2000])
            if link.relevance_note:
                det.append(Finding("FACT", f"Linked evidence {doc.filename}: {link.relevance_note}", [sid]))

        rag = RAGService(db, self.llm)
        linked_ids = {str(doc.id) for _, doc in links}
        for chunk in await rag.retrieve(
            f"{claim.title} {claim.description or ''}", Corpus.CASE, case_id=str(case.id), top_k=5, org_id=str(case.org_id)
        ):
            if chunk.document_id not in linked_ids:  # linked documents are already in context in full
                ctx.add_chunk(chunk)
        for chunk in await rag.retrieve(f"{claim.claim_type.value} {claim.title}", Corpus.CONSTRUCTION, top_k=3):
            ctx.add_chunk(chunk)

        gaps_struct = await compute_evidence_gaps(case.id, db, claim_id=claim.id)
        gaps = [m for g in gaps_struct for m in g.messages]

        task = (
            f"Analyse construction claim {claim.claim_ref} ({claim.claim_type.value}): {claim.title}. "
            f"Description: {claim.description or 'n/a'}. Identify the factual basis in the documents, the "
            "contractual mechanism relied on, notice / time-bar compliance points, causation and quantum "
            "evidence, and counter-arguments the other side may raise. Label anything requiring legal judgment "
            "as REQUIRES_HUMAN_REVIEW. Do not assess the likelihood of success."
        )
        return await self._run(task, ctx, det, gaps=gaps, fallback_summary=f"Claim {claim.claim_ref}: {claim.title}.")


class ResearchAgent(_BaseAgent):
    name = "ResearchAgent"

    async def research(
        self,
        query: str,
        institution: str | None = None,
        *,
        db: AsyncSession,
        case_id: str | None = None,
        org_id: str | None = None,
    ) -> AgentResponse:
        ctx = _ContextBuilder()
        rag = RAGService(db, self.llm)
        for chunk in await rag.retrieve(query, Corpus.RULES, institution=institution, top_k=5):
            ctx.add_chunk(chunk)
        for chunk in await rag.retrieve(query, Corpus.CONSTRUCTION, top_k=3):
            ctx.add_chunk(chunk)
        if case_id:
            for chunk in await rag.retrieve(query, Corpus.CASE, case_id=case_id, org_id=org_id, top_k=5):
                ctx.add_chunk(chunk)

        det: list[Finding] = []
        review: list[str] = []
        if not ctx.sources:
            det.append(Finding("REQUIRES_HUMAN_REVIEW", f"{SOURCE_NOT_FOUND} No indexed source matched the query.", []))
            review.append("No sources retrieved — the answer cannot be grounded; consult primary sources.")
        task = (
            f"Research question: {query}\n"
            + (f"Institution focus: {institution}\n" if institution else "")
            + "Answer using only the sources. For rules, cite institution, rule version and article number. "
            "If the sources do not answer the question, say 'Source not found.'"
        )
        return await self._run(task, ctx, det, review=review, fallback_summary=SOURCE_NOT_FOUND if not ctx.sources else "Retrieved sources listed below.")


class CaseIntelligenceAgent(_BaseAgent):
    name = "CaseIntelligenceAgent"
    max_tokens = 3000

    async def analyze_case(self, case_id: str, db: AsyncSession) -> AgentResponse:
        cid = uuid.UUID(str(case_id))
        case = await _load_case(cid, db)
        ctx = _ContextBuilder()
        det: list[Finding] = []
        review: list[str] = []

        parties = (await db.execute(select(CaseParty).where(CaseParty.case_id == cid))).scalars().all()
        claims = (await db.execute(select(Claim).where(Claim.case_id == cid).order_by(Claim.claim_ref))).scalars().all()
        issues = (await db.execute(select(Issue).where(Issue.case_id == cid))).scalars().all()
        timeline = (
            await db.execute(select(TimelineEvent).where(TimelineEvent.case_id == cid).order_by(TimelineEvent.event_date))
        ).scalars().all()
        proc = (
            await db.execute(select(ProceduralEvent).where(ProceduralEvent.case_id == cid).order_by(ProceduralEvent.due_date))
        ).scalars().all()

        party_txt = "; ".join(f"{p.name} ({p.role.value})" for p in parties) or "n/a"
        claim_txt = "; ".join(
            " ".join(str(x) for x in (c.claim_ref, c.claim_type.value, c.title, c.currency or "", c.quantum or "") if x != "")
            for c in claims
        ) or "none"
        issue_txt = "; ".join(f"{i.title} [{i.severity.value}]" for i in issues) or "none"
        amount = case.amount_in_dispute if case.amount_in_dispute is not None else "n/a"
        overview = (
            f"Case: {case.title} | Institution: {case.institution.value} | Seat: {case.seat or 'n/a'} | "
            f"Governing law: {case.governing_law or 'n/a'} | Amount in dispute: {case.currency or ''} {amount}\n"
            f"Parties: {party_txt}\nClaims: {claim_txt}\nRecorded issues: {issue_txt}"
        )
        ctx.sources.append(_Source("C1", "Case record (structured data)", overview, {"id": "C1", "type": "case_record", "case_id": str(cid)}))
        det.append(Finding("FACT", f"{case.institution.value} arbitration seated in {case.seat or 'n/a'}; governing law {case.governing_law or 'n/a'}.", ["C1"]))

        if timeline:
            tl_text = "\n".join(f"{e.event_date.isoformat()}: {e.description}" for e in timeline[:60])
            ctx.sources.append(_Source("T1", "Case chronology", tl_text, {"id": "T1", "type": "timeline", "case_id": str(cid)}))
            det.append(
                Finding(
                    "FACT",
                    f"Chronology spans {timeline[0].event_date.isoformat()} to {timeline[-1].event_date.isoformat()} ({len(timeline)} events).",
                    ["T1"],
                )
            )

        today = date.today()
        for ev in proc:
            if ev.status in (ProceduralEventStatus.COMPLETED, ProceduralEventStatus.NOT_APPLICABLE):
                continue
            if ev.due_date and ev.due_date < today:
                det.append(
                    Finding("POTENTIAL_ISSUE", f"Procedural step '{ev.title or ev.event_type}' was due {ev.due_date.isoformat()} and is not marked complete ({ev.rule_reference or 'no rule reference'}).", [])
                )
            if ev.requires_confirmation:
                review.append(f"AI-suggested procedural step '{ev.title or ev.event_type}' awaits human confirmation.")

        for issue in issues:
            det.append(Finding("POTENTIAL_ISSUE", f"{issue.title} ({issue.severity.value}): {issue.description or ''}".strip(), ["C1"]))

        gaps_struct = await compute_evidence_gaps(cid, db)
        gaps = [m for g in gaps_struct for m in g.messages]

        rag = RAGService(db, self.llm)
        for chunk in await rag.retrieve(
            "delay notice extension of time claim concurrent delay quantum payment arbitration",
            Corpus.CASE,
            case_id=str(cid),
            org_id=str(case.org_id),
            top_k=8,
        ):
            ctx.add_chunk(chunk)
        for chunk in await rag.retrieve("terms of reference case management procedural timetable", Corpus.RULES, institution=case.institution.value, top_k=3):
            ctx.add_chunk(chunk)

        task = (
            "Provide a case intelligence briefing for the arbitration team: (1) a neutral summary of the dispute, "
            "(2) key facts from the chronology and documents, (3) potential issues a lawyer may wish to examine "
            "(notice compliance, concurrent delay, quantum methodology, procedural steps), (4) potential evidence "
            "gaps, and (5) items that require human legal review. Do not predict the outcome."
        )
        return await self._run(task, ctx, det, gaps=gaps, review=review, fallback_summary=f"Briefing for {case.title}.")


AGENTS: dict[str, type[_BaseAgent]] = {
    cls.name: cls
    for cls in (
        DocumentAgent,
        ContractAgent,
        EvidenceAgent,
        ProcedureAgent,
        ConstructionClaimsAgent,
        ResearchAgent,
        CaseIntelligenceAgent,
    )
}
