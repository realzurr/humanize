"""Testes dos modelos de referência."""

from __future__ import annotations

from app.services.references.models import Author, Reference, ReferenceType


def test_author_sort_name() -> None:
    autor = Author(surname="Silva", given="R. A.")
    assert autor.sort_name == "Silva, R. A."


def test_author_full_name() -> None:
    autor = Author(surname="Silva", given="R. A.")
    assert autor.full_name == "R. A. Silva"


def test_author_organizacao() -> None:
    autor = Author(surname="IBGE", organization=True)
    assert autor.sort_name == "IBGE"


def test_reference_first_surname() -> None:
    ref = Reference(id="r1", authors=(Author(surname="Silva", given="R."),))
    assert ref.first_surname == "Silva"


def test_reference_sem_autor() -> None:
    assert Reference(id="r1").first_surname == ""
    assert Reference(id="r1").type is ReferenceType.OTHER
