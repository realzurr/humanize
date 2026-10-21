"""Testes unitários das regras de normalização.

Cada regra tem pelo menos um caso de transformação e um caso "não faz nada"
(entrada sem ocorrência ou regra aplicada a texto vazio).
"""

from __future__ import annotations

import pytest

from app.services.normalizer.rules import build_default_rules
from app.services.normalizer.rules.base import NormalizationRule
from app.services.normalizer.rules.html_entities import DecodeHtmlEntitiesRule
from app.services.normalizer.rules.invisibles import (
    RemoveBidiRule,
    RemoveSoftHyphenRule,
    RemoveVariationSelectorRule,
    RemoveZwspRule,
)
from app.services.normalizer.rules.markdown import (
    NormalizeMarkdownBulletRule,
    RemoveEmptyMarkdownHeadingRule,
    RemoveMarkdownCodeRule,
    RemoveMarkdownDividerRule,
    RemoveMarkdownEmphasisRule,
    RemoveMarkdownEscapeRule,
    RemoveMarkdownHeadingRule,
    RemoveMarkdownQuoteRule,
)
from app.services.normalizer.rules.punctuation import (
    RemoveSpaceBeforePunctuationRule,
    StripAnsiRule,
    StripControlCharsRule,
)
from app.services.normalizer.rules.symbols import (
    NormalizeBulletRule,
    NormalizeDashRule,
    NormalizeEllipsisRule,
    NormalizePseudographicsRule,
    NormalizeQuotesRule,
    RemoveEmojiRule,
)
from app.services.normalizer.rules.unicode_rules import (
    NormalizeLineBreakRule,
    NormalizeNfcRule,
    NormalizeNfkcRule,
)
from app.services.normalizer.rules.whitespace import (
    CollapseBlankLinesRule,
    CollapseSpacesRule,
    RemoveTrailingSpacesRule,
    ReplaceNbspRule,
)


def _aplica(regra: NormalizationRule, texto: str) -> str:
    return regra.apply(texto).text


class TestInvisiveis:
    def test_zwsp_remove_espaco_largura_zero(self) -> None:
        assert _aplica(RemoveZwspRule(), "a\u200bb") == "ab"

    def test_zwsp_nao_faz_nada_sem_ocorrencia(self) -> None:
        assert _aplica(RemoveZwspRule(), "texto limpo") == "texto limpo"

    def test_bidi_remove_controle_direcional(self) -> None:
        assert _aplica(RemoveBidiRule(), "a\u202eb") == "ab"

    def test_soft_hyphen_remove_hifen_opcional(self) -> None:
        assert _aplica(RemoveSoftHyphenRule(), "hi\u00adfen") == "hifen"

    def test_variation_remove_seletor(self) -> None:
        assert _aplica(RemoveVariationSelectorRule(), "a\ufe0fb") == "ab"


class TestUnicode:
    def test_linebreak_unifica_crlf(self) -> None:
        assert _aplica(NormalizeLineBreakRule(), "a\r\nb\rc\nd") == "a\nb\nc\nd"

    def test_nfc_compoe_acento(self) -> None:
        texto = "a\u0301"  # a + acento agudo combinante
        assert _aplica(NormalizeNfcRule(), texto) == "á"

    def test_nfkc_destroi_superindice(self) -> None:
        assert _aplica(NormalizeNfkcRule(), "x\u00b2") == "x2"

    def test_nfkc_desligada_por_padrao(self) -> None:
        assert NormalizeNfkcRule().enabled_by_default is False


class TestWhitespace:
    def test_nbsp_vira_espaco(self) -> None:
        assert _aplica(ReplaceNbspRule(), "a\u00a0b") == "a b"

    def test_collapse_reduz_espacos(self) -> None:
        assert _aplica(CollapseSpacesRule(), "a   b  c") == "a b c"

    def test_trailing_remove_fim_de_linha(self) -> None:
        assert _aplica(RemoveTrailingSpacesRule(), "a   \nb\t") == "a\nb"

    def test_blank_lines_reduz_tres_para_duas(self) -> None:
        assert _aplica(CollapseBlankLinesRule(), "a\n\n\n\nb") == "a\n\n\nb"


