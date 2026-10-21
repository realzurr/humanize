"""Estruturação e formatação acadêmica determinística.

A LLM **nunca** define layout (ver `ADR-0005`). Este pacote resolve a
estrutura, a numeração, a paginação e os estilos a partir dos templates
versionados, com rastreabilidade de fonte por regra (`ADR-0015`) e a
precedência ``instituição > template > norma`` (`ADR-0007`).
"""

from __future__ import annotations

from app.services.academic.metadata import missing_fields, required_fields
from app.services.academic.numbering import (
    number_headings,
    progressive_numbers,
    validate_sequence,
)
from app.services.academic.pagination import PageSide, page_number_position, resolve_margins
from app.services.academic.sections import (
    POS_TEXTUAL,
    PRE_TEXTUAL,
    TEXTUAL,
    TOC_IS_FIELD,
    classify,
    is_post_textual,
    is_pre_textual,
    is_textual,
)
from app.services.academic.structure import Section, detect_structure
from app.services.academic.styles import available_styles, style_for_kind, style_for_level
from app.services.academic.template_model import (
    Conflito,
    Elemento,
    Estilo,
    Fonte,
    Margens,
    Pagina,
    Paginacao,
    SectionsConfig,
    Template,
    TemplateResolved,
    Tipografia,
)
from app.services.academic.templates import VIGENTES, TemplateNotFoundError, TemplateRegistry

__all__ = [
    "POS_TEXTUAL",
    "PRE_TEXTUAL",
    "TEXTUAL",
    "TOC_IS_FIELD",
    "VIGENTES",
    "Conflito",
    "Elemento",
    "Estilo",
    "Fonte",
    "Margens",
    "PageSide",
    "Pagina",
    "Paginacao",
    "Section",
    "SectionsConfig",
    "Template",
    "TemplateNotFoundError",
    "TemplateRegistry",
    "TemplateResolved",
    "Tipografia",
    "available_styles",
    "classify",
    "detect_structure",
    "is_post_textual",
    "is_pre_textual",
    "is_textual",
    "missing_fields",
    "number_headings",
    "page_number_position",
    "progressive_numbers",
    "required_fields",
    "resolve_margins",
    "style_for_kind",
    "style_for_level",
    "validate_sequence",
]
