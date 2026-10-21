"""Estilos tipográficos de títulos e blocos.

Mapeia níveis de título e tipos de bloco para os estilos declarados no
template. Os estilos são parametrizados no YAML; este módulo apenas os
resolve com padrões seguros quando o template não declara um estilo.
"""

from __future__ import annotations

from app.services.academic.template_model import Estilo

#: Nome do estilo por nível de título (1..3).
_ESTILO_POR_NIVEL = {1: "heading1", 2: "heading2", 3: "heading3"}

#: Nome do estilo por tipo de bloco especial.
_ESTILO_POR_TIPO = {
    "citacao_longa": "citacao_longa",
    "legenda": "legenda",
    "fonte": "fonte",
    "referencia": "referencia",
    "nota_rodape": "nota_rodape",
    "sem_indicativo": "sem_indicativo",
}

_PADRAO = Estilo()


def style_for_level(styles: dict[str, Estilo], level: int) -> Estilo:
    """Devolve o estilo do título de um nível (1, 2, 3...)."""
    nome = _ESTILO_POR_NIVEL.get(level)
    if nome is None:
        return _PADRAO
    return styles.get(nome, _PADRAO)


def style_for_kind(styles: dict[str, Estilo], kind: str) -> Estilo:
    """Devolve o estilo de um tipo de bloco especial (citação, legenda...)."""
    nome = _ESTILO_POR_TIPO.get(kind, kind)
    return styles.get(nome, _PADRAO)


def available_styles(styles: dict[str, Estilo]) -> tuple[str, ...]:
    """Devolve os nomes dos estilos declarados no template."""
    return tuple(sorted(styles))
