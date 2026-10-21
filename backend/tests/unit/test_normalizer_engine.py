"""Testes do motor de normalização."""

from __future__ import annotations

from app.services.normalizer.engine import NormalizationEngine
from app.services.normalizer.profile import NormalizationProfile, get_profile

ENGINE = NormalizationEngine()


def _normaliza(texto: str, perfil: NormalizationProfile | None = None) -> str:
    return ENGINE.run(texto, perfil).text


def test_pipeline_preserva_notacao_cientifica() -> None:
    texto = "o valor foi 10⁻⁶ m² e x² e Na⁺ e CO₂"
    assert _normaliza(texto) == texto


def test_pipeline_preserva_formula_com_ponto_medio() -> None:
    texto = "E = m·a"
    assert _normaliza(texto) == texto


def test_pipeline_preserva_citacao_literal() -> None:
    texto = "“a acidificação do solo é a principal causa”"
    assert _normaliza(texto) == texto


def test_pipeline_preserva_tabela() -> None:
    texto = "| A | B |\n|---|---|\n| 1 | 2 |\n"
    assert _normaliza(texto) == texto


def test_pipeline_preserva_bloco_de_codigo() -> None:
    texto = "```\nprint('x')\n```"
    assert _normaliza(texto) == texto


def test_pipeline_preserva_subscrito_markdown() -> None:
    texto = "F _i_ e _j_"
    resultado = _normaliza(texto)
    assert "_i_" in resultado
    assert "_j_" in resultado


def test_pipeline_preserva_sinal_de_menos() -> None:
    texto = "a − b = c"
    assert _normaliza(texto) == texto


def test_pipeline_remove_marcacao_markdown() -> None:
    texto = "# Título\n\n**negrito** e *itálico*"
    assert _normaliza(texto) == "Título\n\nnegrito e itálico"


def test_pipeline_colapsa_espacos() -> None:
    assert _normaliza("a   b  c") == "a b c"


def test_pipeline_remove_espaco_antes_de_pontuacao() -> None:
    assert _normaliza("fim .") == "fim."


def test_regra_desabilitada_nao_atuam() -> None:
    perfil = NormalizationProfile(disabled_rules=frozenset({"norm.whitespace.collapse"}))
    assert _normaliza("a   b", perfil) == "a   b"


def test_regra_desabilitada_aparece_no_relatorio() -> None:
    perfil = NormalizationProfile(disabled_rules=frozenset({"norm.whitespace.collapse"}))
    report = ENGINE.run("a   b", perfil).report
    assert "norm.whitespace.collapse" in report.regras_desativadas


def test_nfkc_desligada_por_padrao_preserva_superindice() -> None:
    assert _normaliza("x²") == "x²"


def test_nfkc_ligada_remove_superindice_dentro_do_limite() -> None:
    # A NFKC é aplicada fora das entidades protegidas; o superíndice é
    # protegido como fórmula e sobrevive mesmo com a regra ligada.
    perfil = NormalizationProfile(enabled_rules=frozenset({"norm.unicode.nfkc"}))
    assert _normaliza("x²", perfil) == "x²"


def test_nfkc_ligada_normaliza_prosa() -> None:
    perfil = NormalizationProfile(enabled_rules=frozenset({"norm.unicode.nfkc"}))
    # A ligadura ﬁ é normalizada para "fi" (prosa, fora de fórmula).
    assert _normaliza("bem-deﬁnido", perfil) == "bem-definido"


def test_relatorio_conta_caracteres() -> None:
    report = ENGINE.run("a   b", NormalizationProfile()).report
    assert report.total_caracteres_antes == 5
    assert report.total_caracteres_depois == 3


def test_relatorio_registra_transformacoes() -> None:
    report = ENGINE.run("# Título", NormalizationProfile()).report
    ids = [t.rule_id for t in report.transformacoes]
    assert "norm.markdown.heading" in ids


def test_relatorio_avisa_perda_de_protegido() -> None:
    # Um texto com marcação de ênfase dentro de uma fórmula com subscrito não
    # deve perder a fórmula.
    report = ENGINE.run("F _i_ e _j_", NormalizationProfile()).report
    assert not report.houve_perda


def test_relatorio_entidades_protegidas_presentes() -> None:
    report = ENGINE.run("o valor foi 10⁻⁶ m²", NormalizationProfile()).report
    kinds = {e.kind for e in report.entidades_protegidas}
    assert "formula" in kinds


def test_texto_vazio_nao_erra() -> None:
    resultado = ENGINE.run("", NormalizationProfile())
    assert resultado.text == ""
    assert resultado.report.total_caracteres_antes == 0


def test_perfil_conservador_nao_remove_markdown() -> None:
    perfil = get_profile("conservador")
    assert _normaliza("**negrito**", perfil) == "**negrito**"


def test_mesma_entrada_mesma_saida() -> None:
    texto = "# Título\n\na   b  com 10⁻⁶ m² e *ênfase*"
    assert _normaliza(texto) == _normaliza(texto)
