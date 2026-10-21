"""Formatação de referências conforme a ABNT NBR 6023:2025.

Reproduz a **estrutura** e as regras públicas (ordem dos elementos, caixa
alta no sobrenome, pontuação), nunca o texto integral da norma (ver
`ADR-0015`). A Emenda de 05/2025 ainda não foi lida (pendência P-07), então a
regra de ``et al.`` e detalhes de pontuação são marcados como `medium`.
"""

from __future__ import annotations

from app.services.references.models import Author, Reference, ReferenceType


def format_authors(authors: tuple[Author, ...]) -> str:
    """Formata os autores no padrão ``SOBRENOME, Nome`` separados por ``;``.

    Com mais de três autores, lista o primeiro seguido de ``et al.``.
    """
    if not authors:
        return ""
    if len(authors) <= 3:
        return "; ".join(_ordem_de_catalogacao(a) for a in authors)
    return f"{_ordem_de_catalogacao(authors[0])} et al."


def _ordem_de_catalogacao(author: Author) -> str:
    if author.organization:
        return author.surname.upper()
    sobrenome = author.surname.upper() if not author.surname.isupper() else author.surname
    given = author.given.rstrip(".")
    return f"{sobrenome}, {given}".strip() if given else sobrenome


def format_reference(reference: Reference) -> str:
    """Formata uma referência no estilo NBR 6023:2025."""
    autores = format_authors(reference.authors)
    if reference.type is ReferenceType.ARTICLE:
        return _formato_artigo(reference, autores)
    if reference.type in (ReferenceType.THESIS, ReferenceType.DISSERTATION):
        return _formato_tese(reference, autores)
    if reference.type is ReferenceType.WEB:
        return _formato_web(reference, autores)
    return _formato_livro(reference, autores)


def _formato_artigo(reference: Reference, autores: str) -> str:
    partes = [autores]
    if reference.title:
        partes.append(reference.title)
    if reference.container:
        partes.append(reference.container)
    dados: list[str] = []
    if reference.place:
        dados.append(reference.place)
    if reference.volume:
        dados.append(f"v. {reference.volume}")
    if reference.issue:
        dados.append(f"n. {reference.issue}")
    if reference.pages:
        dados.append(f"p. {reference.pages}")
    if reference.year:
        dados.append(reference.year)
    if dados:
        partes.append(", ".join(dados))
    if reference.doi:
        partes.append(f"DOI: {reference.doi}")
    elif reference.url:
        partes.append(f"Disponível em: {reference.url}")
    return ". ".join(p for p in partes if p).rstrip(".") + "."


def _formato_livro(reference: Reference, autores: str) -> str:
    partes = [autores]
    if reference.title:
        partes.append(reference.title)
    local_editora = []
    if reference.place:
        local_editora.append(reference.place)
    if reference.publisher:
        local_editora.append(reference.publisher)
    if local_editora:
        partes.append(": ".join(local_editora))
    if reference.year:
        partes.append(reference.year)
    return ". ".join(p for p in partes if p).rstrip(".") + "."


def _formato_tese(reference: Reference, autores: str) -> str:
    natureza = (
        "Tese (Doutorado)" if reference.type is ReferenceType.THESIS else "Dissertação (Mestrado)"
    )
    local = f" — {reference.place}" if reference.place else ""
    partes = [
        autores,
        reference.title or "",
        f"{natureza}{local}",
        reference.year or "",
    ]
    return ". ".join(p for p in partes if p).rstrip(".") + "."


def _formato_web(reference: Reference, autores: str) -> str:
    partes = [autores]
    if reference.title:
        partes.append(reference.title)
    if reference.year:
        partes.append(reference.year)
    if reference.url:
        partes.append(f"Disponível em: {reference.url}")
    if reference.accessed_at:
        partes.append(f"Acesso em: {reference.accessed_at}")
    return ". ".join(p for p in partes if p).rstrip(".") + "."
