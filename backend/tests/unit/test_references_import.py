"""Testes da importação BibTeX e CSL-JSON."""

from __future__ import annotations

from app.services.references.bibtex import parse_bibtex
from app.services.references.csl_json import parse_csl_json
from app.services.references.models import ReferenceType


def test_parse_bibtex_artigo() -> None:
    bibtex = (
        "@article{key2020,\n"
        "  author = {Silva, R. A. and Souza, M.},\n"
        "  title = {Titulo do artigo},\n"
        "  journal = {Revista X},\n"
        "  year = {2020},\n"
        "  doi = {10.1111/abc.123}\n"
        "}"
    )
    refs = parse_bibtex(bibtex)
    assert len(refs) == 1
    assert refs[0].type is ReferenceType.ARTICLE
    assert refs[0].authors[0].surname == "Silva"
    assert refs[0].doi == "10.1111/abc.123"


def test_parse_bibtex_invalido() -> None:
    assert parse_bibtex("não é bibtex") == []


def test_parse_bibtex_tese() -> None:
    bibtex = "@phdthesis{tese, author={Silva, R.}, title={Tese}, year={2020}}"
    refs = parse_bibtex(bibtex)
    assert refs[0].type is ReferenceType.THESIS


def test_parse_csl_json_artigo() -> None:
    csl = [
        {
            "type": "article-journal",
            "title": "Titulo",
            "author": [{"family": "Silva", "given": "R. A."}],
            "issued": {"date-parts": [[2020]]},
            "container-title": "Revista X",
            "DOI": "10.1111/abc.123",
        }
    ]
    refs = parse_csl_json(csl)
    assert len(refs) == 1
    assert refs[0].year == "2020"
    assert refs[0].doi == "10.1111/abc.123"
    assert refs[0].authors[0].surname == "Silva"


def test_parse_csl_json_item_unico() -> None:
    refs = parse_csl_json({"type": "book", "title": "Livro", "issued": {"date-parts": [[2019]]}})
    assert len(refs) == 1
    assert refs[0].type is ReferenceType.BOOK
