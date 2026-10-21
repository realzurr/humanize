"""Regressão documental da normalização.

O texto-fixture :file:`tests/fixtures/artigo_cientifico.md` é um documento
acadêmico anonimizado contendo: fórmulas, unidades, tabelas, bloco de código,
citação literal, DOI, referências, superíndices, subscritos e alfabeto grego.

A regressão verifica duas coisas, independentes entre si:

1. o resultado do perfil padrão é **idêntico** ao arquivo de referência
   versionado (:file:`artigo_cientifico_esperado.txt`);
2. nenhum trecho protegido (número, fórmula, unidade, DOI, URL, citação,
   tabela, código) foi **perdido ou alterado** durante a normalização.

A segunda verificação é a mais importante: ela testa a proteção, não apenas
a ausência de erro.
"""

from __future__ import annotations

from pathlib import Path

from app.services.normalizer.engine import NormalizationEngine
from app.services.normalizer.profile import get_profile

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
FONTE = FIXTURES / "artigo_cientifico.md"
ESPERADO = FIXTURES / "artigo_cientifico_esperado.txt"


def _carregar(caminho: Path) -> str:
    return caminho.read_text(encoding="utf-8")


def test_saida_do_perfil_padrao_e_estavel() -> None:
    """O resultado do perfil padrão deve ser idêntico ao arquivo versionado."""
    engine = NormalizationEngine()
    resultado = engine.run(_carregar(FONTE), get_profile("padrao"))
    assert resultado.text == _carregar(ESPERADO)


def test_nenhum_trecho_protegido_e_perdido_ou_alterado() -> None:
    """Números, fórmulas, unidades, DOIs, URLs, citações e tabelas permanecem."""
    engine = NormalizationEngine()
    resultado = engine.run(_carregar(FONTE), get_profile("padrao"))
    assert not resultado.report.houve_perda, resultado.report.avisos


def test_fixture_contem_todos_os_elementos_exigidos() -> None:
    """O fixture cobre os elementos que o ROADMAP exige proteger."""
    fonte = _carregar(FONTE)
    assert "10⁻⁶" in fonte or "m·a" in fonte or "η" in fonte  # fórmula
    assert "g·dm⁻³" in fonte  # unidade com superíndice
    assert "|" in fonte and "---" in fonte  # tabela
    assert "```" in fonte  # bloco de código
    assert "“" in fonte  # citação literal
    assert "10.1111" in fonte  # DOI
    assert "REFERÊNCIAS" in fonte  # lista de referências
    assert "Ca²⁺" in fonte  # superíndice
    assert "CO₂" in fonte or "dm⁻³" in fonte  # subscrito/superíndice
    assert "η" in fonte or "α" in fonte  # alfabeto grego


def test_saida_mantem_notacao_cientifica() -> None:
    """Os trechos de notação científica do fixture são preservados verbatim."""
    engine = NormalizationEngine()
    resultado = engine.run(_carregar(FONTE), get_profile("padrao"))
    saida = resultado.text
    for trecho in ("g·dm⁻³", "m·a", "Ca²⁺", "Mg²⁺", "η", "±", "×"):
        if trecho in _carregar(FONTE):
            assert trecho in saida, trecho
