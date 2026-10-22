"""Testes do repositório de exportações (isolamento, retenção e consistência de schema)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.models.export import Export
from app.repositories.exports import ExportRepository
from app.schemas.exports import ExportRequest


def _salvar(repo: ExportRepository, export_id: str, owner_id: str | None, **extra: object) -> None:
    repo.save(
        export_id=export_id,
        document_id="doc-1",
        owner_id=owner_id,
        fmt="txt",
        filename=f"{export_id}.txt",
        sha256="0" * 64,
        size_bytes=3,
        template_id="abnt.tcc",
        **extra,  # type: ignore[arg-type]
    )


def test_get_e_listagem_isoladas_por_dono(db_session) -> None:
    repo = ExportRepository(db_session)
    _salvar(repo, "exp-u1", "u1", warnings=("aviso",))
    _salvar(repo, "exp-local", None)

    assert repo.get("exp-u1", "u1") is not None
    assert repo.get("exp-u1", "u2") is None
    assert repo.get("exp-u1", None) is None
    assert [e.id for e in repo.list_for_owner("u1")] == ["exp-u1"]
    assert [e.id for e in repo.list_for_owner(None)] == ["exp-local"]
    assert repo.list_for_owner("u1", document_id="outro") == []


def test_save_atualiza_registro_existente(db_session) -> None:
    repo = ExportRepository(db_session)
    _salvar(repo, "exp-1", "u1")
    repo.save(
        export_id="exp-1",
        document_id="doc-1",
        owner_id="u1",
        fmt="txt",
        filename="exp-1.txt",
        sha256="f" * 64,
        size_bytes=10,
        template_id="abnt.tcc",
    )
    atualizado = repo.get("exp-1", "u1")
    assert atualizado is not None
    assert atualizado.size_bytes == 10


def test_prune_remove_linha_e_arquivo_em_disco(db_session, tmp_path: Path) -> None:
    repo = ExportRepository(db_session)
    antigo = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=40)
    _salvar(repo, "exp-velho", "u1", created_at=antigo)
    _salvar(repo, "exp-novo", "u1")
    arquivo_velho = tmp_path / "exp-velho.txt"
    arquivo_novo = tmp_path / "exp-novo.txt"
    arquivo_velho.write_text("x")
    arquivo_novo.write_text("x")

    removidos = repo.prune_expired(
        now=datetime.now(UTC).replace(tzinfo=None),
        retention_days=30,
        owner_id="u1",
        export_dir=tmp_path,
    )

    assert removidos == 1
    assert not arquivo_velho.exists()
    assert arquivo_novo.exists()
    assert repo.get("exp-velho", "u1") is None


def test_prune_por_dono_nao_toca_outros_usuarios(db_session) -> None:
    repo = ExportRepository(db_session)
    antigo = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=40)
    _salvar(repo, "exp-u1", "u1", created_at=antigo)
    _salvar(repo, "exp-u2", "u2", created_at=antigo)

    agora = datetime.now(UTC).replace(tzinfo=None)
    assert repo.prune_expired(now=agora, retention_days=30, owner_id="u1") == 1
    assert repo.get("exp-u2", "u2") is not None
    assert repo.prune_expired(now=agora, retention_days=30, all_owners=True) == 1


def test_coluna_document_id_comporta_o_limite_do_schema() -> None:
    limite_schema = next(
        m.max_length
        for m in ExportRequest.model_fields["document_id"].metadata
        if hasattr(m, "max_length")
    )
    tamanho_coluna = Export.__table__.c.document_id.type.length  # type: ignore[attr-defined]
    assert tamanho_coluna >= limite_schema
