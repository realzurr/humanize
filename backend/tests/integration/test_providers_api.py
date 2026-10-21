"""Testes de integração da rota de provedores."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def _cliente() -> TestClient:
    return TestClient(create_app())


def test_listar_provedores() -> None:
    with _cliente() as client:
        resposta = client.get("/api/v1/providers")
    assert resposta.status_code == 200
    provedores = resposta.json()
    ids = {p["id"] for p in provedores}
    assert ids == {"openai", "anthropic", "gemini", "ollama", "openai_compatible"}
    assert all("last4" in p and "configurado" in p for p in provedores)


def test_listar_modelos_de_um_provedor() -> None:
    with _cliente() as client:
        resposta = client.get("/api/v1/providers/openai/models")
    assert resposta.status_code == 200
    modelos = resposta.json()
    assert any(m["id"] == "gpt-4o" for m in modelos)


def test_provedor_desconhecido_retorna_404() -> None:
    with _cliente() as client:
        resposta = client.get("/api/v1/providers/nao_existe/models")
    assert resposta.status_code == 404


def test_armazenar_credencial_devolve_indicador() -> None:
    chave = "sk-teste-abcdef123456"
    with _cliente() as client:
        resposta = client.post(
            "/api/v1/providers/openai/credentials",
            json={"api_key": chave},
        )
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["configurado"] is True
    assert corpo["last4"] == "3456"
    # A chave nunca aparece na resposta.
    assert chave not in str(corpo)


def test_credencial_persiste_na_sessao() -> None:
    with _cliente() as client:
        client.post("/api/v1/providers/openai/credentials", json={"api_key": "sk-1234-5678"})
        resposta = client.get("/api/v1/providers")
    openai = next(p for p in resposta.json() if p["id"] == "openai")
    assert openai["configurado"] is True
    assert openai["last4"] == "5678"


def test_remover_credencial() -> None:
    with _cliente() as client:
        client.post("/api/v1/providers/openai/credentials", json={"api_key": "sk-1234-5678"})
        resposta = client.delete("/api/v1/providers/openai/credentials")
    corpo = resposta.json()
    assert corpo["configurado"] is False


def test_credencial_vazia_e_rejeitada() -> None:
    with _cliente() as client:
        resposta = client.post("/api/v1/providers/openai/credentials", json={"api_key": ""})
    assert resposta.status_code == 422


def test_campo_desconhecido_e_rejeitado() -> None:
    with _cliente() as client:
        resposta = client.post(
            "/api/v1/providers/openai/credentials",
            json={"api_key": "sk-x", "inventado": True},
        )
    assert resposta.status_code == 422
