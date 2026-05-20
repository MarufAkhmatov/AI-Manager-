"""notifications table (auto-audit findings)

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-20
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("kind", sa.Text, nullable=False, server_default="audit"),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("source_url", sa.Text),
        sa.Column("summary", sa.Text, nullable=False, server_default=""),
        sa.Column(
            "case_analysis",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "read", sa.Boolean, nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_notifications_created", "notifications", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_notifications_created", table_name="notifications")
    op.drop_table("notifications")
