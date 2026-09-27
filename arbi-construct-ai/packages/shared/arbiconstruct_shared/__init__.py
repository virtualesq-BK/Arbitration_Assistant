"""Shared, dependency-free Python types for ArbiConstruct AI.

Used by the crawler, ingest scripts and any future worker services so they agree with the
API on enum values and AI-output labels without importing the FastAPI application.
"""
from arbiconstruct_shared.types import (
    AI_DISCLAIMER,
    PRODUCT_DISCLAIMER,
    AgentResponseDict,
    CorpusName,
    FindingDict,
    FindingLabel,
    InstitutionCode,
    ProcedureStageName,
    SourceTier,
)

__all__ = [
    "AI_DISCLAIMER",
    "PRODUCT_DISCLAIMER",
    "AgentResponseDict",
    "CorpusName",
    "FindingDict",
    "FindingLabel",
    "InstitutionCode",
    "ProcedureStageName",
    "SourceTier",
]
