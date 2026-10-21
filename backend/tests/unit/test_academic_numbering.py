"""Testes da numeração progressiva (NBR 6024)."""

from __future__ import annotations

from app.services.academic.numbering import (
    number_headings,
    progressive_numbers,
    validate_sequence,
)


def test_numeracao_simples() -> None:
    assert progressive_numbers([1, 1, 1]) == ["1", "2", "3"]


def test_numeracao_aninhada() -> None:
    assert progressive_numbers([1, 2, 2, 1, 2, 3]) == [
        "1",
        "1.1",
        "1.2",
        "2",
        "2.1",
        "2.1.1",
    ]


def test_numeracao_reinicia_niveis() -> None:
    # 1, 1.1, 2, 2.1 (o nível 2 reinicia ao subir para o nível 1).
    assert progressive_numbers([1, 2, 1, 2]) == ["1", "1.1", "2", "2.1"]


def test_numeracao_nivel_invalido() -> None:
    import pytest

    with pytest.raises(ValueError):
        progressive_numbers([0])


def test_numeracao_vazia() -> None:
    assert progressive_numbers([]) == []


def test_number_headings_combina_indicativo_e_titulo() -> None:
    resultado = number_headings([(1, "Introdução"), (2, "Objetivos")])
    assert resultado == [("1", "Introdução"), ("1.1", "Objetivos")]


def test_validate_sequence_detecta_repeticao() -> None:
    assert validate_sequence(["1", "1", "2"]) == ["indicativo repetido: 1"]
    assert validate_sequence(["1", "2", "3"]) == []
