"""Testes de segurança (QA) — isolamento e resolução de credenciais.

Cobrem o `GAP-01` (vazamento cross-tenant de credenciais em sessão) e o
`GAP-02` (desconexão entre `PersistentCredentialStore` e `ProviderRegistry.build`).
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.services.providers.credentials import CredentialResolver, SecretCipher
from app.services.providers.persistent_credentials import PersistentCredentialStore
from app.services.providers.registry import ProviderRegistry


def _registrar_logar(client: TestClient, username: str) -> str:
    client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": "senha-forte-123"},
    )
    return client.post(
        "/api/v1/auth/token",
        json={"username": username, "password": "senha-forte-123"},
    ).json()["access_token"]


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_credencial_de_sessao_isolada_por_usuario(app_with_auth) -> None:
    """GAP-01: o usuário B não vê nem usa a chave de sessão do usuário A."""
    with TestClient(app_with_auth) as client:
        token_a = _registrar_logar(client, "alice")
        token_b = _registrar_logar(client, "bob")

        client.post(
            "/api/v1/providers/openai/credentials",
            json={"api_key": "sk-alice-1234"},
            headers=_headers(token_a),
        )

        provedores_b = client.get("/api/v1/providers", headers=_headers(token_b)).json()
        openai_b = next(p for p in provedores_b if p["id"] == "openai")
        assert openai_b["configurado"] is False

        provedores_a = client.get("/api/v1/providers", headers=_headers(token_a)).json()
        openai_a = next(p for p in provedores_a if p["id"] == "openai")
        assert openai_a["configurado"] is True
        assert openai_a["last4"] == "1234"


def test_persistent_store_isolado_por_usuario(db_session) -> None:
    """GAP-02: a chave persistida é resolvida apenas para o dono correto."""
    store = PersistentCredentialStore(SecretCipher(b"0" * 32))
    store.save(db_session, "openai", "sk-persist-9999", owner_id="u1")

    assert store.resolve_plaintext(db_session, "openai", owner_id="u1") == "sk-persist-9999"
    assert store.resolve_plaintext(db_session, "openai", owner_id="u2") is None


def test_registry_build_usa_chave_explicita() -> None:
    """GAP-02: `build(api_key=...)` entrega a chave persistida ao adaptador."""
    settings = Settings()
    registry = ProviderRegistry(settings, CredentialResolver(settings))
    provider = registry.build("openai", api_key="sk-fornecida")
    assert provider._api_key == "sk-fornecida"


def test_cifra_requerida_para_persistir(db_session) -> None:
    """Persistir sem chave de criptografia é rejeitado, não gravado em claro."""
    import pytest

    from app.core.errors import ValidationError

    store = PersistentCredentialStore(SecretCipher(None))
    with pytest.raises(ValidationError):
        store.save(db_session, "openai", "sk-sem-cifra")


def test_chave_base64_invalida_nao_persiste() -> None:
    """Uma `encryption_key` inválida desabilita a cifra (e a persistência)."""
    from app.core.config import Settings

    resolver = CredentialResolver(Settings(encryption_key="nao-e-base64"))
    assert resolver._cipher.available is False
