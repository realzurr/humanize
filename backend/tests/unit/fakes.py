"""Fakes reutilizáveis para os testes de humanização (sem rede)."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from app.services.providers.base import (
    CredentialCheck,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    ModelInfo,
    ProviderId,
    TokenUsage,
)


class FakeLLMProvider(LLMProvider):
    """Provedor que devolve uma resposta fixa e registra as requisições."""

    provider_id = ProviderId.CUSTOM
    requires_key = False

    def __init__(
        self,
        resposta: str | None = None,
        *,
        registrar: Callable[[LLMRequest], None] | None = None,
        modelos: Sequence[ModelInfo] = (),
    ) -> None:
        self._resposta = resposta
        self._registrar = registrar
        self._modelos = tuple(modelos)
        self.requisicoes: list[LLMRequest] = []

    async def list_models(self) -> Sequence[ModelInfo]:
        return self._modelos

    async def check_credentials(self) -> CredentialCheck:
        return CredentialCheck(provider=self.provider_id, ok=True, requires_key=False)

    async def generate(self, request: LLMRequest) -> LLMResponse:
        self.requisicoes.append(request)
        if self._registrar is not None:
            self._registrar(request)
        texto = self._resposta if self._resposta is not None else request.messages[-1].content
        return LLMResponse(
            text=texto,
            model=request.model,
            provider=self.provider_id,
            usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        )
