"""Catálogo de regras de normalização.

A ordem do pipeline é fixa e documentada. Ela existe porque algumas
transformações se condicionam: unificar quebras de linha antes de agir sobre
linhas, decodificar entidades antes de remover marcação, remover ênfase
depois de remover o código inline (que protegeria as crases) e, por fim,
atacar os espaços.

NFKC roda **antes** da remoção de invisíveis e da limpeza de Markdown, como
no repositório de referência: é o NFKC que expõe formas compostas (por
exemplo, uma crase seguida de seletor de variação) que a limpeza seguinte
precisa alcançar.
"""

from __future__ import annotations

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

#: Ordem canônica do pipeline.
PIPELINE_ORDER: tuple[str, ...] = (
    "norm.unicode.linebreak",
    "norm.invisible.zwsp",
    "norm.invisible.bidi",
    "norm.invisible.soft_hyphen",
    "norm.invisible.variation",
    "norm.control.strip",
    "norm.ansi.strip",
    "norm.unicode.nfkc",
    "norm.unicode.nfc",
    "norm.html.entities",
    "norm.pseudographics",
    "norm.dash.normalize",
    "norm.quotes.ascii",
    "norm.ellipsis.ascii",
    "norm.bullet.normalize",
    "norm.markdown.divider",
    "norm.markdown.heading",
    "norm.markdown.heading_empty",
    "norm.markdown.quote",
    "norm.markdown.bullet",
    "norm.markdown.emphasis",
    "norm.markdown.code",
    "norm.markdown.escape",
    "norm.emoji.remove",
    "norm.whitespace.nbsp",
    "norm.punctuation.space_before",
    "norm.whitespace.collapse",
    "norm.whitespace.trailing",
    "norm.whitespace.blank_lines",
)


def build_default_rules() -> list[NormalizationRule]:
    """Instancia todas as regras do catálogo, na ordem do pipeline."""
    regras: list[NormalizationRule] = [
        NormalizeLineBreakRule(),
        RemoveZwspRule(),
        RemoveBidiRule(),
        RemoveSoftHyphenRule(),
        RemoveVariationSelectorRule(),
        StripControlCharsRule(),
        StripAnsiRule(),
        NormalizeNfkcRule(),
        NormalizeNfcRule(),
        DecodeHtmlEntitiesRule(),
        NormalizePseudographicsRule(),
        NormalizeDashRule(),
        NormalizeQuotesRule(),
        NormalizeEllipsisRule(),
        NormalizeBulletRule(),
        RemoveMarkdownDividerRule(),
        RemoveMarkdownHeadingRule(),
        RemoveEmptyMarkdownHeadingRule(),
        RemoveMarkdownQuoteRule(),
        NormalizeMarkdownBulletRule(),
        RemoveMarkdownEmphasisRule(),
        RemoveMarkdownCodeRule(),
        RemoveMarkdownEscapeRule(),
        RemoveEmojiRule(),
        ReplaceNbspRule(),
        RemoveSpaceBeforePunctuationRule(),
        CollapseSpacesRule(),
        RemoveTrailingSpacesRule(),
        CollapseBlankLinesRule(),
    ]
    _validar_ordem(regras)
    return regras


def _validar_ordem(regras: list[NormalizationRule]) -> None:
    """Garante que o catálogo e a ordem canônica não divirjam."""
    ids = [regra.rule_id for regra in regras]
    if len(set(ids)) != len(ids):
        raise ValueError("Há identificadores de regra duplicados no catálogo.")
    if tuple(ids) != PIPELINE_ORDER:
        raise ValueError("A ordem das regras diverge de PIPELINE_ORDER.")


__all__ = [
    "PIPELINE_ORDER",
    "build_default_rules",
]
