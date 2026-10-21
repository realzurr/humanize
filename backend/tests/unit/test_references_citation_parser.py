"""Testes da extração de citações."""

from __future__ import annotations

from app.services.references.citation_parser import parse_citations
from app.services.references.models import CitationKind


def test_citacao_numerica() -> None:
    citacoes = parse_citations("conforme [12] indica")
    assert citacoes[0].numeric is True
    assert citacoes[0].numbers == (12,)


def test_citacao_numerica_intervalo() -> None:
    citacoes = parse_citations("ver [3-5]")
    assert citacoes[0].numbers == (3, 4, 5)


def test_citacao_autor_data_entre_parenteses() -> None:
    citacoes = parse_citations("conforme (SILVA, 2020)")
    autor_data = next(c for c in citacoes if not c.numeric)
    assert autor_data.authors == ("SILVA",)
    assert autor_data.year == "2020"


def test_citacao_multiplos_autores() -> None:
    citacoes = parse_citations("(SOUZA; PEREIRA, 2018)")
    autor_data = next(c for c in citacoes if not c.numeric)
    assert autor_data.authors == ("SOUZA", "PEREIRA")
    assert autor_data.year == "2018"


def test_citacao_nua_nao_engole_marcador() -> None:
    citacoes = parse_citations("Segundo Silva (2020), ...")
    autor_data = next(c for c in citacoes if not c.numeric)
    assert autor_data.authors == ("SILVA",)


def test_citacao_direta_entre_aspas() -> None:
    citacoes = parse_citations("“texto literal” (SILVA, 2020, p. 45)")
    direta = next(c for c in citacoes if c.kind is CitationKind.DIRECT)
    assert direta is not None


def test_texto_sem_citacao() -> None:
    assert parse_citations("Nenhuma citação aqui.") == []
