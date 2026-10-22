"""Testes de integração da autenticação (registro, login, me)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _registrar_e_logar(client: TestClient, username: str) -> str:
    resposta = client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": "senha-forte-123"},
    )
    assert resposta.status_code == 201
    token = client.post(
        "/api/v1/auth/token",
        json={"username": username, "password": "senha-forte-123"},
    ).json()["access_token"]
    return token


def test_registro_login_e_me(app_with_auth) -> None:
    with TestClient(app_with_auth) as client:
        token = _registrar_e_logar(client, "alice")
        resposta = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resposta.status_code == 200
        assert resposta.json()["username"] == "alice"


def test_login_com_senha_errada(app_with_auth) -> None:
    with TestClient(app_with_auth) as client:
        client.post(
            "/api/v1/auth/register",
            json={"username": "bob", "password": "senha-forte-123"},
        )
        resposta = client.post(
            "/api/v1/auth/token",
            json={"username": "bob", "password": "senha-errada"},
        )
        assert resposta.status_code == 401


def test_registro_duplicado_retorna_conflito(app_with_auth) -> None:
    with TestClient(app_with_auth) as client:
        corpo = {"username": "carol", "password": "senha-forte-123"}
        assert client.post("/api/v1/auth/register", json=corpo).status_code == 201
        assert client.post("/api/v1/auth/register", json=corpo).status_code == 409


def test_me_sem_token_retorna_401(app_with_auth) -> None:
    with TestClient(app_with_auth) as client:
        assert client.get("/api/v1/auth/me").status_code == 401


def test_token_adulterado_retorna_401(app_with_auth) -> None:
    with TestClient(app_with_auth) as client:
        token = _registrar_e_logar(client, "dave")
        resposta = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}x"})
        assert resposta.status_code == 401


def test_username_invalido_rejeitado(app_with_auth) -> None:
    with TestClient(app_with_auth) as client:
        resposta = client.post(
            "/api/v1/auth/register",
            json={"username": "a b!", "password": "senha-forte-123"},
        )
        assert resposta.status_code == 422
