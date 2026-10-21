"""Schemas da API de validação acadêmica."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

MAX_TEXT_LENGTH = 1_000_000


class AcademicValidateRequest(BaseModel):
    """Requisição de validação acadêmica."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    texto: str = Field(default="", max_length=MAX_TEXT_LENGTH)
    consultar_doi: bool = Field(
        default=False,
        description="Consulta metadados de DOI em serviço confiável (opt-in).",
    )


class FindingOut(BaseModel):
    """Achado auditável da validação."""

    model_config = ConfigDict(frozen=True)

    severidade: str
    categoria: str
    veredito: str
    linha: int | None = None
    inicio: int | None = None
    fim: int | None = None
    mensagem: str = ""
    acao_sugerida: str = ""
    confianca: str = ""


class AcademicValidateResponse(BaseModel):
    """Relatório de validação acadêmica."""

    model_config = ConfigDict(frozen=True)

    achados: list[FindingOut] = Field(default_factory=list)
    citacoes: int = 0
    referencias: int = 0
    associadas: int = 0
