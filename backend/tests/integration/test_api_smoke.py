"""Testes de fumaça da API (Onda 0 — scaffolding)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_health_retorna_ok() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_openapi_e_gerado() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/openapi.json")
    assert response.status_code == 200
    assert "/api/v1/health" in response.json()["paths"]


def test_lifespan_inicializa_sem_erro() -> None:
    """O contexto ``with`` executa o lifespan: logging e banco são inicializados.

    Sem este teste, uma falha na configuração de logging durante o startup
    passaria despercebida — o lifespan só roda dentro do gerenciador de
    contexto.
    """
    with TestClient(create_app()) as client:
        assert client.get("/api/v1/health").status_code == 200
