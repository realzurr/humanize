"""Testes do catálogo de modelos e da estimativa de tokens/custo."""

from __future__ import annotations

from app.services.providers.base import ChatMessage, ProviderId
from app.services.providers.catalog import (
    anthropic_models,
    gemini_models,
    ollama_models,
    openai_compatible_models,
    openai_models,
)
from app.services.providers.usage import compute_cost, estimate_prompt_tokens, estimate_tokens


def test_estimate_tokens_heuristica() -> None:
    assert estimate_tokens("") == 0
    assert estimate_tokens("abcd") == 1
    assert estimate_tokens("a" * 40) == 10


def test_estimate_prompt_tokens_soma_mensagens() -> None:
    mensagens = [ChatMessage(role="user", content="a" * 400)]
    total = estimate_prompt_tokens(mensagens)
    assert total > 100  # 400/4 = 100 + sobrecarga


def test_compute_cost_sem_modelo_e_zero() -> None:
    assert compute_cost(1000, 1000, None) == 0.0


def test_compute_cost_com_precos() -> None:
    modelo = openai_models()[0]  # gpt-4.1
    custo = compute_cost(1000, 1000, modelo)
    assert custo == round(0.002 + 0.008, 6)


def test_catalogo_openai_tem_modelos() -> None:
    ids = [m.id for m in openai_models()]
    assert "gpt-4o" in ids
    assert all(m.provider is ProviderId.OPENAI for m in openai_models())


def test_catalogo_ollama_sem_custo() -> None:
    assert all(m.input_cost_per_1k is None for m in ollama_models())


def test_catalogo_anthropic_e_gemini_nao_vazios() -> None:
    assert anthropic_models()
    assert gemini_models()


def test_catalogo_openai_compatible_usa_declarados() -> None:
    modelos = openai_compatible_models(["llama-local", "mistral-local"])
    assert [m.id for m in modelos] == ["llama-local", "mistral-local"]
    assert not openai_compatible_models(None)
