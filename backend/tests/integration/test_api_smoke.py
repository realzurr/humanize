"""Testes de fumaça da API (Onda 0 — scaffolding)."""

from __future__ import annotations

from pathlib import Path

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


def test_readiness_ok(app_with_db) -> None:
    """GAP-06: `/health/readiness` verifica banco e templates reais."""
    with TestClient(app_with_db) as client:
        resposta = client.get("/api/v1/health/readiness")
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["status"] == "ok"
    assert corpo["checks"]["database"]["ok"] is True
    assert corpo["checks"]["templates"]["ok"] is True


def test_readiness_degraded_sem_templates(app_with_db) -> None:
    app_with_db.state.settings.templates_dir = Path("/caminho/inexistente")
    with TestClient(app_with_db) as client:
        resposta = client.get("/api/v1/health/readiness")
    assert resposta.json()["status"] == "degraded"
