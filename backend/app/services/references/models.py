"""Modelos de referências bibliográficas e citações.

Representação neutra e estruturada (independente de BibTeX, CSL-JSON ou da
formatação NBR 6023). A extração de metadados é heurística; nenhum metadado
ausente é inventado.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.ir.spans import SourceRange


class ReferenceType(StrEnum):
    """Tipo de referência bibliográfica."""

    ARTICLE = "article"
    """Artigo de periódico."""

    BOOK = "book"
    BOOK_SECTION = "book_section"
    THESIS = "thesis"
    DISSERTATION = "dissertation"
    CONFERENCE = "conference"
    WEB = "web"
    LEGAL = "legal"
    REPORT = "report"
    OTHER = "other"


class Author(BaseModel):
    """Autor de uma referência (pessoa ou organização)."""

    model_config = ConfigDict(frozen=True)

    surname: str
    """Sobrenome (ou nome da organização, quando ``organization``)."""

    given: str = ""
    """Prenome e iniciais."""

    organization: bool = False
    """Verdadeiro quando o autor é uma entidade (IBGE, ONU...)."""

    @property
    def sort_name(self) -> str:
        """Nome em ordem de catalogação: ``SURNAME, Given``."""
        if self.organization:
            return self.surname.upper()
        base = self.surname.upper() if self.surname.isupper() else self.surname
        return f"{base}, {self.given}".strip() if self.given else base

    @property
    def full_name(self) -> str:
        """Nome em ordem natural: ``Given Surname``."""
        if self.organization:
            return self.surname
        return f"{self.given} {self.surname}".strip() or self.surname


class Reference(BaseModel):
    """Entrada de referência bibliográfica."""

    model_config = ConfigDict(frozen=True)

    id: str
    """Identificador local (ex.: ``ref0001``)."""

    type: ReferenceType = ReferenceType.OTHER
    authors: tuple[Author, ...] = ()
    title: str = ""
    year: str = ""
    container: str = ""
    """Nome do periódico, editora ou veículo."""

    volume: str = ""
    issue: str = ""
    pages: str = ""
    publisher: str = ""
    place: str = ""
    doi: str = ""
    url: str = ""
    accessed_at: str = ""
    source_range: SourceRange | None = None
    """Localização no texto original, quando extraída dele."""

    extra: dict[str, str] = Field(default_factory=dict)

    @property
    def first_surname(self) -> str:
        if not self.authors:
            return ""
        return self.authors[0].surname


class CitationKind(StrEnum):
    """Tipo de citação."""

    DIRECT = "direct"
    """Citação direta (literal), curta."""

    INDIRECT = "indirect"
    """Citação indireta (paráfrase)."""

    LONG = "long"
    """Citação direta longa (mais de três linhas, com recuo)."""


class Citation(BaseModel):
    """Citação detectada no texto."""

    model_config = ConfigDict(frozen=True)

    id: str
    kind: CitationKind = CitationKind.INDIRECT
    numeric: bool = False
    """Verdadeiro para citação numérica (``[12]``)."""

    numbers: tuple[int, ...] = ()
    """Números, para citação numérica."""

    authors: tuple[str, ...] = ()
    """Sobrenomes, para citação autor-data."""

    year: str = ""
    source_range: SourceRange | None = None


class MatchConfidence(StrEnum):
    """Grau de confiança da associação citação ↔ referência."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Match(BaseModel):
    """Associação entre uma citação e uma referência."""

    model_config = ConfigDict(frozen=True)

    citation_id: str
    reference_id: str | None = None
    """``None`` quando não há referência correspondente."""

    confidence: MatchConfidence = MatchConfidence.LOW
    note: str = ""
