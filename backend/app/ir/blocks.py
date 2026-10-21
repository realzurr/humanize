"""Modelo de blocos do documento intermediário.

Um documento acadêmico é uma sequência *ordenada* de blocos. Cada bloco é
autossuficiente (tipo, conteúdo inline, atributos) e carrega sua origem no
texto original quando existir. A estrutura em blocos permite:

* gerar elementos pré-textuais e pós-textuais (Onda 4) sem tocar no texto do
  autor;
* aplicar estilos reais do Word por tipo de bloco;
* manter tabelas, equações e blocos de código como unidades atômicas.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.ir.spans import InlineSpan, SourceRange


class BlockKind(StrEnum):
    """Tipo estrutural de um bloco."""

    # --- Pré-textuais ---------------------------------------------------
    COVER = "cover"
    """Capa."""

    TITLE_PAGE = "title_page"
    """Folha de rosto."""

    APPROVAL_PAGE = "approval_page"
    """Folha de aprovação."""

    CATALOG_RECORD = "catalog_record"
    """Ficha catalográfica. Reservado; nunca gerado automaticamente."""

    ERRATA = "errata"
    """Errata."""

    DEDICATION = "dedication"
    """Dedicatória."""

    ACKNOWLEDGMENTS = "acknowledgments"
    """Agradecimentos."""

    EPIGRAPH = "epigraph"
    """Epígrafe."""

    ABSTRACT_PT = "abstract_pt"
    """Resumo na língua vernácula."""

    ABSTRACT_EN = "abstract_en"
    """Resumo em língua estrangeira."""

    KEYWORDS = "keywords"
    """Palavras-chave."""

    LIST_OF_ILLUSTRATIONS = "list_of_illustrations"
    """Lista de ilustrações."""

    LIST_OF_TABLES = "list_of_tables"
    """Lista de tabelas."""

    LIST_OF_ABBREVIATIONS = "list_of_abbreviations"
    """Lista de abreviaturas e siglas."""

    LIST_OF_SYMBOLS = "list_of_symbols"
    """Lista de símbolos."""

    TABLE_OF_CONTENTS = "table_of_contents"
    """Sumário (campo dinâmico)."""

    # --- Textuais --------------------------------------------------------
    HEADING = "heading"
    """Título de seção, com nível em ``attributes['level']``."""

    PARAGRAPH = "paragraph"
    """Parágrafo corrido."""

    QUOTE = "quote"
    """Citação direta (curta ou longa)."""

    QUOTE_LONG = "quote_long"
    """Citação direta com mais de três linhas."""

    LIST_ITEM = "list_item"
    """Item de lista."""

    TABLE = "table"
    """Tabela estruturada."""

    FIGURE = "figure"
    """Figura/imagem."""

    CAPTION = "caption"
    """Legenda de figura ou tabela."""

    SOURCE_NOTE = "source_note"
    """Fonte de figura/tabela."""

    EQUATION = "equation"
    """Equação display numerada."""

    CODE_BLOCK = "code_block"
    """Bloco de código literal."""

    FOOTNOTE_TEXT = "footnote_text"
    """Texto de nota de rodapé."""

    # --- Pós-textuais ----------------------------------------------------
    REFERENCES = "references"
    """Lista de referências (contém ``REFERENCE_ITEM``)."""

    REFERENCE_ITEM = "reference_item"
    """Entrada individual de referência."""

    GLOSSARY = "glossary"
    """Glossário."""

    APPENDIX = "appendix"
    """Apêndice."""

    ANNEX = "annex"
    """Anexo."""

    INDEX = "index"
    """Índice remissivo."""

    # --- Auxiliares ------------------------------------------------------
    PAGE_BREAK = "page_break"
    """Quebra de página explícita."""

    SECTION_BREAK = "section_break"
    """Quebra de seção (para mudança de margens/paginação)."""

    NOTE = "note"
    """Bloco textual genérico."""

    EMPTY = "empty"
    """Bloco vazio, usado como espaçamento controlado."""


#: Blocos que, por regra ABNT, iniciam em página nova (ímpar, quando a
#: impressão é anverso/verso).
PAGE_BREAK_BLOCKS: frozenset[BlockKind] = frozenset(
    {
        BlockKind.TITLE_PAGE,
        BlockKind.APPROVAL_PAGE,
        BlockKind.ERRATA,
        BlockKind.DEDICATION,
        BlockKind.ACKNOWLEDGMENTS,
        BlockKind.EPIGRAPH,
        BlockKind.ABSTRACT_PT,
        BlockKind.ABSTRACT_EN,
        BlockKind.LIST_OF_ILLUSTRATIONS,
        BlockKind.LIST_OF_TABLES,
        BlockKind.LIST_OF_ABBREVIATIONS,
        BlockKind.LIST_OF_SYMBOLS,
        BlockKind.TABLE_OF_CONTENTS,
        BlockKind.REFERENCES,
        BlockKind.GLOSSARY,
        BlockKind.APPENDIX,
        BlockKind.ANNEX,
        BlockKind.INDEX,
    }
)


class TableData(BaseModel):
    """Tabela estruturada preservada como unidade atômica."""

    model_config = ConfigDict(frozen=True)

    rows: tuple[tuple[str, ...], ...]
    """Células em ordem de leitura; o cabeçalho ocupa ``rows[0]``."""

    caption: str = ""
    source: str = ""
    label: str = ""
    """Identificador, ex.: ``Tabela 1``."""

    column_count: int = Field(ge=0)


class Block(BaseModel):
    """Unidade estrutural do documento."""

    model_config = ConfigDict(frozen=True)

    id: str
    """Identificador estável do bloco (ex.: ``b0007``)."""

    kind: BlockKind
    """Tipo estrutural."""

    spans: tuple[InlineSpan, ...] = ()
    """Trechos inline do bloco."""

    attributes: dict[str, Any] = Field(default_factory=dict)
    """Atributos dependentes do tipo (nível de título, estilo, numeração...)."""

    source_range: SourceRange | None = None
    """Origem no texto original, quando o bloco deriva do texto do autor."""

    protected_ids: tuple[str, ...] = ()
    """Entidades protegidas contidas no bloco."""

    table: TableData | None = None
    """Conteúdo tabular, quando ``kind is TABLE``."""

    children: tuple[Block, ...] = ()
    """Sub-blocos (ex.: a lista de referências dentro de ``REFERENCES``)."""

    @property
    def plain_text(self) -> str:
        return "".join(span.text for span in self.spans)

    @property
    def level(self) -> int:
        """Nível hierárquico do título (1 = primário)."""
        return int(self.attributes.get("level", 1))

    @property
    def starts_new_page(self) -> bool:
        return self.kind in PAGE_BREAK_BLOCKS

    def is_protected(self) -> bool:
        return bool(self.protected_ids) or self.kind in {
            BlockKind.TABLE,
            BlockKind.EQUATION,
            BlockKind.CODE_BLOCK,
        }
