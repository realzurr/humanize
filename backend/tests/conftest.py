"""Fixtures compartilhadas dos testes."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, make_session_factory
from app.services.academic.templates import TemplateRegistry

#: Diretório de templates do repositório (backend/tests -> repo).
TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates"


@pytest.fixture
def template_registry() -> TemplateRegistry:
    """Catálogo de templates apontando para o diretório real do repositório."""
    return TemplateRegistry(TEMPLATES_DIR)


@pytest.fixture
def db_engine():
    """Motor SQLite em memória compartilhado (StaticPool) para os testes de banco."""
    import app.models  # noqa: F401  (registra os modelos no metadata)

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session_factory(db_engine) -> sessionmaker[Session]:
    """Fábrica de sessões vinculada ao motor em memória."""
    return make_session_factory(db_engine)


@pytest.fixture
def db_session(db_session_factory):
    """Sessão transacional isolada para testes unitários de repositório."""
    with db_session_factory() as session:
        yield session


@pytest.fixture
def app_with_db(db_engine, db_session_factory):
    """Aplicação com a sessão de banco apontando para o SQLite em memória."""
    from app.main import create_app

    app = create_app()
    app.state.engine = db_engine
    app.state.session_factory = db_session_factory
    return app


@pytest.fixture
def app_with_auth(app_with_db):
    """Aplicação com autenticação habilitada e chave de token configurada."""
    from app.core.config import Settings
    from app.core.security import TokenService

    settings = Settings(
        secret_key="segredo-de-teste-suficientemente-longo-123",
        auth_enabled=True,
        environment="test",
    )
    app_with_db.state.settings = settings
    app_with_db.state.token_service = TokenService(settings.secret_key)
    return app_with_db
