"""Adaptador do provedor Anthropic Claude.

O Claude exige ``max_tokens`` e trata o prompt de sistema como campo separado
do corpo da requisição. A resposta usa ``content`` (lista de blocos) e
``stop_reason``.
"""

from __future__ import annotations

import time
from typing import Any

from app.services.providers.base import (
    LLMRequest,
    LLMResponse,
    ModelInfo,
    ProviderId,
    TokenUsage,
)
from app.services.providers.transport import HTTPProvider
from app.services.providers.usage import compute_cost, estimate_prompt_tokens, estimate_tokens

#: Versão da API Anthropic exigida no cabeçalho.
_ANTHROPIC_VERSION = "2023-06-01"


class AnthropicProvider(HTTPProvider):
    """Provedor Anthropic (Messages API)."""

    provider_id = ProviderId.ANTHROPIC
    default_base_url = "https://api.anthropic.com"

    def _headers(self) -> dict[str, str]:
        return {
            "x-api-key": self._api_key,
            "anthropic-version": _ANTHROPIC_VERSION,
            "Content-Type": "application/json",
        }

    def _payload(self, request: LLMRequest) -> dict[str, Any]:
        sistema = "\n".join(m.content for m in request.messages if m.role == "system")
        mensagens = [
            {"role": m.role, "content": m.content}
            for m in request.messages
            if m.role in {"user", "assistant"}
        ]
        payload: dict[str, Any] = {
            "model": request.model,
            "messages": mensagens,
            # max_tokens é obrigatório no Claude.
            "max_tokens": request.max_output_tokens or 4096,
            "temperature": request.temperature,
        }
        if sistema:
            payload["system"] = sistema
        if request.top_p is not None:
            payload["top_p"] = request.top_p
        if request.stop_sequences:
            payload["stop_sequences"] = list(request.stop_sequences)
        return payload

    async def generate(self, request: LLMRequest) -> LLMResponse:
        inicio = time.perf_counter()
        data = await self._request_json(
            "POST",
            "/v1/messages",
            json=self._payload(request),
            headers=self._headers(),
            request_id=request.request_id,
        )
        return self._parse(data, request, inicio)

    def _parse(self, data: dict[str, Any], request: LLMRequest, inicio: float) -> LLMResponse:
        blocos = data.get("content") or []
        texto = "".join(bloco.get("text", "") for bloco in blocos if bloco.get("type") == "text")
        finish_reason = str(data.get("stop_reason") or "stop")

        uso_bruto = data.get("usage") or {}
        prompt_tokens = int(uso_bruto.get("input_tokens") or 0)
        completion_tokens = int(uso_bruto.get("output_tokens") or 0)
        if not prompt_tokens:
            prompt_tokens = estimate_prompt_tokens(request.messages)
        if not completion_tokens:
            completion_tokens = estimate_tokens(texto)

        custo = compute_cost(
            prompt_tokens, completion_tokens, self._model_table().get(request.model)
        )
        uso = TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            estimated_cost_usd=custo,
        )
        return LLMResponse(
            text=texto,
            model=str(data.get("model") or request.model),
            provider=self.provider_id,
            usage=uso,
            finish_reason=finish_reason,
            raw=data,
            latency_ms=int((time.perf_counter() - inicio) * 1000),
        )

    def _model_table(self) -> dict[str, ModelInfo]:
        return {modelo.id: modelo for modelo in self._static_models()}
