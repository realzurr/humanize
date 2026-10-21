"""Regras de símbolos: emoji, pseudo-gráficos, traços, aspas, reticências e marcadores.

As três regras de maior risco desta família são:

* :class:`RemoveEmojiRule` — a remoção por faixa inclui ``©``, ``®`` e ``™`` e
  apaga símbolos técnicos como ``✓`` e ``★``; por isso há uma lista de
  exceção explícita;
* :class:`NormalizePseudographicsRule` — pseudo-gráficos de caixa viram
  ``+``, ``-`` e ``|`` e deformam tabelas; as tabelas são protegidas e as
  setas (faixa U+2190-U+21FF) ficam fora do alcance da regra;
* :class:`NormalizeDashRule` — o sinal de menos matemático (U+2212) é
  tipograficamente distinto do hífen e **não** pode ser convertido.
"""

from __future__ import annotations

import re
import unicodedata

from app.ir.protection import ProtectedKind
from app.services.normalizer.rules.base import (
    NormalizationRule,
    RegexRule,
    RuleGroup,
    RuleOccurrence,
    RuleResult,
)

#: Traços e barras (U+2010-U+2015). U+2212 (sinal de menos) fica de fora.
_DASH = re.compile("[\u2010-\u2015]")

#: Aspas curvas.
_QUOTES_DOUBLE = re.compile("[\u201c\u201d\u201e\u00ab\u00bb]")
_QUOTES_SINGLE = re.compile("[\u2018\u2019\u201a\u2039\u203a]")

#: Reticências.
_ELLIPSIS = re.compile("\u2026")

#: Marcadores de lista.
_BULLET = re.compile("[\u2022\u25e6\u00b7\u2219\u2043\u2027]")

#: Pseudo-gráficos de caixa.
_BOX = re.compile("[\u2500-\u257f]")

#: Faixas de emoji e pictogramas decorativos.
_EMOJI_RANGES: tuple[tuple[int, int], ...] = (
    (0x1F000, 0x1F0FF),
    (0x1F1E6, 0x1F1FF),
    (0x1F300, 0x1F5FF),
    (0x1F600, 0x1F64F),
    (0x1F680, 0x1F6FF),
    (0x1F900, 0x1F9FF),
    (0x1FA70, 0x1FAFF),
    (0x2600, 0x26FF),
    (0x2700, 0x27BF),
    (0x2B00, 0x2B55),
    (0x3030, 0x3030),
    (0x303D, 0x303D),
    (0x3297, 0x3297),
    (0x3299, 0x3299),
)

#: Símbolos com significado acadêmico ou técnico que **não** são removidos.
_EMOJI_PRESERVADOS = frozenset("✓✗★☆♂♀⚙✈⚠⛔☑☒✔✖⚛⚖⚗⚜☀☁☂☃☄☇☈☉☊☋☌☍☎☏⌘⌚⌛▶◀◼◾⬛⬜■□▣▪▫●○◦")


def _is_emoji(char: str) -> bool:
    """Indica se o caractere é um pictograma decorativo."""
    if char in _EMOJI_PRESERVADOS:
        return False
    ponto = ord(char)
    return any(inicio <= ponto <= fim for inicio, fim in _EMOJI_RANGES)


def _box_replacement(match: re.Match[str]) -> str:
    """Converte um pseudo-gráfico de caixa em ASCII.

    A classificação usa o nome Unicode do caractere: junções e cantos têm
    ``AND`` no nome (``DOWN AND RIGHT``), linhas verticais têm ``VERTICAL`` e
    linhas horizontais têm ``HORIZONTAL``.
    """
    nome = unicodedata.name(match.group(0), "")
    if "AND" in nome:
        return "+"
    if "VERTICAL" in nome:
        return "|"
    if "HORIZONTAL" in nome:
        return "-"
    if "DIAGONAL" in nome:
        return "/"
    return " "


class RemoveEmojiRule(NormalizationRule):
    """Remove emoji e pictogramas decorativos.

    A lista de exceção preserva ``©``, ``®``, ``™`` e os símbolos técnicos
    que carregam significado (marcas de conferência, asteriscos, indicadores
    de gênero, engrenagens).
    """

    rule_id = "norm.emoji.remove"
    description = "Remove emoji e pictogramas decorativos (preserva ©, ® e ™)"
    category = "símbolos"
    group = RuleGroup.EMOJI
    severity = "warning"
    protected_kinds = frozenset(
        {
            ProtectedKind.CODE,
            ProtectedKind.TABLE,
            ProtectedKind.CITATION,
            ProtectedKind.QUOTE_LITERAL,
        }
    )

    def apply(self, text: str) -> RuleResult:
        if not text:
            return RuleResult(text=text)
        removidos = [indice for indice, char in enumerate(text) if _is_emoji(char)]
        if not removidos:
            return RuleResult(text=text)
        conjunto = set(removidos)
        novo_texto = "".join(char for indice, char in enumerate(text) if indice not in conjunto)
        return RuleResult(
            text=novo_texto,
            occurrences=(
                RuleOccurrence(
                    rule_id=self.rule_id,
                    count=len(removidos),
                    before="".join(text[indice] for indice in removidos[:10]),
                    after="",
                    severity="warning",
                    positions=tuple(removidos),
                ),
            ),
        )


