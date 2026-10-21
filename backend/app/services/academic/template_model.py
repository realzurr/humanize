"""Modelos de template acadêmico.

Espelham o esquema JSON de ``templates/schemas/template.schema.json``. Toda
regra de formatação carrega sua **fonte** (norma, edição, seção, URL, data de
consulta e grau de confiança), conforme `ADR-0015` e `ADR-0007`.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Confidence(StrEnum):
    """Grau de verificação da fonte de uma regra."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Fonte(BaseModel):
    """Fonte normativa de uma regra de formatação."""

    model_config = ConfigDict(frozen=True)

    norm: str
    edition: str
    section: str = ""
    url: str = ""
    consulted_at: str = ""
    confidence: Confidence = Confidence.MEDIUM
    note: str = ""


class Margens(BaseModel):
    """Margens da página, em centímetros."""

    model_config = ConfigDict(frozen=True)

    top_cm: float = Field(ge=0, le=10)
    bottom_cm: float = Field(ge=0, le=10)
    left_cm: float = Field(ge=0, le=10)
    right_cm: float = Field(ge=0, le=10)


class Paginacao(BaseModel):
    """Configuração de numeração de página."""

    model_config = ConfigDict(frozen=True)

    position: str = "top_right"
    start_at: str = "first_textual"
    count_pre_textual: bool = True
    number_pre_textual: bool = False


class Pagina(BaseModel):
    """Configuração de página."""

    model_config = ConfigDict(frozen=True)

    size: str = "A4"
    mirror: bool = False
    margins_cm: Margens
    margins_verso_cm: Margens | None = None
    gutter_cm: float = Field(default=0.0, ge=0, le=5)
    numbering: Paginacao = Paginacao()


class Tipografia(BaseModel):
    """Tipografia do texto."""

    model_config = ConfigDict(frozen=True)

    font: str
    size_pt: float = Field(ge=6, le=48)
    line_spacing: float = Field(ge=1, le=3)
    paragraph_spacing_pt: float = Field(default=0.0, ge=0)
    indent_cm: float = Field(default=0.0, ge=0, le=5)
    alignment: str = "justify"
    small_size_pt: float = Field(default=10.0)


class Elemento(BaseModel):
    """Elemento estrutural do documento."""

    model_config = ConfigDict(frozen=True)

    id: str
    kind: str
    required: bool = False
    page_break: bool = False
    starts_on_odd_page: bool = False
    numbered: bool = False
    level: int | None = None
    note: str = ""


class Estilo(BaseModel):
    """Estilo tipográfico de um título ou bloco."""

    model_config = ConfigDict(frozen=True)

    font_size_pt: float | None = None
    bold: bool = False
    italic: bool = False
    uppercase: bool = False
    alignment: str = "left"
    spacing_before_pt: float = 0.0
    spacing_after_pt: float = 0.0
    line_spacing: float | None = None
    keep_with_next: bool = False
    indent_cm: float | None = None


class SectionsConfig(BaseModel):
    """Configuração de numeração progressiva (NBR 6024)."""

    model_config = ConfigDict(frozen=True)

    format: str = "1.1.1"
    start_at: int = 1
    include_pre_textual: bool = False


class Conflito(BaseModel):
    """Conflito registrado na resolução (ADR-0007)."""

    model_config = ConfigDict(frozen=True)

    rule_id: str
    """Caminho da regra sobrescrita (ex.: ``typography.font``)."""

    norm_value: str
    institution_value: str
    norm_source: Fonte | None = None
    institution_source: Fonte | None = None
    severity: str = "warning"


class Template(BaseModel):
    """Template de formatação acadêmica (parsed de YAML)."""

    model_config = ConfigDict(frozen=True)

    id: str
    version: str
    kind: str
    title: str = ""
    description: str = ""
    extends: str | None = None
    institution: str | None = None
    sources: tuple[Fonte, ...] = ()
    page: Pagina | None = None
    typography: Tipografia | None = None
    elements: tuple[Elemento, ...] = ()
    styles: dict[str, Estilo] = Field(default_factory=dict)
    sections: SectionsConfig | None = None

    def source_for(self, norm: str) -> Fonte | None:
        """Devolve a fonte declarada para uma norma, se houver."""
        for fonte in self.sources:
            if fonte.norm == norm:
                return fonte
        return None


class TemplateResolved(BaseModel):
    """Resultado da resolução de um template (com herança e instituição)."""

    model_config = ConfigDict(frozen=True)

    template: Template
    """Template final, já com herança e sobreposições aplicadas."""

    conflicts: tuple[Conflito, ...] = ()
    """Conflitos registrados entre instituição e norma (nunca ocultados)."""

    overrides: tuple[str, ...] = ()
    """Caminhos das regras sobrescritas pela instituição."""

    @property
    def has_outdated_source(self) -> bool:
        """Indica se há fonte institucional desatualizada entre os conflitos."""
        return any(c.rule_id.startswith("fonte.") for c in self.conflicts)
