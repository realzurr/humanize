"""Intensidade da humanização.

A intensidade (0/25/50/75/100) é um **parâmetro de orientação** enviado ao
modelo, e não um percentual garantido de alteração. A intensidade 0 não altera
nada; 100 pede reescrita profunda **sem** alterar as entidades protegidas
(que, de todo modo, são mascaradas antes da chamada).
"""

from __future__ import annotations

from enum import IntEnum


class Intensity(IntEnum):
    """Níveis de intensidade da humanização."""

    NENHUMA = 0
    LEVE = 25
    MODERADA = 50
    FORTE = 75
    MAXIMA = 100


#: Intensidades aceitas pela API.
VALID_INTENSITIES: frozenset[int] = frozenset({0, 25, 50, 75, 100})


def validate(value: int) -> Intensity:
    """Valida e converte o valor para o enum de intensidade."""
    try:
        return Intensity(value)
    except ValueError as exc:
        raise ValueError(f"intensidade inválida: {value} (use 0, 25, 50, 75 ou 100)") from exc


def instruction(intensity: Intensity) -> str:
    """Devolve a orientação textual correspondente à intensidade."""
    if intensity is Intensity.NENHUMA:
        return "Não altere o texto."
    if intensity is Intensity.LEVE:
        return "Faça apenas ajustes leves de clareza e fluência."
    if intensity is Intensity.MODERADA:
        return "Reescreva moderadamente, melhorando clareza, coesão e estilo."
    if intensity is Intensity.FORTE:
        return "Reescreva de forma abrangente, reorganizando frases e parágrafos."
    return (
        "Reescreva profundamente o texto, mantendo rigorosamente o significado, "
        "os dados e as citações."
    )


def altera_algo(intensity: Intensity) -> bool:
    """Indica se a intensidade produz qualquer alteração."""
    return intensity is not Intensity.NENHUMA
