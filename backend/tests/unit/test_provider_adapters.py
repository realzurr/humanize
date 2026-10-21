"""Testes dos adaptadores de provedores (sem rede, via MockTransport)."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from app.services.providers.anthropic_provider import AnthropicProvider
from app.services.providers.base import (
    ChatMessage,
    LLMRequest,
    LLMResponse,
    ProviderError,
    ProviderErrorCode,
    ProviderId,
)
from app.services.providers.gemini_provider import GeminiProvider
from app.services.providers.ollama_provider import OllamaProvider
from app.services.providers.openai_compat import OpenAICompatibleProvider
from app.services.providers.openai_provider import OpenAIProvider


def _transporte(payload: dict[str, Any], status: int = 200) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json=payload, request=request)

    return httpx.MockTransport(handler)


def _transporte_captura(
    captura: list[httpx.Request], payload: dict[str, Any]
) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        captura.append(request)
        return httpx.Response(200, json=payload, request=request)

    return httpx.MockTransport(handler)


def _requisicao() -> LLMRequest:
    return LLMRequest(
        messages=(
            ChatMessage(role="system", content="Você é um revisor."),
            ChatMessage(role="user", content="Revise este texto."),
        ),
        model="gpt-4o",
        temperature=0.3,
        max_output_tokens=512,
    )


async def test_openai_generate() -> None:
    captura: list[httpx.Request] = []
    payload = {
        "model": "gpt-4o",
        "choices": [{"message": {"content": "texto revisado"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 4, "total_tokens": 14},
    }
    provider = OpenAIProvider(
        api_key="sk-teste-1234", transport=_transporte_captura(captura, payload)
    )
    resposta = await provider.generate(_requisicao())

    assert resposta.text == "texto revisado"
    assert resposta.provider is ProviderId.OPENAI
    assert resposta.usage.prompt_tokens == 10
    assert resposta.usage.completion_tokens == 4
    assert captura[0].url.path == "/v1/chat/completions"
    assert captura[0].headers["Authorization"] == "Bearer sk-teste-1234"


async def test_anthropic_generate_prompt_de_sistema_separado() -> None:
    captura: list[httpx.Request] = []
    payload = {
        "model": "claude-sonnet-4-5",
        "content": [{"type": "text", "text": "resposta"}],
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 12, "output_tokens": 3},
    }
    provider = AnthropicProvider(api_key="sk-ant", transport=_transporte_captura(captura, payload))
    resposta = await provider.generate(_requisicao())

    assert resposta.text == "resposta"
    corpo = captura[0].content  # bytes
    import json

    dados = json.loads(corpo)
    assert dados["system"] == "Você é um revisor."
    assert dados["max_tokens"] == 512
    assert all(m["role"] in {"user", "assistant"} for m in dados["messages"])


async def test_gemini_generate() -> None:
    payload = {
        "candidates": [
            {"content": {"parts": [{"text": "resposta gemini"}]}, "finishReason": "STOP"}
        ],
        "usageMetadata": {"promptTokenCount": 8, "candidatesTokenCount": 3, "totalTokenCount": 11},
    }
    provider = GeminiProvider(api_key="sk-gemini", transport=_transporte(payload))
    resposta = await provider.generate(_requisicao())
    assert resposta.text == "resposta gemini"
    assert resposta.provider is ProviderId.GEMINI


async def test_ollama_generate() -> None:
    payload = {
        "model": "llama3.1",
        "message": {"content": "resposta local"},
        "done": True,
        "prompt_eval_count": 20,
        "eval_count": 5,
    }
    provider = OllamaProvider(transport=_transporte(payload))
    resposta = await provider.generate(_requisicao())
    assert resposta.text == "resposta local"
    assert resposta.provider is ProviderId.OLLAMA
    assert resposta.usage.estimated_cost_usd == 0.0


async def test_openai_compatible_generate() -> None:
    captura: list[httpx.Request] = []
    payload = {"choices": [{"message": {"content": "resposta compat"}, "finish_reason": "stop"}]}
    provider = OpenAICompatibleProvider(
        api_key="sk-compat",
        base_url="http://localhost:1234/v1",
        declared_models=["llama-local"],
        transport=_transporte_captura(captura, payload),
    )
    resposta = await provider.generate(_requisicao())
    assert resposta.text == "resposta compat"
    assert str(captura[0].url).startswith("http://localhost:1234/v1/chat/completions")


async def test_mesma_requisicao_em_dois_provedores() -> None:
    """O mesmo LLMRequest roda em OpenAI e Ollama com contrato idêntico."""
    requisicao = _requisicao()

    openai = OpenAIProvider(
        api_key="sk-x",
        transport=_transporte(
            {"choices": [{"message": {"content": "resposta"}, "finish_reason": "stop"}]}
        ),
    )
    ollama = OllamaProvider(
        transport=_transporte(
            {
                "message": {"content": "resposta"},
                "done": True,
                "prompt_eval_count": 1,
                "eval_count": 1,
            }
        )
    )

    resultado_openai: LLMResponse = await openai.generate(requisicao)
    resultado_ollama: LLMResponse = await ollama.generate(requisicao)

    assert resultado_openai.text == "resposta"
    assert resultado_ollama.text == "resposta"
    assert resultado_openai.provider is ProviderId.OPENAI
    assert resultado_ollama.provider is ProviderId.OLLAMA
    assert isinstance(resultado_openai.usage.total_tokens, int)
    assert isinstance(resultado_ollama.usage.total_tokens, int)


async def test_erro_auth_nao_vaza_chave() -> None:
    provider = OpenAIProvider(
        api_key="sk-super-secreta",
        transport=_transporte({"error": {"message": "invalid api key"}}, status=401),
    )
    with pytest.raises(ProviderError) as exc_info:
        await provider.generate(_requisicao())
    assert exc_info.value.code is ProviderErrorCode.AUTH
    assert "sk-super-secreta" not in str(exc_info.value)
    assert "sk-super-secreta" not in exc_info.value.to_public_dict()["message"]


async def test_erro_modelo_nao_encontrado() -> None:
    provider = OpenAIProvider(
        api_key="sk-x",
        transport=_transporte({"error": {"message": "model not found"}}, status=404),
    )
    with pytest.raises(ProviderError) as exc_info:
        await provider.generate(_requisicao())
    assert exc_info.value.code is ProviderErrorCode.MODEL_NOT_FOUND


async def test_erro_rate_limit_e_retryable() -> None:
    provider = OpenAIProvider(
        api_key="sk-x",
        transport=_transporte({}, status=429),
    )
    with pytest.raises(ProviderError) as exc_info:
        await provider.generate(_requisicao())
    assert exc_info.value.code is ProviderErrorCode.RATE_LIMIT
    assert exc_info.value.retryable


async def test_check_credentials_sem_chave() -> None:
    provider = OpenAIProvider(transport=_transporte({}))
    resultado = await provider.check_credentials()
    assert not resultado.ok
    assert "não configurada" in resultado.message


async def test_check_credentials_com_chave() -> None:
    provider = OpenAIProvider(api_key="sk-x", transport=_transporte({}))
    resultado = await provider.check_credentials()
    assert resultado.ok
    assert resultado.models


async def test_ollama_check_credentials_sem_chave_exigida() -> None:
    provider = OllamaProvider(transport=_transporte({}))
    resultado = await provider.check_credentials()
    assert resultado.ok


async def test_list_models_estatico() -> None:
    provider = OpenAIProvider(api_key="sk-x", transport=_transporte({}))
    modelos = await provider.list_models()
    assert any(m.id == "gpt-4o" for m in modelos)


async def test_cancelamento_sem_requisicao_ativa() -> None:
    provider = OpenAIProvider(api_key="sk-x", transport=_transporte({}))
    assert await provider.cancel("inexistente") is False
