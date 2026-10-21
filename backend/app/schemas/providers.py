"""Schemas da API de provedores.

A API expõe apenas **indicadores** de credencial (``configurado`` e ``last4``)
e nunca o valor da chave. A chave entra por ``api_key`` no corpo e é
imediatamente entregue ao :class:`CredentialResolver`, que a cifra em memória.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

MAX_KEY_LENGTH = 512


class ProviderOut(BaseModel):
    """Descrição pública de um provedor."""

    model_config = ConfigDict(frozen=True)

    id: str
    nome: str
    requer_chave: bool
    configurado: bool
    last4: str = ""
    fonte: str = ""


class ModelOut(BaseModel):
    """Descrição de um modelo disponível."""

    model_config = ConfigDict(frozen=True)

    id: str
    nome: str = ""
    janela_contexto: int | None = None
    max_tokens_saida: int | None = None
    suporta_streaming: bool = False
    suporta_json: bool = False
    custo_entrada_1k: float | None = None
    custo_saida_1k: float | None = None
    obsoleto: bool = False


class CredentialIn(BaseModel):
    """Corpo da requisição de armazenamento de credencial."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    api_key: str = Field(min_length=1, max_length=MAX_KEY_LENGTH)


class CredentialOut(BaseModel):
    """Indicador público do estado de uma credencial."""

    model_config = ConfigDict(frozen=True)

    provedor: str
    configurado: bool
    last4: str = ""
    fonte: str = ""
