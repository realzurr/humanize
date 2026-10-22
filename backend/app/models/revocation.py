"""Modelos ORM de revogação de tokens de acesso.

Os instantes são guardados como *epoch* (``Float``), o mesmo formato de ``iat``
e ``exp`` no payload do token, evitando conversões de fuso na comparação.
"""

from __future__ import annotations

from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RevokedToken(Base):
    """Token revogado individualmente (``jti``), mantido até expirar."""

    __tablename__ = "revoked_tokens"

    jti: Mapped[str] = mapped_column(String(64), primary_key=True)
    expires_at: Mapped[float] = mapped_column(Float, index=True)


class RevokedSubject(Base):
    """Corte de revogação por usuário: tokens emitidos até ``revoked_before`` são inválidos."""

    __tablename__ = "revoked_subjects"

    subject: Mapped[str] = mapped_column(String(32), primary_key=True)
    revoked_before: Mapped[float] = mapped_column(Float, index=True)
