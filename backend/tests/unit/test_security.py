"""Testes do núcleo de segurança (hash de senha e tokens assinados)."""

from __future__ import annotations

import time

from app.core.security import TokenService, hash_password, verify_password


def test_hash_e_verificacao_de_senha() -> None:
    hashe = hash_password("senha-forte-123")
    assert hashe.startswith("pbkdf2_sha256$")
    assert hashe != "senha-forte-123"
    assert verify_password("senha-forte-123", hashe)
    assert not verify_password("senha-errada", hashe)


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
