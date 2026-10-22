"""Testes das migrações Alembic contra um SQLite descartável."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.core.config import BACKEND_ROOT, get_settings


@pytest.fixture
def alembic_cfg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Config]:
    url = f"sqlite:///{tmp_path / 'migracoes.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    yield cfg
    get_settings.cache_clear()


def _tamanho_document_id(url: str) -> int | None:
    colunas = inspect(create_engine(url)).get_columns("exports")
    tipo = next(c["type"] for c in colunas if c["name"] == "document_id")
    return getattr(tipo, "length", None)


def test_upgrade_downgrade_e_upgrade_limpos(alembic_cfg: Config) -> None:
    url = get_settings().database_url
    command.upgrade(alembic_cfg, "head")
    tabelas = set(inspect(create_engine(url)).get_table_names())
    assert {
        "users",
        "documents",
        "revisions",
        "exports",
        "revoked_tokens",
        "revoked_subjects",
    } <= tabelas
    assert _tamanho_document_id(url) == 120

    command.downgrade(alembic_cfg, "base")
    assert "exports" not in inspect(create_engine(url)).get_table_names()

    command.upgrade(alembic_cfg, "head")
    assert _tamanho_document_id(url) == 120
