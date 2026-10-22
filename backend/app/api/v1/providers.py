"""Rotas de configuração de provedores de LLM (v1).

A chave de API entra por ``POST /providers/{id}/credentials``. Ela é mantida
em sessão (cifrada em memória) para uso imediato e, quando a persistência
está habilitada, gravada cifrada (AES-GCM) na tabela ``provider_credentials``
— isolada por ``owner_id``. A API **nunca** devolve o valor da chave: apenas
``configurado`` e ``last4``.
"""

from __future__ import annotations

from typing import Annotated, cast

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, owner_id_of
from app.core.config import Settings
from app.core.database import get_session
from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.models.user import User
from app.schemas.providers import CredentialIn, CredentialOut, ModelOut, ProviderOut
from app.services.providers.base import ModelInfo, ProviderId
from app.services.providers.credentials import CredentialStatus
from app.services.providers.persistent_credentials import PersistentCredentialStore
from app.services.providers.registry import AVAILABLE_PROVIDERS, ProviderRegistry

router = APIRouter(tags=["provedores"])

logger = get_logger(__name__)


def _registro(request: Request) -> ProviderRegistry:
    return cast(ProviderRegistry, request.app.state.provider_registry)


def _settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def _credential_store(request: Request) -> PersistentCredentialStore:
    return cast(PersistentCredentialStore, request.app.state.credential_store)


def _validar_provider(provider_id: str) -> ProviderId:
    try:
        enum = ProviderId(provider_id)
    except ValueError as exc:
        raise NotFoundError(f"provedor desconhecido: {provider_id}") from exc
    if enum not in AVAILABLE_PROVIDERS:
        raise NotFoundError(f"provedor indisponível: {provider_id}")
    return enum


def _estado_combinado(
    request: Request,
    session: Session,
    enum: ProviderId,
    owner_id: str | None,
) -> CredentialStatus:
    """Combina ambiente → sessão → banco para o estado público da credencial."""
    estado = _registro(request).status(enum, owner_id=owner_id)
    if estado.configured:
        return estado
    if _settings(request).credential_encryption_enabled:
        db = _credential_store(request).status(session, str(enum), owner_id=owner_id)
        if db.configured:
            return db
    return estado


@router.get("/providers", response_model=list[ProviderOut])
async def listar_provedores(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    usuario: Annotated[User | None, Depends(get_current_user)],
) -> list[ProviderOut]:
    """Lista os provedores com o estado da credencial (sem a chave)."""
    owner_id = owner_id_of(usuario)
    registro = _registro(request)
    saida: list[ProviderOut] = []
    for enum in AVAILABLE_PROVIDERS:
        base = registro.describe(enum)
        estado = _estado_combinado(request, session, enum, owner_id)
        saida.append(
            ProviderOut(
                id=str(enum),
                nome=str(base["nome"]),
                requer_chave=bool(base["requer_chave"]),
                configurado=estado.configured,
                last4=estado.last4,
                fonte=estado.source,
            )
        )
    return saida


@router.get("/providers/{provider_id}/models", response_model=list[ModelOut])
async def listar_modelos(provider_id: str, request: Request) -> list[ModelOut]:
    """Lista os modelos conhecidos de um provedor."""
    enum = _validar_provider(provider_id)
    registro = _registro(request)
    modelos = await registro.build(enum).list_models()
    return [_modelo_para_saida(modelo) for modelo in modelos]


@router.post("/providers/{provider_id}/credentials", response_model=CredentialOut)
async def armazenar_credencial(
    provider_id: str,
    corpo: CredentialIn,
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    usuario: Annotated[User | None, Depends(get_current_user)],
) -> CredentialOut:
    """Armazena a credencial (sessão + banco cifrado) e devolve só o indicador."""
    enum = _validar_provider(provider_id)
    registro = _registro(request)
    owner_id = owner_id_of(usuario)
    estado = registro.status(enum, owner_id=owner_id)
    if estado.configured and estado.source == "env":
        # Não sobrescreve chave de ambiente; apenas reporta que já existe.
        return _status_para_saida(estado)

    estado = request.app.state.provider_resolver.store(enum, corpo.api_key, owner_id=owner_id)
    if _settings(request).credential_encryption_enabled:
        _credential_store(request).save(session, str(enum), corpo.api_key, owner_id=owner_id)
    logger.info(
        "credencial.armazenada",
        provedor=str(enum),
        configurada=True,
        fonte=estado.source,
    )
    return _status_para_saida(estado)


@router.delete("/providers/{provider_id}/credentials", response_model=CredentialOut)
async def remover_credencial(
    provider_id: str,
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    usuario: Annotated[User | None, Depends(get_current_user)],
) -> CredentialOut:
    """Remove a credencial de sessão e a persistida (a de ambiente permanece)."""
    enum = _validar_provider(provider_id)
    owner_id = owner_id_of(usuario)
    estado = request.app.state.provider_resolver.delete(enum, owner_id=owner_id)
    if _settings(request).credential_encryption_enabled:
        _credential_store(request).delete(session, str(enum), owner_id=owner_id)
    logger.info("credencial.removida", provedor=str(enum), configurada=estado.configured)
    return _status_para_saida(estado)


def _modelo_para_saida(modelo: ModelInfo) -> ModelOut:
    return ModelOut(
        id=modelo.id,
        nome=modelo.display_name,
        janela_contexto=modelo.context_window,
        max_tokens_saida=modelo.max_output_tokens,
        suporta_streaming=modelo.supports_streaming,
        suporta_json=modelo.supports_json_mode,
        custo_entrada_1k=modelo.input_cost_per_1k,
        custo_saida_1k=modelo.output_cost_per_1k,
        obsoleto=modelo.deprecated,
    )


def _status_para_saida(estado: CredentialStatus) -> CredentialOut:
    return CredentialOut(
        provedor=estado.provider,
        configurado=estado.configured,
        last4=estado.last4,
        fonte=estado.source,
    )
