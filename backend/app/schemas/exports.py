"""Schemas da API de exportação de documentos (Onda 6)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.ir.document import DocumentMetadata
from app.services.document_export.writer import (
    DocumentPreview,
    ExportFormat,
    ExportRecord,
)

MAX_EXPORT_TEXT_LENGTH = 1_000_000


class ExportRequest(BaseModel):
    """Requisição de geração e exportação de documento acadêmico."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    document_id: str = Field(default="doc-local", min_length=1, max_length=120)
    texto: str = Field(default="", max_length=MAX_EXPORT_TEXT_LENGTH)
    template_id: str = Field(default="abnt.tcc", min_length=1, max_length=120)
    instituicao: str | None = Field(default=None, max_length=120)
    metadados: DocumentMetadata = Field(default_factory=DocumentMetadata)
    formatos: tuple[ExportFormat, ...] = (
        ExportFormat.DOCX,
        ExportFormat.PDF,
        ExportFormat.TXT,
        ExportFormat.MARKDOWN,
    )
    incluir_pre_textual: bool = True


class ExportPreviewRequest(BaseModel):
    """Requisição de pré-visualização estruturada do documento."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    document_id: str = Field(default="doc-local", min_length=1, max_length=120)
    texto: str = Field(default="", max_length=MAX_EXPORT_TEXT_LENGTH)
    template_id: str = Field(default="abnt.tcc", min_length=1, max_length=120)
    instituicao: str | None = Field(default=None, max_length=120)
    metadados: DocumentMetadata = Field(default_factory=DocumentMetadata)


class ExportResponse(BaseModel):
    """Resposta da exportação com registros de versão, pré-visualização e limitações."""

    model_config = ConfigDict(frozen=True)

    document_id: str
    revision_id: str
    template_id: str
    instituicao: str | None = None
    pdf_available: bool
    exports: list[ExportRecord] = Field(default_factory=list)
    preview: DocumentPreview
    warnings: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class DocumentHistoryResponse(BaseModel):
    """Histórico de revisões e exportações de um documento."""

    model_config = ConfigDict(frozen=True)

    document_id: str
    original_immutable: bool = True
    revisions: list[dict[str, Any]] = Field(default_factory=list)
    exports: list[dict[str, Any]] = Field(default_factory=list)
