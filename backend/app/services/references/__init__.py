"""Integridade acadêmica: citações, referências e validação.

Módulo da Onda 5. Nenhum metadado é inventado; metadados de DOI são tratados
como **propostas**, nunca aplicados automaticamente.
"""

from __future__ import annotations

from app.services.references.bibtex import parse_bibtex
from app.services.references.citation_parser import parse_citations
from app.services.references.csl_json import parse_csl_json
from app.services.references.doi import DOIResolver, ProposedChange, identify_dois
from app.services.references.matcher import match, uncited_references
from app.services.references.models import (
    Author,
    Citation,
    CitationKind,
    Match,
    MatchConfidence,
    Reference,
    ReferenceType,
)
from app.services.references.nbr6023 import format_authors, format_reference
from app.services.references.parser import (
    find_references_block,
    parse_entry,
    parse_references,
)
from app.services.references.validator import (
    Finding,
    FindingCategory,
    Severity,
    ValidationReport,
    Verdict,
    validate,
)

__all__ = [
    "Author",
    "Citation",
    "CitationKind",
    "DOIResolver",
    "Finding",
    "FindingCategory",
    "Match",
    "MatchConfidence",
    "ProposedChange",
    "Reference",
    "ReferenceType",
    "Severity",
    "ValidationReport",
    "Verdict",
    "find_references_block",
    "format_authors",
    "format_reference",
    "identify_dois",
    "match",
    "parse_bibtex",
    "parse_citations",
    "parse_csl_json",
    "parse_entry",
    "parse_references",
    "uncited_references",
    "validate",
]
