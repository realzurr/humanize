"""Testes da associação citação ↔ referência."""

from __future__ import annotations

from app.services.references.citation_parser import parse_citations
from app.services.references.matcher import match, uncited_references
from app.services.references.models import MatchConfidence
from app.services.references.parser import parse_references


def _texto(citacao: str, referencias: str) -> str:
    return f"{citacao}\n\n## REFERÊNCIAS\n\n{referencias}"


def test_match_autor_data_high() -> None:
    texto = _texto("(SILVA, 2020)", "SILVA, R. A. Título. Revista, 2020.")
    associacoes = match(parse_citations(texto), parse_references(texto))
    assert associacoes[0].confidence is MatchConfidence.HIGH
    assert associacoes[0].reference_id is not None


def test_match_ano_divergente_medium() -> None:
    texto = _texto("(SILVA, 2020)", "SILVA, R. A. Título. Revista, 2019.")
    associacoes = match(parse_citations(texto), parse_references(texto))
    assert associacoes[0].confidence is MatchConfidence.MEDIUM


def test_match_sem_referencia_low() -> None:
    texto = _texto("(SOUZA, 2020)", "SILVA, R. A. Título. Revista, 2020.")
    associacoes = match(parse_citations(texto), parse_references(texto))
    assert associacoes[0].reference_id is None
    assert associacoes[0].confidence is MatchConfidence.LOW


def test_match_numerica_high() -> None:
    texto = _texto("[1]", "SILVA, R. A. Título. Revista, 2020.")
    associacoes = match(parse_citations(texto), parse_references(texto))
    assert associacoes[0].confidence is MatchConfidence.HIGH
    assert associacoes[0].reference_id == "ref0001"


def test_uncited_references() -> None:
    texto = _texto(
        "(SILVA, 2020)",
        "SILVA, R. A. Título. Revista, 2020.\n\nSOUZA, M. Outro. Revista, 2021.",
    )
    referencias = parse_references(texto)
    associacoes = match(parse_citations(texto), referencias)
    nao_citadas = uncited_references(associacoes, referencias)
    assert [r.first_surname for r in nao_citadas] == ["SOUZA"]