class NormalizePseudographicsRule(RegexRule):
    """Converte pseudo-gráficos de caixa em ASCII.

    A regra não alcança a faixa de setas (U+2190-U+21FF), que indica
    produto e equilíbrio em reações químicas, e não alcança tabelas, que
    ficariam deformadas.
    """

    rule_id = "norm.pseudographics"
    description = "Converte pseudo-gráficos de caixa em caracteres ASCII"
    category = "símbolos"
    group = RuleGroup.SYMBOLS
    severity = "warning"
    pattern = _BOX
    replacement = ""
    protected_kinds = frozenset({ProtectedKind.CODE, ProtectedKind.TABLE, ProtectedKind.FORMULA})

    def apply(self, text: str) -> RuleResult:
        return self._substitute(text, _box_replacement)


class NormalizeDashRule(RegexRule):
    """Converte traços tipográficos em hífen.

    O sinal de menos matemático (U+2212) é preservado: em equações,
    ``a − b`` não é o mesmo que ``a-b``.
    """

    rule_id = "norm.dash.normalize"
    description = "Converte traços tipográficos em hífen (preserva o sinal de menos U+2212)"
    category = "símbolos"
    group = RuleGroup.SYMBOLS
    pattern = _DASH
    replacement = "-"
    protected_kinds = frozenset(
        {ProtectedKind.CODE, ProtectedKind.FORMULA, ProtectedKind.NUMBER, ProtectedKind.TABLE}
    )


class NormalizeQuotesRule(NormalizationRule):
    """Converte aspas curvas em aspas retas.

    As aspas que delimitam uma citação literal são protegidas e, portanto,
    preservadas: é essa distinção que permite detectar citações literais
    nas ondas seguintes.
    """

    rule_id = "norm.quotes.ascii"
    description = "Converte aspas curvas em aspas retas (preserva citação literal)"
    category = "símbolos"
    group = RuleGroup.SYMBOLS
    severity = "warning"
    protected_kinds = frozenset(
        {
            ProtectedKind.CODE,
            ProtectedKind.QUOTE_LITERAL,
            ProtectedKind.CITATION,
            ProtectedKind.TABLE,
        }
    )

    def apply(self, text: str) -> RuleResult:
        if not text:
            return RuleResult(text=text)
        novo_texto = _QUOTES_DOUBLE.sub('"', text)
        novo_texto = _QUOTES_SINGLE.sub("'", novo_texto)
        if novo_texto == text:
            return RuleResult(text=text)
        alterados = sum(1 for a, b in zip(text, novo_texto, strict=False) if a != b)
        return RuleResult(
            text=novo_texto,
            occurrences=(
                RuleOccurrence(
                    rule_id=self.rule_id,
                    count=max(alterados, 1),
                    before="aspas curvas",
                    after="aspas retas",
                    severity="warning",
                ),
            ),
        )


class NormalizeEllipsisRule(RegexRule):
    """Converte a reticência tipográfica em três pontos."""

    rule_id = "norm.ellipsis.ascii"
    description = "Converte a reticência tipográfica em três pontos"
    category = "símbolos"
    group = RuleGroup.SYMBOLS
    pattern = _ELLIPSIS
    replacement = "..."
    protected_kinds = frozenset(
        {ProtectedKind.CODE, ProtectedKind.QUOTE_LITERAL, ProtectedKind.TABLE}
    )


class NormalizeBulletRule(RegexRule):
    """Converte marcadores de lista em hífen.

    O ponto médio (U+00B7) é marcador de lista em alguns documentos, mas
    também é o ponto de multiplicação em fórmulas (``E = m·a``). Por isso a
    regra não alcança trechos com notação matemática.
    """

    rule_id = "norm.bullet.normalize"
    description = "Converte marcadores de lista em hífen"
    category = "símbolos"
    group = RuleGroup.SYMBOLS
    pattern = _BULLET
    replacement = "-"
    protected_kinds = frozenset({ProtectedKind.CODE, ProtectedKind.TABLE, ProtectedKind.FORMULA})
