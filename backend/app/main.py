"""Ponto de entrada da API.

A aplicação expõe a API e os arquivos estáticos do frontend quando buildado.
Cada versão de rota vive em ``app/api/v1`` e é registrada em
:mod:`app.api.router`. A Onda 8 adiciona a camada de persistência relacional,
autenticação opt-in, rate limiting e armazenamento durável de credenciais.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import models  # noqa: F401  (registro dos modelos no Base.metadata)
from app.api.router import api_router
from app.core.config import get_settings
from app.core.database import Base, make_engine, make_session_factory
from app.core.errors import HumanizaError
from app.core.logging import configure_logging, get_logger
from app.core.ratelimit import SlidingWindowLimiter
from app.core.security import TokenService
from app.services.academic.templates import TemplateRegistry
from app.services.document_export.writer import ExportHistoryStore
from app.services.providers.credentials import CredentialResolver, SecretCipher
from app.services.providers.persistent_credentials import PersistentCredentialStore
from app.services.providers.registry import ProviderRegistry
from app.services.references.doi import DOIResolver

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Inicialização e encerramento da aplicação."""
    settings = get_settings()
    configure_logging(settings)
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    settings.export_dir.mkdir(parents=True, exist_ok=True)

    # Em produção as tabelas vêm de migrações Alembic; em desenvolvimento e
    # teste, o create_all é usado por conveniência.
    if not settings.is_production:
        Base.metadata.create_all(app.state.engine)

    logger.info(
        "aplicacao.iniciada",
        app=settings.app_name,
        versao=settings.app_version,
        ambiente=settings.environment,
        autenticacao=settings.auth_enabled,
    )
    yield
    logger.info("aplicacao.encerrada")


def create_app() -> FastAPI:
    """Cria e configura a instância do FastAPI."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Estado compartilhado: configuração, banco, provedores, templates e DOI.
    app.state.settings = settings
    app.state.engine = make_engine(settings.database_url, echo=settings.sql_echo)
    app.state.session_factory = make_session_factory(app.state.engine)

    app.state.provider_resolver = CredentialResolver(settings)
    app.state.provider_registry = ProviderRegistry(settings, app.state.provider_resolver)
    app.state.credential_store = PersistentCredentialStore(SecretCipher.from_settings(settings))
    app.state.template_registry = TemplateRegistry(settings.templates_dir)
    app.state.doi_resolver = DOIResolver(
        timeout_seconds=settings.doi_lookup_timeout_seconds,
        user_agent=settings.doi_user_agent,
    )
    app.state.export_store = ExportHistoryStore(
        settings.export_dir,
        retention_days=settings.document_retention_days,
    )

    # Autenticação opt-in e rate limiting.
    app.state.token_service = TokenService(settings.secret_key) if settings.secret_key else None
    app.state.rate_limiters = {
        "login": SlidingWindowLimiter(
            limit=settings.rate_limit_login_per_minute, window_seconds=60.0
        ),
        "humanize": SlidingWindowLimiter(
            limit=settings.rate_limit_humanize_per_minute, window_seconds=60.0
        ),
    }

    app.include_router(api_router, prefix=settings.api_prefix)

    @app.exception_handler(HumanizaError)
    async def _domain_error_handler(request: Request, exc: HumanizaError) -> JSONResponse:
        logger.warning("erro.dominio", rota=request.url.path, codigo=exc.code)
        return JSONResponse(status_code=exc.status_code, content=exc.to_payload())

    return app


app = create_app()
