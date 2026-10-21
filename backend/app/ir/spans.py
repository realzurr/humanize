"""Modelo de trechos (spans) em nível de linha.

O documento intermediário é composed de blocos (ver ``blocks.py``); cada bloco
contém uma lista plana de trechos inline. A lista é deliberadamente *plana*
(não uma árvore) para que a camada de máscara/prottenção possa fatiar e
remontar o conteúdo com offsets estáveis, sem rebalancear árvores.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SpanKind(StrEnum):
    """Natureza semântica de um trecho inline.

    A distinção entre ``TEXT`` e os demais tipos é o que permite ao motor de
    normalização decidir, com precisão, quais trechos são intocáveis.
    """

    TEXT = "text"
    """Texto corrido sem marcação especial."""

    EMPHASIS = "emphasis"
    """Texto em itálico (fase ou ênfase)."""

    STRONG = "strong"
    """Texto em negrito."""

    CODE_INLINE = "code_inline"
    """Trecho de código no meio do parágrafo."""

    CODE_BLOCK = "code_block"
    """Bloco de código; nunca deve ser reformatado nem reescrito por LLM."""

    MATH = "math"
    """Fórmula ou expressão matemática inline."""

    EQUATION = "equation"
    """Equação display, com numeração."""

    LINK = "link"
    """Hiperlink. O texto exibido e o destino são atributos."""

    CITATION = "citation"
    """Citação autor-data ou numérica, inclusive citação literal."""

    FOOTNOTE_REF = "footnote_ref"
    """Marca de chamada de nota de rodapé."""

    QUOTE = "quote"
    """Citação direta (literal ou não literal)."""

    PRESERVED = "preserved"
    """Trecho mascarado por uma entidade protegida (placeholder)."""

    FIELD = "field"
    """Campo dinâmico de Word (ex.: TOC, PAGE, SEQ)."""

    LINE_BREAK = "line_break"
    """Quebra de linha forçada dentro do parágrafo."""

    TAB = "tab"
    """Tabulação."""


class SourceRange(BaseModel):
    """Intervalo [start, end) no texto original imutável.

    Todos os offsets são medidos em *code points* Unicode (não bytes, não
    unidades UTF-16), de modo que o mesmo texto produza os mesmos offsets em
    Python e em TypeScript.
    """

    model_config = ConfigDict(frozen=True)

    start: int = Field(ge=0)
    end: int = Field(ge=0)

    @model_validator(mode="after")
    def _check_bounds(self) -> SourceRange:
        if self.end < self.start:
            raise ValueError("SourceRange.end deve ser >= SourceRange.start")
        return self

    def __len__(self) -> int:
        return self.end - self.start

    def slice(self, text: str) -> str:
        return text[self.start : self.end]

    def overlaps(self, other: SourceRange) -> bool:
        return self.start < other.end and other.start < self.end


class InlineSpan(BaseModel):
    """Trecho inline com origem rastreável.

    ``source_range`` é opcional porque trechos criados do zero (por exemplo,
    elementos pré-textuais gerados na Onda 4) não existem no original.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    kind: SpanKind = SpanKind.TEXT
    text: str
    source_range: SourceRange | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    """Metadados livres dependentes do tipo (href, language, placeholder_id...)."""

    protected_ids: tuple[str, ...] = ()
    """Identificadores das entidades protegidas contidas neste trecho."""

    @property
    def is_protected(self) -> bool:
        return self.kind is SpanKind.PRESERVED or bool(self.protected_ids)

    @property
    def is_lossless_target(self) -> bool:
        """Trechos que nunca podem ser reescritos automaticamente."""
        return self.kind in {
            SpanKind.CODE_BLOCK,
            SpanKind.CODE_INLINE,
            SpanKind.MATH,
            SpanKind.EQUATION,
            SpanKind.CITATION,
            SpanKind.PRESERVED,
            SpanKind.FIELD,
        }


class SpanBuilder:
    """Construtor auxiliar para sequências de trechos.

    Mantém os offsets acumulados para que o consumidor possa remontar o texto
    original a partir dos trechos, byte a byte.
    """

    def __init__(self, *, start_offset: int = 0) -> None:
        self._cursor = start_offset
        self._spans: list[InlineSpan] = []
        self._counter = 0

    def add(
        self,
        text: str,
        *,
        kind: SpanKind = SpanKind.TEXT,
        source_range: SourceRange | None = None,
        attributes: dict[str, Any] | None = None,
        protected_ids: tuple[str, ...] = (),
    ) -> InlineSpan:
        span = InlineSpan(
            id=f"s{self._counter:06d}",
            kind=kind,
            text=text,
            source_range=source_range,
            attributes=attributes or {},
            protected_ids=protected_ids,
        )
        self._counter += 1
        self._spans.append(span)
        self._cursor += len(text)
        return span

    @property
    def spans(self) -> list[InlineSpan]:
        return list(self._spans)

    def plain_text(self) -> str:
        return "".join(span.text for span in self._spans)
