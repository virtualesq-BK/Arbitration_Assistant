"""Initial schema: pgvector extension + all ArbiConstruct AI tables.

Revision ID: 001_initial
Revises:
Create Date: 2026-09-28
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EMBEDDING_DIM = 1536
ENUM_LEN = 40  # enums are stored as VARCHAR (non-native) — see models/base.py::enum_column


def _base_cols() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ]


def _fk(column: str, target: str, ondelete: str = "CASCADE", nullable: bool = False, index: bool = True) -> sa.Column:
    return sa.Column(column, sa.Uuid(), sa.ForeignKey(target, ondelete=ondelete), nullable=nullable, index=index)


def _enum(name: str, nullable: bool = False) -> sa.Column:
    return sa.Column(name, sa.String(ENUM_LEN), nullable=nullable)


def upgrade() -> None:
    # 1. Extensions first
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # 2. Tenancy
    op.create_table(
        "organizations",
        *_base_cols(),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=True, unique=True),
        sa.Column("country", sa.String(100), nullable=True),
    )
    op.create_table(
        "users",
        *_base_cols(),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        _enum("role"),
        _fk("org_id", "organizations.id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table(
        "organization_members",
        *_base_cols(),
        _fk("org_id", "organizations.id"),
        _fk("user_id", "users.id"),
        _enum("role"),
        sa.UniqueConstraint("org_id", "user_id", name="uq_org_member"),
    )

    # 3. Cases
    op.create_table(
        "cases",
        *_base_cols(),
        _fk("org_id", "organizations.id"),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        _enum("institution"),
        sa.Column("seat", sa.String(255), nullable=True),
        sa.Column("governing_law", sa.String(255), nullable=True),
        sa.Column("language", sa.String(50), nullable=False, server_default="English"),
        _enum("status"),
        sa.Column("amount_in_dispute", sa.Numeric(20, 2), nullable=True),
        sa.Column("currency", sa.String(3), nullable=True),
        sa.Column("case_ref", sa.String(100), nullable=True, index=True),
    )
    op.create_table(
        "case_parties",
        *_base_cols(),
        _fk("case_id", "cases.id"),
        sa.Column("name", sa.String(500), nullable=False),
        _enum("role"),
        sa.Column("counsel", sa.String(500), nullable=True),
        sa.Column("country", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )

    # 4. Documents + chunks (CASE corpus)
    op.create_table(
        "documents",
        *_base_cols(),
        _fk("case_id", "cases.id"),
        _fk("org_id", "organizations.id"),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("s3_key", sa.String(1000), nullable=True),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("mime_type", sa.String(255), nullable=True),
        _enum("document_type"),
        sa.Column("author", sa.String(500), nullable=True),
        sa.Column("recipient", sa.String(500), nullable=True),
        sa.Column("doc_date", sa.Date(), nullable=True, index=True),
        sa.Column("language", sa.String(50), nullable=True),
        _enum("confidentiality_level"),
        _enum("privilege_status"),
        sa.Column("evidence_number", sa.String(50), nullable=True),
        sa.Column("file_hash", sa.String(64), nullable=True, index=True),
        sa.Column("ocr_text", sa.Text(), nullable=True),
        _enum("ocr_status"),
        _enum("classification_status"),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
    )
    op.create_table(
        "document_chunks",
        *_base_cols(),
        _fk("document_id", "documents.id"),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
        _fk("case_id", "cases.id"),
        _fk("org_id", "organizations.id"),
    )
    op.execute(
        "CREATE INDEX ix_document_chunks_embedding_hnsw ON document_chunks "
        "USING hnsw (embedding vector_cosine_ops)"
    )
    op.execute(
        "CREATE INDEX ix_document_chunks_text_fts ON document_chunks "
        "USING gin (to_tsvector('english', text))"
    )

    # 5. Institutions, rules and shared knowledge (RULES / CONSTRUCTION corpora)
    op.create_table(
        "arbitration_institutions",
        *_base_cols(),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("short_name", sa.String(32), nullable=False),
        sa.Column("website", sa.String(500), nullable=True),
        sa.Column("rules_version", sa.String(50), nullable=True),
        sa.Column("rules_effective_date", sa.Date(), nullable=True),
        sa.Column("rules_url", sa.String(1000), nullable=True),
        sa.Column("source_tier", sa.String(20), nullable=False, server_default="official"),
    )
    op.create_index("ix_arbitration_institutions_short_name", "arbitration_institutions", ["short_name"], unique=True)
    op.create_table(
        "arbitration_rules",
        *_base_cols(),
        _fk("institution_id", "arbitration_institutions.id"),
        sa.Column("stage", sa.String(ENUM_LEN), nullable=False, index=True),
        sa.Column("article_number", sa.String(100), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("source_url", sa.String(1000), nullable=True),
        sa.Column("rule_version", sa.String(50), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("typical_deadline_days", sa.Integer(), nullable=True),
    )
    op.create_table(
        "knowledge_chunks",
        *_base_cols(),
        sa.Column("corpus", sa.String(32), nullable=False, index=True),
        sa.Column("source_name", sa.String(500), nullable=False),
        sa.Column("source_url", sa.String(1000), nullable=True),
        sa.Column("institution", sa.String(32), nullable=True, index=True),
        sa.Column("rule_version", sa.String(50), nullable=True),
        sa.Column("article_number", sa.String(100), nullable=True),
        _fk("rule_id", "arbitration_rules.id", nullable=True, index=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
    )
    op.execute(
        "CREATE INDEX ix_knowledge_chunks_embedding_hnsw ON knowledge_chunks "
        "USING hnsw (embedding vector_cosine_ops)"
    )

    # 6. Case analysis entities
    op.create_table(
        "timeline_events",
        *_base_cols(),
        _fk("case_id", "cases.id"),
        sa.Column("event_date", sa.Date(), nullable=False, index=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False, server_default="GENERAL"),
        _fk("source_document_id", "documents.id", ondelete="SET NULL", nullable=True, index=False),
        sa.Column("source_page", sa.Integer(), nullable=True),
        sa.Column("source_excerpt", sa.Text(), nullable=True),
        sa.Column("is_ai_extracted", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "claims",
        *_base_cols(),
        _fk("case_id", "cases.id"),
        sa.Column("claim_ref", sa.String(100), nullable=False),
        _enum("claim_type"),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("quantum", sa.Numeric(20, 2), nullable=True),
        sa.Column("currency", sa.String(3), nullable=True),
        _enum("status"),
        sa.Column("contract_clause", sa.String(255), nullable=True),
    )
    op.create_table(
        "claim_evidence",
        *_base_cols(),
        _fk("claim_id", "claims.id"),
        _fk("document_id", "documents.id"),
        sa.Column("relevance_note", sa.Text(), nullable=True),
        sa.Column("added_by_ai", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("claim_id", "document_id", name="uq_claim_document"),
    )
    op.create_table(
        "issues",
        *_base_cols(),
        _fk("case_id", "cases.id"),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(100), nullable=True),
        _enum("severity"),
        _enum("status"),
    )
    op.create_table(
        "procedural_events",
        *_base_cols(),
        _fk("case_id", "cases.id"),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("source_rule", sa.String(255), nullable=True),
        sa.Column("rule_reference", sa.String(255), nullable=True),
        sa.Column("source_url", sa.String(1000), nullable=True),
        _enum("status"),
        _fk("responsible_user_id", "users.id", ondelete="SET NULL", nullable=True, index=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_ai_suggested", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("requires_confirmation", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    # 7. Audit
    op.create_table(
        "ai_analyses",
        *_base_cols(),
        _fk("case_id", "cases.id", nullable=True),
        _fk("user_id", "users.id", ondelete="SET NULL", nullable=True),
        sa.Column("agent", sa.String(100), nullable=False),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column("prompt_version", sa.String(50), nullable=False),
        sa.Column("query", sa.Text(), nullable=True),
        sa.Column("retrieved_sources_json", postgresql.JSONB(), nullable=True),
        sa.Column("output_json", postgresql.JSONB(), nullable=True),
    )
    op.create_table(
        "audit_logs",
        *_base_cols(),
        _fk("org_id", "organizations.id", nullable=True),
        _fk("user_id", "users.id", ondelete="SET NULL", nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("resource_id", sa.String(100), nullable=True),
        sa.Column("details_json", postgresql.JSONB(), nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
    )


def downgrade() -> None:
    for table in (
        "audit_logs",
        "ai_analyses",
        "procedural_events",
        "issues",
        "claim_evidence",
        "claims",
        "timeline_events",
        "knowledge_chunks",
        "arbitration_rules",
        "arbitration_institutions",
        "document_chunks",
        "documents",
        "case_parties",
        "cases",
        "organization_members",
        "users",
        "organizations",
    ):
        op.drop_table(table)
