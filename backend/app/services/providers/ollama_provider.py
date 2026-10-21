"""Adaptador do provedor Ollama (modelos locais).

O Ollama não exige chave externa e roda na máquina do usuário. O endpoint
``/api/chat`` devolve ``message.content``, ``prompt_eval_count`` (tokens de
entrada) e ``eval_count`` (tokens de saída).
"""

from __future__ import annotations

import time
from typing import Any

from app.services.providers.base import (
    LLMRequest,
    LLMResponse,
    ProviderId,
    TokenUsage,
)
from app.services.providers.transport import HTTPProvider
from app.services.providers.usage import estimate_prompt_tokens, estimate_tokens


class OllamaProvider(HTTPProvider):
    """Provedor Ollama (sem chave, modelos locais)."""

    provider_id = ProviderId.OLLAMA
    requires_key = False
    default_base_url = "http://127.0.0.1:11434"

    def _payload(self, request: LLMRequest) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": request.model,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "stream": False,
            "options": {"temperature": request.temperature},
        }
        if request.max_output_tokens is not None:
            payload["options"]["num_predict"] = request.max_output_tokens
        if request.top_p is not None:
            payload["options"]["top_p"] = request.top_p
        if request.stop_sequences:
            payload["options"]["stop"] = list(request.stop_sequences)
        return payload

    async def generate(self, request: LLMRequest) -> LLMResponse:
        inicio = time.perf_counter()
        data = await self._request_json(
            "POST",
            "/api/chat",
            json=self._payload(request),
            request_id=request.request_id,
        )
        return self._parse(data, request, inicio)

    def _parse(self, data: dict[str, Any], request: LLMRequest, inicio: float) -> LLMResponse:
        mensagem = data.get("message") or {}
        texto = mensagem.get("content") or ""
        done_reason = str(data.get("done_reason") or "stop")

        prompt_tokens = int(data.get("prompt_eval_count") or 0)
        completion_tokens = int(data.get("eval_count") or 0)
        if not prompt_tokens:
            prompt_tokens = estimate_prompt_tokens(request.messages)
        if not completion_tokens:
            completion_tokens = estimate_tokens(texto)

        uso = TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            estimated_cost_usd=0.0,
        )
        return LLMResponse(
            text=texto,
            model=str(data.get("model") or request.model),
            provider=self.provider_id,
            usage=uso,
            finish_reason=done_reason,
            raw=data,
            latency_ms=int((time.perf_counter() - inicio) * 1000),
        )
