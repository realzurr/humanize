"""Associação entre citações e referências.

Associa cada citação a uma entrada da lista de referências, reportando o grau
de confiança: ``high`` (sobrenome + ano, ou número dentro do intervalo),
``medium`` (sobrenome confere, ano diverge) e ``low`` (sem correspondência).
"""

from __future__ import annotations

from app.services.references.models import Citation, Match, MatchConfidence, Reference


def match(citations: list[Citation], references: list[Reference]) -> list[Match]:
    """Associa cada citação à sua referência, na ordem das citações."""
    return [
        _match_numeric(citation, references)
        if citation.numeric
        else _match_author_date(citation, references)
        for citation in citations
    ]


def _match_numeric(citation: Citation, references: list[Reference]) -> Match:
    if not citation.numbers:
        return Match(
            citation_id=citation.id,
            reference_id=None,
            confidence=MatchConfidence.LOW,
            note="citação numérica sem número",
        )
    indice = citation.numbers[0]
    if 1 <= indice <= len(references):
        return Match(
            citation_id=citation.id,
            reference_id=references[indice - 1].id,
            confidence=MatchConfidence.HIGH,
        )
    return Match(
        citation_id=citation.id,
        reference_id=None,
        confidence=MatchConfidence.LOW,
        note=f"número {indice} fora do intervalo da lista ({len(references)} entradas)",
    )


def _match_author_date(citation: Citation, references: list[Reference]) -> Match:
    if not citation.authors:
        return Match(
            citation_id=citation.id,
            reference_id=None,
            confidence=MatchConfidence.LOW,
            note="citação autor-data sem sobrenome",
        )
    sobrenome = citation.authors[0].lower()

    for referencia in references:
        if referencia.first_surname.lower() == sobrenome and referencia.year == citation.year:
            return Match(
                citation_id=citation.id,
                reference_id=referencia.id,
                confidence=MatchConfidence.HIGH,
            )

    for referencia in references:
        if referencia.first_surname.lower() == sobrenome:
            return Match(
                citation_id=citation.id,
                reference_id=referencia.id,
                confidence=MatchConfidence.MEDIUM,
                note="sobrenome confere, mas o ano diverge",
            )

    return Match(
        citation_id=citation.id,
        reference_id=None,
        confidence=MatchConfidence.LOW,
        note="sem referência correspondente",
    )


def uncited_references(matches: list[Match], references: list[Reference]) -> list[Reference]:
    """Devolve as referências que não foram citadas."""
    citadas = {m.reference_id for m in matches if m.reference_id}
    return [r for r in references if r.id not in citadas]
