"""Testes de integração do upload seguro de documentos."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_upload_texto_valido(app_with_db) -> None:
    with TestClient(app_with_db) as client:
        resposta = client.post(
            "/api/v1/uploads",
            files={"arquivo": ("documento.txt", b"conteudo de teste", "text/plain")},
        )
        assert resposta.status_code == 201
        corpo = resposta.json()
        assert corpo["format"] == "text"
        assert corpo["texto"] == "conteudo de teste"
        assert corpo["filename"] == "documento.txt"


def test_upload_rejeita_extensao_nao_suportada(app_with_db) -> None:
    with TestClient(app_with_db) as client:
        resposta = client.post(
            "/api/v1/uploads",
            files={"arquivo": ("programa.exe", b"MZ\x00\x00\x00", "application/octet-stream")},
        )
        assert resposta.status_code == 422


def test_upload_rejeita_docx_invalido(app_with_db) -> None:
    with TestClient(app_with_db) as client:
        resposta = client.post(
            "/api/v1/uploads",
            files={"arquivo": ("falso.docx", b"nao-eh-um-zip", "application/octet-stream")},
        )
        assert resposta.status_code == 422


def test_upload_rejeita_tamanho_excedido(app_with_db) -> None:
    app_with_db.state.settings.max_upload_bytes = 10
    with TestClient(app_with_db) as client:
        resposta = client.post(
            "/api/v1/uploads",
            files={"arquivo": ("grande.txt", b"x" * 100, "text/plain")},
        )
        assert resposta.status_code == 413
