"""Seed the synthetic demo case: org, user, case, parties, 30 documents (+chunks), claims,
evidence links, timeline, issues and procedural checklist.

Usage (from the repository root, after seed_institutions.py):
    python scripts/seed/seed_synthetic_case.py

Idempotent: an existing "Demo Legal LLP" organisation (and everything under it) is deleted first.
Demo login: demo@arbiconstruct.ai / Demo1234!
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import uuid
from datetime import date
from decimal import Decimal

import _common  # noqa: F401  (sys.path bootstrap)
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import AsyncSessionLocal, engine
from core.security import hash_password
from models import (
    AIAnalysis,
    ArbitrationInstitution,
    AuditLog,
    ArbitrationInstitutionEnum,
    ArbitrationRule,
    Case,
    CaseParty,
    CaseStatus,
    Claim,
    ClaimEvidence,
    ClaimStatus,
    ClaimType,
    ConfidentialityLevel,
    Document,
    DocumentChunk,
    DocumentType,
    Issue,
    IssueSeverity,
    Organization,
    OrganizationMember,
    PartyRole,
    PrivilegeStatus,
    ProceduralEvent,
    ProceduralEventStatus,
    ProcedureStage,
    ProcessingStatus,
    TimelineEvent,
    User,
    UserRole,
)
from services.ingest_service import index_document
from services.llm_service import LLMService
from synthetic_documents import CONTRACTOR, DOCUMENTS, EMPLOYER

logger = logging.getLogger("seed_synthetic_case")

ORG_NAME = "Demo Legal LLP"
DEMO_EMAIL = "demo@arbiconstruct.ai"
DEMO_PASSWORD = "Demo1234!"

# Timeline descriptions keyed by document key (event_type, description)
TIMELINE: dict[str, tuple[str, str]] = {
    "CONTRACT": ("CONTRACT", "Contract GIA/AX2/2022-01 signed (FIDIC Red Book 1999; Contract Price USD 250,000,000)."),
    "BASELINE": ("PROGRAMME", "Baseline Programme Rev 0 submitted (planned completion 3 July 2025)."),
    "NTP": ("COMMENCEMENT", "Notice to Proceed: Commencement Date 15 January 2023; Time for Completion expires 3 July 2025."),
    "SI-001": ("INSTRUCTION", "SI-001: relocation of utilities trench in Zone A."),
    "VO-001": ("VARIATION", "VO-001 issued for utilities trench relocation (USD 3.2m)."),
    "SI-002": ("DELAY_EVENT", "SI-002: HOLD on Apron 4 pavement works pending redesign (critical path)."),
    "DR-2023-05-23": ("SITE_RECORD", "Daily report records Apron 4 paving crews stood down following SI-002."),
    "DN-01": ("NOTICE", "Delay Notice DN-01 re SI-002 (7 days after the event)."),
    "IPC-03": ("PAYMENT", "IPC 3 certified USD 9.12m (paid in full)."),
    "DR-2023-06-15": ("SITE_RECORD", "Daily report: Apron 4 still on HOLD; revised drawings not received."),
    "VO-002": ("VARIATION", "VO-002: Apron 4 redesign (USD 8.75m); HOLD lifted 10 July 2023."),
    "SI-003": ("INSTRUCTION", "SI-003: change of Baggage Hall steel grade S355 → S460."),
    "DR-2023-08-16": ("SITE_RECORD", "Daily report: S460 lead time 14-16 weeks advised by supplier."),
    "DN-02": ("NOTICE", "Delay Notice DN-02 re SI-003 steel change (37 days after the event)."),
    "VO-003": ("VARIATION", "VO-003: steel grade change valued at USD 5.4m."),
    "IPC-07": ("PAYMENT", "IPC 7 certified USD 12.64m (paid 28 days late)."),
    "SI-004": ("INSTRUCTION", "SI-004: additional passive fire protection."),
    "VO-004": ("VARIATION", "VO-004: additional fire protection (USD 2.1m)."),
    "PROG-REV3": ("PROGRAMME", "Revised Programme Rev 3 forecasts completion 26 November 2025 (+146 days)."),
    "EOT-CLAIM-1": ("CLAIM", "EOT Claim No. 1 submitted: 146 days + USD 14.6m prolongation."),
    "SI-005": ("DELAY_EVENT", "SI-005: Taxiway Kilo resequenced to night-only works; Zone C access restricted."),
    "DR-2024-02-21": ("SITE_RECORD", "Daily report: first night shift on Taxiway Kilo; ~35% of planned output."),
    "DN-03": ("NOTICE", "Delay Notice DN-03 re SI-005 (35 days after the event)."),
    "VO-005": ("VARIATION", "VO-005: Taxiway resequencing valued at USD 4.6m by the Engineer (Contractor claims USD 6.95m)."),
    "IPC-12": ("PAYMENT", "IPC 12 certified USD 10.98m; Employer paid USD 4.03m and withheld USD 6.95m."),
    "DR-2024-06-12": ("SITE_RECORD", "Daily report: Taxiway works suspended (lightning); final S460 steel delivered 28 May 2024."),
    "EOT-CLAIM-2": ("CLAIM", "EOT Claim No. 2 submitted: 98 days + USD 9.8m; concurrent delay argument."),
    "EMPLOYER-RESPONSE": ("RESPONSE", "Employer rejects EOT claims (time bar, concurrency) and gives notice of Delay Damages."),
    "QUANTUM": ("QUANTUM", "Quantum Summary Report (draft, privileged): total USD 62.95m."),
    "NOA": ("ARBITRATION", "Request for Arbitration filed with the ICC Secretariat (Art. 4, ICC Rules 2021)."),
}

CLAIMS = [
    dict(claim_ref="EOT-01", claim_type=ClaimType.EOT, title="Extension of time — Apron 4 HOLD and redesign",
         description="146 days EOT and prolongation costs arising from SI-002 suspension and VO-002 redesign of Apron 4.",
         quantum=Decimal("14600000"), contract_clause="Sub-Clauses 8.4(a), 8.4(e), 20.1",
         evidence=[("SI-002", "Instruction suspending critical-path paving"), ("VO-002", "Redesign and lifting of HOLD"),
                   ("DN-01", "Notice given 7 days after SI-002"), ("DR-2023-05-23", "Crews stood down"),
                   ("DR-2023-06-15", "Drawings still outstanding"), ("EOT-CLAIM-1", "Fully detailed claim"),
                   ("BASELINE", "Accepted baseline critical path"), ("PROG-REV3", "Forecast +146 days")]),
    dict(claim_ref="EOT-02", claim_type=ClaimType.EOT, title="Extension of time — Taxiway Kilo resequencing",
         description="98 days EOT and prolongation costs arising from SI-005 night-only resequencing; concurrent delay with late S460 steel is disputed.",
         quantum=Decimal("9800000"), contract_clause="Sub-Clauses 8.4(a), 8.4(e), 20.1",
         evidence=[("SI-005", "Resequencing instruction"), ("DN-03", "Notice — timing disputed (35 days)"),
                   ("DR-2024-02-21", "Reduced productive hours"), ("DR-2024-06-12", "Access restrictions / steel delivery"),
                   ("EOT-CLAIM-2", "Fully detailed claim incl. concurrency argument")]),
    dict(claim_ref="LD-DEFENCE", claim_type=ClaimType.LD_DEFENCE, title="Defence to Delay Damages and repayment of sums withheld",
         description="Employer threatens / deducts Delay Damages up to the USD 25m cap; Contractor contends entitlement to EOT and relies on prevention principle.",
         quantum=Decimal("25000000"), contract_clause="Sub-Clauses 8.7, 2.5",
         evidence=[("CONTRACT", "Delay Damages rate and cap"), ("EMPLOYER-RESPONSE", "Employer's notice to deduct"),
                   ("PROG-REV3", "Forecast completion and critical path")]),
    dict(claim_ref="VAR-001", claim_type=ClaimType.VARIATION, title="Valuation of VO-005 (Taxiway resequencing)",
         description="Difference between Engineer's valuation (USD 4.6m) and Contractor's valuation (USD 6.95m).",
         quantum=Decimal("2350000"), contract_clause="Sub-Clauses 12.3, 13.3",
         evidence=[("VO-005", "Engineer's valuation and disputed difference"), ("SI-005", "Instruction giving rise to Variation"),
                   ("CONTRACT", "Variation and valuation clauses")]),
    dict(claim_ref="PAYMENT-FINAL", claim_type=ClaimType.PAYMENT, title="Unpaid certified sums and retention",
         description="IPC-12 shortfall of USD 6.95m and retention release of USD 4.25m.",
         quantum=Decimal("11200000"), contract_clause="Sub-Clauses 14.7, 14.9",
         evidence=[("IPC-03", "Payment history"), ("IPC-07", "Late payment"), ("IPC-12", "Shortfall withheld"),
                   ("QUANTUM", "Quantum summary")]),
]

ISSUES = [
    dict(title="Notice Compliance", category="NOTICE", severity=IssueSeverity.HIGH,
         description="DN-02 (37 days after SI-003) and DN-03 (35 days after SI-005) were issued more than 28 days after the "
                     "triggering instructions. The Employer relies on the Sub-Clause 20.1 time bar. Enforceability under "
                     "English law and the date of awareness require legal review."),
    dict(title="Concurrent Delay", category="DELAY", severity=IssueSeverity.HIGH,
         description="EOT-02 overlaps with the Contractor's late S460 steel procurement (Mar-May 2024). Parties dispute "
                     "criticality and the approach to concurrency (SCL Protocol vs. English law authorities)."),
    dict(title="Quantum Methodology", category="QUANTUM", severity=IssueSeverity.MEDIUM,
         description="Prolongation costs are based on tender preliminaries rather than actual cost records; actual site "
                     "overhead records for 2023-2024 have not yet been obtained."),
]

# (stage, rule article as seeded, title, due date, status)
PROCEDURE = [
    (ProcedureStage.NOTICE_OF_ARBITRATION, "Art. 4", "Request for Arbitration filed", date(2025, 9, 1), ProceduralEventStatus.COMPLETED),
    (ProcedureStage.RESPONSE, "Art. 5", "Answer and any counterclaim (30 days)", date(2025, 10, 1), ProceduralEventStatus.COMPLETED),
    (ProcedureStage.TRIBUNAL_CONSTITUTION, "Arts. 11-13", "Tribunal constituted / confirmed", date(2025, 12, 15), ProceduralEventStatus.COMPLETED),
    (ProcedureStage.TERMS_OF_REFERENCE, "Art. 23", "Terms of Reference signed (2 months from file transmission)", date(2026, 2, 15), ProceduralEventStatus.COMPLETED),
    (ProcedureStage.PRELIMINARY_STAGE, "Art. 24", "Case management conference; Procedural Order No. 1", date(2026, 2, 20), ProceduralEventStatus.COMPLETED),
    (ProcedureStage.PLEADINGS, "Arts. 4-6 + PO1", "Statement of Claim (per PO1)", date(2026, 5, 15), ProceduralEventStatus.COMPLETED),
    (ProcedureStage.DOCUMENT_PRODUCTION, "Practice Note / Art. 25", "Document production — Redfern requests and responses", date(2026, 8, 31), ProceduralEventStatus.IN_PROGRESS),
    (ProcedureStage.PLEADINGS, "Arts. 4-6 + PO1", "Statement of Defence and Counterclaim (per PO1)", date(2026, 10, 30), ProceduralEventStatus.PENDING),
    (ProcedureStage.WITNESS_STATEMENTS, "Art. 25", "Exchange of witness statements", date(2026, 12, 15), ProceduralEventStatus.PENDING),
    (ProcedureStage.WITNESS_STATEMENTS, "Art. 25", "Delay and quantum expert reports", date(2027, 2, 15), ProceduralEventStatus.PENDING),
    (ProcedureStage.EVIDENTIARY_HEARING, "Art. 26", "Evidentiary hearing (Singapore, 10 days)", date(2027, 5, 10), ProceduralEventStatus.PENDING),
    (ProcedureStage.AWARD, "Arts. 34-36", "Final award (Art. 31 six-month limit — extension required)", None, ProceduralEventStatus.PENDING),
]


async def _remove_existing(session: AsyncSession) -> None:
    existing_user = (await session.execute(select(User).where(User.email == DEMO_EMAIL))).scalar_one_or_none()
    org_ids = {o for o in (await session.execute(select(Organization.id).where(Organization.name == ORG_NAME))).scalars()}
    if existing_user is not None:
        org_ids.add(existing_user.org_id)
    for org_id in org_ids:
        # Delete children explicitly (portable even where FK cascades are not enforced).
        case_ids = list((await session.execute(select(Case.id).where(Case.org_id == org_id))).scalars())
        if case_ids:
            claim_ids = list((await session.execute(select(Claim.id).where(Claim.case_id.in_(case_ids)))).scalars())
            if claim_ids:
                await session.execute(delete(ClaimEvidence).where(ClaimEvidence.claim_id.in_(claim_ids)))
            for model in (Claim, TimelineEvent, Issue, ProceduralEvent, CaseParty, AIAnalysis, DocumentChunk):
                await session.execute(delete(model).where(model.case_id.in_(case_ids)))  # type: ignore[attr-defined]
            await session.execute(delete(Document).where(Document.case_id.in_(case_ids)))
            await session.execute(delete(Case).where(Case.id.in_(case_ids)))
        user_ids = list((await session.execute(select(User.id).where(User.org_id == org_id))).scalars())
        if user_ids:
            await session.execute(delete(AIAnalysis).where(AIAnalysis.user_id.in_(user_ids)))
        await session.execute(delete(AuditLog).where(AuditLog.org_id == org_id))
        await session.execute(delete(OrganizationMember).where(OrganizationMember.org_id == org_id))
        await session.execute(delete(User).where(User.org_id == org_id))
        await session.execute(delete(Organization).where(Organization.id == org_id))
    if org_ids:
        await session.commit()
        logger.info("Removed previous demo organisation(s)")


async def seed(session: AsyncSession, llm: LLMService) -> None:
    await _remove_existing(session)

    org = Organization(id=uuid.uuid4(), name=ORG_NAME, slug="demo-legal-llp", country="Singapore")
    session.add(org)
    await session.flush()
    user = User(
        id=uuid.uuid4(),
        email=DEMO_EMAIL,
        hashed_password=hash_password(DEMO_PASSWORD),
        full_name="Demo Counsel",
        is_active=True,
        role=UserRole.ORG_ADMIN,
        org_id=org.id,
    )
    session.add(user)
    await session.flush()
    session.add(OrganizationMember(org_id=org.id, user_id=user.id, role=UserRole.ORG_ADMIN))

    case = Case(
        id=uuid.uuid4(),
        org_id=org.id,
        title="International Airport Expansion Arbitration",
        description=(
            f"ICC arbitration between {CONTRACTOR} (Claimant/Contractor) and {EMPLOYER} (Respondent/Employer) concerning "
            "delay, variations and payment on the Airport Expansion Phase 2 works (FIDIC Red Book 1999). Synthetic demo data."
        ),
        institution=ArbitrationInstitutionEnum.ICC,
        seat="Singapore",
        governing_law="English law",
        language="English",
        status=CaseStatus.ACTIVE,
        amount_in_dispute=Decimal("62950000"),
        currency="USD",
        case_ref="ICC Case No. 29999/DEMO",
    )
    session.add(case)
    await session.flush()
    session.add_all(
        [
            CaseParty(case_id=case.id, name=EMPLOYER, role=PartyRole.EMPLOYER, counsel="Respondent's counsel (TBC)", country="Singapore"),
            CaseParty(case_id=case.id, name=CONTRACTOR, role=PartyRole.CONTRACTOR, counsel=ORG_NAME, country="Republic of Korea"),
        ]
    )

    docs: dict[str, Document] = {}
    total_chunks = 0
    for i, spec in enumerate(DOCUMENTS, start=1):
        text = spec.text
        confidentiality = ConfidentialityLevel(spec.confidentiality)
        doc = Document(
            id=uuid.uuid4(),
            case_id=case.id,
            org_id=org.id,
            filename=spec.filename,
            s3_key=None,  # synthetic: text only, no stored file
            file_size=len(text.encode()),
            mime_type="text/plain",
            document_type=DocumentType(spec.document_type),
            author=spec.author,
            recipient=spec.recipient,
            doc_date=spec.doc_date,
            language="en",
            confidentiality_level=confidentiality,
            privilege_status=PrivilegeStatus.PRIVILEGED if confidentiality == ConfidentialityLevel.PRIVILEGED else PrivilegeStatus.NOT_PRIVILEGED,
            evidence_number=spec.evidence_number or f"C-{i}",
            file_hash=hashlib.sha256(text.encode()).hexdigest(),
            ocr_text=text,
            ocr_status=ProcessingStatus.NOT_REQUIRED,
            classification_status=ProcessingStatus.COMPLETED,
            metadata_json={"synthetic": True, "key": spec.key},
        )
        session.add(doc)
        await session.flush()
        total_chunks += await index_document(session, doc, llm)
        doc.ocr_status = ProcessingStatus.NOT_REQUIRED
        docs[spec.key] = doc
    logger.info("Created %d documents / %d chunks", len(docs), total_chunks)

    for key, (etype, desc) in TIMELINE.items():
        doc = docs[key]
        session.add(
            TimelineEvent(
                case_id=case.id,
                event_date=doc.doc_date,
                description=desc,
                event_type=etype,
                source_document_id=doc.id,
                source_page=1,
                source_excerpt=(doc.ocr_text or "")[:280],
                is_ai_extracted=False,
            )
        )

    for c in CLAIMS:
        claim = Claim(
            id=uuid.uuid4(),
            case_id=case.id,
            claim_ref=c["claim_ref"],
            claim_type=c["claim_type"],
            title=c["title"],
            description=c["description"],
            quantum=c["quantum"],
            currency="USD",
            status=ClaimStatus.IN_ARBITRATION,
            contract_clause=c["contract_clause"],
        )
        session.add(claim)
        await session.flush()
        for key, note in c["evidence"]:
            session.add(ClaimEvidence(claim_id=claim.id, document_id=docs[key].id, relevance_note=note, added_by_ai=False))

    for issue in ISSUES:
        session.add(Issue(case_id=case.id, **issue))

    inst = (
        await session.execute(select(ArbitrationInstitution).where(ArbitrationInstitution.short_name == "ICC"))
    ).scalar_one_or_none()
    rule_urls: dict[str, str | None] = {}
    if inst is not None:
        for rule in (await session.execute(select(ArbitrationRule).where(ArbitrationRule.institution_id == inst.id))).scalars():
            rule_urls[rule.article_number] = rule.source_url
    else:
        logger.warning("ICC institution not seeded — run seed_institutions.py first for rule links")
    for stage, article, title, due, status in PROCEDURE:
        session.add(
            ProceduralEvent(
                case_id=case.id,
                event_type=stage.value,
                title=title,
                due_date=due,
                source_rule="ICC Rules 2021",
                rule_reference=article,
                source_url=rule_urls.get(article),
                status=status,
                responsible_user_id=user.id,
                notes="Deadline per PO1 / ICC Rules — confirm against the procedural timetable." if due else
                      "AI-suggested: Art. 31 six-month limit runs from the Terms of Reference; the Court usually extends it.",
                is_ai_suggested=due is None,
                requires_confirmation=due is None,
            )
        )

    await session.commit()
    logger.info("Seeded demo case '%s' (id=%s). Login: %s / %s", case.title, case.id, DEMO_EMAIL, DEMO_PASSWORD)


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    llm = LLMService()
    async with AsyncSessionLocal() as session:
        await seed(session, llm)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
