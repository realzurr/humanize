"""Estimativa de tokens e custo.

O sistema **não** cobra nada e, sem um tokenizador dedicado (``tiktoken``,
``sentencepiece``), a contagem é uma heurística: aproximadamente quatro
caracteres por token para o português e o inglês. O custo é calculado a
partir da tabela local de preços (:mod:`app.services.providers.catalog`) e
serve apenas para **estimativa** exibida ao usuário.

Quando o provedor devolve a contagem real de tokens na resposta (OpenAI,
Anthropic e Gemini fazem isso), ela tem precedência sobre a heurística.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from app.services.providers.base import ChatMessage, ModelInfo

#: Caracteres aproximados por token (heurística sem tokenizador).
CHARS_PER_TOKEN = 4.0

#: Sobrecarga fixa de prompt, para não subestimar o custo de entrada.
PROMPT_OVERHEAD_TOKENS = 16


def estimate_tokens(text: str) -> int:
    """Estima a quantidade de tokens de um texto pela heurística char/4."""
    if not text:
        return 0
    return max(1, math.ceil(len(text) / CHARS_PER_TOKEN))


def estimate_prompt_tokens(messages: Sequence[ChatMessage]) -> int:
    """Estima os tokens do prompt a partir das mensagens."""
    if not messages:
        return PROMPT_OVERHEAD_TOKENS
    total = PROMPT_OVERHEAD_TOKENS
    for mensagem in messages:
        total += estimate_tokens(mensagem.content) + 4  # sobrecarga por mensagem
    return total


def compute_cost(
    input_tokens: int,
    output_tokens: int,
    model: ModelInfo | None,
) -> float:
    """Estima o custo em USD a partir da tabela de preços do modelo."""
    if model is None:
        return 0.0
    custo_entrada = (model.input_cost_per_1k or 0.0) * input_tokens / 1000.0
    custo_saida = (model.output_cost_per_1k or 0.0) * output_tokens / 1000.0
    return round(custo_entrada + custo_saida, 6)
