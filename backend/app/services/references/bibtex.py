"""Importação de referências em formato BibTeX.

Converte entradas BibTeX para o modelo interno :class:`Reference`. A
importação é *melhor esforço*: campos ausentes ficam vazios, nunca são
inventados.
"""

from __future__ import annotations

import bibtexparser

from app.services.references.models import Author, Reference, ReferenceType

#: Mapeamento de tipos BibTeX para o modelo interno.
_BIBTEX_TYPES: dict[str, ReferenceType] = {
    "article": ReferenceType.ARTICLE,
    "book": ReferenceType.BOOK,
    "inbook": ReferenceType.BOOK_SECTION,
    "incollection": ReferenceType.BOOK_SECTION,
    "inproceedings": ReferenceType.CONFERENCE,
    "conference": ReferenceType.CONFERENCE,
    "phdthesis": ReferenceType.THESIS,
    "mastersthesis": ReferenceType.DISSERTATION,
    "misc": ReferenceType.OTHER,
    "techreport": ReferenceType.REPORT,
    "online": ReferenceType.WEB,
    "www": ReferenceType.WEB,
}


def parse_bibtex(text: str) -> list[Reference]:
    """Converte um bloco BibTeX em referências internas."""
    try:
        biblioteca = bibtexparser.parse_string(text)  # type: ignore[attr-defined]
    except Exception:
        return []

    referencias: list[Reference] = []
    for indice, entrada in enumerate(biblioteca.entries, start=1):
        campos = {campo.key: campo.value for campo in entrada.fields}
        referencias.append(
            Reference(
                id=f"ref{indice:04d}",
                type=_BIBTEX_TYPES.get(entrada.entry_type.lower(), ReferenceType.OTHER),
                authors=tuple(_parse_authors(campos.get("author", ""))),
                title=campos.get("title", ""),
                year=campos.get("year", ""),
                container=campos.get("journal")
                or campos.get("booktitle")
                or campos.get("publisher", ""),
                volume=campos.get("volume", ""),
                issue=campos.get("number", ""),
                pages=campos.get("pages", ""),
                publisher=campos.get("publisher", ""),
                place=campos.get("address", ""),
                doi=campos.get("doi", ""),
                url=campos.get("url", ""),
                extra={chave: valor for chave, valor in campos.items() if valor},
            )
        )
    return referencias


def _parse_authors(author_field: str) -> list[Author]:
    """Converte ``Silva, R. A. and Souza, M.`` em autores."""
    if not author_field.strip():
        return []
    autores: list[Author] = []
    for nome in author_field.split(" and "):
        nome = nome.strip()
        if "," in nome:
            sobrenome, _, given = nome.partition(",")
            autores.append(Author(surname=sobrenome.strip(), given=given.strip()))
        else:
            autores.append(Author(surname=nome))
    return autores
