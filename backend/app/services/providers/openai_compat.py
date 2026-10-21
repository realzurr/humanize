"""Adaptador de endpoint compatível com a API da OpenAI.

Cobre LM Studio, vLLM, gateways corporativos e qualquer servidor que fale o
formato ``/chat/completions``. O endpoint e a lista de modelos são
configuráveis (``Settings.openai_compatible_*``).
"""

from __future__ import annotations

from typing import Any

from app.services.providers.base import ModelInfo, ProviderId
from app.services.providers.catalog import openai_compatible_models
from app.services.providers.openai_provider import OpenAIProvider


class OpenAICompatibleProvider(OpenAIProvider):
    """Endpoint compatível com a API da OpenAI."""

    provider_id = ProviderId.OPENAI_COMPATIBLE

    def __init__(
        self,
        *,
        api_key: str = "",
        base_url: str = "",
        declared_models: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(api_key=api_key, base_url=base_url, **kwargs)
        self._declared = declared_models or []

    def _static_models(self) -> tuple[ModelInfo, ...]:
        return openai_compatible_models(self._declared)
