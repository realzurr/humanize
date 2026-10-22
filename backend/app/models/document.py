"""Modelos ORM de documento e revisões.

``original_text`` é imutável: nenhuma rota ou serviço o sobrescreve (regra de
engenharia 4). Cada estágio produz uma ``DocumentRevision`` com o texto
resultante e as transformações aplicadas (serializadas em JSON para
rastreabilidade, sem inventar estrutura relacional adicional).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models._util import new_id, utcnow


class Document(Base):
    """Documento acadêmico persistido, isolado por ``owner_id``."""

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    owner_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    original_text: Mapped[str] = mapped_column(Text)
    current_revision_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    revisions: Mapped[list[DocumentRevision]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentRevision.created_at",
    )


class DocumentRevision(Base):
    """Uma versão do documento, produzida por um estágio do pipeline."""

    __tablename__ = "revisions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    stage: Mapped[str] = mapped_column(String(40))
    text: Mapped[str] = mapped_column(Text)
    parent_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    transformations_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    document: Mapped[Document] = relationship(back_populates="revisions")
