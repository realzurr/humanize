"""Testes de intensidade."""

from __future__ import annotations

import pytest

from app.services.humanizer.intensity import (
    VALID_INTENSITIES,
    Intensity,
    altera_algo,
    instruction,
    validate,
)


def test_valores_validos() -> None:
    assert {0, 25, 50, 75, 100} == VALID_INTENSITIES
    assert validate(0) is Intensity.NENHUMA
    assert validate(50) is Intensity.MODERADA
    assert validate(100) is Intensity.MAXIMA


def test_valor_invalido_levanta_erro() -> None:
    with pytest.raises(ValueError):
        validate(30)


def test_intensidade_zero_nao_altera() -> None:
    assert not altera_algo(Intensity.NENHUMA)
    assert altera_algo(Intensity.MODERADA)


def test_instrucao_distinta_por_nivel() -> None:
    instrucoes = {instruction(Intensity(i)) for i in (25, 50, 75, 100)}
    assert len(instrucoes) == 4
    assert "Não altere" in instruction(Intensity.NENHUMA)
