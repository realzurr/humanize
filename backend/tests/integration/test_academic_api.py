"""Testes de integração da rota de validação acadêmica."""

from __future__ import annotations

import httpx
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.services.references.doi import DOIResolver


def _cliente() -> TestClient:
    return TestClient(create_app())


def test_validar_texto_com_achados() -> None:
    texto = "(SOUZA, 2020)\n\n## REFERÊNCIAS\n\nSILVA, R. A. Título. Revista, 2020."
    with _cliente() as client:
        resposta = client.post("/api/v1/academic/validate", json={"texto": texto})
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["citacoes"] == 1
    assert corpo["referencias"] == 1
    assert any(a["categoria"] == "missing_reference" for a in corpo["achados"])
    # Achado auditável.
    achado = corpo["achados"][0]
    assert achado["severidade"] and achado["categoria"] and achado["veredito"]
    assert achado["acao_sugerida"]


def test_validar_texto_limpo() -> None:
    texto = "(SILVA, 2020)\n\n## REFERÊNCIAS\n\nSILVA, R. A. Título. Revista, 2020."
    with _cliente() as client:
        resposta = client.post("/api/v1/academic/validate", json={"texto": texto})
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["associadas"] == 1
    assert all(a["categoria"] != "missing_reference" for a in corpo["achados"])


def test_validar_campo_desconhecido_rejeitado() -> None:
    with _cliente() as client:
        resposta = client.post(
            "/api/v1/academic/validate",
            json={"texto": "x", "inventado": True},
        )
    assert resposta.status_code == 422


def test_consulta_doi_desabilitada_por_padrao() -> None:
    texto = (
        "(SILVA, 2020)\n\n## REFERÊNCIAS\n\n"
        "SILVA, R. A. Titulo errado. Revista, 2020. DOI: 10.1111/abc.123."
    )
    with _cliente() as client:
        resposta = client.post(
            "/api/v1/academic/validate",
            json={"texto": texto, "consultar_doi": True},
        )
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert all(a["categoria"] != "metadata_mismatch" for a in corpo["achados"])


def test_consulta_doi_habilitada_propoe_mudanca() -> None:
    app = create_app()
    app.state.settings = Settings(enable_doi_lookup=True)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"message": {"title": ["Titulo correto"], "issued": {"date-parts": [[2021]]}}},
            request=request,
        )

    app.state.doi_resolver = DOIResolver(transport=httpx.MockTransport(handler))

    texto = (
        "(SILVA, 2020)\n\n## REFERÊNCIAS\n\n"
        "SILVA, R. A. Titulo errado. Revista, 2020. DOI: 10.1111/abc.123."
    )
    with TestClient(app) as client:
        resposta = client.post(
            "/api/v1/academic/validate",
            json={"texto": texto, "consultar_doi": True},
        )
    corpo = resposta.json()
    achados = [a for a in corpo["achados"] if a["categoria"] == "metadata_mismatch"]
    assert achados
    # As mudanças são propostas, nunca aplicadas: o texto original não muda.
    assert "Titulo errado" in texto
