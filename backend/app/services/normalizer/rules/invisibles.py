"""Regras de caracteres invisíveis.

Remove os caracteres que não ocupam espaço mas alteram o resultado da
comparação de textos, a indexação ou a renderização. O risco acadêmico é
baixo, exceto pelos controles bidirecionais, que podem inverter a ordem de
exibição sem qualquer aviso visual no texto-fonte.
"""

from __future__ import annotations

import re

from app.ir.protection import ProtectedKind
from app.services.normalizer.rules.base import RegexRule, RuleGroup

#: ZWSP, ZWNJ, ZWJ, word-joiner e BOM (ZWNBSP).
_ZWSP = re.compile("[\u200b\u200c\u200d\u2060\ufeff]")

#: Controles bidirecionais, marcas de direção forte e marcas direcionais.
_BIDI = re.compile("[\u200e\u200f\u202a-\u202e\u2066-\u2069]")

#: Hífen opcional.
_SOFT_HYPHEN = re.compile("\u00ad")

#: Seletores de variação (U+FE00-U+FE0F e U+E0100-U+E01EF).
_VARIATION = re.compile("[\ufe00-\ufe0f\U000e0100-\U000e01ef]")


class RemoveZwspRule(RegexRule):
    """Remove ZWSP, ZWNJ, ZWJ, word-joiner e BOM."""

    rule_id = "norm.invisible.zwsp"
    description = "Remove espaços de largura zero, ZWJ/ZWNJ, word-joiner e BOM"
    category = "invisíveis"
    group = RuleGroup.INVISIBLE
    pattern = _ZWSP
    replacement = ""
    protected_kinds = frozenset({ProtectedKind.CODE, ProtectedKind.FORMULA})


class RemoveBidiRule(RegexRule):
    """Remove controles de direção bidirecional."""

    rule_id = "norm.invisible.bidi"
    description = "Remove controles bidirecionais (podem inverter a exibição)"
    category = "invisíveis"
    group = RuleGroup.INVISIBLE
    pattern = _BIDI
    replacement = ""
    severity = "warning"
    protected_kinds = frozenset({ProtectedKind.CODE, ProtectedKind.FORMULA})


class RemoveSoftHyphenRule(RegexRule):
    """Remove o hífen opcional."""

    rule_id = "norm.invisible.soft_hyphen"
    description = "Remove hífen opcional"
    category = "invisíveis"
    group = RuleGroup.INVISIBLE
    pattern = _SOFT_HYPHEN
    replacement = ""
    protected_kinds = frozenset({ProtectedKind.CODE})


class RemoveVariationSelectorRule(RegexRule):
    """Remove seletores de variação."""

    rule_id = "norm.invisible.variation"
    description = "Remove seletores de variação Unicode"
    category = "invisíveis"
    group = RuleGroup.INVISIBLE
    pattern = _VARIATION
    replacement = ""
    protected_kinds = frozenset({ProtectedKind.CODE, ProtectedKind.FORMULA})
