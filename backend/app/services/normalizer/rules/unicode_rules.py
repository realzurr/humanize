"""Regras de normalização Unicode.

A NFKC é a transformação mais destrutiva do catálogo: ela converte
compatibilidades Unicode em seus equivalentes "planos" e, com isso, apaga
superíndices, subscritos, cargas iônicas e o sinal de menos matemático. Por
isso ela é **desligada por padrão** e, mesmo quando ligada, o motor a
aplica apenas fora dos trechos protegidos (números, fórmulas, unidades,
códigos, citações, DOIs, URLs, datas e tabelas).
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

#: CRLF, CR, U+2028 (line separator) e U+2029 (paragraph separator).
_LINEBREAK = re.compile("\r\n|\r|\u2028|\u2029")

#: Categorias que a NFKC nunca pode alcançar.
_TODAS_AS_PROTEGIDAS = frozenset(ProtectedKind)


class NormalizeLineBreakRule(RegexRule):
    """Unifica as quebras de linha em ``\\n``."""

    rule_id = "norm.unicode.linebreak"
    description = "Unifica CRLF, CR, U+2028 e U+2029 em quebra de linha Unix"
    category = "unicode"
    group = RuleGroup.UNICODE
    pattern = _LINEBREAK
    replacement = "\n"
    protected_kinds = frozenset({ProtectedKind.CODE, ProtectedKind.TABLE})


class NormalizeNfcRule(NormalizationRule):
    """Composição canônica (NFC).

    A NFC apenas compõe caracteres que já são visualmente idênticos. Ela não
    destrói notação científica, mas é aplicada apenas fora de código e
    tabelas, onde a sequência original pode ser significativa.
    """

    rule_id = "norm.unicode.nfc"
    description = "Composição canônica Unicode (NFC)"
    category = "unicode"
    group = RuleGroup.UNICODE
    protected_kinds = frozenset({ProtectedKind.CODE, ProtectedKind.TABLE})

    def apply(self, text: str) -> RuleResult:
        if not text:
            return RuleResult(text=text)
        novo_texto = unicodedata.normalize("NFC", text)
        if novo_texto == text:
            return RuleResult(text=text)
        alterados = sum(
            1 for original, novo in zip(text, novo_texto, strict=False) if original != novo
        )
        return RuleResult(
            text=novo_texto,
            occurrences=(
                RuleOccurrence(
                    rule_id=self.rule_id,
                    count=max(alterados, 1),
                    before=text[:80],
                    after=novo_texto[:80],
                    severity="info",
                ),
            ),
        )


class NormalizeNfkcRule(NormalizationRule):
    """Normalização de compatibilidade (NFKC).

    Desligada por padrão: converter ``10⁻⁶`` em ``10-6`` altera a ordem de
    grandeza, e ``x²`` em ``x2`` apaga o quadrado. O risco é tão alto que a
    regra exige ativação explícita, e o motor ainda a restringe aos trechos
    que não contêm conteúdo protegido.
    """

    rule_id = "norm.unicode.nfkc"
    description = (
        "Normalização de compatibilidade Unicode (NFKC) — destrutiva em notação científica"
    )
    category = "unicode"
    group = RuleGroup.UNICODE
    enabled_by_default = False
    touches_protected_content = True
    severity = "critical"
    protected_kinds = _TODAS_AS_PROTEGIDAS

    def apply(self, text: str) -> RuleResult:
        if not text:
            return RuleResult(text=text)
        novo_texto = unicodedata.normalize("NFKC", text)
        if novo_texto == text:
            return RuleResult(text=text)
        alterados = sum(
            1 for original, novo in zip(text, novo_texto, strict=False) if original != novo
        )
        return RuleResult(
            text=novo_texto,
            occurrences=(
                RuleOccurrence(
                    rule_id=self.rule_id,
                    count=max(alterados, 1),
                    before=text[:80],
                    after=novo_texto[:80],
                    severity="critical",
                ),
            ),
        )
