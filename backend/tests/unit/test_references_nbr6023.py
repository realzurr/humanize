"""Testes da formatação NBR 6023."""

from __future__ import annotations

from app.services.references.models import Author, Reference, ReferenceType
from app.services.references.nbr6023 import format_authors, format_reference


def test_format_um_autor() -> None:
    autores = (Author(surname="Silva", given="R. A."),)
    assert format_authors(autores) == "SILVA, R. A"


def test_format_tres_autores() -> None:
    autores = (
        Author(surname="Silva", given="R. A."),
        Author(surname="Souza", given="M."),
        Author(surname="Pereira", given="D. F."),
    )
    assert format_authors(autores) == "SILVA, R. A; SOUZA, M; PEREIRA, D. F"


def test_format_quatro_autores_et_al() -> None:
    autores = tuple(Author(surname=s, given="X.") for s in ("A", "B", "C", "D"))
    assert format_authors(autores).endswith("et al.")


def test_format_artigo() -> None:
    ref = Reference(
        id="r1",
        type=ReferenceType.ARTICLE,
        authors=(Author(surname="SILVA", given="R. A."),),
        title="Título do artigo",
        year="2020",
        container="Revista X",
        volume="10",
        pages="45-60",
        doi="10.1111/abc.123",
    )
    resultado = format_reference(ref)
    assert resultado.startswith("SILVA, R. A. Título do artigo.")
    assert "DOI: 10.1111/abc.123" in resultado


def test_format_livro() -> None:
    ref = Reference(
        id="r1",
        type=ReferenceType.BOOK,
        authors=(Author(surname="Freitas", given="L. C."),),
        title="Nutrição em solos",
        year="2019",
        place="São Paulo",
        publisher="Editora Agronômica",
    )
    assert "São Paulo: Editora Agronômica" in format_reference(ref)


def test_format_tese() -> None:
    ref = Reference(
        id="r1",
        type=ReferenceType.THESIS,
        authors=(Author(surname="Silva", given="R."),),
        title="Uma tese",
        year="2020",
        place="Campo Grande",
    )
    resultado = format_reference(ref)
    assert "Tese (Doutorado)" in resultado


def test_format_web() -> None:
    ref = Reference(
        id="r1",
        type=ReferenceType.WEB,
        authors=(Author(surname="IBGE", organization=True),),
        title="Censo",
        year="2022",
        url="https://www.ibge.gov.br",
        accessed_at="10 out. 2024",
    )
    resultado = format_reference(ref)
    assert "Disponível em: https://www.ibge.gov.br" in resultado


def test_format_organizacao() -> None:
    assert format_authors((Author(surname="IBGE", organization=True),)) == "IBGE"
