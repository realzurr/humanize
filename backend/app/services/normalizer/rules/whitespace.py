"""Regras de espaços em branco.

O risco acadêmico é baixo, mas o impacto visual é alto: um espaço não
separável que sobrevive à exportação quebra a justificação e um espaço duplo
no fim da linha aparece como caixa alta invertida no Word.
"""

from __future__ import annotations

import re

from app.ir.protection import ProtectedKind
from app.services.normalizer.rules.base import RegexRule, RuleGroup

#: Espaços não separáveis: NBSP, U+2000-U+200A, NNBSP, MMSP e ideográfico.
_NBSP = re.compile("[\u00a0\u2000-\u200a\u202f\u205f\u3000]")

#: Sequências de dois ou mais espaços.
_RUNS = re.compile(" {2,}")

#: Espaços no fim da linha e no fim do texto.
_TRAILING = re.compile("[ \t]+(?=\n)|[ \t]+\\Z")

#: Três ou mais linhas em branco consecutivas viram duas.
_BLANK_LINES = re.compile("\n{4,}")


class ReplaceNbspRule(RegexRule):
    """Converte espaços não separáveis em espaço comum."""

    rule_id = "norm.whitespace.nbsp"
    description = "Converte espaços não separáveis em espaço comum"
    category = "espaços"
    group = RuleGroup.WHITESPACE
    pattern = _NBSP
    replacement = " "
    protected_kinds = frozenset({ProtectedKind.CODE, ProtectedKind.TABLE})


class CollapseSpacesRule(RegexRule):
    """Reduz sequências de espaços a um único espaço."""

    rule_id = "norm.whitespace.collapse"
    description = "Reduz sequências de espaços a um único espaço"
    category = "espaços"
    group = RuleGroup.WHITESPACE
    pattern = _RUNS
    replacement = " "
    protected_kinds = frozenset({ProtectedKind.CODE, ProtectedKind.TABLE})


class RemoveTrailingSpacesRule(RegexRule):
    """Remove espaços no fim das linhas."""

    rule_id = "norm.whitespace.trailing"
    description = "Remove espaços no fim das linhas"
    category = "espaços"
    group = RuleGroup.WHITESPACE
    pattern = _TRAILING
    replacement = ""
    protected_kinds = frozenset({ProtectedKind.CODE, ProtectedKind.TABLE})


class CollapseBlankLinesRule(RegexRule):
    """Reduz três ou mais linhas em branco a duas."""

    rule_id = "norm.whitespace.blank_lines"
    description = "Reduz três ou mais linhas em branco a duas"
    category = "espaços"
    group = RuleGroup.WHITESPACE
    pattern = _BLANK_LINES
    replacement = "\n\n\n"
    protected_kinds = frozenset({ProtectedKind.CODE, ProtectedKind.TABLE})
