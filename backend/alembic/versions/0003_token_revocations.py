"""tabelas de revogação de tokens (revoked_tokens, revoked_subjects)

Revision ID: 0003_token_revocations
Revises: 0002_exports_document_id
Create Date: 2026-10-22

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_token_revocations"
down_revision = "0002_exports_document_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "revoked_tokens",
        sa.Column("jti", sa.String(length=64), primary_key=True),
        sa.Column("expires_at", sa.Float(), nullable=False),
    )
    op.create_index("ix_revoked_tokens_expires_at", "revoked_tokens", ["expires_at"])
    op.create_table(
        "revoked_subjects",
        sa.Column("subject", sa.String(length=32), primary_key=True),
        sa.Column("revoked_before", sa.Float(), nullable=False),
    )
    op.create_index("ix_revoked_subjects_revoked_before", "revoked_subjects", ["revoked_before"])


def downgrade() -> None:
    op.drop_index("ix_revoked_subjects_revoked_before", table_name="revoked_subjects")
    op.drop_table("revoked_subjects")
    op.drop_index("ix_revoked_tokens_expires_at", table_name="revoked_tokens")
    op.drop_table("revoked_tokens")
