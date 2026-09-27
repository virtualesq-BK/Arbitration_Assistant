"""Seed ArbitrationInstitution + ArbitrationRule records and the RULES / CONSTRUCTION knowledge corpora.

Usage (from the repository root, database migrated):
    python scripts/seed/seed_institutions.py

Idempotent: re-running replaces the rules and knowledge chunks for each seeded institution.

IMPORTANT: rule summaries below are short paraphrases prepared for navigation. They are NOT the
official text. Every record carries the official source URL; users must verify against the
official rules before relying on them.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import date

import _common  # noqa: F401  (sys.path bootstrap)
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import AsyncSessionLocal, engine
from models.arbitration_institution import ArbitrationInstitution
from models.arbitration_rule import ArbitrationRule, ProcedureStage as S
from models.knowledge_chunk import KnowledgeChunk
from services.ingest_service import index_knowledge
from services.llm_service import LLMService

logger = logging.getLogger("seed_institutions")

VERIFY_NOTE = "Paraphrased summary for navigation only — verify against the official rules text."


@dataclass
class RuleSeed:
    stage: S
    article: str
    title: str
    summary: str
    days: int | None = None
    notes: str | None = None


@dataclass
class InstitutionSeed:
    name: str
    short_name: str
    website: str
    rules_version: str
    effective: date
    rules_url: str
    rules: list[RuleSeed]
    source_tier: str = "official"


ICC_URL = "https://iccwbo.org/dispute-resolution/dispute-resolution-services/arbitration/rules-of-arbitration/"
SIAC_URL = "https://siac.org.sg/siac-rules/"
LCIA_URL = "https://www.lcia.org/"

INSTITUTIONS: list[InstitutionSeed] = [
    InstitutionSeed(
        name="International Chamber of Commerce — International Court of Arbitration",
        short_name="ICC",
        website="https://iccwbo.org/",
        rules_version="2021",
        effective=date(2021, 1, 1),
        rules_url=ICC_URL,
        rules=[
            RuleSeed(S.NOTICE_OF_ARBITRATION, "Art. 4", "Request for Arbitration",
                     "A party wishing to arbitrate submits its Request for Arbitration to the Secretariat. The arbitration "
                     "is deemed to commence on the date the Secretariat receives the Request. The Request should identify "
                     "the parties, describe the dispute and the relief sought, and include the relevant agreements, "
                     "including the arbitration agreement."),
            RuleSeed(S.RESPONSE, "Art. 5", "Answer to the Request; Counterclaims",
                     "The respondent submits an Answer within 30 days from receipt of the Request (extendable by the "
                     "Secretariat). Any counterclaim is submitted with the Answer.", days=30),
            RuleSeed(S.TRIBUNAL_CONSTITUTION, "Arts. 11-13", "Constitution of the Arbitral Tribunal",
                     "Every arbitrator must be and remain impartial and independent and sign a statement of acceptance, "
                     "availability, impartiality and independence (Art. 11). Arts. 12-13 govern the number of arbitrators, "
                     "party nominations and confirmation or appointment by the Court.",
                     notes="Challenges to arbitrators are addressed separately in Art. 14."),
            RuleSeed(S.TERMS_OF_REFERENCE, "Art. 23", "Terms of Reference",
                     "As soon as it has received the file, the tribunal draws up Terms of Reference defining the parties, "
                     "a summary of claims and relief sought, and (unless inappropriate) a list of issues. The Terms are to be "
                     "signed and transmitted to the Court within two months of the file being transmitted to the tribunal.",
                     days=60),
            RuleSeed(S.PRELIMINARY_STAGE, "Art. 24", "Case Management Conference and Procedural Timetable",
                     "When drawing up the Terms of Reference, or as soon as possible thereafter, the tribunal convenes a case "
                     "management conference to consult the parties on procedural measures and establishes the procedural "
                     "timetable (typically recorded in Procedural Order No. 1)."),
            RuleSeed(S.PLEADINGS, "Arts. 4-6 + PO1", "Written Submissions",
                     "Initial positions are set out in the Request (Art. 4) and Answer (Art. 5); jurisdictional objections are "
                     "addressed under Art. 6. The sequence and deadlines of subsequent written submissions (statement of claim, "
                     "defence, reply, rejoinder) are fixed by the tribunal in Procedural Order No. 1 under Art. 24.",
                     notes="Submission deadlines come from PO1, not from the Rules themselves."),
            RuleSeed(S.DOCUMENT_PRODUCTION, "Practice Note / Art. 25", "Establishing the Facts; Document Production",
                     "The tribunal establishes the facts by all appropriate means (Art. 25) and may order a party to produce "
                     "documents. Document production procedure is normally set in PO1, often by reference to the IBA Rules on "
                     "the Taking of Evidence and ICC guidance notes.",
                     notes="Refer to the ICC Note to Parties and Arbitral Tribunals on the Conduct of the Arbitration."),
            RuleSeed(S.WITNESS_STATEMENTS, "Art. 25", "Witnesses and Experts",
                     "The tribunal may hear witnesses, party-appointed experts or any other person, and may appoint its own "
                     "expert after consulting the parties."),
            RuleSeed(S.EVIDENTIARY_HEARING, "Art. 26", "Hearings",
                     "A hearing is held if a party requests it or the tribunal decides of its own motion. The tribunal is in "
                     "full charge of the hearing; hearings may be held in person or remotely."),
            RuleSeed(S.CLOSING, "Art. 27", "Closing of the Proceedings",
                     "After the last hearing or filing of the last authorised submissions, the tribunal declares the "
                     "proceedings closed and informs the Secretariat and parties of the date it expects to submit its draft award."),
            RuleSeed(S.AWARD, "Arts. 34-36", "Scrutiny, Notification and Correction of the Award",
                     "The draft award is submitted to the Court for scrutiny before signature (Art. 34). The signed award is "
                     "notified by the Secretariat (Art. 35). Applications for correction or interpretation may be made within "
                     "30 days of notification (Art. 36). The time limit for the final award is six months from the Terms of "
                     "Reference unless extended (Art. 31).",
                     days=180),
        ],
    ),
    InstitutionSeed(
        name="Singapore International Arbitration Centre",
        short_name="SIAC",
        website="https://siac.org.sg/",
        rules_version="2016",
        effective=date(2016, 8, 1),
        rules_url=SIAC_URL,
        rules=[
            RuleSeed(S.NOTICE_OF_ARBITRATION, "Rule 3", "Notice of Arbitration",
                     "The claimant files a Notice of Arbitration with the Registrar. The arbitration is deemed to commence on the "
                     "date of receipt of the complete Notice by the Registrar."),
            RuleSeed(S.RESPONSE, "Rule 4", "Response to the Notice of Arbitration",
                     "The respondent files a Response within 14 days of receipt of the Notice of Arbitration, including any "
                     "counterclaim and comments on the number and nomination of arbitrators.", days=14,
                     notes="Rule 5 of SIAC 2016 is the Expedited Procedure."),
            RuleSeed(S.TRIBUNAL_CONSTITUTION, "Rules 9-11", "Number and Appointment of Arbitrators",
                     "A sole arbitrator is appointed unless the parties agree otherwise or the Registrar determines three are "
                     "appropriate (Rule 9). Rules 10-11 set the procedure for sole and three-member tribunals, with appointment "
                     "by the President of the SIAC Court where parties fail to nominate."),
            RuleSeed(S.PRELIMINARY_STAGE, "Rule 19.3", "Preliminary Meeting",
                     "As soon as practicable after constitution, the tribunal conducts a preliminary meeting with the parties to "
                     "discuss the procedures most appropriate and efficient for the case."),
            RuleSeed(S.PLEADINGS, "Rule 20", "Submissions by the Parties",
                     "Unless otherwise directed, the claimant files a Statement of Claim and the respondent a Statement of "
                     "Defence (and any Counterclaim) within the times determined by the tribunal; further submissions as "
                     "directed."),
            RuleSeed(S.DOCUMENT_PRODUCTION, "Rule 27(f)", "Additional Powers — Document Production",
                     "The tribunal may order any party to produce documents in its possession or control which the tribunal "
                     "considers relevant to the case and material to its outcome."),
            RuleSeed(S.EVIDENTIARY_HEARING, "Rule 24", "Hearings",
                     "Unless the parties agree to a documents-only arbitration, the tribunal holds a hearing for the presentation "
                     "of evidence and/or oral submissions if a party requests or the tribunal decides.",
                     notes="Witnesses are addressed in Rule 25."),
            RuleSeed(S.AWARD, "Rule 32", "The Award",
                     "Before making an award, the tribunal submits it in draft to the Registrar within 45 days of the date the "
                     "proceedings are declared closed. The Registrar may suggest modifications as to form. Corrections are "
                     "governed by Rule 33.", days=45),
        ],
    ),
    InstitutionSeed(
        name="London Court of International Arbitration",
        short_name="LCIA",
        website="https://www.lcia.org/",
        rules_version="2020",
        effective=date(2020, 10, 1),
        rules_url=LCIA_URL,
        rules=[
            RuleSeed(S.NOTICE_OF_ARBITRATION, "Art. 1", "Request for Arbitration",
                     "The claimant delivers a Request for Arbitration to the LCIA Registrar. The arbitration commences on the "
                     "date the Registrar receives the Request."),
            RuleSeed(S.RESPONSE, "Art. 2", "Response",
                     "The respondent delivers a Response within 28 days of the commencement date (or such lesser/greater period "
                     "set by the LCIA Court).", days=28),
            RuleSeed(S.TRIBUNAL_CONSTITUTION, "Arts. 5-10", "Formation of the Arbitral Tribunal",
                     "The LCIA Court appoints the tribunal (Art. 5), taking into account party nominations (Art. 7) and "
                     "multi-party situations (Art. 8); Art. 9 provides for expedited formation and emergency arbitrators; "
                     "Art. 10 addresses revocation and challenges."),
            RuleSeed(S.PLEADINGS, "Art. 15", "Written Stage of the Arbitration",
                     "Unless otherwise agreed or ordered: Statement of Case within 28 days of notification of the tribunal's "
                     "formation, Statement of Defence within 28 days thereafter, followed by Reply and Rejoinder.", days=28),
            RuleSeed(S.DOCUMENT_PRODUCTION, "Arts. 21-22", "Experts and Additional Powers (Evidence)",
                     "The tribunal may appoint experts (Art. 21) and, under its additional powers (Art. 22), order a party to "
                     "produce documents, decide rules of evidence and conduct enquiries."),
            RuleSeed(S.EVIDENTIARY_HEARING, "Art. 19", "Oral Hearing(s)",
                     "Any party has the right to a hearing before the tribunal on the merits unless the parties agree in writing "
                     "to a documents-only arbitration. The tribunal organises the conduct of the hearing, which may be virtual."),
            RuleSeed(S.AWARD, "Arts. 26-28", "Award, Correction and Costs",
                     "The tribunal makes its award in writing with reasons (Art. 26). Correction of errors and additional awards "
                     "may be requested within 28 days of receipt (Art. 27). Arbitration and legal costs are addressed in Art. 28.",
                     notes="Art. 15.10 targets the final award within three months of the last submission."),
        ],
    ),
]

CONSTRUCTION_KNOWLEDGE: list[dict[str, str]] = [
    {
        "source_name": "FIDIC Conditions of Contract for Construction (1999 Red Book) — Sub-Clause 20.1 (overview)",
        "source_url": "https://fidic.org/",
        "text": (
            "Under Sub-Clause 20.1 of the 1999 FIDIC Red Book, a Contractor who considers itself entitled to an extension "
            "of time and/or additional payment must give notice to the Engineer describing the event or circumstance "
            "as soon as practicable and not later than 28 days after it became aware, or should have become aware, of it. "
            "The clause states that if the Contractor fails to give notice within 28 days, the Time for Completion shall "
            "not be extended and the Contractor shall not be entitled to additional payment. Whether the time bar is "
            "enforced depends on the governing law and the facts; this is a matter requiring legal analysis.\n\n"
            "A fully detailed claim is to be sent within 42 days after the Contractor became aware of the event, with "
            "monthly interim claims where the effect is continuing."
        ),
    },
    {
        "source_name": "FIDIC 1999 Red Book — Sub-Clauses 8.4 and 8.7 (overview)",
        "source_url": "https://fidic.org/",
        "text": (
            "Sub-Clause 8.4 lists the grounds on which the Contractor may be entitled, subject to Sub-Clause 20.1, to an "
            "extension of the Time for Completion, including Variations, exceptionally adverse climatic conditions, "
            "and delay, impediment or prevention caused by the Employer.\n\n"
            "Sub-Clause 8.7 provides for Delay Damages payable by the Contractor at the rate stated in the Appendix to "
            "Tender for each day between the Time for Completion and the date stated in the Taking-Over Certificate, "
            "subject to the maximum amount stated."
        ),
    },
    {
        "source_name": "SCL Delay and Disruption Protocol (2nd ed., 2017) — concurrent delay (overview)",
        "source_url": "https://www.scl.org.uk/resources/delay-disruption-protocol",
        "text": (
            "The Society of Construction Law Delay and Disruption Protocol describes true concurrent delay as the "
            "occurrence of two or more delay events at the same time, one an Employer Risk Event and the other a "
            "Contractor Risk Event, the effects of which are felt at the same time. The Protocol's guidance is that, "
            "where Contractor Delay to Completion occurs concurrently with Employer Delay to Completion, the "
            "Contractor's concurrent delay should not reduce any EOT due. Compensation for concurrent delay is treated "
            "differently. The Protocol is guidance, not law; tribunals and courts in different jurisdictions take "
            "different approaches.\n\n"
            "The Protocol recommends that delay analysis be conducted contemporaneously where practicable, and discusses "
            "methods including impacted as-planned, time impact analysis, time slice windows analysis, as-planned vs "
            "as-built windows analysis, and longest path analysis."
        ),
    },
    {
        "source_name": "Construction arbitration practice — quantum of prolongation and disruption (overview)",
        "source_url": None,
        "text": (
            "Prolongation cost claims typically seek time-related preliminaries or site overheads for the period of "
            "compensable delay, often supported by cost records rather than tender allowances. Disruption claims "
            "concern loss of productivity; commonly discussed methods include the measured mile, earned value and "
            "industry-study approaches. Global or total-cost claims face evidential challenges where causation between "
            "specific events and specific losses is not demonstrated.\n\n"
            "Head-office overhead formulae (e.g. Hudson, Emden, Eichleay) are frequently contested; tribunals often "
            "require evidence that the contractor was prevented from earning contribution elsewhere."
        ),
    },
    {
        "source_name": "Construction arbitration practice — the prevention principle and liquidated damages (overview)",
        "source_url": None,
        "text": (
            "Under the prevention principle recognised in several common-law jurisdictions, an employer who prevents the "
            "contractor from completing by the completion date may be unable to recover liquidated damages unless the "
            "contract contains a mechanism to extend time for that act of prevention. The interaction of the prevention "
            "principle with notice conditions precedent is jurisdiction-specific and fact-sensitive and must be assessed "
            "by qualified counsel under the governing law."
        ),
    },
]


async def seed(session: AsyncSession, llm: LLMService) -> None:
    for spec in INSTITUTIONS:
        inst = (
            await session.execute(select(ArbitrationInstitution).where(ArbitrationInstitution.short_name == spec.short_name))
        ).scalar_one_or_none()
        if inst is None:
            inst = ArbitrationInstitution(id=uuid.uuid4(), short_name=spec.short_name, name=spec.name)
            session.add(inst)
        inst.name = spec.name
        inst.website = spec.website
        inst.rules_version = spec.rules_version
        inst.rules_effective_date = spec.effective
        inst.rules_url = spec.rules_url
        inst.source_tier = spec.source_tier
        await session.flush()

        await session.execute(delete(KnowledgeChunk).where(KnowledgeChunk.institution == spec.short_name, KnowledgeChunk.corpus == "rules"))
        await session.execute(delete(ArbitrationRule).where(ArbitrationRule.institution_id == inst.id))

        for r in spec.rules:
            rule = ArbitrationRule(
                id=uuid.uuid4(),
                institution_id=inst.id,
                stage=r.stage,
                article_number=r.article,
                title=r.title,
                summary=r.summary,
                source_url=spec.rules_url,
                rule_version=spec.rules_version,
                notes=f"{r.notes + ' ' if r.notes else ''}{VERIFY_NOTE}",
                typical_deadline_days=r.days,
            )
            session.add(rule)
            await session.flush()
            await index_knowledge(
                session,
                corpus="rules",
                source_name=f"{spec.short_name} Rules {spec.rules_version} {r.article} — {r.title}",
                text=f"{spec.short_name} Rules {spec.rules_version}, {r.article} ({r.title}). {r.summary}",
                source_url=spec.rules_url,
                institution=spec.short_name,
                rule_version=spec.rules_version,
                article_number=r.article,
                rule_id=rule.id,
                llm=llm,
            )
        logger.info("Seeded %s: %d rules", spec.short_name, len(spec.rules))

    await session.execute(delete(KnowledgeChunk).where(KnowledgeChunk.corpus == "construction"))
    for item in CONSTRUCTION_KNOWLEDGE:
        await index_knowledge(
            session,
            corpus="construction",
            source_name=item["source_name"],
            text=item["text"],
            source_url=item["source_url"],
            llm=llm,
        )
    logger.info("Seeded %d construction knowledge sources", len(CONSTRUCTION_KNOWLEDGE))
    await session.commit()


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    llm = LLMService()
    async with AsyncSessionLocal() as session:
        await seed(session, llm)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
