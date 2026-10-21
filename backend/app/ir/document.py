"""Documento intermediário (``AcademicDocument``) e metadados acadêmicos.

Este é o contrato central do sistema. Todos os estágios — normalização,
humanização, estruturação, formatação e exportação — operam sobre este
objeto, nunca sobre texto solto. A regra de ouro:

    o documento original é imutável; cada estágio produz uma nova versão.

A versão original fica em :attr:`AcademicDocument.original_text` e nunca é
sobrescrita. Cada revisão é uma :class:`DocumentRevision`, com rastro do
estágio, das transformações aplicadas e do texto resultante.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.ir.blocks import Block
from app.ir.protection import ProtectionCatalog
from app.ir.spans import SourceRange


class PipelineStage(StrEnum):
    """Estágios do fluxo principal (etapas independentes)."""

    IMPORT = "import"
    NORMALIZE = "normalize"
    STRUCTURE = "structure"
    PROTECT = "protect"
    HUMANIZE = "humanize"
    SEMANTIC_VALIDATE = "semantic_validate"
    REVIEW = "review"
    TEMPLATE = "template"
    FORMAT = "format"
    ACADEMIC_VALIDATE = "academic_validate"
    EXPORT = "export"


class DocumentNature(StrEnum):
    """Natureza do trabalho (preenchida nos metadados)."""

    TESE = "tese"
    DISSERTACAO = "dissertacao"
    TCC = "tcc"
    MONOGRAFIA = "monografia"
    PROJETO_PESQUISA = "projeto_pesquisa"
    RELATORIO = "relatorio"
    ARTIGO = "artigo"
    TRABALHO_ACADEMICO = "trabalho_academico"
    LIVRO = "livro"


class DocumentMetadata(BaseModel):
    """Dados de identificação do documento (formulário de metadados)."""

    model_config = ConfigDict(frozen=True)

    institution: str = ""
    """Instituição de ensino superior."""

    academic_unit: str = ""
    """Unidade acadêmica (departamento, unidade, faculdade)."""

    program: str = ""
    """Curso ou programa de pós-graduação."""

    author: str = ""
    """Autor(a)."""

    title: str = ""
    """Título."""

    subtitle: str = ""
    """Subtítulo."""

    nature: DocumentNature | None = None
    """Natureza do trabalho (ex.: TESE, DISSERTAÇÃO, TCC)."""

    academic_objective: str = ""
    """Objetivo acadêmico (ex.: degree being pursued)."""

    advisor: str = ""
    """Orientador(a)."""

    co_advisor: str = ""
    """Coorientador(a)."""

    area_of_concentration: str = ""
    """Área de concentração."""

    city: str = ""
    """Cidade da apresentação."""

    year: str = ""
    """Ano de entrega."""

    keywords_pt: tuple[str, ...] = ()
    """Palavras-chave em português."""

    keywords_en: tuple[str, ...] = ()
    """Keywords em inglês."""

    language: str = "pt-BR"
    """Idioma principal do documento."""

    extra: dict[str, Any] = Field(default_factory=dict)
    """Campos adicionais definidos por template/instituição."""

    def missing_required(self, required: tuple[str, ...]) -> list[str]:
        """Lista os campos obrigatórios ausentes."""
        missing: list[str] = []
        for field in required:
            value = getattr(self, field, None)
            if value is None or (isinstance(value, str) and not value.strip()):
                missing.append(field)
        return missing


class Transformation(BaseModel):
    """Registro de uma transformação aplicada ao documento.

    Toda alteração relevante é registrada (regra de engenharia 6). O registro
    é exibido ao usuário e alimenta o relatório de conformidade.
    """

    model_config = ConfigDict(frozen=True)

    stage: PipelineStage
    rule_id: str
    """Identificador da regra (ex.: ``norm.invisible.zwsp``)."""

    description: str = ""
    """Descrição legível da regra."""

    count: int = 1
    """Número de ocorrências afetadas."""

    source_range: SourceRange | None = None
    """Localização no texto original, quando aplicável."""

    before: str = ""
    """Trecho antes da transformação (truncado)."""

    after: str = ""
    """Trecho depois da transformação (truncado)."""

    severity: str = "info"
    """``info`` | ``warning`` | ``critical``."""

    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentRevision(BaseModel):
    """Uma versão do documento, gerada por um estágio do pipeline."""

    model_config = ConfigDict(frozen=True)

    id: str
    """Identificador da revisão."""

    stage: PipelineStage
    """Estágio que produziu esta revisão."""

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    """Instante de criação."""

    text: str
    """Texto resultante desta revisão."""

    blocks: tuple[Block, ...] = ()
    """Estrutura de blocos resultante (quando aplicável)."""

    transformations: tuple[Transformation, ...] = ()
    """Transformações aplicadas nesta revisão."""

    parent_id: str | None = None
    """Revisão de origem."""

    metadata: dict[str, Any] = Field(default_factory=dict)
    """Metadados do estágio (tokens, custo, modelo, etc.)."""


class AcademicDocument(BaseModel):
    """Documento acadêmico intermediário.

    Invariantes garantidos pelo código:

    * ``original_text`` é imutável após a criação;
    * ``revisions`` é append-only;
    * ``current_revision_id`` sempre aponta para uma revisão existente.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    """Identificador do documento."""

    original_text: str
    """Texto original, imutável (fonte de verdade)."""

    blocks: tuple[Block, ...] = ()
    """Estrutura de blocos atual."""

    metadata: DocumentMetadata = DocumentMetadata()
    """Metadados de identificação."""

    protection: ProtectionCatalog = ProtectionCatalog()
    """Catálogo de entidades protegidas da revisão atual."""

    revisions: tuple[DocumentRevision, ...] = ()
    """Histórico completo de revisões (append-only)."""

    current_revision_id: str | None = None
    """Revisão corrente."""

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    """Instante de criação."""

    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    """Instante da última atualização."""

    owner_id: str | None = None
    """Dono do documento (isolamento multiusuário, Onda 8)."""

    def current_text(self) -> str:
        """Texto da revisão corrente (ou o original, se ainda não houver)."""
        if self.current_revision_id is None:
            return self.original_text
        for revision in self.revisions:
            if revision.id == self.current_revision_id:
                return revision.text
        return self.original_text

    def revision(self, revision_id: str) -> DocumentRevision | None:
        for revision in self.revisions:
            if revision.id == revision_id:
                return revision
        return None

    def history(self) -> list[DocumentRevision]:
        """Revisões em ordem cronológica."""
        return sorted(self.revisions, key=lambda r: r.created_at)

    def with_revision(self, revision: DocumentRevision) -> AcademicDocument:
        """Devolve uma nova instância com a revisão acrescentada.

        O documento original nunca é mutado; a função retorna uma cópia.
        """
        return AcademicDocument(
            id=self.id,
            original_text=self.original_text,
            blocks=revision.blocks or self.blocks,
            metadata=self.metadata,
            protection=self.protection,
            revisions=(*self.revisions, revision),
            current_revision_id=revision.id,
            created_at=self.created_at,
            updated_at=datetime.now(UTC),
            owner_id=self.owner_id,
        )
