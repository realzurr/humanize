"""amplia exports.document_id para 120 caracteres

O schema da API (``ExportRequest.document_id``) aceita até 120 caracteres;
com ``String(32)`` o PostgreSQL rejeitava a gravação com ``DataError``.

Revision ID: 0002_exports_document_id
Revises: 0001_inicial
Create Date: 2026-10-22

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_exports_document_id"
down_revision = "0001_inicial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("exports") as batch:
        batch.alter_column(
            "document_id",
            existing_type=sa.String(length=32),
            type_=sa.String(length=120),
            existing_nullable=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("exports") as batch:
        batch.alter_column(
            "document_id",
            existing_type=sa.String(length=120),
            type_=sa.String(length=32),
            existing_nullable=True,
        )
