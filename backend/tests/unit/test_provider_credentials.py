"""Testes de credenciais (AES-GCM, resolução env/sessão, indicador last4)."""

from __future__ import annotations

import base64
import os

import pytest

from app.core.config import Settings
from app.services.providers.credentials import CredentialResolver, SecretCipher


@pytest.fixture
def chave_32() -> bytes:
    return os.urandom(32)


def test_cipher_roundtrip(chave_32: bytes) -> None:
    cipher = SecretCipher(chave_32)
    token = cipher.encrypt("sk-segredo-123")
    assert "sk-segredo-123" not in token
    assert cipher.decrypt(token) == "sk-segredo-123"


def test_cipher_indisponivel_sem_chave() -> None:
    cipher = SecretCipher(None)
    assert not cipher.available
    with pytest.raises(RuntimeError):
        cipher.encrypt("x")


def test_cipher_indisponivel_com_chave_invalida() -> None:
    settings = Settings(encryption_key=base64.b64encode(b"curta").decode())
    assert not SecretCipher.from_settings(settings).available


def test_resolver_le_do_ambiente() -> None:
    settings = Settings(openai_api_key="sk-env-12345678")
    resolver = CredentialResolver(settings)
    assert resolver.resolve("openai") == "sk-env-12345678"
    status = resolver.status("openai")
    assert status.configured
    assert status.last4 == "5678"
    assert status.source == "env"


def test_resolver_store_devolve_last4() -> None:
    resolver = CredentialResolver(Settings())
    status = resolver.store("openai", "sk-sessao-abcd")
    assert status.configured
    assert status.last4 == "abcd"
    assert status.source == "session"
    assert resolver.resolve("openai") == "sk-sessao-abcd"


def test_resolver_delete_remove_sessao() -> None:
    resolver = CredentialResolver(Settings())
    resolver.store("openai", "sk-sessao-abcd")
    status = resolver.delete("openai")
    assert not status.configured
    assert resolver.resolve("openai") is None


def test_resolver_delete_preserva_ambiente() -> None:
    resolver = CredentialResolver(Settings(openai_api_key="sk-env-12345678"))
    resolver.store("openai", "sk-sessao-abcd")
    status = resolver.delete("openai")
    assert status.configured
    assert status.source == "env"


def test_resolver_ollama_sem_chave() -> None:
    resolver = CredentialResolver(Settings())
    assert resolver.resolve("ollama") is None
    assert not resolver.status("ollama").configured


def test_resolver_sessao_cifrada(chave_32: bytes) -> None:
    key_b64 = base64.b64encode(chave_32).decode()
    resolver = CredentialResolver(Settings(encryption_key=key_b64))
    resolver.store("openai", "sk-segredo-123456")
    # O valor em memória não deve estar em claro.
    token = resolver._session[(None, "openai")]
    assert "sk-segredo-123456" not in token
    assert resolver.resolve("openai") == "sk-segredo-123456"


def test_status_nunca_expõe_a_chave() -> None:
    resolver = CredentialResolver(Settings(openai_api_key="sk-env-abcdefgh"))
    status = resolver.status("openai")
    payload = {
        "configurado": status.configured,
        "last4": status.last4,
        "fonte": status.source,
    }
    assert "sk-env-abcdefgh" not in str(payload)
