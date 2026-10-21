"""Adaptador do provedor Google Gemini.

O Gemini usa ``generateContent``, com a chave na query string e o prompt de
sistema em ``systemInstruction``. As mensagens são agrupadas em ``contents``
com partes de texto.
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

#: Papéis aceitos pelo Gemini no campo ``role``.
_GEMINI_ROLES = {"user": "user", "assistant": "model", "system": "user"}


class GeminiProvider(HTTPProvider):
    """Provedor Google Gemini (generateContent)."""

    provider_id = ProviderId.GEMINI
    default_base_url = "https://generativelanguage.googleapis.com"

    def _payload(self, request: LLMRequest) -> dict[str, Any]:
        sistema = "\n".join(m.content for m in request.messages if m.role == "system")
        conteudos = [
            {"role": _GEMINI_ROLES.get(m.role, "user"), "parts": [{"text": m.content}]}
            for m in request.messages
            if m.role != "system"
        ]
        payload: dict[str, Any] = {"contents": conteudos}
        if sistema:
            payload["systemInstruction"] = {"parts": [{"text": sistema}]}
        generation: dict[str, Any] = {"temperature": request.temperature}
        if request.max_output_tokens is not None:
            generation["maxOutputTokens"] = request.max_output_tokens
        if request.top_p is not None:
            generation["topP"] = request.top_p
        if request.stop_sequences:
            generation["stopSequences"] = list(request.stop_sequences)
        payload["generationConfig"] = generation
        return payload

    async def generate(self, request: LLMRequest) -> LLMResponse:
        inicio = time.perf_counter()
        data = await self._request_json(
            "POST",
            f"/v1beta/models/{request.model}:generateContent",
            json=self._payload(request),
            params={"key": self._api_key},
            request_id=request.request_id,
        )
        return self._parse(data, request, inicio)

    def _parse(self, data: dict[str, Any], request: LLMRequest, inicio: float) -> LLMResponse:
        candidatos = data.get("candidates") or []
        primeiro = candidatos[0] if candidatos else {}
        partes = (primeiro.get("content") or {}).get("parts") or []
        texto = "".join(parte.get("text", "") for parte in partes)
        finish_reason = str(primeiro.get("finishReason") or "STOP").lower()

        uso_bruto = data.get("usageMetadata") or {}
        prompt_tokens = int(uso_bruto.get("promptTokenCount") or 0)
        completion_tokens = int(uso_bruto.get("candidatesTokenCount") or 0)
        total_tokens = int(uso_bruto.get("totalTokenCount") or 0)
        if not prompt_tokens:
            prompt_tokens = estimate_prompt_tokens(request.messages)
        if not completion_tokens:
            completion_tokens = estimate_tokens(texto)
        if not total_tokens:
            total_tokens = prompt_tokens + completion_tokens

        custo = compute_cost(
            prompt_tokens, completion_tokens, self._model_table().get(request.model)
        )
        uso = TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
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
