"""Elementos estruturais do documento acadêmico.

Classifica os elementos em pré-textuais, textuais e pós-textuais e define a
ordem canônica (Esquema 1 da NBR 14724:2024). O sumário é sempre um **campo
TOC real** do Word, nunca texto digitado.
"""

from __future__ import annotations

#: Elementos pré-textuais, na ordem da NBR 14724:2024.
PRE_TEXTUAL: tuple[str, ...] = (
    "cover",
    "title_page",
    "approval_page",
    "catalog_record",
    "errata",
    "dedication",
    "acknowledgments",
    "epigraph",
    "abstract_pt",
    "abstract_en",
    "keywords",
    "list_of_illustrations",
    "list_of_tables",
    "list_of_abbreviations",
    "list_of_symbols",
    "table_of_contents",
)

#: Elementos textuais.
TEXTUAL: tuple[str, ...] = (
    "introduction",
    "development",
    "conclusion",
)

#: Elementos pós-textuais.
POS_TEXTUAL: tuple[str, ...] = (
    "references",
    "glossary",
    "appendix",
    "annex",
    "index",
)


def is_pre_textual(kind: str) -> bool:
    return kind in PRE_TEXTUAL


def is_textual(kind: str) -> bool:
    return kind in TEXTUAL


def is_post_textual(kind: str) -> bool:
    return kind in POS_TEXTUAL


def classify(kind: str) -> str:
    """Classifica o elemento: ``pre_textual`` | ``textual`` | ``pos_textual`` | ``outro``."""
    if is_pre_textual(kind):
        return "pre_textual"
    if is_textual(kind):
        return "textual"
    if is_post_textual(kind):
        return "pos_textual"
    return "outro"


#: O sumário é gerado como campo TOC real do Word (nunca texto digitado).
TOC_IS_FIELD = True
