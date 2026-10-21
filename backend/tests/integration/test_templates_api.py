"""Testes de integração da rota de templates."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def _cliente() -> TestClient:
    return TestClient(create_app())


def test_listar_templates() -> None:
    with _cliente() as client:
        resposta = client.get("/api/v1/templates")
    assert resposta.status_code == 200
    ids = {t["id"] for t in resposta.json()}
    assert {"abnt.general", "abnt.tcc", "abnt.artigo", "inst.ufms.geral"} <= ids


def test_detalhar_template() -> None:
    with _cliente() as client:
        resposta = client.get("/api/v1/templates/abnt.tcc")
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["kind"] == "tcc"
    assert corpo["typography"]["font"] == "Times New Roman"


def test_resolver_sem_instituicao() -> None:
    with _cliente() as client:
        resposta = client.get("/api/v1/templates/abnt.tcc/resolve")
    assert resposta.status_code == 200
    assert resposta.json()["conflicts"] == []


def test_resolver_com_instituicao_registra_conflito() -> None:
    with _cliente() as client:
        resposta = client.get(
            "/api/v1/templates/abnt.tcc/resolve",
            params={"instituicao": "inst.ufms.geral"},
        )
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["template"]["typography"]["font"] == "Arial"
    assert any(c["rule_id"] == "typography.font" for c in corpo["conflicts"])


def test_template_inexistente_404() -> None:
    with _cliente() as client:
        resposta = client.get("/api/v1/templates/nao_existe")
    assert resposta.status_code == 404


def test_resolver_instituicao_inexistente_404() -> None:
    with _cliente() as client:
        resposta = client.get(
            "/api/v1/templates/abnt.tcc/resolve",
            params={"instituicao": "inst.nao_existe"},
        )
    assert resposta.status_code == 404
