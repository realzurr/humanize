"""Regras de limpeza de Markdown.

A limpeza de Markdown é a transformação de maior risco do catálogo: no
repositório de referência, as expressões de ênfase removiam subscritos de
equação (``F _i_ e _j_`` virava ``F i e j``) e o bloco de código perdia
crases.

Aqui a marcação é removida **apenas fora dos trechos protegidos**. O
detector de subscritos (em :mod:`app.services.normalizer.protect`) protege o
padrão ``letra + espaço + _ + subscrito``, e o código é protegido como
entidade — com a exceção das crases do código inline, que existem justamente
para ser removidas.
"""

from __future__ import annotations

import re

from app.ir.protection import ProtectedKind
from app.services.normalizer.rules.base import (
    NormalizationRule,
    RegexRule,
    RuleGroup,
    RuleOccurrence,
    RuleResult,
)

#: Linhas divisórias (``---``, ``***``, ``===``).
_DIVIDER = re.compile("^[ \t]*(?:-{3,}|\\*{3,}|={3,})[ \t]*$\\n?", re.MULTILINE)

#: Marcadores de título no início da linha.
_HEADING = re.compile("^[ \t]{0,3}#{1,6}[ \t]+(?=\\S)", re.MULTILINE)

#: Título vazio (``##`` sem conteúdo).
_HEADING_VAZIO = re.compile("^[ \t]{0,3}#{1,6}[ \t]*$\\n?", re.MULTILINE)

#: Marcador de citação em bloco.
_QUOTE = re.compile("^[ \t]{0,3}>[ \t]?", re.MULTILINE)

#: Marcadores de lista (``*`` ou ``+``) no início da linha.
_BULLET = re.compile("^([ \t]*)[*+][ \t]+", re.MULTILINE)

#: Crase de código inline (uma ou duas crases; nunca três, que são cerca).
_INLINE_CODE = re.compile("(?<!`)(`{1,2})([^`\n]+)\\1(?!`)")

#: Escape de caractere Markdown (``\\$``).
_ESCAPE = re.compile(r"\\([\\`*_{}\[\]()#+\-.!>~|$])")

#: Ênfase Markdown, do marcador mais específico para o mais genérico.
_EMPHASIS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?<![A-Za-z0-9_*])(\*\*)(?!\s)([^*\n]+?)(?<!\s)(\*\*)(?![A-Za-z0-9_*])"),
    re.compile(r"(?<![A-Za-z0-9_])(__)(?!\s)([^_\n]+?)(?<!\s)(__)(?![A-Za-z0-9_])"),
    re.compile(r"(?<![A-Za-z0-9_*])(\*)(?!\s)([^*\n]+?)(?<!\s)(\*)(?![A-Za-z0-9_*])"),
    re.compile(r"(?<![A-Za-z0-9_])(_)(?!\s)([^_\n]+?)(?<!\s)(_)(?![A-Za-z0-9_])"),
)


class RemoveMarkdownDividerRule(RegexRule):
    """Remove linhas divisórias do Markdown."""

    rule_id = "norm.markdown.divider"
    description = "Remove linhas divisórias do Markdown (---, ***, ===)"
    category = "markdown"
    group = RuleGroup.MARKDOWN
    pattern = _DIVIDER
    replacement = ""
    protected_kinds = frozenset({ProtectedKind.CODE, ProtectedKind.TABLE})


class RemoveMarkdownHeadingRule(RegexRule):
    """Remove os marcadores de título do Markdown."""

    rule_id = "norm.markdown.heading"
    description = "Remove os marcadores de título do Markdown"
    category = "markdown"
    group = RuleGroup.MARKDOWN
    pattern = _HEADING
    replacement = ""
    protected_kinds = frozenset({ProtectedKind.CODE, ProtectedKind.TABLE, ProtectedKind.NUMBER})


class RemoveEmptyMarkdownHeadingRule(RegexRule):
    """Remove títulos vazios do Markdown."""

    rule_id = "norm.markdown.heading_empty"
    description = "Remove títulos vazios do Markdown"
    category = "markdown"
    group = RuleGroup.MARKDOWN
    pattern = _HEADING_VAZIO
    replacement = ""
    protected_kinds = frozenset({ProtectedKind.CODE, ProtectedKind.TABLE})


class RemoveMarkdownQuoteRule(RegexRule):
    """Remove o marcador de citação em bloco."""

    rule_id = "norm.markdown.quote"
    description = "Remove o marcador de citação em bloco do Markdown (>)"
    category = "markdown"
    group = RuleGroup.MARKDOWN
    pattern = _QUOTE
    replacement = ""
    protected_kinds = frozenset({ProtectedKind.CODE, ProtectedKind.TABLE})


class NormalizeMarkdownBulletRule(RegexRule):
    """Converte marcadores de lista em hífen."""

    rule_id = "norm.markdown.bullet"
    description = "Converte marcadores de lista do Markdown em hífen"
    category = "markdown"
    group = RuleGroup.MARKDOWN
    pattern = _BULLET
    replacement = r"\1- "
    protected_kinds = frozenset({ProtectedKind.CODE, ProtectedKind.TABLE, ProtectedKind.NUMBER})


class RemoveMarkdownEmphasisRule(NormalizationRule):
    """Remove a marcação de ênfase do Markdown.

    A ordem de aplicação é do marcador mais específico (``**`` e ``__``) para
    o mais genérico (``*`` e ``_``), para que o texto em negrito não seja
    confundido com dois trechos em itálico.
    """

    rule_id = "norm.markdown.emphasis"
    description = "Remove a marcação de ênfase do Markdown (**, __, *, _)"
    category = "markdown"
    group = RuleGroup.MARKDOWN
    severity = "warning"
    protected_kinds = frozenset(
        {ProtectedKind.CODE, ProtectedKind.TABLE, ProtectedKind.FORMULA, ProtectedKind.NUMBER}
    )

    def apply(self, text: str) -> RuleResult:
        if not text:
            return RuleResult(text=text)

        novo_texto = text
        total = 0
        posicoes: list[int] = []
        for padrao in _EMPHASIS:
            matches = list(padrao.finditer(novo_texto))
            if not matches:
                continue
            total += len(matches)
            posicoes.extend(match.start() for match in matches)
            novo_texto = padrao.sub(r"\2", novo_texto)

        if total == 0 or novo_texto == text:
            return RuleResult(text=text)

        return RuleResult(
            text=novo_texto,
            occurrences=(
                RuleOccurrence(
                    rule_id=self.rule_id,
                    count=total,
                    before="marcação de ênfase",
                    after="texto",
                    severity="warning",
                    positions=tuple(sorted(posicoes)),
                ),
            ),
        )


class RemoveMarkdownCodeRule(RegexRule):
    """Remove as crases do código inline.

    O conteúdo do código em linha é preservado; apenas a marcação é removida.
    A cerca de bloco (```````) não é alcançada por esta regra.
    """

    rule_id = "norm.markdown.code"
    description = "Remove as crases do código inline do Markdown"
    category = "markdown"
    group = RuleGroup.MARKDOWN
    pattern = _INLINE_CODE
    replacement = r"\2"
    protected_kinds = frozenset({ProtectedKind.TABLE})


class RemoveMarkdownEscapeRule(RegexRule):
    """Remove a barra de escape dos caracteres Markdown."""

    rule_id = "norm.markdown.escape"
    description = "Remove a barra de escape dos caracteres Markdown"
    category = "markdown"
    group = RuleGroup.MARKDOWN
    pattern = _ESCAPE
    replacement = r"\1"
    protected_kinds = frozenset({ProtectedKind.CODE, ProtectedKind.TABLE})
