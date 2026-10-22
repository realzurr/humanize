"""Camada de persistência relacional (SQLAlchemy 2.0).

Define a ``Base`` declarativa, a criação do motor e da fábrica de sessões, e a
dependência FastAPI que injeta uma sessão por requisição. Em produção as
tabelas são criadas por **migrações Alembic** (nunca ``create_all``); em
ambientes de desenvolvimento/teste o ``create_all`` é usado por conveniência.
"""

from __future__ import annotations

from collections.abc import Generator

from fastapi import Request
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """Base declarativa comum a todos os modelos ORM."""


def make_engine(database_url: str, *, echo: bool = False) -> Engine:
    """Cria o motor de banco a partir de uma URL SQLAlchemy."""
    connect_args: dict[str, object] = {}
    if database_url.startswith("sqlite"):
        # Permite o uso do SQLite em ambientes multithread (FastAPI/TestClient).
        connect_args["check_same_thread"] = False
    return create_engine(database_url, echo=echo, future=True, connect_args=connect_args)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Cria a fábrica de sessões vinculada ao motor."""
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=Session)


def get_session(request: Request) -> Generator[Session, None, None]:
    """Dependência que entrega uma sessão transacional por requisição."""
    factory: sessionmaker[Session] = request.app.state.session_factory
    with factory() as session:
        yield session
