"""Catálogo de entidades protegidas.

Toda informação verificável que o pipeline de humanização *não pode* alterar
é extraída do texto antes de qualquer chamada de LLM, catalogada aqui, e
mascarada com placeholders estáveis. Após a revisão, o catálogo é usado para:

1. restaurar os valores originais (unmasking);
2. verificar que nenhum valor protegido foi perdido ou alterado (validação
   semântica);
3. emitir alertas ao usuário quando houver divergência.

O catálogo é **imutável**: entidades nunca são editadas, apenas recriadas em
uma nova revisão.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections.abc import Iterable, Iterator
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.ir.spans import SourceRange


class ProtectedKind(StrEnum):
    """Categorias de conteúdo protegido."""

    NUMBER = "number"
    """Valores numéricos, percentuais, grandezas e resultados numéricos."""

    DATE = "date"
    """Datas, anos e intervalos temporais."""

    CITATION = "citation"
    """Citações diretas, indiretas e autor-data."""

    REFERENCE = "reference"
    """Entradas da lista de referências."""

    DOI = "doi"
    """Identificadores DOI."""

    URL = "url"
    """URLs."""

    FORMULA = "formula"
    """Fórmulas, equações e expressões matemáticas."""

    TERM_DEFINED = "term_defined"
    """Termo técnico definido pelo autor (sigla, glossário)."""

    PERSON = "person"
    """Nomes próprios de pessoas citadas (autores,.researchers)."""

    INSTITUTION = "institution"
    """Instituições, órgãos e entidades nomeadas."""

    STATISTIC = "statistic"
    """Dados estatísticos (percentuais, médias, intervalos de confiança)."""

    TABLE_ID = "table_id"
    """Identificadores e títulos de tabelas."""

    FIGURE_ID = "figure_id"
    """Identificadores e títulos de figuras."""

    CODE = "code"
    """Trechos de código-fonte."""

    QUOTE_LITERAL = "quote_literal"
    """Citação literal entre aspas, que deve ser preservada verbatim."""

    UNIT = "unit"
    """Unidades de medida (kg, cm, mol, °C, m/s...)."""

    SPECIMEN = "specimen"
    """Nomenclatura binomial, códigos de amostra, identificadores de withheld."""


#: Severidade da proteção. Conteúdo ``CRITICAL`` bloqueia a aprovação
#: automática quando há divergência.
class ProtectionLevel(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


#: Níveis por padrão.
_DEFAULT_LEVELS: dict[ProtectedKind, ProtectionLevel] = {
    ProtectedKind.NUMBER: ProtectionLevel.CRITICAL,
    ProtectedKind.DATE: ProtectionLevel.HIGH,
    ProtectedKind.CITATION: ProtectionLevel.CRITICAL,
    ProtectedKind.REFERENCE: ProtectionLevel.CRITICAL,
    ProtectedKind.DOI: ProtectionLevel.CRITICAL,
    ProtectedKind.URL: ProtectionLevel.HIGH,
    ProtectedKind.FORMULA: ProtectionLevel.CRITICAL,
    ProtectedKind.TERM_DEFINED: ProtectionLevel.MEDIUM,
    ProtectedKind.PERSON: ProtectionLevel.HIGH,
    ProtectedKind.INSTITUTION: ProtectionLevel.MEDIUM,
    ProtectedKind.STATISTIC: ProtectionLevel.CRITICAL,
    ProtectedKind.TABLE_ID: ProtectionLevel.HIGH,
    ProtectedKind.FIGURE_ID: ProtectionLevel.HIGH,
    ProtectedKind.CODE: ProtectionLevel.CRITICAL,
    ProtectedKind.QUOTE_LITERAL: ProtectionLevel.CRITICAL,
    ProtectedKind.UNIT: ProtectionLevel.HIGH,
    ProtectedKind.SPECIMEN: ProtectionLevel.HIGH,
}


def normalize_fingerprint(text: str) -> str:
    """Normaliza um valor para comparação estável entre revisões.

    Remove espaços redundantes, unifica dígitos Unicode (via NFKC), normaliza
    separadores de milhar e case-folding. Usado para detectar se um número foi
    alterado (e.g. ``1.000`` -> ``1000``).

    Heurística de separador (heurística, não norma):

    * grupo de exatamente 3 dígitos após ``.`` ou ``,`` -> separador de milhar,
      removido (``1.000`` -> ``1000``);
    * demais separadores entre dígitos -> separador decimal, normalizado
      para ``.`` (``45,5%`` -> ``45.5%``).

    Ambiguidade conhecida: ``1.000`` pode significar ``1.0`` em textos em
    inglês. O sistema trabalha em pt-BR, onde a leitura de milhar é a
    dominante; ainda assim, o fingerprint é usado **apenas para comparação**,
    nunca para reescrever o valor exibido.
    """
    folded = unicodedata.normalize("NFKC", text).strip().lower()
    folded = folded.replace("−", "-").replace("–", "-").replace("—", "-")
    folded = re.sub(r"\s+", "", folded)
    folded = re.sub(r"(?<=\d)[.,](?=\d{3}(?!\d))", "", folded)
    folded = re.sub(r"(?<=\d),(?=\d)", ".", folded)
    return folded


def fingerprint(text: str) -> str:
    """Hash estável (SHA-256, 16 hex) do valor normalizado."""
    return hashlib.sha256(normalize_fingerprint(text).encode("utf-8")).hexdigest()[:16]


class ProtectedEntity(BaseModel):
    """Uma entidade protegida extraída do documento."""

    model_config = ConfigDict(frozen=True)

    id: str
    """Identificador estável, ex.: ``P0007``."""

    kind: ProtectedKind
    """Categoria da entidade."""

    text: str
    """Texto exato como aparece no documento."""

    source_range: SourceRange
    """Origem no texto original imutável."""

    level: ProtectionLevel = ProtectionLevel.MEDIUM
    """Severidade da proteção."""

    fingerprint: str = ""
    """Hash de comparação (preenchido pelo extrator)."""

    rule_id: str = ""
    """Regra que detectou a entidade (para rastreabilidade)."""

    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    """Confiança da detecção, de 0 a 1."""

    attributes: dict[str, Any] = Field(default_factory=dict)
    """Contexto (ex.: unidade associada a um número, tipo de citação)."""

    def __hash__(self) -> int:
        return hash((self.kind, self.fingerprint, self.text))


class ProtectionCatalog(BaseModel):
    """Coleção de entidades protegidas de um documento.

    Mantém índice por intervalo para consulta rápida de sobreposição e um
    índice por fingerprint para reconciliação entre revisões.
    """

    model_config = ConfigDict(frozen=True)

    entities: tuple[ProtectedEntity, ...] = ()

    def __len__(self) -> int:
        return len(self.entities)

    def iter_entities(self) -> Iterator[ProtectedEntity]:
        """Itera sobre as entidades do catálogo."""
        return iter(self.entities)

    def by_id(self, entity_id: str) -> ProtectedEntity | None:
        for entity in self.entities:
            if entity.id == entity_id:
                return entity
        return None

    def in_range(self, source_range: SourceRange) -> list[ProtectedEntity]:
        return [e for e in self.entities if e.source_range.overlaps(source_range)]

    def of_kind(self, kind: ProtectedKind) -> list[ProtectedEntity]:
        return [e for e in self.entities if e.kind is kind]

    def fingerprints(self) -> dict[str, list[ProtectedEntity]]:
        """Agrupa entidades por fingerprint (para detectar divergências)."""
        grouped: dict[str, list[ProtectedEntity]] = {}
        for entity in self.entities:
            grouped.setdefault(entity.fingerprint, []).append(entity)
        return grouped

    def missing_fingerprints(self, other: ProtectionCatalog) -> list[str]:
        """Fingerprints presentes em ``self`` e ausentes em ``other``.

        Base para a validação de perda de dados protegidos: se a revisão do
        LLM removeu uma entidade protegida, o fingerprint correspondente não
        aparece no catálogo pós-revisão.
        """
        other_fps = {fp for fp in other.fingerprints() if fp}
        return [
            entity.fingerprint
            for entity in self.entities
            if entity.fingerprint and entity.fingerprint not in other_fps
        ]

    def changed_fingerprints(self, other: ProtectionCatalog) -> list[tuple[ProtectedEntity, str]]:
        """Entidades cujo valor mudou de forma detectável.

        Compara pelo fingerprint normalizado; detecta tanto alteração de
        dígitos (ex.: ``45%`` -> ``45,5%``) quanto troca de unidade.
        """
        other_fps = other.fingerprints()
        changed: list[tuple[ProtectedEntity, str]] = []
        for entity in self.entities:
            if not entity.fingerprint:
                continue
            candidates = other_fps.get(entity.fingerprint)
            if candidates:
                continue
            # Fingerprint ausente: procura por proximidade textual para
            # distinguir "alterado" de "removido".
            normalized = normalize_fingerprint(entity.text)
            for other_entity in other.entities:
                if normalize_fingerprint(other_entity.text) == normalized:
                    break
            else:
                changed.append((entity, entity.fingerprint))
        return changed

    def merge(self, entities: Iterable[ProtectedEntity]) -> ProtectionCatalog:
        return ProtectionCatalog(entities=(*self.entities, *entities))


def default_level(kind: ProtectedKind) -> ProtectionLevel:
    return _DEFAULT_LEVELS.get(kind, ProtectionLevel.MEDIUM)
