"""Regra de decodificação de entidades HTML.

Texto copiado de páginas web e de processadores de texto chega ao documento
com ``&amp;`` e ``&#x2014;`` no lugar dos caracteres correspondentes. A
decodificação é feita **apenas** para entidades com ponto e vírgula explícito,
para não mexer em textos como ``AT&T`` ou ``R&D``.
"""

from __future__ import annotations

import html
import re

from app.ir.protection import ProtectedKind
from app.services.normalizer.rules.base import RegexRule, RuleGroup, RuleResult

#: Entidade nomeada ou numérica com ponto e vírgula explícito.
_ENTITY = re.compile(r"&(?:[A-Za-z][A-Za-z0-9]{1,31}|#\d{1,7}|#[xX][0-9A-Fa-f]{1,6});")


def _decodificar(match: re.Match[str]) -> str:
    """Decodifica a entidade encontrada."""
    return html.unescape(match.group(0))


class DecodeHtmlEntitiesRule(RegexRule):
    """Decodifica entidades HTML explícitas."""

    rule_id = "norm.html.entities"
    description = "Decodifica entidades HTML (&amp;, &#x2014;, ...)"
    category = "html"
    group = RuleGroup.HTML
    severity = "warning"
    pattern = _ENTITY
    replacement = ""
    protected_kinds = frozenset({ProtectedKind.CODE, ProtectedKind.URL})

    def apply(self, text: str) -> RuleResult:
        return self._substitute(text, _decodificar)
