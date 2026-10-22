"""Testes de integração da API `/api/v1/exports` (Onda 6)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.services.document_export.writer import ExportHistoryStore


@pytest.fixture
def client(app_with_db: FastAPI, tmp_path: Path) -> TestClient:
    app_with_db.state.export_store = ExportHistoryStore(tmp_path / "exports", retention_days=30)
    return TestClient(app_with_db)


def test_exports_api_generates_docx_txt_md_and_declares_pdf_limitation_when_none(
    client: TestClient,
) -> None:
    # Força pdf_renderer="none" para validar a regra de declaração explícita de limitação
    client.app.state.settings = client.app.state.settings.model_copy(  # type: ignore[attr-defined]
        update={"pdf_renderer": "none"}
    )

    payload = {
        "document_id": "tcc-2026",
        "texto": (
            "# Introdução\n\n"
            "Texto científico com dados 10⁻⁶ mol/L.\n\n"
            "## Metodologia\n\n"
            "Descrição do método.\n\n"
            "REFERÊNCIAS\n\n"
            "SILVA, J. C. Pesquisa aplicada. São Paulo: Atlas, 2023.\n"
        ),
        "template_id": "abnt.tcc",
        "instituicao": "inst.ufms.geral",
        "metadados": {
            "institution": "Universidade Federal de Mato Grosso do Sul",
            "author": "Renato Peixoto",
            "title": "Arquitetura de Exportação Acadêmica",
            "advisor": "Profa. Dra. Maria",
            "city": "Campo Grande",
            "year": "2026",
        },
        "formatos": ["docx", "pdf", "txt", "md"],
        "incluir_pre_textual": True,
    }

    resp = client.post("/api/v1/exports", json=payload)
    assert resp.status_code == 200
    body = resp.json()

    assert body["document_id"] == "tcc-2026"
    assert body["pdf_available"] is False
    assert len(body["limitations"]) >= 1
    assert "apenas DOCX, TXT e Markdown" in body["limitations"][0]

    formatos_gerados = {item["format"] for item in body["exports"]}
    assert formatos_gerados == {"docx", "txt", "md"}

    docx_export = next(item for item in body["exports"] if item["format"] == "docx")
    assert docx_export["docx_inspection"]["has_toc_field"] is True
    assert docx_export["docx_inspection"]["has_alignment_simulation"] is False
    assert docx_export["docx_inspection"]["catalog_record_reserved"] is True

    # Download do DOCX gerado
    dl_resp = client.get(f"/api/v1/exports/{docx_export['id']}/download")
    assert dl_resp.status_code == 200
    assert (
        dl_resp.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert dl_resp.content.startswith(b"PK")

    # Detalhe da exportação
    det_resp = client.get(f"/api/v1/exports/{docx_export['id']}")
    assert det_resp.status_code == 200
    assert det_resp.json()["id"] == docx_export["id"]

    # Listagem e histórico do documento
    list_resp = client.get("/api/v1/exports", params={"document_id": "tcc-2026"})
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 3

    hist_resp = client.get("/api/v1/exports/documents/tcc-2026/history")
    assert hist_resp.status_code == 200
    hist = hist_resp.json()
    assert hist["original_immutable"] is True
    assert len(hist["revisions"]) == 1
    assert len(hist["exports"]) == 3


def test_exports_preview_and_404_errors(client: TestClient) -> None:
    prev_resp = client.post(
        "/api/v1/exports/preview",
        json={
            "document_id": "doc-prev-api",
            "texto": "# Introdução\n\nTexto da introdução.",
            "template_id": "abnt.artigo",
        },
    )
    assert prev_resp.status_code == 200
    assert prev_resp.json()["template_id"] == "abnt.artigo"
    assert len(prev_resp.json()["toc_entries"]) == 1

    not_found_tpl = client.post(
        "/api/v1/exports/preview",
        json={"texto": "Teste", "template_id": "template.inexistente"},
    )
    assert not_found_tpl.status_code == 404

    not_found_exp = client.get("/api/v1/exports/exp_inexistente")
    assert not_found_exp.status_code == 404

    not_found_dl = client.get("/api/v1/exports/exp_inexistente/download")
    assert not_found_dl.status_code == 404


def test_exports_api_pdf_only_falls_back_to_docx_txt_md_when_renderer_none(
    client: TestClient,
) -> None:
    client.app.state.settings = client.app.state.settings.model_copy(  # type: ignore[attr-defined]
        update={"pdf_renderer": "none"}
    )
    resp = client.post(
        "/api/v1/exports",
        json={
            "document_id": "doc-fallback",
            "texto": "# Seção 1\n\nConteúdo.",
            "template_id": "abnt.tcc",
            "formatos": ["pdf"],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["pdf_available"] is False
    assert {item["format"] for item in data["exports"]} == {"docx", "txt", "md"}
    assert len(data["limitations"]) >= 1


def test_exports_api_persists_in_orm_and_recovers_after_memory_store_reset(
    app_with_db: object,
    tmp_path: Path,
) -> None:
    from fastapi import FastAPI

    app = app_with_db  # type: ignore[assignment]
    assert isinstance(app, FastAPI)
    export_dir = tmp_path / "exports_orm"
    app.state.settings = app.state.settings.model_copy(
        update={"pdf_renderer": "none", "export_dir": export_dir}
    )
    app.state.export_store = ExportHistoryStore(export_dir, retention_days=30)
    client = TestClient(app)

    resp = client.post(
        "/api/v1/exports",
        json={
            "document_id": "doc-orm-persist",
            "texto": "# Introdução\n\nTexto persistido.",
            "template_id": "abnt.tcc",
            "formatos": ["txt"],
        },
    )
    assert resp.status_code == 200
    exp_id = resp.json()["exports"][0]["id"]

    # Simula reinício do processo limpando o store em memória (mantendo o disco e o banco)
    app.state.export_store = ExportHistoryStore(export_dir, retention_days=30)

    lista = client.get("/api/v1/exports", params={"document_id": "doc-orm-persist"})
    assert lista.status_code == 200
    assert [item["id"] for item in lista.json()] == [exp_id]

    detalhe = client.get(f"/api/v1/exports/{exp_id}")
    assert detalhe.status_code == 200
    assert detalhe.json()["id"] == exp_id

    download = client.get(f"/api/v1/exports/{exp_id}/download")
    assert download.status_code == 200
    assert "Texto persistido." in download.text
