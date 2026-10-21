"""Testes da extração de referências."""

from __future__ import annotations

from app.services.references.models import ReferenceType
from app.services.references.parser import (
    find_references_block,
    parse_entry,
    parse_references,
)


def test_parse_artigo() -> None:
    texto = (
        "SILVA, R. A. Acidification and crop productivity. Journal of Soil "
        "Science, São Paulo, v. 10, n. 2, p. 45-60, 2020. DOI: 10.1111/jss.12845."
    )
    ref = parse_entry(texto)
    assert ref.type is ReferenceType.ARTICLE
    assert ref.authors[0].surname == "SILVA"
    assert ref.title == "Acidification and crop productivity"
    assert ref.container == "Journal of Soil Science"
    assert ref.year == "2020"
    assert ref.volume == "10"
    assert ref.pages == "45-60"
    assert ref.doi == "10.1111/jss.12845"


def test_parse_livro() -> None:
    texto = (
        "FREITAS, L. C. Nutrição em solos tropicais. 2. ed. São Paulo: Editora Agronômica, 2019."
    )
    ref = parse_entry(texto)
    assert ref.type is ReferenceType.BOOK
    assert ref.place == "São Paulo"
    assert ref.publisher == "Editora Agronômica"
    assert ref.year == "2019"


def test_parse_referencias_multiplas() -> None:
    texto = (
        "## REFERÊNCIAS\n\n"
        "SILVA, R. A. Título um. Revista, 2020.\n\n"
        "SOUZA, M. Título dois. Revista, 2021.\n"
    )
    refs = parse_references(texto)
    assert len(refs) == 2
    assert refs[0].first_surname == "SILVA"
    assert refs[1].first_surname == "SOUZA"


def test_parse_referencias_registra_localizacao() -> None:
    texto = "Texto antes.\n\n## REFERÊNCIAS\n\nSILVA, R. A. Título um. Revista, 2020.\n"
    refs = parse_references(texto)
    assert refs[0].source_range is not None
    assert refs[0].source_range.start > 0


def test_find_references_block_sem_cabecalho() -> None:
    assert find_references_block("SILVA, R. A. Título. 2020.") == "SILVA, R. A. Título. 2020."


def test_parse_sem_autor_nao_gera_referencia() -> None:
    assert parse_references("Texto comum sem referência.") == []


def test_parse_web() -> None:
    texto = (
        "IBGE. Censo. Rio de Janeiro: IBGE, 2022. "
        "Disponível em: https://www.ibge.gov.br. Acesso em: 10 out. 2024."
    )
    ref = parse_entry(texto)
    assert ref.type is ReferenceType.WEB
    assert ref.url == "https://www.ibge.gov.br"
