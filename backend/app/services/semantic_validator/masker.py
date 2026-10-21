"""Máscara e restauração de entidades protegidas.

Antes de qualquer chamada ao LLM, cada entidade protegida é substituída por um
placeholder **estável e não-natural** (``⟦P0001⟧``). O modelo nunca vê o valor
real — apenas o placeholder, que deve reproduzir verbatim. Após a resposta, a
restauração devolve o valor **original** (nunca o do modelo) para cada
placeholder que sobreviveu.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.ir.protection import ProtectedEntity, ProtectionCatalog


def placeholder(entity: ProtectedEntity) -> str:
    """Placeholder estável de uma entidade."""
    return f"⟦{entity.id}⟧"


@dataclass(frozen=True, slots=True)
class MaskedText:
    """Texto mascarado e o mapeamento placeholder -> entidade."""

    text: str
    """Texto com os placeholders no lugar das entidades."""

    mapping: dict[str, ProtectedEntity]
    """Placeholder (ex.: ``⟦P0001⟧``) -> entidade protegida."""


def mask(text: str, catalog: ProtectionCatalog) -> MaskedText:
    """Substitui as entidades protegidas por placeholders.

    A substituição é feita do fim para o início, para que os offsets não se
    desloquem ao longo da operação.
    """
    mapeamento: dict[str, ProtectedEntity] = {}
    resultado = text
    # Entidades ordenadas por posição decrescente para substituir de trás
    # para frente sem invalidar os offsets.
    for entidade in sorted(
        catalog.iter_entities(), key=lambda e: e.source_range.start, reverse=True
    ):
        token = placeholder(entidade)
        mapeamento[token] = entidade
        resultado = (
            resultado[: entidade.source_range.start]
            + token
            + resultado[entidade.source_range.end :]
        )
    return MaskedText(text=resultado, mapping=mapeamento)


def unmask(text: str, masked: MaskedText) -> str:
    """Restaura os placeholders com os valores originais.

    Placeholders que o modelo não reproduziu permanecem ausentes — a perda é
    detectada depois pelo validador, não aqui.
    """
    resultado = text
    for token, entidade in masked.mapping.items():
        resultado = resultado.replace(token, entidade.text)
    return resultado


def placeholders_reproduzidos(text: str, masked: MaskedText) -> set[str]:
    """Devolve os placeholders que o modelo reproduziu no texto revisado."""
    return {token for token in masked.mapping if token in text}
