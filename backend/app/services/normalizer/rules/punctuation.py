"""Regras de pontuação e caracteres de controle.

A remoção de espaço antes de pontuação é reversível e de baixo risco; já a
remoção de caracteres de controle precisa preservar o tabulador e a
quebra de linha, que carregam a estrutura do parágrafo.
"""

from __future__ import annotations

import re

from app.ir.protection import ProtectedKind
from app.services.normalizer.rules.base import RegexRule, RuleGroup

#: Espaço antes de pontuação final ou de fechamento.
_SPACE_BEFORE = re.compile("[ \t]+([.,!?;:)\\]}])")

#: Controles C0 (exceto TAB, LF e CR) e C1.
_CONTROL = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")

#: Sequências de escape ANSI (CSI e sequências de duas letras).
_ANSI = re.compile("\x1b\\[[0-9;?]*[ -/]*[@-~]|\x1b[@-Z\\\\-_]")


class RemoveSpaceBeforePunctuationRule(RegexRule):
    """Remove o espaço que antecede a pontuação."""

    rule_id = "norm.punctuation.space_before"
    description = "Remove o espaço antes de pontuação final"
    category = "pontuação"
    group = RuleGroup.WHITESPACE
    pattern = _SPACE_BEFORE
    replacement = r"\1"
    protected_kinds = frozenset({ProtectedKind.CODE, ProtectedKind.TABLE})


class StripControlCharsRule(RegexRule):
    """Remove caracteres de controle C0/C1 (preservando TAB, LF e CR)."""

    rule_id = "norm.control.strip"
    description = "Remove caracteres de controle C0/C1"
    category = "controle"
    group = RuleGroup.INVISIBLE
    pattern = _CONTROL
    replacement = ""
    protected_kinds = frozenset({ProtectedKind.CODE})


class StripAnsiRule(RegexRule):
    """Remove sequências de escape ANSI."""

    rule_id = "norm.ansi.strip"
    description = "Remove sequências de escape ANSI"
    category = "controle"
    group = RuleGroup.INVISIBLE
    pattern = _ANSI
    replacement = ""
    protected_kinds = frozenset({ProtectedKind.CODE})
