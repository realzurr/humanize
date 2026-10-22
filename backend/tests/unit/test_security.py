"""Testes do núcleo de segurança (hash de senha e tokens assinados)."""

from __future__ import annotations

import time

import pytest

from app.core.security import (
    InMemoryRevocationStore,
    TokenService,
    hash_password,
    needs_rehash,
    verify_password,
)


def test_hash_e_verificacao_de_senha() -> None:
    hashe = hash_password("senha-forte-123")
    assert hashe.startswith("argon2id$")
    assert hashe != "senha-forte-123"
    assert not needs_rehash(hashe)
    assert verify_password("senha-forte-123", hashe)
    assert not verify_password("senha-errada", hashe)


def test_compatibilidade_pbkdf2_legado_e_needs_rehash() -> None:
    legado = hash_password("senha-legada-123", algorithm="pbkdf2_sha256")
    assert legado.startswith("pbkdf2_sha256$")
    assert needs_rehash(legado)
    assert verify_password("senha-legada-123", legado)
    assert not verify_password("outra-senha", legado)


def test_hashes_sao_salteados() -> None:
    primeiro = hash_password("mesma-senha")
    segundo = hash_password("mesma-senha")
    assert primeiro != segundo
    assert verify_password("mesma-senha", primeiro)
    assert verify_password("mesma-senha", segundo)


def test_verificacao_de_hash_invalido_nao_lanca() -> None:
    assert not verify_password("x", "formato-invalido")
    assert not verify_password("x", "pbkdf2_sha256$abc$def$ghi")


def test_token_emite_e_verifica() -> None:
    servico = TokenService("chave-secreta-para-tokens", ttl_seconds=60)
    token = servico.issue("usuario-1")
    assert servico.verify(token) == "usuario-1"


def test_token_invalido_ou_adulterado() -> None:
    servico = TokenService("chave-secreta-para-tokens", ttl_seconds=60)
    token = servico.issue("usuario-1")
    corpo, assinatura = token.split(".", 1)
    adulterado = f"{corpo}.{'A' * len(assinatura)}"
    assert servico.verify(adulterado) is None
    assert servico.verify("token-sem-ponto") is None


def test_token_expirado() -> None:
    servico = TokenService("chave-secreta-para-tokens", ttl_seconds=-1)
    token = servico.issue("usuario-1")
    time.sleep(0.01)
    assert servico.verify(token) is None


def test_token_service_exige_chave() -> None:
    import pytest

    with pytest.raises(ValueError):
        TokenService("")


def test_token_rotacao_de_chave_e_revogacao() -> None:
    antigo = TokenService("chave-antiga-v1", ttl_seconds=60)
    token_antigo = antigo.issue("usuario-rotacao")

    rotacionado = TokenService(
        "chave-nova-v2",
        ttl_seconds=60,
        previous_keys=("chave-antiga-v1",),
    )
    assert rotacionado.verify(token_antigo) == "usuario-rotacao"

    token_novo = rotacionado.issue("usuario-rotacao")
    assert rotacionado.verify(token_novo) == "usuario-rotacao"
    assert antigo.verify(token_novo) is None

    # Revogação individual por jti
    assert rotacionado.revoke_token(token_antigo) is True
    assert rotacionado.verify(token_antigo) is None
    assert rotacionado.verify(token_novo) == "usuario-rotacao"

    # Revogação de todos os tokens do subject
    rotacionado.revoke_subject("usuario-rotacao")
    assert rotacionado.verify(token_novo) is None


def test_avisar_configuracao_invalida_emite_warnings(
    monkeypatch: object,
) -> None:
    import pytest

    from app.core.config import Settings
    from app.main import _avisar_configuracao_invalida, logger

    mp = pytest.MonkeyPatch()
    avisos: list[tuple[str, dict[str, object]]] = []

    def _capturar(evento: str, **kwargs: object) -> None:
        avisos.append((evento, kwargs))

    mp.setattr(logger, "warning", _capturar)
    try:
        invalida = Settings(
            environment="production",
            auth_enabled=True,
            secret_key="",
            credential_encryption_enabled=True,
            encryption_key="invalida",
            behind_proxy=False,
        )
        _avisar_configuracao_invalida(invalida)
        detalhes = [str(kw.get("detalhe", "")) for _, kw in avisos]
        assert any("auth_enabled=true sem secret_key" in d for d in detalhes)
        assert any("credential_encryption_enabled=true sem encryption_key" in d for d in detalhes)
        assert any("behind_proxy=false" in d for d in detalhes)

        avisos.clear()
        prod_sem_auth = Settings(
            environment="production",
            auth_enabled=False,
            behind_proxy=True,
        )
        _avisar_configuracao_invalida(prod_sem_auth)
        detalhes_prod = [str(kw.get("detalhe", "")) for _, kw in avisos]
        assert any("auth_enabled=false" in d for d in detalhes_prod)
    finally:
        mp.undo()


def test_needs_rehash_quando_parametros_argon2_divergem() -> None:
    atual = hash_password("senha-forte-123")
    algoritmo, _params, salt, digest = atual.split("$")
    enfraquecido = f"{algoritmo}$m=8192,t=1,p=1${salt}${digest}"
    assert needs_rehash(enfraquecido)
    assert not needs_rehash(atual)


def test_revogacoes_de_tokens_expirados_sao_podadas(monkeypatch: pytest.MonkeyPatch) -> None:
    store = InMemoryRevocationStore()
    servico = TokenService("segredo-de-teste", ttl_seconds=60, revocation_store=store)
    token = servico.issue("usuario-poda")
    assert servico.revoke_token(token) is True
    assert len(store) == 1

    instante_futuro = time.time() + 120
    monkeypatch.setattr("app.core.security.time.time", lambda: instante_futuro)
    novo = servico.issue("usuario-poda")
    assert servico.revoke_token(novo) is True
    assert len(store) == 1
