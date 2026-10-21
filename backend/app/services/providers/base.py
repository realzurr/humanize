"""Contrato de provedores de LLM.

Toda a integração com modelos de linguagem passa por :class:`LLMProvider`.
Nenhuma parte do sistema (exceto os adaptadores) deve conhecer detalhes de
um fornecedor específico.

Invariantes do contrato:

* entrada e saída são **independentes do fornecedor**;
* credenciais **nunca** aparecem em logs, exceções ou respostas de API;
* todo erro de fornecedor é normalizado para :class:`ProviderError`, com
  ``retryable`` indicando se vale a pena repetir a chamada;
* custos são estimados, nunca cobrados.
"""

from __future__ import annotations

import abc
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProviderId(StrEnum):
    """Identificadores canônicos de provedores."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    OLLAMA = "ollama"
    OPENAI_COMPATIBLE = "openai_compatible"
    """Qualquer endpoint compatível com a API da OpenAI (LM Studio, vLLM, etc.)."""

    CUSTOM = "custom"


class ModelInfo(BaseModel):
    """Descrição de um modelo disponível em um provedor."""

    model_config = ConfigDict(frozen=True)

    id: str
    """Identificador do modelo junto ao provedor."""

    provider: ProviderId
    """Provedor ao qual o modelo pertence."""

    display_name: str = ""
    """Nome amigável para a interface."""

    context_window: int | None = None
    """Janela de contexto, quando conhecida."""

    max_output_tokens: int | None = None
    """Limite de tokens de saída."""

    supports_streaming: bool = False
    supports_json_mode: bool = False
    supports_system_prompt: bool = True
    input_cost_per_1k: float | None = None
    """Custo estimado de entrada por mil tokens (USD)."""

    output_cost_per_1k: float | None = None
    """Custo estimado de saída por mil tokens (USD)."""

    deprecated: bool = False
    """Marcado como descontinuado pelo provedor."""

    notes: str = ""


class ChatMessage(BaseModel):
    """Mensagem de conversa, formato neutro de fornecedor."""

    model_config = ConfigDict(frozen=True)

    role: str
    """``system`` | ``user`` | ``assistant``."""

    content: str


class LLMRequest(BaseModel):
    """Requisição neutra de geração."""

    model_config = ConfigDict(frozen=True)

    messages: tuple[ChatMessage, ...]
    model: str
    temperature: float = 0.7
    max_output_tokens: int | None = None
    top_p: float | None = None
    stop_sequences: tuple[str, ...] = ()
    response_format: str | None = None
    """``text`` | ``json`` — quando o provedor suporta modo JSON."""

    metadata: dict[str, Any] = Field(default_factory=dict)
    """Contexto adicional (id do documento, estágio, etc.)."""

    timeout_seconds: float = 120.0
    """Timeout sugerido para esta requisição."""

    request_id: str | None = None


class TokenUsage(BaseModel):
    """Consumo de tokens de uma chamada."""

    model_config = ConfigDict(frozen=True)

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    estimated_cost_usd: float = 0.0
    """Custo estimado (USD). Nunca é cobrado pelo sistema."""


class LLMResponse(BaseModel):
    """Resposta neutra de geração."""

    model_config = ConfigDict(frozen=True)

    text: str
    model: str
    provider: ProviderId
    usage: TokenUsage = TokenUsage()
    finish_reason: str = "stop"
    """``stop`` | ``length`` | ``content_filter`` | ``cancelled`` | ``error``."""

    raw: dict[str, Any] = Field(default_factory=dict, exclude=True)
    """Resposta bruta do provedor. Nunca serializada para o cliente."""

    latency_ms: int = 0


class ProviderErrorCode(StrEnum):
    """Códigos de erro normalizados."""

    AUTH = "auth"
    """Chave ausente, inválida ou expirada."""

    RATE_LIMIT = "rate_limit"
    """Limite de requisições excedido."""

    TIMEOUT = "timeout"
    NETWORK = "network"
    """Falha de rede ou DNS."""

    QUOTA = "quota"
    """Crédito insuficiente ou cota de uso esgotada."""

    MODEL_NOT_FOUND = "model_not_found"
    """Modelo inexistente ou indisponível."""

    INVALID_RESPONSE = "invalid_response"
    """Resposta malformada ou em formato inesperado."""

    CONTENT_FILTER = "content_filter"
    """Bloqueio pelo filtro de segurança do provedor."""

    UNSUPPORTED = "unsupported"
    """Recurso não suportado pelo provedor."""

    CANCELLED = "cancelled"
    """Requisição cancelada pelo usuário."""

    SERVER_ERROR = "server_error"
    """Erro 5xx do provedor."""

    UNKNOWN = "unknown"


class ProviderError(Exception):
    """Erro normalizado de provedor."""

    def __init__(
        self,
        code: ProviderErrorCode,
        message: str,
        *,
        provider: ProviderId | str = "unknown",
        retryable: bool = False,
        retry_after_seconds: float | None = None,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.provider = provider
        self.retryable = retryable
        self.retry_after_seconds = retry_after_seconds
        self.status_code = status_code
        self.details = details or {}

    def __str__(self) -> str:
        return f"[{self.provider}/{self.code}] {super().__str__()}"

    def to_public_dict(self) -> dict[str, Any]:
        """Forma segura de expor o erro ao cliente (sem credenciais)."""
        return {
            "code": self.code.value,
            "provider": str(self.provider),
            "message": super().__str__(),
            "retryable": self.retryable,
            "status_code": self.status_code,
            "retry_after_seconds": self.retry_after_seconds,
        }


@dataclass(frozen=True, slots=True)
class CredentialCheck:
    """Resultado da verificação de credenciais de um provedor."""

    provider: ProviderId
    ok: bool
    message: str = ""
    models: tuple[ModelInfo, ...] = field(default_factory=tuple)
    checked_at: str = ""
    requires_key: bool = True


class LLMProvider(abc.ABC):
    """Interface comum a todos os provedores de LLM.

    Implementações devem ser seguras para uso concorrente e nunca registrar
    credenciais.
    """

    #: Identificador canônico do provedor.
    provider_id: ProviderId = ProviderId.CUSTOM

    #: Se o provedor exige chave de API.
    requires_key: bool = True

    @abc.abstractmethod
    async def list_models(self) -> Sequence[ModelInfo]:
        """Lista os modelos disponíveis (pode exigir chamada de rede)."""

    @abc.abstractmethod
    async def check_credentials(self) -> CredentialCheck:
        """Verifica se as credenciais são válidas, sem executar inferência."""

    @abc.abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Executa uma geração não-streaming."""

    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        """Gera tokens incrementalmente.

        O padrão delega a :meth:`generate` e emite o texto em blocos, para que
        provedores sem suporte a streaming funcionem sem código adicional.
        """
        response = await self.generate(request)
        for chunk in response.text.split(" "):
            yield chunk + " "

    async def cancel(self, request_id: str) -> bool:
        """Cancela uma requisição em andamento, quando suportado."""
        return False

    def estimate_cost(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        """Estima o custo em USD a partir da tabela local de preços."""
        for info in self._model_table().values():
            if info.id == model:
                prompt_cost = (info.input_cost_per_1k or 0.0) * prompt_tokens / 1000
                output_cost = (info.output_cost_per_1k or 0.0) * completion_tokens / 1000
                return round(prompt_cost + output_cost, 6)
        return 0.0

    def _model_table(self) -> dict[str, ModelInfo]:
        return {}
