"""Modelo ORM de exportação (histórico relacional, isolado por ``owner_id``)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models._util import new_id, utcnow


class Export(Base):
    """Metadados de uma exportação persistida.

    O conteúdo binário permanece em disco (``export_dir``); aqui ficam os
    metadados rastreáveis (hash, tamanho, formato, dono) e as listas de
    avisos/limitações serializadas em JSON.
    """

    __tablename__ = "exports"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    document_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    owner_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    format: Mapped[str] = mapped_column(String(10))
    filename: Mapped[str] = mapped_column(String(255))
    sha256: Mapped[str] = mapped_column(String(64), default="")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    template_id: Mapped[str] = mapped_column(String(120), default="")
    institution_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    warnings_json: Mapped[str] = mapped_column(Text, default="[]")
    limitations_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
