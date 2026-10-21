"""Importação de referências em formato CSL-JSON.

Converte itens CSL-JSON (usados por Zotero, Mendeley e outros gerenciadores)
para o modelo interno :class:`Reference`. A importação é *melhor esforço*.
"""

from __future__ import annotations

from typing import Any

from app.services.references.models import Author, Reference, ReferenceType

#: Mapeamento de tipos CSL para o modelo interno.
_CSL_TYPES: dict[str, ReferenceType] = {
    "article-journal": ReferenceType.ARTICLE,
    "article": ReferenceType.ARTICLE,
    "book": ReferenceType.BOOK,
    "chapter": ReferenceType.BOOK_SECTION,
    "paper-conference": ReferenceType.CONFERENCE,
    "thesis": ReferenceType.THESIS,
    "report": ReferenceType.REPORT,
    "webpage": ReferenceType.WEB,
}


def parse_csl_json(data: Any) -> list[Reference]:
    """Converte CSL-JSON (lista de itens ou item único) em referências."""
    itens = data if isinstance(data, list) else [data]
    referencias: list[Reference] = []
    for indice, item in enumerate(itens, start=1):
        if not isinstance(item, dict):
            continue
        referencias.append(_converter(item, indice))
    return referencias


def _converter(item: dict[str, Any], indice: int) -> Reference:
    tipo = _CSL_TYPES.get(str(item.get("type", "")), ReferenceType.OTHER)

    autores: list[Author] = []
    for autor in item.get("author", []) or []:
        if isinstance(autor, dict):
            family = str(autor.get("family", "") or autor.get("literal", "") or "")
            given = str(autor.get("given", "") or "")
            autores.append(Author(surname=family, given=given))

    titulo = str(item.get("title", "") or "")
    ano = _ano(item)

    return Reference(
        id=f"ref{indice:04d}",
        type=tipo,
        authors=tuple(autores),
        title=titulo,
        year=ano,
        container=_container(item),
        volume=str(item.get("volume", "") or ""),
        issue=str(item.get("issue", "") or ""),
        pages=str(item.get("page", "") or ""),
        publisher=str(item.get("publisher", "") or ""),
        place=str(item.get("publisher-place", "") or ""),
        doi=str(item.get("DOI", "") or ""),
        url=str(item.get("URL", "") or ""),
        accessed_at=_acessado(item),
    )


def _ano(item: dict[str, Any]) -> str:
    issued = item.get("issued") or {}
    if isinstance(issued, dict):
        partes = issued.get("date-parts") or []
        if partes and isinstance(partes[0], list) and partes[0]:
            return str(partes[0][0])
    return ""


def _container(item: dict[str, Any]) -> str:
    container = item.get("container-title") or ""
    if isinstance(container, list):
        return str(container[0]) if container else ""
    return str(container or "")


def _acessado(item: dict[str, Any]) -> str:
    accessed = item.get("accessed") or {}
    if isinstance(accessed, dict):
        partes = accessed.get("date-parts") or []
        if partes and isinstance(partes[0], list):
            return "-".join(str(p) for p in partes[0])
    return ""
