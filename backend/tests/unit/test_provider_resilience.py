"""Testes de resiliência (timeout, retry, backoff, Retry-After, mapeamento)."""

from __future__ import annotations

import asyncio

import pytest

from app.services.providers.base import ProviderError, ProviderErrorCode
from app.services.providers.resilience import (
    RetryPolicy,
    call_with_retry,
    map_http_error,
)


def test_delay_for_respeita_retry_after() -> None:
    policy = RetryPolicy()
    assert policy.delay_for(0, 5.0) == 5.0


def test_delay_for_cresce_exponencialmente() -> None:
    policy = RetryPolicy(base_delay_seconds=1.0, jitter=0.0)
    assert policy.delay_for(0, None) == 1.0
    assert policy.delay_for(1, None) == 2.0
    assert policy.delay_for(2, None) == 4.0


def test_delay_for_limita_ao_maximo() -> None:
    policy = RetryPolicy(max_delay_seconds=10.0, jitter=0.0)
    assert policy.delay_for(10, None) == 10.0


async def test_retry_sucesso_na_primeira_tentativa() -> None:
    chamadas = 0

    async def operacao() -> str:
        nonlocal chamadas
        chamadas += 1
        return "ok"

    resultado = await call_with_retry(operacao, RetryPolicy())
    assert resultado == "ok"
    assert chamadas == 1


async def test_retry_repeticao_de_erro_recuperavel() -> None:
    chamadas = 0

    async def operacao() -> str:
        nonlocal chamadas
        chamadas += 1
        if chamadas < 3:
            raise ProviderError(ProviderErrorCode.SERVER_ERROR, "erro", retryable=True)
        return "ok"

    resultado = await call_with_retry(operacao, RetryPolicy(base_delay_seconds=0.0, jitter=0.0))
    assert resultado == "ok"
    assert chamadas == 3


async def test_retry_nao_repete_erro_nao_recuperavel() -> None:
    chamadas = 0

    async def operacao() -> str:
        nonlocal chamadas
        chamadas += 1
        raise ProviderError(ProviderErrorCode.AUTH, "chave inválida", retryable=False)

    with pytest.raises(ProviderError) as exc_info:
        await call_with_retry(operacao, RetryPolicy())
    assert exc_info.value.code is ProviderErrorCode.AUTH
    assert chamadas == 1


async def test_retry_respeita_limite_de_tentativas() -> None:
    chamadas = 0

    async def operacao() -> str:
        nonlocal chamadas
        chamadas += 1
        raise ProviderError(ProviderErrorCode.RATE_LIMIT, "limite", retryable=True)

    with pytest.raises(ProviderError):
        await call_with_retry(
            operacao, RetryPolicy(max_retries=2, base_delay_seconds=0.0, jitter=0.0)
        )
    assert chamadas == 3  # 1 tentativa + 2 retries


async def test_retry_timeout_vira_provider_error() -> None:
    async def operacao() -> str:
        await asyncio.sleep(0.2)
        return "ok"

    with pytest.raises(ProviderError) as exc_info:
        await call_with_retry(operacao, RetryPolicy(timeout_seconds=0.01, max_retries=0))
    assert exc_info.value.code is ProviderErrorCode.TIMEOUT


def test_map_http_error_auth() -> None:
    erro = map_http_error(401, '{"error": {"message": "bad key"}}', "openai")
    assert erro is not None and erro.code is ProviderErrorCode.AUTH
    assert not erro.retryable


def test_map_http_error_rate_limit_com_retry_after() -> None:
    erro = map_http_error(429, "{}", "openai", {"Retry-After": "3"})
    assert erro is not None and erro.code is ProviderErrorCode.RATE_LIMIT
    assert erro.retryable
    assert erro.retry_after_seconds == 3.0


def test_map_http_error_modelo_nao_encontrado() -> None:
    erro = map_http_error(404, '{"error": {"message": "model not found"}}', "openai")
    assert erro is not None and erro.code is ProviderErrorCode.MODEL_NOT_FOUND


def test_map_http_error_sem_erro() -> None:
    assert map_http_error(200, "{}", "openai") is None


def test_map_http_error_extrai_mensagem() -> None:
    erro = map_http_error(500, '{"error": {"message": "internal"}}', "openai")
    assert erro is not None and "internal" in str(erro)


def test_map_http_error_quota() -> None:
    erro = map_http_error(402, '{"error": {"message": "quota"}}', "openai")
    assert erro is not None and erro.code is ProviderErrorCode.QUOTA


def test_map_http_error_timeout_gateway() -> None:
    erro = map_http_error(504, "{}", "openai")
    assert erro is not None and erro.code is ProviderErrorCode.TIMEOUT
    assert erro.retryable


def test_map_http_error_filtro_de_conteudo() -> None:
    erro = map_http_error(400, '{"error": {"message": "content filter triggered"}}', "openai")
    assert erro is not None and erro.code is ProviderErrorCode.CONTENT_FILTER


def test_map_http_error_server() -> None:
    erro = map_http_error(503, "{}", "openai")
    assert erro is not None and erro.code is ProviderErrorCode.SERVER_ERROR


def test_map_http_error_desconhecido() -> None:
    erro = map_http_error(418, "{}", "openai")
    assert erro is not None and erro.code is ProviderErrorCode.UNKNOWN


def test_map_http_error_nao_vaza_corpo_completo() -> None:
    corpo = '{"error": {"message": "' + "x" * 500 + '"}}'
    erro = map_http_error(500, corpo, "openai")
    assert erro is not None and len(str(erro)) < 400


def test_parse_retry_after_data_http() -> None:
    from app.services.providers.resilience import _parse_retry_after

    futuro = "Wed, 21 Oct 2099 00:00:00 GMT"
    resultado = _parse_retry_after({"Retry-After": futuro})
    assert resultado is not None and resultado > 0.0


def test_parse_retry_after_invalido() -> None:
    from app.services.providers.resilience import _parse_retry_after

    assert _parse_retry_after({"Retry-After": "abc"}) is None
    assert _parse_retry_after(None) is None
