"""Contrato de regras de normalização.

Cada transformação de texto é uma regra isolada, testável e configurável. A
regra recebe um trecho de texto e devolve o texto transformado mais um
registro de ocorrências. O motor (:mod:`app.services.normalizer.engine`)
compõe as regras em um pipeline determinístico.

A separação existe para que a normalização nunca dependa de LLM e cada regra
possa ser medida e revertida isoladamente.
"""

from __future__ import annotations

import abc
import re
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.ir.protection import ProtectedKind


class RuleGroup(StrEnum):
    """Agrupamento funcional das regras.

    O agrupamento existe para que a interface ofereça opções em vez de uma
    lista de dezenas de caixas de seleção. A granularidade fina permanece
    disponível pelo ``rule_id``.
    """

    UNICODE = "unicode"
    """Normalização Unicode (NFKC, NFC, quebras de linha)."""

    INVISIBLE = "invisible"
    """Caracteres invisíveis, de controle e sequências de escape."""

    EMOJI = "emoji"
    """Emoji e pictogramas decorativos."""

    MARKDOWN = "markdown"
    """Marcação Markdown."""

    WHITESPACE = "whitespace"
    """Espaços em branco e pontuação adjacente."""

    SYMBOLS = "symbols"
    """Traços, aspas, reticências, marcadores e pseudo-gráficos."""

    HTML = "html"
    """Entidades HTML."""


@dataclass(frozen=True, slots=True)
class RuleOccurrence:
    """Uma ocorrência detectada por uma regra."""

    rule_id: str
    """Identificador estável da regra, ex.: ``norm.invisible.zwsp``."""

    count: int
    """Quantidade de trechos afetados."""

    before: str = ""
    """Amostra do texto original afetado (truncado)."""

    after: str = ""
    """Amostra do texto resultante (truncado)."""

    severity: str = "info"
    """``info`` | ``warning`` | ``critical``."""

    positions: tuple[int, ...] = ()
    """Offsets (code points) das ocorrências no texto recebido."""


class RuleResult(BaseModel):
    """Saída de uma regra."""

    model_config = ConfigDict(frozen=True)

    text: str
    occurrences: tuple[RuleOccurrence, ...] = ()
    metadata: dict[str, Any] = {}


class NormalizationRule(abc.ABC):
    """Base para regras de normalização.

    Subclasses implementam :meth:`apply`. O identificador ``rule_id`` deve ser
    único e estável, pois é a chave usada em relatórios, métricas e na
    configuração por perfil.
    """

    #: Identificador estável, ex.: ``norm.invisible.zwsp``.
    rule_id: str = "norm.unknown"

    #: Descrição legível (pt-BR) usada na interface e nos relatórios.
    description: str = ""

    #: Categoria funcional, usada para agrupar na interface.
    category: str = "geral"

    #: Agrupamento funcional (usado pelas opções da interface).
    group: RuleGroup = RuleGroup.WHITESPACE

    #: Se a regra pode ser desligada pelo usuário.
    configurable: bool = True

    #: Padrão de ativação.
    enabled_by_default: bool = True

    #: Se a regra pode alterar/remover trechos protegidos. Deve ser ``False``
    #: para qualquer regra que possa tocar em números, fórmulas ou citações.
    touches_protected_content: bool = False

    #: Tipos de conteúdo protegido que a regra **não** pode alterar.
    protected_kinds: frozenset[ProtectedKind] = frozenset()
    """Categorias de entidade protegida que o motor isola antes da regra.

    O motor segmenta o texto em trechos protegidos e livres e aplica a regra
    apenas nos trechos livres. Uma regra que declare ``NUMBER`` aqui nunca
    alcança um valor numérico, ainda que o texto seja alterado por outra
    regra antes.
    """

    @abc.abstractmethod
    def apply(self, text: str) -> RuleResult:
        """Aplica a regra ao texto recebido."""

    def describe(self) -> dict[str, Any]:
        """Descrição serializável da regra (usada na API de configuração)."""
        return {
            "rule_id": self.rule_id,
            "description": self.description,
            "category": self.category,
            "group": str(self.group),
            "configurable": self.configurable,
            "enabled_by_default": self.enabled_by_default,
            "touches_protected_content": self.touches_protected_content,
            "protected_kinds": sorted(str(kind) for kind in self.protected_kinds),
        }


#: Limite de caracteres das amostras ``before``/``after``.
SAMPLE_LIMIT = 80


def _sample(text: str, limit: int = SAMPLE_LIMIT) -> str:
    """Trunca a amostra preservando a indicação de que ela foi cortada."""
    if len(text) <= limit:
        return text
    return text[:limit] + "…"


class RegexRule(NormalizationRule):
    """Regra baseada em substituição por expressão regular.

    Cobre a maioria das transformações. Regras com lógica própria (Markdown,
    emoji) implementam :meth:`apply` diretamente.
    """

    #: Padrão compilado da regra.
    pattern: re.Pattern[str] = re.compile(r"(?!x)x")

    #: Substituição: literal ou função que recebe o ``match``.
    replacement: str | Callable[[re.Match[str]], str] = ""

    #: Severidade registrada quando a regra altera o texto.
    severity: str = "info"

    def apply(self, text: str) -> RuleResult:
        return self._substitute(text, self.replacement)

    def _substitute(
        self,
        text: str,
        replacement: str | Callable[[re.Match[str]], str],
    ) -> RuleResult:
        """Aplica ``replacement`` ao texto e registra as ocorrências.

        A função de substituição é recebida como argumento (e não guardada em
        atributo de classe) para evitar que uma função de módulo seja
        promovida a *bound method* pelo protocolo de descritor.
        """
        if not text:
            return RuleResult(text=text)

        matches = list(self.pattern.finditer(text))
        if not matches:
            return RuleResult(text=text)

        novo_texto = self.pattern.sub(replacement, text)
        if novo_texto == text:
            return RuleResult(text=text)

        primeira = matches[0]
        amostra_antes = _sample(primeira.group(0))
        if callable(replacement):
            amostra_depois = _sample(replacement(primeira))
        else:
            amostra_depois = _sample(primeira.expand(replacement))

        return RuleResult(
            text=novo_texto,
            occurrences=(
                RuleOccurrence(
                    rule_id=self.rule_id,
                    count=len(matches),
                    before=amostra_antes,
                    after=amostra_depois,
                    severity=self.severity,
                    positions=tuple(match.start() for match in matches),
                ),
            ),
        )
