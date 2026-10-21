"""Rotas de configuração de provedores de LLM (v1).

A chave de API entra por ``POST /providers/{id}/credentials`` e é armazenada
na sessão (cifrada em memória). A API **nunca** devolve o valor da chave —
apenas ``configurado`` e ``last4``. A exclusão remove a credencial de sessão;
uma credencial de ambiente (variável de ambiente) permanece.
"""

from __future__ import annotations

from typing import cast

from fastapi import APIRouter, Request

from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.schemas.providers import CredentialIn, CredentialOut, ModelOut, ProviderOut
from app.services.providers.base import ModelInfo, ProviderId
from app.services.providers.credentials import CredentialStatus
from app.services.providers.registry import AVAILABLE_PROVIDERS, ProviderRegistry

router = APIRouter(tags=["provedores"])

logger = get_logger(__name__)


def _registro(request: Request) -> ProviderRegistry:
    return cast(ProviderRegistry, request.app.state.provider_registry)


def _validar_provider(provider_id: str) -> ProviderId:
    try:
        enum = ProviderId(provider_id)
    except ValueError as exc:
        raise NotFoundError(f"provedor desconhecido: {provider_id}") from exc
    if enum not in AVAILABLE_PROVIDERS:
        raise NotFoundError(f"provedor indisponível: {provider_id}")
    return enum


@router.get("/providers", response_model=list[ProviderOut])
async def listar_provedores(request: Request) -> list[ProviderOut]:
    """Lista os provedores com o estado da credencial (sem a chave)."""
    registro = _registro(request)
    return [ProviderOut(**registro.describe(enum)) for enum in AVAILABLE_PROVIDERS]


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
) -> CredentialOut:
    """Armazena a credencial na sessão e devolve apenas o indicador."""
    enum = _validar_provider(provider_id)
    registro = _registro(request)
    estado = registro.status(enum)
    if estado.configured and estado.source == "env":
        # Não sobrescreve chave de ambiente; apenas reporta que já existe.
        return _status_para_saida(estado)
    estado = request.app.state.provider_resolver.store(enum, corpo.api_key)
    logger.info(
        "credencial.armazenada",
        provedor=str(enum),
        configurada=True,
        fonte=estado.source,
    )
    return _status_para_saida(estado)


@router.delete("/providers/{provider_id}/credentials", response_model=CredentialOut)
async def remover_credencial(provider_id: str, request: Request) -> CredentialOut:
    """Remove a credencial de sessão do provedor."""
    enum = _validar_provider(provider_id)
    estado = request.app.state.provider_resolver.delete(enum)
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
