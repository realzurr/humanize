"""Registro de provedores de LLM.

Resolve um identificador canônico (:class:`ProviderId`) para a instância do
adaptador correspondente, já configurado com a chave (resolvida pelo
:class:`~app.services.providers.credentials.CredentialResolver`) e com a
política de resiliência.

O registro é a única porta de entrada para obter um provedor; o resto do
sistema nunca instancia um adaptador diretamente.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import Settings
from app.services.providers.anthropic_provider import AnthropicProvider
from app.services.providers.base import LLMProvider, ProviderId
from app.services.providers.credentials import CredentialResolver, CredentialStatus
from app.services.providers.gemini_provider import GeminiProvider
from app.services.providers.ollama_provider import OllamaProvider
from app.services.providers.openai_compat import OpenAICompatibleProvider
from app.services.providers.openai_provider import OpenAIProvider
from app.services.providers.resilience import RetryPolicy

#: Nome amigável de cada provedor, para a interface.
PROVIDER_NAMES: dict[ProviderId, str] = {
    ProviderId.OPENAI: "OpenAI",
    ProviderId.ANTHROPIC: "Anthropic Claude",
    ProviderId.GEMINI: "Google Gemini",
    ProviderId.OLLAMA: "Ollama (local)",
    ProviderId.OPENAI_COMPATIBLE: "Compatível com OpenAI",
}

#: Provedores que a API expõe.
AVAILABLE_PROVIDERS: tuple[ProviderId, ...] = (
    ProviderId.OPENAI,
    ProviderId.ANTHROPIC,
    ProviderId.GEMINI,
    ProviderId.OLLAMA,
    ProviderId.OPENAI_COMPATIBLE,
)


class ProviderRegistry:
    """Fábrica e catálogo de provedores."""

    def __init__(
        self,
        settings: Settings,
        resolver: CredentialResolver,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._settings = settings
        self._resolver = resolver
        self._transport = transport

    def _retry_policy(self) -> RetryPolicy:
        return RetryPolicy(
            max_retries=self._settings.llm_max_retries,
            timeout_seconds=self._settings.llm_timeout_seconds,
        )

    def build(self, provider_id: ProviderId | str) -> LLMProvider:
        """Constrói o adaptador de um provedor, já configurado."""
        enum = ProviderId(provider_id)
        chave = self._resolver.resolve(enum) or ""
        retry = self._retry_policy()
        transport = self._transport

        if enum is ProviderId.OLLAMA:
            return OllamaProvider(
                base_url=self._settings.ollama_base_url,
                transport=transport,
                retry_policy=retry,
            )
        if enum is ProviderId.OPENAI_COMPATIBLE:
            return OpenAICompatibleProvider(
                api_key=chave,
                base_url=self._settings.openai_compatible_base_url,
                declared_models=list(self._settings.openai_compatible_models),
                transport=transport,
                retry_policy=retry,
            )
        if enum is ProviderId.OPENAI:
            return OpenAIProvider(api_key=chave, transport=transport, retry_policy=retry)
        if enum is ProviderId.ANTHROPIC:
            return AnthropicProvider(api_key=chave, transport=transport, retry_policy=retry)
        if enum is ProviderId.GEMINI:
            return GeminiProvider(api_key=chave, transport=transport, retry_policy=retry)
        raise ValueError(f"provedor desconhecido: {provider_id}")

    def status(self, provider_id: ProviderId | str) -> CredentialStatus:
        """Indicador público da credencial do provedor (configured/last4)."""
        return self._resolver.status(provider_id)

    def describe(self, provider_id: ProviderId | str) -> dict[str, Any]:
        """Descrição serializável do provedor para a API de configuração."""
        enum = ProviderId(provider_id)
        provider = self.build(enum)
        estado = self.status(enum)
        return {
            "id": str(enum),
            "nome": PROVIDER_NAMES.get(enum, str(enum)),
            "requer_chave": provider.requires_key,
            "configurado": estado.configured,
            "last4": estado.last4,
            "fonte": estado.source,
        }
