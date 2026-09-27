from __future__ import annotations

from enum import Enum
from typing import Any, TypedDict

PRODUCT_DISCLAIMER = (
    "ArbiConstruct AI provides AI-assisted information management and research. It does not provide "
    "legal advice or legal representation. AI outputs must be reviewed by qualified legal professionals."
)
AI_DISCLAIMER = "AI-assisted analysis. Final legal judgment must be performed by qualified legal professionals."


class FindingLabel(str, Enum):
    FACT = "FACT"
    SOURCE_BASED_INFO = "SOURCE_BASED_INFO"
    AI_SUMMARY = "AI_SUMMARY"
    POTENTIAL_ISSUE = "POTENTIAL_ISSUE"
    POTENTIAL_EVIDENCE_GAP = "POTENTIAL_EVIDENCE_GAP"
    REQUIRES_HUMAN_REVIEW = "REQUIRES_HUMAN_REVIEW"


class CorpusName(str, Enum):
    RULES = "rules"
    CONSTRUCTION = "construction"
    CASE = "case"


class InstitutionCode(str, Enum):
    ICC = "ICC"
    SIAC = "SIAC"
    LCIA = "LCIA"
    HKIAC = "HKIAC"
    ICDR = "ICDR"
    UNCITRAL = "UNCITRAL"
    ICSID = "ICSID"
    OTHER = "OTHER"


class SourceTier(str, Enum):
    OFFICIAL = "official"
    INSTITUTIONAL = "institutional"
    SECONDARY = "secondary"


class ProcedureStageName(str, Enum):
    ARBITRATION_AGREEMENT = "ARBITRATION_AGREEMENT"
    PRE_ARBITRATION = "PRE_ARBITRATION"
    NOTICE_OF_ARBITRATION = "NOTICE_OF_ARBITRATION"
    RESPONSE = "RESPONSE"
    TRIBUNAL_CONSTITUTION = "TRIBUNAL_CONSTITUTION"
    PRELIMINARY_STAGE = "PRELIMINARY_STAGE"
    TERMS_OF_REFERENCE = "TERMS_OF_REFERENCE"
    PLEADINGS = "PLEADINGS"
    DOCUMENT_PRODUCTION = "DOCUMENT_PRODUCTION"
    WITNESS_STATEMENTS = "WITNESS_STATEMENTS"
    EXPERT_REPORTS = "EXPERT_REPORTS"
    PROCEDURAL_HEARINGS = "PROCEDURAL_HEARINGS"
    EVIDENTIARY_HEARING = "EVIDENTIARY_HEARING"
    POST_HEARING = "POST_HEARING"
    CLOSING = "CLOSING"
    AWARD = "AWARD"
    CORRECTION_INTERPRETATION = "CORRECTION_INTERPRETATION"
    RECOGNITION_ENFORCEMENT = "RECOGNITION_ENFORCEMENT"
    ANNULMENT = "ANNULMENT"


class FindingDict(TypedDict):
    label: str
    content: str
    citations: list[str]


class AgentResponseDict(TypedDict):
    summary: str
    findings: list[FindingDict]
    evidence_gaps: list[str]
    requires_human_review: list[str]
    sources: list[dict[str, Any]]
    model: str
    agent: str
