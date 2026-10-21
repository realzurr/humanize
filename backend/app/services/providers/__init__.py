"""Integração multi-LLM por uma interface comum.

A camada expõe :class:`LLMProvider` (contrato) e o :class:`ProviderRegistry`
(resolução por id). Nenhuma parte do sistema conhece um fornecedor específico
fora deste pacote, e nenhuma chave de API aparece em log, exceção ou resposta.
"""

from __future__ import annotations

from app.services.providers.base import (
    ChatMessage,
    CredentialCheck,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    ModelInfo,
    ProviderError,
    ProviderErrorCode,
    ProviderId,
    TokenUsage,
)
from app.services.providers.credentials import CredentialResolver, CredentialStatus
from app.services.providers.registry import AVAILABLE_PROVIDERS, PROVIDER_NAMES, ProviderRegistry

__all__ = [
    "AVAILABLE_PROVIDERS",
    "PROVIDER_NAMES",
    "ChatMessage",
    "CredentialCheck",
    "CredentialResolver",
    "CredentialStatus",
    "LLMProvider",
    "LLMRequest",
    "LLMResponse",
    "ModelInfo",
    "ProviderError",
    "ProviderErrorCode",
    "ProviderId",
    "ProviderRegistry",
    "TokenUsage",
]
