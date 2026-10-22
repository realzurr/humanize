"""Testes de segurança (QA) — aplicação de autenticação e isolamento por dono.

Cobrem o `GAP-03`: com ``auth_enabled=True``, as rotas `/exports/**`, `/uploads`
e `/humanize` exigem autenticação e isolam dados por ``owner_id``.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


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


def test_humanize_exige_autenticacao(app_with_auth) -> None:
    with TestClient(app_with_auth) as client:
        resposta = client.post("/api/v1/humanize", json={"texto": "Texto."})
        assert resposta.status_code == 401


def test_uploads_exige_autenticacao(app_with_auth) -> None:
    with TestClient(app_with_auth) as client:
        resposta = client.post(
            "/api/v1/uploads", files={"arquivo": ("a.txt", b"texto", "text/plain")}
        )
        assert resposta.status_code == 401


def test_exports_exigem_autenticacao(app_with_auth) -> None:
    with TestClient(app_with_auth) as client:
        assert client.get("/api/v1/exports").status_code == 401
        assert client.post("/api/v1/exports", json={"texto": "x"}).status_code == 401


def test_exports_isolados_por_usuario(app_with_auth) -> None:
    with TestClient(app_with_auth) as client:
        token_a = _registrar_logar(client, "alice")
        token_b = _registrar_logar(client, "bob")

        resposta = client.post(
            "/api/v1/exports",
            json={
                "document_id": "doc-alice",
                "texto": "Título\n\nTexto do documento.",
                "template_id": "abnt.tcc",
                "formatos": ["txt"],
            },
            headers=_headers(token_a),
        )
        assert resposta.status_code == 200

        lista_b = client.get("/api/v1/exports", headers=_headers(token_b)).json()
        assert lista_b == []

        lista_a = client.get("/api/v1/exports", headers=_headers(token_a)).json()
        assert len(lista_a) == 1

        export_id = lista_a[0]["id"]
        # Bob não baixa nem detalha a exportação de Alice.
        assert (
            client.get(f"/api/v1/exports/{export_id}", headers=_headers(token_b)).status_code == 404
        )
        assert (
            client.get(
                f"/api/v1/exports/{export_id}/download", headers=_headers(token_b)
            ).status_code
            == 404
        )