class TestPontuacao:
    def test_space_before_remove_espaco(self) -> None:
        assert _aplica(RemoveSpaceBeforePunctuationRule(), "fim .") == "fim."

    def test_control_strip_remove_c0(self) -> None:
        assert _aplica(StripControlCharsRule(), "a\x01b") == "ab"

    def test_control_preserva_tab_e_lf(self) -> None:
        assert _aplica(StripControlCharsRule(), "a\tb\n") == "a\tb\n"

    def test_ansi_strip_remove_escape(self) -> None:
        assert _aplica(StripAnsiRule(), "\x1b[31mvermelho\x1b[0m") == "vermelho"


class TestMarkdown:
    def test_heading_remove_jogo_da_velha(self) -> None:
        assert _aplica(RemoveMarkdownHeadingRule(), "# Título") == "Título"

    def test_heading_empty_remove_titulo_vazio(self) -> None:
        assert _aplica(RemoveEmptyMarkdownHeadingRule(), "##\n") == ""

    def test_quote_remove_marcador(self) -> None:
        assert _aplica(RemoveMarkdownQuoteRule(), "> citação") == "citação"

    def test_bullet_converte_asterisco(self) -> None:
        assert _aplica(NormalizeMarkdownBulletRule(), "* item") == "- item"

    def test_emphasis_remove_negrito(self) -> None:
        assert _aplica(RemoveMarkdownEmphasisRule(), "**negrito**") == "negrito"

    def test_code_remove_crases(self) -> None:
        assert _aplica(RemoveMarkdownCodeRule(), "`código`") == "código"

    def test_code_preserva_cerca_de_bloco(self) -> None:
        texto = "```\nprint('x')\n```"
        assert _aplica(RemoveMarkdownCodeRule(), texto) == texto

    def test_escape_remove_barra(self) -> None:
        assert _aplica(RemoveMarkdownEscapeRule(), "\\$") == "$"

    def test_divider_remove_linha(self) -> None:
        assert _aplica(RemoveMarkdownDividerRule(), "texto\n---\nmais") == "texto\nmais"


class TestSimbolos:
    def test_emoji_remove_pictograma(self) -> None:
        assert _aplica(RemoveEmojiRule(), "a😀b") == "ab"

    def test_emoji_preserva_copyright(self) -> None:
        assert _aplica(RemoveEmojiRule(), "©®™✓") == "©®™✓"

    def test_pseudographics_converte_caixa(self) -> None:
        assert _aplica(NormalizePseudographicsRule(), "─│┌") == "-|+"

    def test_pseudographics_preserva_seta(self) -> None:
        assert _aplica(NormalizePseudographicsRule(), "→⇌") == "→⇌"

    def test_dash_converte_travessao(self) -> None:
        assert _aplica(NormalizeDashRule(), "a—b") == "a-b"

    def test_dash_preserva_sinal_de_menos(self) -> None:
        assert _aplica(NormalizeDashRule(), "a−b") == "a−b"

    def test_quotes_converte_curvas(self) -> None:
        assert _aplica(NormalizeQuotesRule(), "\u201caspas\u201d") == '"aspas"'

    def test_ellipsis_converte_reticencias(self) -> None:
        assert _aplica(NormalizeEllipsisRule(), "a…b") == "a...b"

    def test_bullet_converte_marcador(self) -> None:
        assert _aplica(NormalizeBulletRule(), "• item") == "- item"


class TestHtml:
    def test_entities_decodifica(self) -> None:
        assert _aplica(DecodeHtmlEntitiesRule(), "a&amp;b&#x2014;c") == "a&b—c"

    def test_entities_preserva_texto_sem_ponto_virgula(self) -> None:
        assert _aplica(DecodeHtmlEntitiesRule(), "AT&T R&D") == "AT&T R&D"


def test_catalogo_sem_duplicatas() -> None:
    """Os ``rule_id`` do catálogo são únicos e estáveis."""
    regras = build_default_rules()
    ids = [regra.rule_id for regra in regras]
    assert len(ids) == len(set(ids))
    assert len(regras) == 29


@pytest.mark.parametrize("regra", build_default_rules())
def test_regra_texto_vazio_nao_erra(regra: NormalizationRule) -> None:
    resultado = regra.apply("")
    assert resultado.text == ""
    assert resultado.occurrences == ()


@pytest.mark.parametrize("regra", build_default_rules())
def test_regra_sem_ocorrencia_nao_altera(regra: NormalizationRule) -> None:
    """Aplicar a regra a um texto já limpo não o altera (idempotência)."""
    limpo = "texto simples sem nada a normalizar"
    assert regra.apply(limpo).text == limpo
