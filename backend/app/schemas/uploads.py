"""Schemas de upload de documentos."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class UploadResponse(BaseModel):
    """Resultado de um upload validado e armazenado."""

    model_config = ConfigDict(frozen=True)

    id: str
    filename: str
    format: str
    size_bytes: int
    texto: str
