"""Testes de integração da rota de humanização (fake provider, sem rede)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app
from app.services.providers.base import LLMProvider
from tests.unit.fakes import FakeLLMProvider


class _StubRegistry:
    """Registro que devolve sempre o mesmo provider (fake)."""

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    def build(self, provider_id: str, *, api_key: str | None = None) -> LLMProvider:
        return self._provider


def _cliente(provider: LLMProvider | None = None) -> TestClient:
    app = create_app()
    app.state.provider_registry = _StubRegistry(provider or FakeLLMProvider())
    return TestClient(app)


def test_humanize_preserva_entidades() -> None:
    texto = "O valor foi 45,5 % no dia 12/03/2025, conforme Silva (2020). DOI: 10.1111/jss.12845."
    with _cliente() as client:
        resposta = client.post(
            "/api/v1/humanize",
            json={
                "texto": texto,
                "perfil": "academico_cientifico",
                "intensidade": 50,
                "provedor": "openai",
                "modelo": "gpt-4o",
            },
        )
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["texto"] == texto
    assert corpo["validacao"]["perdas"] == 0
    assert corpo["bloqueado"] is False
    assert corpo["uso"]["total_tokens"] > 0


def test_humanize_perfil_desconhecido() -> None:
    with _cliente() as client:
        resposta = client.post(
            "/api/v1/humanize",
            json={"texto": "x", "perfil": "nao_existe"},
        )
    assert resposta.status_code == 404


def test_humanize_intensidade_invalida() -> None:
    with _cliente() as client:
        resposta = client.post(
            "/api/v1/humanize",
            json={"texto": "x", "intensidade": 30},
        )
    assert resposta.status_code == 422


def test_humanize_autoral_exige_owner_id() -> None:
    with _cliente() as client:
        resposta = client.post(
            "/api/v1/humanize",
            json={"texto": "x", "perfil": "autoral_personalizado"},
        )
    assert resposta.status_code == 422


def test_humanize_autoral_com_owner_id() -> None:
    with _cliente() as client:
        resposta = client.post(
            "/api/v1/humanize",
            json={
                "texto": "Texto a reescrever.",
                "perfil": "autoral_personalizado",
                "owner_id": "dono-1",
                "textos_autorais": ["meu estilo autoral"],
            },
        )
    assert resposta.status_code == 200
    assert resposta.json()["perfil"] == "autoral_personalizado"


def test_humanize_campo_desconhecido_rejeitado() -> None:
    with _cliente() as client:
        resposta = client.post(
            "/api/v1/humanize",
            json={"texto": "x", "inventado": True},
        )
    assert resposta.status_code == 422
