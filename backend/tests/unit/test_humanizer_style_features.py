"""Testes de extração de traços de estilo."""

from __future__ import annotations

from app.services.humanizer.style_features import extract_style_features


def test_extrai_comprimento_medio_de_frase() -> None:
    estilo = extract_style_features("Frase curta. Outra frase também curta. Mais uma frase.")
    assert estilo.comprimento_medio_frase > 0


def test_formalidade_alta_com_marcadores_formais() -> None:
    estilo = extract_style_features(
        "Portanto, o resultado é consistente. Entretanto, há ressalvas."
    )
    assert estilo.formalidade >= 0.5


def test_detecta_conectivos() -> None:
    texto = "Portanto, o dado é relevante. Contudo, há limites. Ademais, resta investigar."
    estilo = extract_style_features(texto)
    assert "portanto" in estilo.conectivos_recorrentes
    assert "contudo" in estilo.conectivos_recorrentes


def test_detecta_terminologia_latim() -> None:
    estilo = extract_style_features("O ensaio foi conduzido in vitro e in vivo.")
    assert "in vitro" in estilo.terminologia


def test_vocabulario_tecnico_quando_ha_terminologia() -> None:
    estilo = extract_style_features("Análise in silico do genoma.")
    assert estilo.vocabulario == "técnico"


def test_texto_vazio() -> None:
    estilo = extract_style_features("")
    assert estilo.comprimento_medio_frase == 0.0
    assert estilo.formalidade == 0.5


def test_organizacao_de_paragrafos() -> None:
    texto = "A\n\nB\n\nC\n\nD"
    assert extract_style_features(texto).organizacao_paragrafos == "complexa"
