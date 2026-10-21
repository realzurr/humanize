"""Testes da detecção determinística de estrutura."""

from __future__ import annotations

from app.services.academic.structure import detect_structure


def test_detecta_titulos_markdown() -> None:
    texto = "# Título\n## Subtítulo\ncorpo"
    secoes = detect_structure(texto)
    assert [s.level for s in secoes] == [1, 2]
    assert secoes[0].title == "Título"


def test_detecta_numeracao_progressiva() -> None:
    texto = "1 INTRODUÇÃO\n1.1 Objetivos\n2 DESENVOLVIMENTO"
    secoes = detect_structure(texto)
    assert [s.number for s in secoes] == ["1", "1.1", "2"]
    assert [s.level for s in secoes] == [1, 2, 1]


def test_detecta_titulo_sem_indicativo() -> None:
    texto = "REFERÊNCIAS\nSILVA, R. A. Título. 2020."
    secoes = detect_structure(texto)
    assert secoes
    assert secoes[0].kind == "unnumbered"
    assert secoes[0].title == "REFERÊNCIAS"


def test_nao_detecta_paragrafo_como_titulo() -> None:
    texto = "Este é um parágrafo comum com várias palavras e nenhuma numeração."
    assert detect_structure(texto) == []


def test_texto_vazio() -> None:
    assert detect_structure("") == []
