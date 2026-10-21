"""Testes de análise textual."""

from __future__ import annotations

from app.services.humanizer.analysis import analyze


def test_detecta_repeticoes() -> None:
    texto = "O estudo analisou o resultado. O resultado foi positivo. O resultado confirma."
    relatorio = analyze(texto)
    assert "resultado" in relatorio.repeticoes


def test_detecta_frase_padronizada() -> None:
    relatorio = analyze("É importante ressaltar que o dado é relevante.")
    assert "é importante ressaltar que" in relatorio.frases_padronizadas


def test_detecta_voz_passiva() -> None:
    relatorio = analyze("O experimento foi realizado em triplicata.")
    assert any("foi realizado" in trecho for trecho in relatorio.voz_passiva)


def test_detecta_vaguidade() -> None:
    relatorio = analyze("Vários autores consideram algo relevante.")
    assert "vários" in relatorio.vaguidade


def test_detecta_redundancia() -> None:
    relatorio = analyze("O valor subiu para cima.")
    assert relatorio.redundancia


def test_detecta_transicao_artificial() -> None:
    relatorio = analyze("Primeiramente, o método. Em segundo lugar, os resultados.")
    assert "primeiramente" in relatorio.transicoes_artificiais


def test_texto_vazio() -> None:
    relatorio = analyze("")
    assert relatorio.repeticoes == ()
    assert relatorio.voz_passiva == ()
