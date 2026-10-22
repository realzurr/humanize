"""Testes de integração do rate limiting (login)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.ratelimit import SlidingWindowLimiter


def test_login_rate_limit_bloqueia_excesso(app_with_auth) -> None:
    app_with_auth.state.rate_limiters["login"] = SlidingWindowLimiter(limit=2, window_seconds=60)
    with TestClient(app_with_auth) as client:
        client.post(
            "/api/v1/auth/register",
            json={"username": "alice", "password": "senha-forte-123"},
        )
        for _ in range(2):
            resposta = client.post(
                "/api/v1/auth/token",
                json={"username": "alice", "password": "senha-errada"},
            )
            assert resposta.status_code == 401

        resposta = client.post(
            "/api/v1/auth/token",
            json={"username": "alice", "password": "senha-errada"},
        )
        assert resposta.status_code == 429


def test_rate_limit_nao_e_contornado_por_x_forwarded_for(app_with_auth) -> None:
    """GAP-04: com ``behind_proxy=False``, rotacionar `X-Forwarded-For` não contorna o limite."""
    app_with_auth.state.rate_limiters["login"] = SlidingWindowLimiter(limit=2, window_seconds=60)
    with TestClient(app_with_auth) as client:
        client.post(
            "/api/v1/auth/register",
            json={"username": "alice", "password": "senha-forte-123"},
        )
        for indice in range(2):
            resposta = client.post(
                "/api/v1/auth/token",
                json={"username": "alice", "password": "senha-errada"},
                headers={"X-Forwarded-For": f"203.0.113.{indice}"},
            )
            assert resposta.status_code == 401

        resposta = client.post(
            "/api/v1/auth/token",
            json={"username": "alice", "password": "senha-errada"},
            headers={"X-Forwarded-For": "203.0.113.99"},
        )
        assert resposta.status_code == 429
