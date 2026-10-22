"""Schemas de documentos persistidos."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

MAX_TEXT_LENGTH = 1_000_000


class DocumentCreateRequest(BaseModel):
    """Criação de um documento (o texto original é imutável)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    texto: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)


class DocumentOut(BaseModel):
    """Representação de um documento (sem expor o texto completo)."""

    model_config = ConfigDict(frozen=True)

    id: str
    owner_id: str | None = None
    tamanho_caracteres: int
    created_at: datetime
    updated_at: datetime


class PruneResponse(BaseModel):
    """Resultado da aplicação da política de retenção."""

    model_config = ConfigDict(frozen=True)

    removidos: int
    """Total removido (documentos + exportações); mantido por compatibilidade."""
    documentos: int = 0
    exportacoes: int = 0
