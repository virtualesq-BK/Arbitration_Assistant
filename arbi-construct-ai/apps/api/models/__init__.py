"""Import every model so Base.metadata is complete (used by Alembic and tests)."""
from models.base import Base, TimestampMixin
from models.user import User, UserRole
from models.organization import Organization, OrganizationMember
from models.case import ArbitrationInstitutionEnum, Case, CaseStatus
from models.case_party import CaseParty, PartyRole
from models.document import (
    ConfidentialityLevel,
    Document,
    DocumentType,
    PrivilegeStatus,
    ProcessingStatus,
)
from models.document_chunk import EMBEDDING_DIM, DocumentChunk
from models.arbitration_institution import ArbitrationInstitution
from models.arbitration_rule import STAGE_ORDER, ArbitrationRule, ProcedureStage
from models.knowledge_chunk import KnowledgeChunk
from models.timeline_event import TimelineEvent
from models.claim import Claim, ClaimStatus, ClaimType
from models.claim_evidence import ClaimEvidence
from models.issue import Issue, IssueSeverity, IssueStatus
from models.procedural_event import ProceduralEvent, ProceduralEventStatus
from models.ai_analysis import AIAnalysis
from models.audit_log import AuditLog

__all__ = [
    "Base",
    "TimestampMixin",
    "User",
    "UserRole",
    "Organization",
    "OrganizationMember",
    "Case",
    "CaseStatus",
    "ArbitrationInstitutionEnum",
    "CaseParty",
    "PartyRole",
    "Document",
    "DocumentType",
    "ConfidentialityLevel",
    "PrivilegeStatus",
    "ProcessingStatus",
    "DocumentChunk",
    "EMBEDDING_DIM",
    "KnowledgeChunk",
    "TimelineEvent",
    "Claim",
    "ClaimType",
    "ClaimStatus",
    "ClaimEvidence",
    "Issue",
    "IssueSeverity",
    "IssueStatus",
    "ArbitrationInstitution",
    "ArbitrationRule",
    "ProcedureStage",
    "STAGE_ORDER",
    "ProceduralEvent",
    "ProceduralEventStatus",
    "AIAnalysis",
    "AuditLog",
]
