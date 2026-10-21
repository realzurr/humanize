"""Extração de entidades protegidas para a humanização.

Reutiliza o extrator determinístico da normalização
(:mod:`app.services.normalizer.protect`), que identifica números, datas,
citações, referências, DOIs, URLs, fórmulas, unidades, estatísticas, citações
literais, código, tabelas, termos definidos e identificadores de tabela/figura.
"""

from __future__ import annotations

from app.ir.protection import ProtectionCatalog
from app.services.normalizer.protect import build_catalog


def extract(text: str) -> ProtectionCatalog:
    """Extrai o catálogo de entidades protegidas do texto."""
    return build_catalog(text)
