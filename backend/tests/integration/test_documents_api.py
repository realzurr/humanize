"""Testes de integração de documentos (isolamento por dono e retenção)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _token(client: TestClient, username: str) -> str:
    client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": "senha-forte-123"},
    )
    return client.post(
        "/api/v1/auth/token",
        json={"username": username, "password": "senha-forte-123"},
    ).json()["access_token"]


def _autenticar(client: TestClient, token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_criar_listar_excluir_documento(app_with_auth) -> None:
    with TestClient(app_with_auth) as client:
        token = _token(client, "alice")
        headers = _autenticar(client, token)

        resposta = client.post("/api/v1/documents", json={"texto": "meu texto"}, headers=headers)
        assert resposta.status_code == 201
        documento_id = resposta.json()["id"]

        lista = client.get("/api/v1/documents", headers=headers)
        assert lista.status_code == 200
        assert any(d["id"] == documento_id for d in lista.json())

        assert (
            client.delete(f"/api/v1/documents/{documento_id}", headers=headers).status_code == 204
        )
        assert client.get(f"/api/v1/documents/{documento_id}", headers=headers).status_code == 404


def test_isolamento_entre_usuarios(app_with_auth) -> None:
    with TestClient(app_with_auth) as client:
        token_alice = _token(client, "alice")
        token_bob = _token(client, "bob")

        resposta = client.post(
            "/api/v1/documents",
            json={"texto": "segredo da alice"},
            headers=_autenticar(client, token_alice),
        )
        documento_id = resposta.json()["id"]

        # Bob não vê nem exclui o documento da Alice.
        assert (
            client.get(
                f"/api/v1/documents/{documento_id}", headers=_autenticar(client, token_bob)
            ).status_code
            == 404
        )
        assert (
            client.delete(
                f"/api/v1/documents/{documento_id}", headers=_autenticar(client, token_bob)
            ).status_code
            == 404
        )


def test_retencao_via_rota(app_with_auth) -> None:
    with TestClient(app_with_auth) as client:
        token = _token(client, "alice")
        client.post("/api/v1/documents", json={"texto": "x"}, headers=_autenticar(client, token))
        resposta = client.post("/api/v1/documents/prune", headers=_autenticar(client, token))
        assert resposta.status_code == 200
        assert resposta.json()["removidos"] == 0


def test_run_retention_sweep_unificado(app_with_db, tmp_path) -> None:
    from datetime import UTC, datetime, timedelta

    from app.main import run_retention_sweep
    from app.services.document_export.writer import ExportHistoryStore
    from app.services.ingestion.upload import store_upload

    app_with_db.state.settings = app_with_db.state.settings.model_copy(
        update={
            "storage_dir": tmp_path,
            "export_dir": tmp_path / "exports",
            "document_retention_days": 30,
        }
    )
    app_with_db.state.export_store = ExportHistoryStore(tmp_path / "exports", retention_days=30)

    with TestClient(app_with_db) as client:
        client.post("/api/v1/documents", json={"texto": "doc expirar"})
        client.post(
            "/api/v1/exports",
            json={
                "document_id": "doc-exp",
                "texto": "# Título\n\nTexto.",
                "template_id": "abnt.tcc",
                "formatos": ["txt"],
            },
        )
        store_upload(str(tmp_path / "uploads"), "up.txt", b"conteudo")

        futuro = datetime.now(UTC) + timedelta(days=31)
        resumo = run_retention_sweep(app_with_db, now=futuro)
        assert resumo["documents"] == 1
        assert resumo["exports_orm"] == 1
        assert resumo["exports_disk"] == 1
        assert resumo["uploads"] == 1


async def test_loop_de_retencao_sobrevive_a_falha(monkeypatch) -> None:
    import asyncio

    from app import main

    chamadas: list[int] = []
    segunda_execucao = asyncio.Event()

    def _varredura_instavel(_app: object) -> dict[str, int]:
        chamadas.append(1)
        if len(chamadas) == 1:
            raise RuntimeError("banco indisponível")
        segunda_execucao.set()
        return {"documents": 0}

    monkeypatch.setattr(main, "run_retention_sweep", _varredura_instavel)
    tarefa = asyncio.create_task(main._loop_retencao(object(), 0))  # type: ignore[arg-type]
    try:
        await asyncio.wait_for(segunda_execucao.wait(), timeout=2)
    finally:
        tarefa.cancel()
    assert len(chamadas) >= 2


def test_retencao_via_rota_separa_contadores(app_with_auth) -> None:
    with TestClient(app_with_auth) as client:
        token = _token(client, "carol")
        resposta = client.post("/api/v1/documents/prune", headers=_autenticar(client, token))
        corpo = resposta.json()
        assert corpo == {"removidos": 0, "documentos": 0, "exportacoes": 0}
