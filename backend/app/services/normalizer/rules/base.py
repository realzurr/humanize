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
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict


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

    #: Se a regra pode ser desligada pelo usuário.
    configurable: bool = True

    #: Padrão de ativação.
    enabled_by_default: bool = True

    #: Se a regra pode alterar/remover trechos protegidos. Deve ser ``False``
    #: para qualquer regra que possa tocar em números, fórmulas ou citações.
    touches_protected_content: bool = False

    @abc.abstractmethod
    def apply(self, text: str) -> RuleResult:
        """Aplica a regra ao texto recebido."""

    def describe(self) -> dict[str, Any]:
        """Descrição serializável da regra (usada na API de configuração)."""
        return {
            "rule_id": self.rule_id,
            "description": self.description,
            "category": self.category,
            "configurable": self.configurable,
            "enabled_by_default": self.enabled_by_default,
            "touches_protected_content": self.touches_protected_content,
        }
