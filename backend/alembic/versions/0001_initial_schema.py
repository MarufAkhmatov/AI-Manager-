"""initial schema (users + 5 design tables, pgvector + HNSW)

Revision ID: 0001
Revises:
Create Date: 2026-05-18
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

EMBED_DIM = 1024


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("username", sa.Text, unique=True, nullable=False),
        sa.Column("password_hash", sa.Text, nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("disabled_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "role IN ('admin','analyst','viewer')", name="users_role_check"
        ),
    )

    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("sha256", sa.String(64), unique=True, nullable=False),
        sa.Column("title", sa.Text),
        sa.Column("category", sa.Text, nullable=False),
        sa.Column("authority", sa.Text),
        sa.Column("source_url", sa.Text),
        sa.Column("raw_path", sa.Text, nullable=False),
        sa.Column("processed_path", sa.Text),
        sa.Column("status", sa.Text, nullable=False, server_default="active"),
        sa.Column(
            "is_confidential", sa.Boolean, nullable=False, server_default=sa.text("false")
        ),
        sa.Column("issued_at", sa.Date),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "superseded_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id"),
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.create_index("ix_documents_category_status", "documents", ["category", "status"])
    op.create_index("ix_documents_authority", "documents", ["authority"])

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("token_count", sa.Integer, nullable=False),
        sa.Column("embedding", Vector(EMBED_DIM), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("section_path", sa.Text),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_chunk_doc_idx"),
    )
    op.create_index(
        "ix_document_chunks_content_hash", "document_chunks", ["content_hash"]
    )
    op.execute(
        "CREATE INDEX document_chunks_hnsw ON document_chunks "
        "USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
    )

    op.create_table(
        "processed_files",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("stage", sa.Text, nullable=False),
        sa.Column("status", sa.Text, nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
    )
    op.create_index(
        "ix_processed_files_doc_stage", "processed_files", ["document_id", "stage"]
    )

    op.create_table(
        "agent_logs",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("task_id", postgresql.UUID(as_uuid=True)),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column("agent", sa.Text, nullable=False),
        sa.Column("event", sa.Text, nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("ms_elapsed", sa.Integer),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_agent_logs_task_created", "agent_logs", ["task_id", "created_at"])

    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("kind", sa.Text, nullable=False),
        sa.Column("status", sa.Text, nullable=False, server_default="queued"),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "input",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("output", postgresql.JSONB),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_tasks_status_kind", "tasks", ["status", "kind"])


def downgrade() -> None:
    op.drop_index("ix_tasks_status_kind", table_name="tasks")
    op.drop_table("tasks")
    op.drop_index("ix_agent_logs_task_created", table_name="agent_logs")
    op.drop_table("agent_logs")
    op.drop_index("ix_processed_files_doc_stage", table_name="processed_files")
    op.drop_table("processed_files")
    op.execute("DROP INDEX IF EXISTS document_chunks_hnsw")
    op.drop_index("ix_document_chunks_content_hash", table_name="document_chunks")
    op.drop_table("document_chunks")
    op.drop_index("ix_documents_authority", table_name="documents")
    op.drop_index("ix_documents_category_status", table_name="documents")
    op.drop_table("documents")
    op.drop_table("users")
