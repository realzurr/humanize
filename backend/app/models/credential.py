"""Modelo ORM de credencial de provedor (persistida, cifrada em repouso)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models._util import utcnow


class ProviderCredential(Base):
    """Credencial de provedor de LLM.

    Armazena apenas o **ciphertext** (token AES-GCM ``v1:...``) e o sufixo
    ``last4`` — nunca o valor em claro. O ``owner_id`` é nulo no modo local
    (sem autenticação) e preenchido quando a autenticação está ativa.
    """

    __tablename__ = "provider_credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    owner_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    ciphertext: Mapped[str] = mapped_column(Text)
    last4: Mapped[str] = mapped_column(String(4), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
