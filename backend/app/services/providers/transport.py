"""Base comum dos provedores baseados em HTTP.

Todos os adaptadores usam :mod:`httpx` diretamente (em vez dos SDKs oficiais)
para reduzir a superfície de dependências e permitir testes determinísticos
com ``httpx.MockTransport``. O transporte não conhece o formato de requisição
de nenhum fornecedor; cada adaptador traduz o contrato neutro
(:class:`LLMRequest` / :class:`LLMResponse`) para o formato específico.

Aqui ficam:

* a construção do cliente HTTP;
* o mapeamento de erros HTTP para :class:`ProviderError` (via
  :mod:`app.services.providers.resilience`);
* o registro de tarefas ativas para cancelamento por ``request_id``.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import Any, cast

import httpx

from app.services.providers.base import (
    CredentialCheck,
    LLMProvider,
    ModelInfo,
    ProviderError,
    ProviderErrorCode,
    ProviderId,
)
from app.services.providers.catalog import STATIC_CATALOG
from app.services.providers.resilience import RetryPolicy, call_with_retry, map_http_error


class HTTPProvider(LLMProvider):
    """Provedor que fala HTTP (JSON) com um endpoint de fornecedor."""

    provider_id: ProviderId = ProviderId.CUSTOM
    requires_key: bool = True
    default_base_url: str = ""

    def __init__(
        self,
        *,
        api_key: str = "",
        base_url: str = "",
        transport: httpx.AsyncBaseTransport | None = None,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url or self.default_base_url
        self._transport = transport
        self._retry_policy = retry_policy or RetryPolicy()
        self._active: dict[str, asyncio.Task[Any]] = {}

    def _build_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            transport=self._transport,
            base_url=self._base_url,
            timeout=self._retry_policy.timeout_seconds,
        )

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        headers: Mapping[str, str] | None = None,
        params: Mapping[str, str] | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        """Executa uma requisição JSON com retry, timeout e erro normalizado."""

        async def operacao() -> dict[str, Any]:
            async with self._build_client() as client:
                try:
                    resposta = await client.request(
                        method, path, json=json, headers=headers, params=params
                    )
                except httpx.TimeoutException as exc:
                    raise ProviderError(
                        ProviderErrorCode.TIMEOUT,
                        "a chamada excedeu o tempo limite",
                        provider=self.provider_id,
                        retryable=True,
                    ) from exc
                except httpx.HTTPError as exc:
                    raise ProviderError(
                        ProviderErrorCode.NETWORK,
                        "falha de rede ou conexão",
                        provider=self.provider_id,
                        retryable=True,
                    ) from exc

                if resposta.status_code >= 400:
                    erro = map_http_error(
                        resposta.status_code,
                        resposta.text,
                        self.provider_id,
                        dict(resposta.headers),
                    )
                    if erro is not None:
                        raise erro

                try:
                    return cast(dict[str, Any], resposta.json())
                except ValueError as exc:
                    raise ProviderError(
                        ProviderErrorCode.INVALID_RESPONSE,
                        "resposta não é JSON válido",
                        provider=self.provider_id,
                        retryable=False,
                    ) from exc

        return await self._run_tracked(request_id, operacao)

    async def _run_tracked(
        self,
        request_id: str | None,
        operation: Callable[[], Awaitable[dict[str, Any]]],
    ) -> dict[str, Any]:
        """Registra a tarefa para cancelamento e executa com retry."""
        task = asyncio.current_task()
        if request_id and task is not None:
            self._active[request_id] = task
        try:
            return await call_with_retry(operation, self._retry_policy, provider=self.provider_id)
        finally:
            if request_id:
                self._active.pop(request_id, None)

    async def cancel(self, request_id: str) -> bool:
        """Cancela uma requisição em andamento pelo ``request_id``."""
        task = self._active.get(request_id)
        if task is None:
            return False
        task.cancel()
        return True

    def _static_models(self) -> tuple[ModelInfo, ...]:
        """Catálogo estático do provedor (síncrono, sem rede)."""
        return STATIC_CATALOG.get(self.provider_id, ())

    async def list_models(self) -> Sequence[ModelInfo]:
        """Lista os modelos disponíveis (catálogo estático, sem rede)."""
        return self._static_models()

    async def check_credentials(self) -> CredentialCheck:
        """Verifica a configuração da credencial, sem executar inferência."""
        if self.requires_key and not self._api_key:
            return CredentialCheck(
                provider=self.provider_id,
                ok=False,
                message="chave de API não configurada",
                requires_key=True,
            )
        return CredentialCheck(
            provider=self.provider_id,
            ok=True,
            message="configurada",
            models=tuple(await self.list_models()),
            requires_key=self.requires_key,
        )
