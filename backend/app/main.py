"""Ponto de entrada da API.

A aplicação expõe apenas a API e os arquivos estáticos do frontend quando
buildado. Cada versão de rota vive em ``app/api/v1`` e é registrada em
:mod:`app.api.router`.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import get_settings
from app.core.errors import HumanizaError
from app.core.logging import configure_logging, get_logger
from app.services.providers.credentials import CredentialResolver
from app.services.providers.registry import ProviderRegistry

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Inicialização e encerramento da aplicação."""
    settings = get_settings()
    configure_logging(settings)
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    settings.export_dir.mkdir(parents=True, exist_ok=True)
    logger.info(
        "aplicacao.iniciada",
        app=settings.app_name,
        versao=settings.app_version,
        ambiente=settings.environment,
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

    # Estado compartilhado: registro de provedores e resolvedor de credenciais.
    app.state.provider_resolver = CredentialResolver(settings)
    app.state.provider_registry = ProviderRegistry(settings, app.state.provider_resolver)

    app.include_router(api_router, prefix=settings.api_prefix)

    @app.exception_handler(HumanizaError)
    async def _domain_error_handler(request: Request, exc: HumanizaError) -> JSONResponse:
        logger.warning("erro.dominio", rota=request.url.path, codigo=exc.code)
        return JSONResponse(status_code=exc.status_code, content=exc.to_payload())

    return app


app = create_app()
