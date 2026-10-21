"""Testes do registro de provedores."""

from __future__ import annotations

from app.core.config import Settings
from app.services.providers.anthropic_provider import AnthropicProvider
from app.services.providers.base import ProviderId
from app.services.providers.credentials import CredentialResolver
from app.services.providers.gemini_provider import GeminiProvider
from app.services.providers.ollama_provider import OllamaProvider
from app.services.providers.openai_compat import OpenAICompatibleProvider
from app.services.providers.openai_provider import OpenAIProvider
from app.services.providers.registry import AVAILABLE_PROVIDERS, ProviderRegistry


def _registro() -> ProviderRegistry:
    return ProviderRegistry(Settings(), CredentialResolver(Settings()))


def test_build_devolve_adaptador_correto() -> None:
    registro = _registro()
    assert isinstance(registro.build("openai"), OpenAIProvider)
    assert isinstance(registro.build("anthropic"), AnthropicProvider)
    assert isinstance(registro.build("gemini"), GeminiProvider)
    assert isinstance(registro.build("ollama"), OllamaProvider)
    assert isinstance(registro.build("openai_compatible"), OpenAICompatibleProvider)


def test_ollama_nao_requer_chave() -> None:
    assert not _registro().build("ollama").requires_key


def test_describe_nao_expoe_chave() -> None:
    registro = _registro()
    registro._resolver.store("openai", "sk-abcd-efgh-1234")
    descricao = registro.describe("openai")
    assert descricao["configurado"] is True
    assert descricao["last4"] == "1234"
    assert "sk-abcd-efgh-1234" not in str(descricao)


def test_status_devolve_indicador() -> None:
    registro = _registro()
    estado = registro.status("gemini")
    assert estado.configured is False
    assert estado.last4 == ""


def test_provedor_desconhecido_levanta_erro() -> None:
    import pytest

    with pytest.raises(ValueError):
        _registro().build("nao_existe")


def test_available_providers_inclui_os_cinco() -> None:
    ids = set(AVAILABLE_PROVIDERS)
    assert ids == {
        ProviderId.OPENAI,
        ProviderId.ANTHROPIC,
        ProviderId.GEMINI,
        ProviderId.OLLAMA,
        ProviderId.OPENAI_COMPATIBLE,
    }
