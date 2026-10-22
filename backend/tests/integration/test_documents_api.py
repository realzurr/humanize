"""Testes de integração de documentos (isolamento por dono e retenção)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _token(client: TestClient, username: str) -> str:
    client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": "senha-forte-123"},
    )
    return client.post(
        "/api/v1/auth/token",
        json={"username": username, "password": "senha-forte-123"},
    ).json()["access_token"]


def _autenticar(client: TestClient, token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_criar_listar_excluir_documento(app_with_auth) -> None:
    with TestClient(app_with_auth) as client:
        token = _token(client, "alice")
        headers = _autenticar(client, token)

        resposta = client.post("/api/v1/documents", json={"texto": "meu texto"}, headers=headers)
        assert resposta.status_code == 201
        documento_id = resposta.json()["id"]

        lista = client.get("/api/v1/documents", headers=headers)
        assert lista.status_code == 200
        assert any(d["id"] == documento_id for d in lista.json())

        assert (
            client.delete(f"/api/v1/documents/{documento_id}", headers=headers).status_code == 204
        )
        assert client.get(f"/api/v1/documents/{documento_id}", headers=headers).status_code == 404


def test_isolamento_entre_usuarios(app_with_auth) -> None:
    with TestClient(app_with_auth) as client:
        token_alice = _token(client, "alice")
        token_bob = _token(client, "bob")

        resposta = client.post(
            "/api/v1/documents",
            json={"texto": "segredo da alice"},
            headers=_autenticar(client, token_alice),
        )
        documento_id = resposta.json()["id"]

        # Bob não vê nem exclui o documento da Alice.
        assert (
            client.get(
                f"/api/v1/documents/{documento_id}", headers=_autenticar(client, token_bob)
            ).status_code
            == 404
        )
        assert (
            client.delete(
                f"/api/v1/documents/{documento_id}", headers=_autenticar(client, token_bob)
            ).status_code
            == 404
        )


def test_retencao_via_rota(app_with_auth) -> None:
    with TestClient(app_with_auth) as client:
        token = _token(client, "alice")
        client.post("/api/v1/documents", json={"texto": "x"}, headers=_autenticar(client, token))
        resposta = client.post("/api/v1/documents/prune", headers=_autenticar(client, token))
        assert resposta.status_code == 200
        assert resposta.json()["removidos"] == 0
