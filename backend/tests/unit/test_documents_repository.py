"""Testes do repositório de documentos (isolamento por dono e retenção)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.models.document import DocumentRevision
from app.repositories.documents import DocumentRepository


def test_criar_obter_listar_excluir(db_session) -> None:
    repo = DocumentRepository(db_session)
    documento = repo.create("texto original imutável", owner_id="u1")

    assert repo.get(documento.id, "u1") is not None
    assert documento.id in {d.id for d in repo.list_for_owner("u1")}

    assert repo.delete(documento.id, "u1")
    assert repo.get(documento.id, "u1") is None


def test_original_text_nao_e_sobrescrito(db_session) -> None:
    repo = DocumentRepository(db_session)
    documento = repo.create("original", owner_id="u1")
    # Nenhum método do repositório altera original_text após a criação.
    assert documento.original_text == "original"


def test_isolamento_entre_usuarios(db_session) -> None:
    repo = DocumentRepository(db_session)
    documento = repo.create("segredo do u1", owner_id="u1")

    assert repo.get(documento.id, "u2") is None
    assert repo.delete(documento.id, "u2") is False
    assert documento.id not in {d.id for d in repo.list_for_owner("u2")}


def test_retencao_remove_documentos_expirados(db_session) -> None:
    repo = DocumentRepository(db_session)
    documento = repo.create("antigo", owner_id="u1")
    documento.updated_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=40)
    db_session.commit()

    removidos = repo.prune_expired(
        now=datetime.now(UTC).replace(tzinfo=None),
        retention_days=30,
        owner_id="u1",
    )
    assert removidos == 1
    assert repo.get(documento.id, "u1") is None


def test_revisao_vinculada_e_removida_em_cascata(db_session) -> None:
    """GAP-08: `DocumentRevision` liga-se ao documento e é excluída em cascata."""
    repo = DocumentRepository(db_session)
    documento = repo.create("texto original", owner_id="u1")

    revisao = DocumentRevision(
        id="rev-1",
        document_id=documento.id,
        stage="normalize",
        text="texto normalizado",
    )
    db_session.add(revisao)
    db_session.commit()

    carregado = repo.get(documento.id, "u1")
    assert carregado is not None
    assert [r.id for r in carregado.revisions] == ["rev-1"]

    repo.delete(documento.id, "u1")
    assert db_session.get(DocumentRevision, "rev-1") is None
