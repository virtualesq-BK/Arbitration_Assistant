"""Agent pipeline: safety + citation post-processing is applied to LLM output."""
from __future__ import annotations

import uuid
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from models import (
    ArbitrationInstitution,
    ArbitrationRule,
    Case,
    Claim,
    ClaimType,
    Document,
    DocumentType,
    Organization,
    ProcedureStage,
)
from services.agent_service import CaseIntelligenceAgent, EvidenceAgent, ProcedureAgent
from services.ingest_service import chunk_text, index_document
from services.llm_service import LLMError


async def _seed(db: AsyncSession, llm: Any) -> Case:
    org = Organization(id=uuid.uuid4(), name="Org")
    db.add(org)
    await db.flush()
    case = Case(id=uuid.uuid4(), org_id=org.id, title="Airport")
    db.add(case)
    await db.flush()
    doc = Document(id=uuid.uuid4(), case_id=case.id, org_id=org.id, filename="notice.txt",
                   document_type=DocumentType.NOTICE, ocr_text="Delay notice under Sub-Clause 8.4 dated 2023-06-01.")
    db.add(doc)
    db.add(Claim(id=uuid.uuid4(), case_id=case.id, claim_ref="EOT-01", claim_type=ClaimType.EOT, title="EOT 1"))
    inst = ArbitrationInstitution(id=uuid.uuid4(), name="ICC", short_name="ICC", rules_version="2021")
    db.add(inst)
    await db.flush()
    db.add(ArbitrationRule(institution_id=inst.id, stage=ProcedureStage.TERMS_OF_REFERENCE, article_number="Art. 23",
                           title="Terms of Reference", summary="The tribunal draws up Terms of Reference.", rule_version="2021"))
    await index_document(db, doc, llm)
    await db.commit()
    return case


@pytest.mark.asyncio
async def test_case_agent_sanitises_output(db: AsyncSession, mock_llm: Any) -> None:
    case = await _seed(db, mock_llm)
    mock_llm.next_response = {
        "summary": "The contractor will win this case.",
        "findings": [
            {"label": "SOURCE_BASED_INFO", "content": "ICC Rule 99 requires a reply.", "citations": ["S9"]},
            {"label": "FACT", "content": "A delay notice was issued.", "citations": ["D1"]},
        ],
        "evidence_gaps": [],
        "requires_human_review": [],
    }
    resp = await CaseIntelligenceAgent(mock_llm).analyze_case(str(case.id), db)
    assert "will win" not in resp.summary
    assert any("forbidden phrase" in r for r in resp.requires_human_review)
    assert any("99" in r for r in resp.requires_human_review), "ungrounded citation must be flagged"
    assert any("S9" in r for r in resp.requires_human_review), "unknown source id must be flagged"
    assert resp.evidence_gaps, "EOT claim with no linked evidence should produce gaps"
    assert resp.agent == "CaseIntelligenceAgent"


@pytest.mark.asyncio
async def test_agent_degrades_gracefully_without_llm(db: AsyncSession, mock_llm: Any) -> None:
    case = await _seed(db, mock_llm)

    async def boom(*_: Any, **__: Any) -> str:
        raise LLMError("gateway down")

    mock_llm.complete = boom  # type: ignore[method-assign]
    resp = await EvidenceAgent(mock_llm).analyze_case(str(case.id), db)
    assert resp.model.endswith("(unavailable)")
    assert any(f.label == "POTENTIAL_EVIDENCE_GAP" for f in resp.findings)


@pytest.mark.asyncio
async def test_procedure_agent_cites_seeded_rule(db: AsyncSession, mock_llm: Any) -> None:
    await _seed(db, mock_llm)
    resp = await ProcedureAgent(mock_llm).get_procedure("ICC", "TERMS_OF_REFERENCE", db=db)
    assert any(f.label == "SOURCE_BASED_INFO" and "Art. 23" in f.content for f in resp.findings)
    assert any(s.get("institution") == "ICC" for s in resp.sources)


def test_chunk_text_splits_paragraphs() -> None:
    text = "\n\n".join(f"Paragraph {i} " + "x" * 400 for i in range(6))
    chunks = chunk_text(text)
    assert len(chunks) >= 3
    assert all(len(c) <= 1500 for c in chunks)
