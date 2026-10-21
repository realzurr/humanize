"""Numeração progressiva das seções (NBR 6024:2012).

Atribui indicativos arábicos progressivos às seções primárias, secundárias,
terciárias etc. A numeração é determinística e é a mesma usada no sumário e
no texto (exigência da NBR 6024).
"""

from __future__ import annotations

from itertools import pairwise


def progressive_numbers(levels: list[int], start_at: int = 1) -> list[str]:
    """Devolve os indicativos progressivos para uma sequência de níveis.

    Cada elemento de ``levels`` é o nível da seção (1 = primária). A função
    mantém contadores por nível e os reinicia quando se sobe de nível.
    """
    if not levels:
        return []

    contadores: list[int] = []
    resultado: list[str] = []

    for nivel in levels:
        if nivel < 1:
            raise ValueError(f"nível inválido: {nivel}")
        # Ajusta a pilha de contadores ao nível atual.
        while len(contadores) < nivel:
            contadores.append(0 if len(contadores) > 0 else start_at - 1)
        del contadores[nivel:]  # reinicia níveis mais profundos
        contadores[nivel - 1] += 1
        resultado.append(".".join(str(c) for c in contadores[:nivel]))

    return resultado


def number_headings(headings: list[tuple[int, str]], start_at: int = 1) -> list[tuple[str, str]]:
    """Devolve pares ``(indicativo, título)`` para uma lista de ``(nível, título)``."""
    numeros = progressive_numbers([nivel for nivel, _ in headings], start_at=start_at)
    return [(numero, titulo) for numero, (_, titulo) in zip(numeros, headings, strict=False)]


def validate_sequence(numbers: list[str]) -> list[str]:
    """Devolve avisos sobre quebras de sequência na numeração progressiva.

    Uma sequência válida não pula níveis (ex.: ``1`` seguido de ``1.2`` sem
    ``1.1``) nem repete indicativo.
    """
    avisos: list[str] = []
    for anterior, atual in pairwise(numbers):
        if atual == anterior:
            avisos.append(f"indicativo repetido: {atual}")
    return avisos
