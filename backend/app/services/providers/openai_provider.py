"""Adaptador do provedor OpenAI.

Traduz o contrato neutro para o formato ``/chat/completions``. A contagem de
tokens devolvida pelo provedor tem precedência sobre a heurística local.
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


class OpenAIProvider(HTTPProvider):
    """Provedor OpenAI (Chat Completions)."""

    provider_id = ProviderId.OPENAI
    default_base_url = "https://api.openai.com/v1"

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}

    def _payload(self, request: LLMRequest) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": request.model,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "temperature": request.temperature,
        }
        if request.max_output_tokens is not None:
            payload["max_tokens"] = request.max_output_tokens
        if request.top_p is not None:
            payload["top_p"] = request.top_p
        if request.stop_sequences:
            payload["stop"] = list(request.stop_sequences)
        if request.response_format == "json":
            payload["response_format"] = {"type": "json_object"}
        return payload

    async def generate(self, request: LLMRequest) -> LLMResponse:
        inicio = time.perf_counter()
        data = await self._request_json(
            "POST",
            "/chat/completions",
            json=self._payload(request),
            headers=self._auth_headers(),
            request_id=request.request_id,
        )
        return self._parse(data, request, inicio)

    def _parse(self, data: dict[str, Any], request: LLMRequest, inicio: float) -> LLMResponse:
        choices = data.get("choices") or []
        primeiro = choices[0] if choices else {}
        mensagem = primeiro.get("message") or {}
        texto = mensagem.get("content") or ""
        finish_reason = str(primeiro.get("finish_reason") or "stop")

        return LLMResponse(
            text=texto,
            model=str(data.get("model") or request.model),
            provider=self.provider_id,
            usage=self._usage(data, request, texto),
            finish_reason=finish_reason,
            raw=data,
            latency_ms=int((time.perf_counter() - inicio) * 1000),
        )

    def _usage(self, data: dict[str, Any], request: LLMRequest, texto: str) -> TokenUsage:
        uso_bruto = data.get("usage") or {}
        prompt_tokens = int(uso_bruto.get("prompt_tokens") or 0)
        completion_tokens = int(uso_bruto.get("completion_tokens") or 0)
        total_tokens = int(uso_bruto.get("total_tokens") or 0)

        if not prompt_tokens:
            prompt_tokens = estimate_prompt_tokens(request.messages)
        if not completion_tokens:
            completion_tokens = estimate_tokens(texto)
        if not total_tokens:
            total_tokens = prompt_tokens + completion_tokens

        custo = compute_cost(
            prompt_tokens, completion_tokens, self._model_table().get(request.model)
        )
        return TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=custo,
        )

    def _model_table(self) -> dict[str, ModelInfo]:
        return {modelo.id: modelo for modelo in self._static_models()}
