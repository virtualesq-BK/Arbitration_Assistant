"""Instantiate each model, check required columns, and round-trip them through the database."""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.ext.asyncio import AsyncSession

from models import (
    AIAnalysis,
    ArbitrationInstitution,
    ArbitrationInstitutionEnum,
    ArbitrationRule,
    AuditLog,
    Base,
    Case,
    CaseParty,
    CaseStatus,
    Claim,
    ClaimEvidence,
    ClaimType,
    ConfidentialityLevel,
    Document,
    DocumentChunk,
    DocumentType,
    Issue,
    KnowledgeChunk,
    Organization,
    OrganizationMember,
    PartyRole,
    ProceduralEvent,
    ProcedureStage,
    TimelineEvent,
    User,
    UserRole,
)

EXPECTED_REQUIRED = {
    "users": {"email", "hashed_password", "role", "org_id"},
    "organizations": {"name"},
    "organization_members": {"org_id", "user_id", "role"},
    "cases": {"org_id", "title", "institution", "status"},
    "case_parties": {"case_id", "name", "role"},
    "documents": {"case_id", "org_id", "filename", "document_type", "confidentiality_level"},
    "document_chunks": {"document_id", "chunk_index", "text", "case_id", "org_id"},
    "knowledge_chunks": {"corpus", "source_name", "text"},
    "timeline_events": {"case_id", "event_date", "description"},
    "claims": {"case_id", "claim_ref", "claim_type", "title"},
    "claim_evidence": {"claim_id", "document_id"},
    "issues": {"case_id", "title"},
    "arbitration_institutions": {"name", "short_name"},
    "arbitration_rules": {"institution_id", "stage", "article_number", "title", "summary"},
    "procedural_events": {"case_id", "event_type"},
    "ai_analyses": {"agent", "model_name", "prompt_version"},
    "audit_logs": {"action", "resource_type"},
}


@pytest.mark.parametrize("table_name,required", sorted(EXPECTED_REQUIRED.items()))
def test_required_columns_are_not_nullable(table_name: str, required: set[str]) -> None:
    table = Base.metadata.tables[table_name]
    for col in required | {"id", "created_at", "updated_at"}:
        assert col in table.c, f"{table_name}.{col} missing"
        assert table.c[col].nullable is False, f"{table_name}.{col} should be NOT NULL"


def test_embedding_dimension() -> None:
    col = Base.metadata.tables["document_chunks"].c["embedding"]
    assert getattr(col.type, "dim", 1536) == 1536


def test_enum_values() -> None:
    assert {r.value for r in UserRole} == {"ORG_ADMIN", "CASE_MANAGER", "LAWYER", "LEGAL_TEAM", "CLAIMS_TEAM", "VIEWER"}
    assert "ATTORNEY_WORK_PRODUCT" in {c.value for c in ConfidentialityLevel}
    assert len(list(DocumentType)) == 25
    assert len(list(ProcedureStage)) == 19
    assert {c.value for c in ClaimType} >= {"EOT", "LD_DEFENCE", "VARIATION", "PAYMENT"}


@pytest.mark.asyncio
async def test_round_trip_all_models(db: AsyncSession) -> None:
    org = Organization(id=uuid.uuid4(), name="Demo Legal LLP")
    db.add(org)
    await db.flush()
    user = User(id=uuid.uuid4(), email="x@example.com", hashed_password="h", full_name="X", role=UserRole.LAWYER, org_id=org.id)
    db.add(user)
    await db.flush()
    db.add(OrganizationMember(org_id=org.id, user_id=user.id, role=UserRole.LAWYER))
    case = Case(id=uuid.uuid4(), org_id=org.id, title="T", institution=ArbitrationInstitutionEnum.ICC,
                amount_in_dispute=Decimal("250000000.00"), currency="USD")
    db.add(case)
    await db.flush()
    db.add(CaseParty(case_id=case.id, name="ABC Construction Ltd", role=PartyRole.CONTRACTOR))
    doc = Document(id=uuid.uuid4(), case_id=case.id, org_id=org.id, filename="c.txt", document_type=DocumentType.CONTRACT,
                   doc_date=date(2022, 11, 1), metadata_json={"k": "v"})
    db.add(doc)
    await db.flush()
    db.add(DocumentChunk(document_id=doc.id, chunk_index=0, text="t", embedding=[0.1] * 1536, case_id=case.id, org_id=org.id))
    inst = ArbitrationInstitution(id=uuid.uuid4(), name="International Chamber of Commerce", short_name="ICC", rules_version="2021")
    db.add(inst)
    await db.flush()
    rule = ArbitrationRule(id=uuid.uuid4(), institution_id=inst.id, stage=ProcedureStage.TERMS_OF_REFERENCE,
                           article_number="Art. 23", title="Terms of Reference", summary="s")
    db.add(rule)
    await db.flush()
    db.add(KnowledgeChunk(corpus="rules", source_name="ICC Rules 2021", text="t", institution="ICC", rule_id=rule.id))
    db.add(TimelineEvent(case_id=case.id, event_date=date(2023, 1, 15), description="NTP", source_document_id=doc.id))
    claim = Claim(id=uuid.uuid4(), case_id=case.id, claim_ref="EOT-01", claim_type=ClaimType.EOT, title="EOT 1")
    db.add(claim)
    await db.flush()
    db.add(ClaimEvidence(claim_id=claim.id, document_id=doc.id, relevance_note="n"))
    db.add(Issue(case_id=case.id, title="Notice Compliance"))
    db.add(ProceduralEvent(case_id=case.id, event_type=ProcedureStage.TERMS_OF_REFERENCE.value))
    db.add(AIAnalysis(case_id=case.id, user_id=user.id, agent="CaseIntelligenceAgent", model_name="m", prompt_version="v",
                      output_json={"summary": "s"}))
    db.add(AuditLog(org_id=org.id, user_id=user.id, action="a", resource_type="r"))
    await db.commit()

    fetched = await db.get(Case, case.id)
    assert fetched is not None
    assert fetched.status == CaseStatus.ACTIVE  # default applied
    assert fetched.amount_in_dispute == Decimal("250000000.00")
    fetched_doc = await db.get(Document, doc.id)
    assert fetched_doc is not None and fetched_doc.metadata_json == {"k": "v"}
    assert fetched_doc.confidentiality_level == ConfidentialityLevel.CONFIDENTIAL
    # every mapped class has a primary key "id"
    for cls in (User, Organization, Case, Document, Claim, ArbitrationRule):
        assert [c.name for c in sa_inspect(cls).primary_key] == ["id"]
