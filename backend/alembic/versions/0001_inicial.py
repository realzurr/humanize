"""criação inicial das tabelas (Onda 8)

Revision ID: 0001_inicial
Revises:
Create Date: 2026-10-22

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_inicial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("password_hash", sa.String(length=256), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "provider_credentials",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("owner_id", sa.String(length=32), nullable=True),
        sa.Column("ciphertext", sa.Text(), nullable=False),
        sa.Column("last4", sa.String(length=4), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_provider_credentials_provider", "provider_credentials", ["provider"])
    op.create_index("ix_provider_credentials_owner_id", "provider_credentials", ["owner_id"])

    op.create_table(
        "documents",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("owner_id", sa.String(length=32), nullable=True),
        sa.Column("original_text", sa.Text(), nullable=False),
        sa.Column("current_revision_id", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_documents_owner_id", "documents", ["owner_id"])

    op.create_table(
        "revisions",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("document_id", sa.String(length=32), nullable=False),
        sa.Column("stage", sa.String(length=40), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("parent_id", sa.String(length=32), nullable=True),
        sa.Column("transformations_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_revisions_document_id", "revisions", ["document_id"])

    op.create_table(
        "exports",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("document_id", sa.String(length=32), nullable=True),
        sa.Column("owner_id", sa.String(length=32), nullable=True),
        sa.Column("format", sa.String(length=10), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("template_id", sa.String(length=120), nullable=False),
        sa.Column("institution_id", sa.String(length=120), nullable=True),
        sa.Column("warnings_json", sa.Text(), nullable=False),
        sa.Column("limitations_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_exports_document_id", "exports", ["document_id"])
    op.create_index("ix_exports_owner_id", "exports", ["owner_id"])


def downgrade() -> None:
    op.drop_index("ix_exports_owner_id", table_name="exports")
    op.drop_index("ix_exports_document_id", table_name="exports")
    op.drop_table("exports")
    op.drop_index("ix_revisions_document_id", table_name="revisions")
    op.drop_table("revisions")
    op.drop_index("ix_documents_owner_id", table_name="documents")
    op.drop_table("documents")
    op.drop_index("ix_provider_credentials_owner_id", table_name="provider_credentials")
    op.drop_index("ix_provider_credentials_provider", table_name="provider_credentials")
    op.drop_table("provider_credentials")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
