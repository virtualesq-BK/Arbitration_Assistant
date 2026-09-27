"""Thirty synthetic project documents for the demo case.

All names, figures and events are fictitious. The document set is designed to exercise the
platform: it contains notice-timing questions, a concurrent-delay dispute, a disputed variation
valuation and certified-but-unpaid sums.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

EMPLOYER = "Global Infrastructure Authority"
CONTRACTOR = "ABC Construction Ltd"
ENGINEER = "AeroConsult Engineering Pte Ltd (the Engineer)"


@dataclass
class DocSeed:
    key: str
    filename: str
    document_type: str
    doc_date: date
    author: str
    recipient: str | None
    text: str
    confidentiality: str = "CONFIDENTIAL"
    evidence_number: str | None = None


def _si(n: int, d: date, subject: str, body: str) -> DocSeed:
    return DocSeed(
        key=f"SI-{n:03d}",
        filename=f"Site_Instruction_SI-{n:03d}.txt",
        document_type="SITE_INSTRUCTION",
        doc_date=d,
        author=ENGINEER,
        recipient=CONTRACTOR,
        text=(
            f"SITE INSTRUCTION No. SI-{n:03d}\nDate: {d.isoformat()}\nProject: International Airport Expansion — Phase 2\n"
            f"Contract No. GIA/AX2/2022-01\nFrom: {ENGINEER}\nTo: {CONTRACTOR}\n\nSubject: {subject}\n\n{body}\n\n"
            "This instruction is issued under Sub-Clause 3.3 [Instructions of the Engineer]. Where this instruction "
            "constitutes a Variation the procedure of Clause 13 shall apply."
        ),
    )


def _vo(n: int, d: date, si: str, subject: str, amount: str, body: str) -> DocSeed:
    return DocSeed(
        key=f"VO-{n:03d}",
        filename=f"Variation_Order_VO-{n:03d}.txt",
        document_type="VARIATION_ORDER",
        doc_date=d,
        author=ENGINEER,
        recipient=CONTRACTOR,
        text=(
            f"VARIATION ORDER No. VO-{n:03d}\nDate: {d.isoformat()}\nReference: {si}\nContract No. GIA/AX2/2022-01\n\n"
            f"Subject: {subject}\n\n{body}\n\nValuation: {amount} (Sub-Clause 12.3 / 13.3).\n\n"
            "Time implications: to be assessed under Sub-Clause 8.4 upon receipt of a claim in accordance with Sub-Clause 20.1."
        ),
    )


def _ipc(n: int, d: date, gross: str, cert: str, paid: str, note: str) -> DocSeed:
    return DocSeed(
        key=f"IPC-{n:02d}",
        filename=f"Interim_Payment_Certificate_IPC-{n:02d}.txt",
        document_type="PAYMENT_CERTIFICATE",
        doc_date=d,
        author=ENGINEER,
        recipient=EMPLOYER,
        text=(
            f"INTERIM PAYMENT CERTIFICATE No. {n}\nDate: {d.isoformat()}\nContract No. GIA/AX2/2022-01\n"
            f"Issued under Sub-Clause 14.6\n\nCumulative gross value of work executed: {gross}\n"
            f"Amount certified this certificate (after retention of 5%): {cert}\n"
            f"Amount paid by the Employer as at date of next certificate: {paid}\n\n{note}\n\n"
            "Payment is due within 56 days after the Engineer receives the Statement and supporting documents "
            "(Sub-Clause 14.7(b))."
        ),
    )


def _dr(d: date, weather: str, body: str) -> DocSeed:
    return DocSeed(
        key=f"DR-{d.isoformat()}",
        filename=f"Daily_Report_{d.isoformat()}.txt",
        document_type="DAILY_REPORT",
        doc_date=d,
        author=f"{CONTRACTOR} — Site Manager",
        recipient=ENGINEER,
        text=(
            f"DAILY SITE REPORT\nDate: {d.isoformat()}\nWeather: {weather}\nProject: International Airport Expansion — Phase 2\n\n"
            f"{body}\n\nSigned: Site Manager, {CONTRACTOR}. Countersigned (receipt only): Resident Engineer."
        ),
    )


def _dn(n: int, d: date, event: str, aware: date, body: str) -> DocSeed:
    return DocSeed(
        key=f"DN-{n:02d}",
        filename=f"Delay_Notice_DN-{n:02d}.txt",
        document_type="NOTICE",
        doc_date=d,
        author=CONTRACTOR,
        recipient=ENGINEER,
        text=(
            f"NOTICE OF DELAY AND CLAIM No. DN-{n:02d}\nDate: {d.isoformat()}\nContract No. GIA/AX2/2022-01\n"
            f"From: {CONTRACTOR}\nTo: {ENGINEER}\n\nNotice under Sub-Clause 8.4 and Sub-Clause 20.1\n\n"
            f"Event: {event}\nDate on which the Contractor became aware of the event: {aware.isoformat()}\n\n{body}\n\n"
            "The Contractor reserves its right to submit a fully detailed claim with supporting particulars within 42 days "
            "in accordance with Sub-Clause 20.1."
        ),
    )


DOCUMENTS: list[DocSeed] = [
    # 1. Main Contract
    DocSeed(
        key="CONTRACT",
        filename="Main_Contract_FIDIC_Red_Book.txt",
        document_type="CONTRACT",
        doc_date=date(2022, 11, 1),
        author=EMPLOYER,
        recipient=CONTRACTOR,
        evidence_number="C-1",
        text=(
            "CONTRACT AGREEMENT\nContract No. GIA/AX2/2022-01 — International Airport Expansion, Phase 2 "
            "(Terminal 2 extension, apron and taxiway works)\n\n"
            f"This Agreement is made on 1 November 2022 between {EMPLOYER} (the Employer) and {CONTRACTOR} (the Contractor).\n\n"
            "The Conditions of Contract are the FIDIC Conditions of Contract for Construction for Building and Engineering "
            "Works Designed by the Employer, First Edition 1999 (the Red Book), as amended by the Particular Conditions.\n\n"
            "Contract Price: USD 250,000,000 (two hundred and fifty million United States Dollars), subject to adjustment "
            "in accordance with the Contract.\n\n"
            "Engineer: AeroConsult Engineering Pte Ltd.\n\n"
            "Time for Completion: 900 days from the Commencement Date stated in the Engineer's notice under Sub-Clause 8.1.\n\n"
            "Delay Damages (Sub-Clause 8.7): USD 125,000 per day, subject to a maximum of 10% of the Contract Price "
            "(USD 25,000,000).\n\n"
            "Sub-Clause 8.4 [Extension of Time for Completion]: the Contractor shall be entitled subject to Sub-Clause 20.1 "
            "to an extension of the Time for Completion if completion is or will be delayed by (a) a Variation, "
            "(c) exceptionally adverse climatic conditions, or (e) any delay, impediment or prevention caused by the Employer.\n\n"
            "Sub-Clause 13.1 [Right to Vary]: Variations may be initiated by the Engineer at any time prior to issuing the "
            "Taking-Over Certificate. Sub-Clause 13.3: valuation of Variations in accordance with Clause 12.\n\n"
            "Sub-Clause 14.7 [Payment]: the Employer shall pay the amount certified in each Interim Payment Certificate "
            "within 56 days after the Engineer receives the Statement. Retention: 5% of each interim payment up to a limit "
            "of 5% of the Contract Price.\n\n"
            "Sub-Clause 20.1 [Contractor's Claims]: the Contractor shall give notice to the Engineer as soon as practicable, "
            "and not later than 28 days after the Contractor became aware, or should have become aware, of the event or "
            "circumstance. If the Contractor fails to give notice of a claim within such period of 28 days, the Time for "
            "Completion shall not be extended, the Contractor shall not be entitled to additional payment, and the Employer "
            "shall be discharged from all liability in connection with the claim.\n\n"
            "Sub-Clause 20.6 [Arbitration] (as amended by the Particular Conditions): any dispute not settled amicably shall "
            "be finally settled under the Rules of Arbitration of the International Chamber of Commerce by three arbitrators. "
            "The seat of arbitration shall be Singapore. The language of the arbitration shall be English.\n\n"
            "Governing Law (Sub-Clause 1.4, Particular Conditions): the Contract shall be governed by the law of England and Wales."
        ),
    ),
    # 2. Notice to Proceed
    DocSeed(
        key="NTP",
        filename="Notice_to_Proceed.txt",
        document_type="NOTICE",
        doc_date=date(2023, 1, 15),
        author=ENGINEER,
        recipient=CONTRACTOR,
        evidence_number="C-2",
        text=(
            "NOTICE TO PROCEED — COMMENCEMENT DATE\nDate: 2023-01-15\nContract No. GIA/AX2/2022-01\n\n"
            "Pursuant to Sub-Clause 8.1 [Commencement of Works], the Engineer hereby notifies the Contractor that the "
            "Commencement Date is 15 January 2023. The Time for Completion of 900 days accordingly expires on 3 July 2025.\n\n"
            "Site access to Zones A (Terminal 2 extension) and B (Apron 4) is given with effect from the Commencement Date. "
            "Access to Zone C (Taxiway Kilo) will be given in accordance with the airport operations interface plan."
        ),
    ),
    # 3-7. Site Instructions
    _si(1, date(2023, 3, 10), "Relocation of existing utilities trench — Zone A",
        "The Contractor is instructed to relocate the existing 11kV cable and fibre trench along gridline A-12 to "
        "gridline A-16 to avoid conflict with the revised Terminal 2 foundation layout. Revised drawing U-101 Rev B attached."),
    _si(2, date(2023, 5, 22), "HOLD on Apron 4 pavement works pending redesign",
        "The Contractor is instructed to suspend all pavement quality concrete works on Apron 4 with immediate effect "
        "pending the Employer's redesign of the apron to accommodate Code F aircraft. Revised apron drawings will be issued "
        "in due course. The Contractor shall maintain the works and protect the sub-base."),
    _si(3, date(2023, 8, 14), "Change of structural steel grade — Baggage Hall",
        "The Contractor is instructed to change the structural steel for the Baggage Hall roof from grade S355 to S460 "
        "per revised structural calculations SC-44 Rev C. Existing orders for S355 sections shall be amended."),
    _si(4, date(2023, 11, 6), "Additional passive fire protection — Terminal 2 extension",
        "Following the Civil Defence review, the Contractor is instructed to provide additional intumescent coating "
        "(120-minute rating) to primary steel members in the Terminal 2 extension as per specification section 07-81-16 Rev 2."),
    _si(5, date(2024, 2, 19), "Resequencing of Taxiway Kilo works for airport operations",
        "Owing to increased night-time aircraft movements, the Contractor is instructed to resequence Taxiway Kilo works "
        "into four phases (K1-K4) with works permitted only between 23:30 and 05:00. Access to Zone C is restricted "
        "accordingly until further notice."),
    # 8-12. Variation Orders
    _vo(1, date(2023, 4, 3), "SI-001", "Utilities trench relocation", "USD 3,200,000",
        "The relocation instructed by SI-001 is confirmed as a Variation under Sub-Clause 13.1."),
    _vo(2, date(2023, 7, 10), "SI-002", "Apron 4 redesign for Code F aircraft", "USD 8,750,000",
        "Revised Apron 4 drawings A4-200 series Rev D issued on 3 July 2023. The redesign increases pavement thickness "
        "and adds two stands. The HOLD under SI-002 is lifted with effect from 10 July 2023."),
    _vo(3, date(2023, 9, 25), "SI-003", "Structural steel grade change S355 to S460", "USD 5,400,000",
        "The change of grade is a Variation. The Contractor has stated that mill lead times for S460 sections are "
        "approximately 16 weeks."),
    _vo(4, date(2023, 12, 18), "SI-004", "Additional passive fire protection", "USD 2,100,000",
        "Additional intumescent coating to primary steel members is confirmed as a Variation."),
    _vo(5, date(2024, 3, 28), "SI-005", "Taxiway Kilo resequencing and night working", "USD 4,600,000 (Engineer's valuation; disputed)",
        "The Engineer values the resequencing at USD 4,600,000 using contract rates adjusted for night working. The "
        "Contractor's submitted valuation is USD 6,950,000 including loss of productivity and additional lighting and "
        "security. The difference of USD 2,350,000 is not agreed."),
    # 13. EOT Claim #1
    DocSeed(
        key="EOT-CLAIM-1",
        filename="EOT_Claim_1_Apron_Redesign.txt",
        document_type="CLAIM_SUBMISSION",
        doc_date=date(2024, 1, 20),
        author=CONTRACTOR,
        recipient=ENGINEER,
        evidence_number="C-13",
        text=(
            "FULLY DETAILED CLAIM FOR EXTENSION OF TIME No. 1\nDate: 2024-01-20\nSub-Clauses 8.4(a), 8.4(e) and 20.1\n\n"
            "1. The Contractor claims an extension of the Time for Completion of 146 days and associated prolongation costs "
            "of USD 14,600,000.\n\n"
            "2. Delay events: DE-01 — suspension of Apron 4 pavement works under SI-002 (22 May 2023) until the HOLD was lifted "
            "by VO-002 (10 July 2023); DE-02 — late issue of revised Apron 4 drawings (A4-200 Rev D issued 3 July 2023); "
            "DE-03 — additional pavement thickness and two new stands under VO-002.\n\n"
            "3. Notice: the Contractor gave notice by DN-01 dated 29 May 2023, 7 days after SI-002.\n\n"
            "4. Delay analysis: a time impact analysis was performed by impacting the delay events into the accepted "
            "Programme Revision 2 and verified against Revised Programme Rev 3 (20 December 2023). Apron 4 lies on the "
            "critical path to Sectional Completion of Stands 401-412 and to overall completion.\n\n"
            "5. Contemporaneous records: daily reports of 23 May 2023 and 15 June 2023 record the stoppage and the absence "
            "of revised drawings."
        ),
    ),
    # 14. EOT Claim #2
    DocSeed(
        key="EOT-CLAIM-2",
        filename="EOT_Claim_2_Taxiway_Resequencing.txt",
        document_type="CLAIM_SUBMISSION",
        doc_date=date(2024, 9, 30),
        author=CONTRACTOR,
        recipient=ENGINEER,
        evidence_number="C-14",
        text=(
            "FULLY DETAILED CLAIM FOR EXTENSION OF TIME No. 2\nDate: 2024-09-30\nSub-Clauses 8.4(a), 8.4(e) and 20.1\n\n"
            "1. The Contractor claims a further extension of time of 98 days and prolongation costs of USD 9,800,000 arising "
            "from the resequencing of Taxiway Kilo under SI-005 and restricted night-time access to Zone C.\n\n"
            "2. The Contractor acknowledges that delivery of S460 steel sections for the Baggage Hall was late between "
            "March and May 2024. The Contractor's position is that this delay was not critical because the Taxiway Kilo "
            "restrictions, an Employer risk event, independently delayed completion over the same period. To the extent "
            "the delays are concurrent, the Contractor relies on the approach in the SCL Delay and Disruption Protocol "
            "that concurrent Contractor delay should not reduce the extension of time due.\n\n"
            "3. Notice was given by DN-03 dated 25 March 2024.\n\n"
            "4. An updated programme for the period February to September 2024 will be submitted separately."
        ),
    ),
    # 15-17. Payment certificates
    _ipc(3, date(2023, 5, 31), "USD 31,400,000", "USD 9,120,000", "USD 9,120,000 (paid in full)",
         "No deductions."),
    _ipc(7, date(2023, 10, 31), "USD 88,950,000", "USD 12,640,000", "USD 12,640,000 (paid 28 days late)",
         "Includes valuation of VO-001 and VO-002 (partial)."),
    _ipc(12, date(2024, 4, 30), "USD 141,300,000", "USD 10,980,000", "USD 4,030,000 (partial payment)",
         "The Employer withheld USD 6,950,000 citing the disputed valuation of VO-005 and anticipated Delay Damages. The "
         "Engineer notes that no notice under Sub-Clause 2.5 [Employer's Claims] had been given at the date of this certificate."),
    # 18-22. Daily reports
    _dr(date(2023, 5, 23), "Fine, 31°C",
        "Apron 4: all PQC paving crews stood down following SI-002 HOLD. Slipform paver and 2 batching lines idle. "
        "Labour on Apron 4: 64 operatives redeployed to sub-base protection; 38 operatives idle. Engineer's representative "
        "informed verbally at 08:15."),
    _dr(date(2023, 6, 15), "Heavy showers PM",
        "Apron 4 remains on HOLD. No revised apron drawings received (RFI-233 and RFI-241 outstanding). Paving plant "
        "remains on standby at the Employer's instruction. Terminal 2 steel erection progressing on gridlines T-1 to T-9."),
    _dr(date(2023, 8, 16), "Fine",
        "Baggage Hall: S355 steel deliveries suspended following SI-003. Supplier advises S460 sections lead time "
        "14-16 weeks. Erection sequence revised to proceed with Terminal 2 roof first."),
    _dr(date(2024, 2, 21), "Fine, night works",
        "Taxiway Kilo: first night shift under SI-005 resequencing. Effective working window 23:30-05:00 reduced to 3.5 "
        "productive hours after airside security checks. Output approx. 35% of planned daily production."),
    _dr(date(2024, 6, 12), "Thunderstorms, 62mm rainfall",
        "Taxiway Kilo phase K2: works suspended from 01:10 due to lightning warning; access restricted by airport "
        "operations. Baggage Hall: final S460 sections delivered 28 May 2024; roof erection resumed."),
    # 23-25. Delay notices
    _dn(1, date(2023, 5, 29), "Suspension of Apron 4 pavement works under SI-002", date(2023, 5, 22),
        "The HOLD instruction prevents the execution of critical-path paving works. The Contractor gives notice that "
        "it considers itself entitled to an extension of time and additional payment."),
    _dn(2, date(2023, 9, 20), "Change of structural steel grade under SI-003 and resulting procurement delay", date(2023, 8, 14),
        "The change to S460 requires re-procurement with extended mill lead times. The Contractor gives notice of "
        "delay to the Baggage Hall works and reserves its entitlement."),
    _dn(3, date(2024, 3, 25), "Resequencing of Taxiway Kilo and restricted access to Zone C under SI-005", date(2024, 2, 19),
        "Productive hours on Taxiway Kilo have been reduced by approximately 65%. The Contractor gives notice that "
        "completion will be delayed and claims an extension of time and additional payment."),
    # 26. Employer response
    DocSeed(
        key="EMPLOYER-RESPONSE",
        filename="Employer_Response_to_EOT_Claims.txt",
        document_type="RESPONSE",
        doc_date=date(2024, 11, 15),
        author=EMPLOYER,
        recipient=CONTRACTOR,
        evidence_number="R-1",
        text=(
            "EMPLOYER'S RESPONSE TO EOT CLAIMS No. 1 AND No. 2\nDate: 2024-11-15\n\n"
            "1. EOT Claim No. 1: the Employer accepts that SI-002 suspended the Apron 4 works but contends that only 61 days "
            "of critical delay are demonstrated; the Contractor's time impact analysis relies on Programme Revision 2, which "
            "the Employer says was never accepted by the Engineer.\n\n"
            "2. EOT Claim No. 2: the Employer contends that notice DN-03 dated 25 March 2024 was given 35 days after SI-005 "
            "(19 February 2024) and therefore outside the 28-day period in Sub-Clause 20.1, so that the claim is time-barred. "
            "The Employer further contends that the Contractor's late procurement of S460 steel was the dominant cause of "
            "delay in March-May 2024, and that the Contractor's notice DN-02 regarding the steel was itself given 37 days "
            "after SI-003.\n\n"
            "3. The Employer rejects the application of the SCL Protocol to concurrent delay under English law and the "
            "Contract.\n\n"
            "4. The Employer gives notice under Sub-Clause 2.5 that it intends to deduct Delay Damages at USD 125,000 per "
            "day from the Time for Completion (3 July 2025) up to the cap of USD 25,000,000."
        ),
    ),
    # 27. Notice of Arbitration
    DocSeed(
        key="NOA",
        filename="Request_for_Arbitration_ICC.txt",
        document_type="ARBITRATION_FILING",
        doc_date=date(2025, 9, 1),
        author=f"{CONTRACTOR} (Claimant) by its counsel",
        recipient="ICC International Court of Arbitration — Secretariat",
        evidence_number="C-27",
        confidentiality="HIGHLY_CONFIDENTIAL",
        text=(
            "REQUEST FOR ARBITRATION (Notice of Arbitration)\nDate: 2025-09-01\nSubmitted under Article 4 of the ICC Rules "
            "of Arbitration 2021\n\n"
            f"Claimant: {CONTRACTOR}. Respondent: {EMPLOYER}.\n\n"
            "Arbitration agreement: Sub-Clause 20.6 of the Contract (as amended): ICC Rules, three arbitrators, seat Singapore, "
            "language English. Governing law: English law.\n\n"
            "Relief sought: (a) a declaration that the Claimant is entitled to an extension of time of 244 days (EOT-01: 146 "
            "days; EOT-02: 98 days); (b) prolongation costs of USD 24,400,000; (c) a declaration that the Respondent is not "
            "entitled to Delay Damages and repayment of USD 25,000,000 withheld; (d) USD 2,350,000 in respect of the "
            "valuation of VO-005; (e) USD 11,200,000 in unpaid certified sums and retention; (f) interest and costs.\n\n"
            "The Claimant nominates Ms. J. Tan as co-arbitrator, subject to confirmation under Article 13."
        ),
    ),
    # 28. Baseline Programme
    DocSeed(
        key="BASELINE",
        filename="Baseline_Programme_Rev0.txt",
        document_type="PROGRAMME",
        doc_date=date(2022, 12, 15),
        author=CONTRACTOR,
        recipient=ENGINEER,
        evidence_number="C-28",
        text=(
            "BASELINE PROGRAMME (Revision 0) — narrative\nDate: 2022-12-15\nSubmitted under Sub-Clause 8.3\n\n"
            "Planned Commencement: 15 January 2023. Planned Completion: 3 July 2025 (900 days).\n\n"
            "Critical path: Zone B Apron 4 earthworks → sub-base → PQC paving (planned 1 May - 30 Sept 2023) → AGL and "
            "markings → Sectional Completion Stands 401-412 → Zone C Taxiway Kilo (planned Jan - Jun 2024, day works) → "
            "Completion.\n\nNear-critical: Baggage Hall steel (float 21 days), Terminal 2 fit-out (float 35 days).\n\n"
            "Status: accepted by the Engineer by letter dated 10 January 2023 (ref. AEC/GIA/0112)."
        ),
    ),
    # 29. Revised Programme Rev 3
    DocSeed(
        key="PROG-REV3",
        filename="Revised_Programme_Rev3.txt",
        document_type="PROGRAMME",
        doc_date=date(2023, 12, 20),
        author=CONTRACTOR,
        recipient=ENGINEER,
        evidence_number="C-29",
        text=(
            "REVISED PROGRAMME — Revision 3 — narrative\nDate: 2023-12-20\nSubmitted under Sub-Clause 8.3\n\n"
            "Forecast Completion: 26 November 2025 (146 days later than the Time for Completion), reflecting the Apron 4 "
            "HOLD (SI-002) and the redesign (VO-002).\n\n"
            "Critical path: Apron 4 PQC paving (re-planned 15 Jul 2023 - 31 Jan 2024) → Stands 401-412 → Taxiway Kilo "
            "(re-planned Feb - Aug 2024) → Completion.\n\n"
            "Baggage Hall steel now forecast to complete 30 May 2024 with 12 days float following SI-003.\n\n"
            "Status: the Engineer responded on 18 January 2024 with comments; no formal acceptance recorded. Programme "
            "Revision 2 (August 2023) was returned 'reviewed with comments'."
        ),
    ),
    # 30. Quantum summary
    DocSeed(
        key="QUANTUM",
        filename="Quantum_Summary_Report.txt",
        document_type="EXPERT_REPORT",
        doc_date=date(2025, 6, 30),
        author="QS Advisory Partners (Claimant's quantum consultant)",
        recipient=CONTRACTOR,
        evidence_number="C-30",
        confidentiality="PRIVILEGED",
        text=(
            "QUANTUM SUMMARY REPORT — DRAFT, prepared at the request of counsel, privileged and confidential\n"
            "Date: 2025-06-30\n\n"
            "Summary of heads of claim (USD):\n"
            "EOT-01 prolongation (146 days x USD 100,000/day time-related costs): 14,600,000\n"
            "EOT-02 prolongation (98 days x USD 100,000/day): 9,800,000\n"
            "Delay Damages withheld / to be repaid: 25,000,000\n"
            "VO-005 valuation difference: 2,350,000\n"
            "Unpaid certified sums (IPC-12 shortfall USD 6,950,000) and retention release (USD 4,250,000): 11,200,000\n"
            "Total: 62,950,000 excluding interest and costs.\n\n"
            "Methodology: prolongation costs are calculated using an average daily rate derived from tender preliminaries "
            "rather than actual cost records for the delay periods. Actual cost records for site overheads for 2023-2024 "
            "have been requested from the Claimant's accounts department but not yet received.\n\n"
            "Head office overheads have not been claimed pending further analysis (Emden formula considered)."
        ),
    ),
]

assert len(DOCUMENTS) == 30, len(DOCUMENTS)
