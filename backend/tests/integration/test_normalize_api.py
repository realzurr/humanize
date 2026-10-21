"""Testes de integração da rota de normalização."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def _cliente() -> TestClient:
    return TestClient(create_app())


def test_normalize_devolve_texto_e_relatorio() -> None:
    with _cliente() as client:
        resposta = client.post(
            "/api/v1/normalize",
            json={"texto": "# Título\n\na   b com 10⁻⁶ m²"},
        )
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["texto"] == "Título\n\na b com 10⁻⁶ m²"
    assert corpo["total_caracteres_antes"] >= corpo["total_caracteres_depois"]
    assert any(t["rule_id"] == "norm.markdown.heading" for t in corpo["transformacoes"])
    assert any(e["kind"] == "formula" for e in corpo["entidades_protegidas"])


def test_normalize_preserva_conteudo_protegido() -> None:
    with _cliente() as client:
        resposta = client.post(
            "/api/v1/normalize",
            json={"texto": "o valor foi 10⁻⁶ e a tabela:\n| A |\n|---|\n| 1 |\n"},
        )
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert "10⁻⁶" in corpo["texto"]
    assert "| A |" in corpo["texto"]
    assert not any(a.startswith("perda:") for a in corpo["avisos"])


def test_normalize_opcoes_desligam_markdown() -> None:
    with _cliente() as client:
        resposta = client.post(
            "/api/v1/normalize",
            json={"texto": "**negrito**", "opcoes": {"markdown": False}},
        )
    assert resposta.status_code == 200
    assert resposta.json()["texto"] == "**negrito**"


def test_normalize_regras_desativadas() -> None:
    with _cliente() as client:
        resposta = client.post(
            "/api/v1/normalize",
            json={"texto": "a   b", "regras_desativadas": ["norm.whitespace.collapse"]},
        )
    assert resposta.status_code == 200
    assert resposta.json()["texto"] == "a   b"


def test_normalize_valida_entrada_desconhecida() -> None:
    with _cliente() as client:
        resposta = client.post("/api/v1/normalize", json={"texto": "a", "inventado": 1})
    assert resposta.status_code == 422


def test_normalize_perfis_listados() -> None:
    with _cliente() as client:
        resposta = client.get("/api/v1/normalize/perfis")
    assert resposta.status_code == 200
    ids = [perfil["id"] for perfil in resposta.json()]
    assert "padrao" in ids
    assert "conservador" in ids


def test_normalize_texto_vazio() -> None:
    with _cliente() as client:
        resposta = client.post("/api/v1/normalize", json={"texto": ""})
    assert resposta.status_code == 200
    assert resposta.json()["texto"] == ""
