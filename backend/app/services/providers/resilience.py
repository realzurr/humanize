"""Resiliência de chamadas a provedores de LLM.

Centraliza o timeout, o retry com *backoff* exponencial + jitter e o respeito
ao cabeçalho ``Retry-After``. A política é conservadora: só se repete um erro
que possa ser resolvido por uma nova tentativa (rede, timeout, rate limit,
5xx) e nunca mais que ``max_retries`` vezes.

Também mora aqui o mapeamento de respostas HTTP de erro para
:class:`ProviderError`, de modo que os adaptadores nunca precisam interpretar
o formato de erro específico de cada fornecedor.
"""

from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable, Mapping
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any

from app.services.providers.base import ProviderError, ProviderErrorCode, ProviderId


class RetryPolicy:
    """Política de retry e timeout de um provedor."""

    def __init__(
        self,
        *,
        max_retries: int = 3,
        base_delay_seconds: float = 1.0,
        max_delay_seconds: float = 30.0,
        timeout_seconds: float = 120.0,
        jitter: float = 0.2,
    ) -> None:
        self.max_retries = max_retries
        self.base_delay_seconds = base_delay_seconds
        self.max_delay_seconds = max_delay_seconds
        self.timeout_seconds = timeout_seconds
        self.jitter = jitter

    def delay_for(self, attempt: int, retry_after_seconds: float | None) -> float:
        """Calcula o atraso antes da tentativa ``attempt`` (base 0)."""
        if retry_after_seconds is not None:
            return min(max(retry_after_seconds, 0.0), self.max_delay_seconds)
        base = min(self.base_delay_seconds * (2.0**attempt), self.max_delay_seconds)
        # Jitter é aleatório por conveniência (evitar rajadas), não criptográfico.
        fator: float = 1.0 + random.uniform(-self.jitter, self.jitter)  # noqa: S311
        return max(base * fator, 0.0)


async def call_with_retry[T](
    operation: Callable[[], Awaitable[T]],
    policy: RetryPolicy,
    *,
    provider: ProviderId | str = "unknown",
) -> T:
    """Executa ``operation`` com timeout e retry, normalizando erros.

    Levanta :class:`ProviderError` quando esgotadas as tentativas ou quando o
    erro não é recuperável.
    """
    tentativa = 0
    while True:
        try:
            async with asyncio.timeout(policy.timeout_seconds):
                return await operation()
        except asyncio.CancelledError:
            raise ProviderError(
                ProviderErrorCode.CANCELLED,
                "requisição cancelada",
                provider=provider,
                retryable=False,
            ) from None
        except TimeoutError:
            erro = ProviderError(
                ProviderErrorCode.TIMEOUT,
                "a chamada excedeu o tempo limite",
                provider=provider,
                retryable=True,
            )
        except ProviderError as exc:
            erro = exc

        if not erro.retryable or tentativa >= policy.max_retries:
            raise erro
        atraso = policy.delay_for(tentativa, erro.retry_after_seconds)
        await asyncio.sleep(atraso)
        tentativa += 1


def map_http_error(
    status_code: int,
    body: str,
    provider: ProviderId | str,
    headers: Mapping[str, str] | None = None,
) -> ProviderError | None:
    """Converte uma resposta HTTP de erro em :class:`ProviderError`.

    Devolve ``None`` para status menores que 400 (não é erro).
    """
    if status_code < 400:
        return None

    mensagem = _extrair_mensagem(body)
    retry_after = _parse_retry_after(headers)

    if status_code in (401, 403):
        return ProviderError(
            ProviderErrorCode.AUTH,
            mensagem,
            provider=provider,
            retryable=False,
            status_code=status_code,
        )
    if status_code == 429:
        return ProviderError(
            ProviderErrorCode.RATE_LIMIT,
            mensagem,
            provider=provider,
            retryable=True,
            retry_after_seconds=retry_after,
            status_code=status_code,
        )
    if status_code == 402:
        return ProviderError(
            ProviderErrorCode.QUOTA,
            mensagem,
            provider=provider,
            retryable=False,
            status_code=status_code,
        )
    if status_code in (408, 504):
        return ProviderError(
            ProviderErrorCode.TIMEOUT,
            mensagem,
            provider=provider,
            retryable=True,
            status_code=status_code,
        )
    if status_code == 404 and "model" in mensagem.lower():
        return ProviderError(
            ProviderErrorCode.MODEL_NOT_FOUND,
            mensagem,
            provider=provider,
            retryable=False,
            status_code=status_code,
        )
    if status_code == 400 and ("content" in mensagem.lower() or "filter" in mensagem.lower()):
        return ProviderError(
            ProviderErrorCode.CONTENT_FILTER,
            mensagem,
            provider=provider,
            retryable=False,
            status_code=status_code,
        )
    if status_code >= 500:
        return ProviderError(
            ProviderErrorCode.SERVER_ERROR,
            mensagem,
            provider=provider,
            retryable=True,
            status_code=status_code,
        )
    return ProviderError(
        ProviderErrorCode.UNKNOWN,
        mensagem,
        provider=provider,
        retryable=False,
        status_code=status_code,
    )


def _extrair_mensagem(body: str) -> str:
    """Extrai uma mensagem legível do corpo de erro, sem vazar segredos."""
    import json

    mensagem = body
    try:
        dados: Any = json.loads(body)
    except (json.JSONDecodeError, TypeError):
        dados = None

    if isinstance(dados, dict):
        erro = dados.get("error")
        if isinstance(erro, dict) and isinstance(erro.get("message"), str):
            mensagem = erro["message"]
        elif isinstance(erro, str):
            mensagem = erro
        elif isinstance(dados.get("message"), str):
            mensagem = dados["message"]
        elif isinstance(dados.get("detail"), str):
            mensagem = dados["detail"]

    # Nunca devolver o corpo completo: pode conter eco da requisição.
    return mensagem[:300]


def _parse_retry_after(headers: Mapping[str, str] | None) -> float | None:
    """Interpreta ``Retry-After`` (segundos ou data HTTP)."""
    if not headers:
        return None
    valor = headers.get("Retry-After") or headers.get("retry-after")
    if not valor:
        return None
    try:
        return max(float(valor), 0.0)
    except ValueError:
        pass
    try:
        quando = parsedate_to_datetime(valor)
        agora = datetime.now(UTC)
        if quando.tzinfo is None:
            quando = quando.replace(tzinfo=UTC)
        return max((quando - agora).total_seconds(), 0.0)
    except (TypeError, ValueError, OverflowError):
        return None
