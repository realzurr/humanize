"""Ponto de entrada da API.

A aplicação expõe a API e os arquivos estáticos do frontend quando buildado.
Cada versão de rota vive em ``app/api/v1`` e é registrada em
:mod:`app.api.router`. A Onda 8 adiciona a camada de persistência relacional,
autenticação opt-in, rate limiting e armazenamento durável de credenciais.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from datetime import UTC, datetime, timedelta

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app import models  # noqa: F401  (registro dos modelos no Base.metadata)
from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.database import Base, make_engine, make_session_factory
from app.core.errors import HumanizaError
from app.core.logging import configure_logging, get_logger
from app.core.ratelimit import build_rate_limiter, connect_redis
from app.core.security import InMemoryRevocationStore, RevocationStore, TokenService
from app.models.document import Document
from app.repositories.exports import ExportRepository
from app.repositories.revocations import SqlRevocationStore
from app.services.academic.templates import TemplateRegistry
from app.services.document_export.writer import ExportHistoryStore
from app.services.ingestion.upload import prune_expired_uploads
from app.services.providers.credentials import CredentialResolver, SecretCipher
from app.services.providers.persistent_credentials import PersistentCredentialStore
from app.services.providers.registry import ProviderRegistry
from app.services.references.doi import DOIResolver

logger = get_logger(__name__)


def run_retention_sweep(app: FastAPI, *, now: datetime | None = None) -> dict[str, int]:
    """Executa uma varredura de retenção sobre documentos, exportações e uploads."""
    settings: Settings = getattr(app.state, "settings", None) or get_settings()
    ref_utc = now if now is not None else datetime.now(UTC)
    if ref_utc.tzinfo is None:
        ref_utc = ref_utc.replace(tzinfo=UTC)
    ref_naive = ref_utc.replace(tzinfo=None)
    limite = ref_naive - timedelta(days=settings.document_retention_days)

    docs_removidos = 0
    exports_orm_removidos = 0
    with app.state.session_factory() as session:
        expirados_docs = list(
            session.scalars(select(Document).where(Document.updated_at < limite)).unique()
        )
        for doc in expirados_docs:
            session.delete(doc)
        docs_removidos = len(expirados_docs)

        session.commit()
        exports_orm_removidos = ExportRepository(session).prune_expired(
            now=ref_naive,
            retention_days=settings.document_retention_days,
            all_owners=True,
            export_dir=settings.export_dir,
        )

    exports_disco_removidos = app.state.export_store.prune_expired(now=ref_utc)
    uploads_removidos = prune_expired_uploads(
        settings.storage_dir / "uploads",
        retention_days=settings.document_retention_days,
        now_epoch=ref_utc.timestamp(),
    )
    return {
        "documents": docs_removidos,
        "exports_orm": exports_orm_removidos,
        "exports_disk": exports_disco_removidos,
        "uploads": uploads_removidos,
    }


async def _loop_retencao(app: FastAPI, intervalo_segundos: int) -> None:
    while True:
        await asyncio.sleep(intervalo_segundos)
        # Uma falha pontual (ex.: banco indisponível) não pode encerrar a rotina.
        try:
            resumo = await asyncio.to_thread(run_retention_sweep, app)
        except Exception:
            logger.exception("retencao.varredura_falhou")
            continue
        logger.info("retencao.varredura_concluida", **resumo)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Inicialização e encerramento da aplicação."""
    settings: Settings = getattr(app.state, "settings", None) or get_settings()
    configure_logging(settings)
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    settings.export_dir.mkdir(parents=True, exist_ok=True)

    _avisar_configuracao_invalida(settings)

    # Em produção as tabelas vêm de migrações Alembic; em desenvolvimento e
    # teste, o create_all é usado por conveniência.
    if not settings.is_production:
        Base.metadata.create_all(app.state.engine)

    tarefa_retencao: asyncio.Task[None] | None = None
    if settings.retention_sweep_interval_seconds > 0:
        tarefa_retencao = asyncio.create_task(
            _loop_retencao(app, settings.retention_sweep_interval_seconds)
        )

    logger.info(
        "aplicacao.iniciada",
        app=settings.app_name,
        versao=settings.app_version,
        ambiente=settings.environment,
        autenticacao=settings.auth_enabled,
    )
    try:
        yield
    finally:
        if tarefa_retencao is not None:
            tarefa_retencao.cancel()
            with suppress(asyncio.CancelledError):
                await tarefa_retencao
        logger.info("aplicacao.encerrada")


def _avisar_configuracao_invalida(settings: Settings) -> None:
    """Loga avisos para combinações de configuração que quebram em runtime.

    Evita "footguns" de segurança: habilitar autenticação sem ``secret_key``
    (impede a emissão de tokens), habilitar criptografia de credenciais sem
    ``encryption_key`` válida (faz ``POST /providers/{id}/credentials`` falhar),
    ou executar em produção sem ``auth_enabled``/``behind_proxy``.
    """
    if settings.auth_enabled and not settings.secret_key:
        logger.warning(
            "seguranca.configuracao_invalida",
            detalhe="auth_enabled=true sem secret_key; tokens não podem ser emitidos",
        )
    if (
        settings.credential_encryption_enabled
        and not SecretCipher.from_settings(settings).available
    ):
        logger.warning(
            "seguranca.configuracao_invalida",
            detalhe="credential_encryption_enabled=true sem encryption_key válida",
        )
    if settings.is_production and not settings.auth_enabled:
        logger.warning(
            "seguranca.configuracao_invalida",
            detalhe="environment=production com auth_enabled=false; isolamento desabilitado",
        )
    if settings.is_production and not settings.behind_proxy:
        logger.warning(
            "seguranca.configuracao_invalida",
            detalhe=(
                "environment=production com behind_proxy=false; atrás de proxy reverso "
                "todos os clientes compartilharão o mesmo IP no rate limiter"
            ),
        )


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
    revogacoes: RevocationStore = (
        SqlRevocationStore(app.state.session_factory)
        if settings.revocation_backend == "database"
        else InMemoryRevocationStore()
    )
    app.state.token_service = (
        TokenService(
            settings.secret_key,
            ttl_seconds=settings.access_token_ttl_seconds,
            previous_keys=settings.previous_secret_keys,
            revocation_store=revogacoes,
        )
        if settings.secret_key
        else None
    )
    rl_db = settings.storage_dir / "ratelimit.db"
    redis_client = (
        connect_redis(settings.redis_url) if settings.rate_limit_backend == "redis" else None
    )
    app.state.rate_limiters = {
        "login": build_rate_limiter(
            limit=settings.rate_limit_login_per_minute,
            window_seconds=60.0,
            backend=settings.rate_limit_backend,
            namespace="login",
            sqlite_path=rl_db,
            redis_client=redis_client,
        ),
        "humanize": build_rate_limiter(
            limit=settings.rate_limit_humanize_per_minute,
            window_seconds=60.0,
            backend=settings.rate_limit_backend,
            namespace="humanize",
            sqlite_path=rl_db,
            redis_client=redis_client,
        ),
    }

    app.include_router(api_router, prefix=settings.api_prefix)

    @app.exception_handler(HumanizaError)
    async def _domain_error_handler(request: Request, exc: HumanizaError) -> JSONResponse:
        logger.warning("erro.dominio", rota=request.url.path, codigo=exc.code)
        return JSONResponse(status_code=exc.status_code, content=exc.to_payload())

    return app


app = create_app()
