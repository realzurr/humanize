"""Dependências FastAPI compartilhadas (autenticação e rate limiting).

A autenticação é **opt-in**: com ``Settings.auth_enabled=False`` (local/desenvolvimento)
as rotas operam sem usuário (modo anterior à Onda 8); com ``auth_enabled=True``
exige-se um ``Authorization: Bearer <token>`` válido e o ``owner_id`` do usuário
isola os dados.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, cast

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.database import get_session
from app.core.errors import RateLimitError, UnauthorizedError
from app.core.ratelimit import SlidingWindowLimiter, client_ip
from app.core.security import TokenService
from app.models.user import User
from app.services.providers.credentials import CredentialResolver
from app.services.providers.persistent_credentials import PersistentCredentialStore


def _settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def _token_service(request: Request) -> TokenService | None:
    return cast(TokenService | None, request.app.state.token_service)


def get_current_user(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
) -> User | None:
    """Devolve o usuário autenticado, ou ``None`` no modo local (sem autenticação)."""
    settings = _settings(request)
    if not settings.auth_enabled:
        return None

    token_service = _token_service(request)
    if token_service is None:
        raise UnauthorizedError("autenticação não configurada")

    authorization = request.headers.get("authorization", "")
    if not authorization.startswith("Bearer "):
        raise UnauthorizedError("credencial ausente")
    token = authorization.removeprefix("Bearer ").strip()
    subject = token_service.verify(token)
    if subject is None:
        raise UnauthorizedError("credencial inválida ou expirada")

    user = session.get(User, subject)
    if user is None or not user.is_active:
        raise UnauthorizedError("usuário inexistente ou inativo")
    return user


def owner_id_of(user: User | None) -> str | None:
    """Deriva o ``owner_id`` a partir do usuário (``None`` no modo local)."""
    return user.id if user is not None else None


def resolve_provider_key(
    request: Request,
    session: Session,
    provider_id: str,
    owner_id: str | None,
) -> str | None:
    """Resolve a chave de um provedor para o dono (ambiente → sessão → banco).

    Fecha o `GAP-02`: a credencial persistida no banco é usada quando não há
    chave em ambiente nem em sessão, permitindo que o ``ProviderRegistry.build``
    receba a chave do usuário autenticado.
    """
    resolver = cast(CredentialResolver, request.app.state.provider_resolver)
    chave = resolver.resolve(provider_id, owner_id=owner_id)
    if chave:
        return chave
    settings = cast(Settings, request.app.state.settings)
    if settings.credential_encryption_enabled:
        store = cast(PersistentCredentialStore, request.app.state.credential_store)
        return store.resolve_plaintext(session, provider_id, owner_id=owner_id)
    return None


def make_rate_limit_dependency(limiter_name: str) -> Callable[[Request], None]:
    """Cria uma dependência de limite de requisições apontando para um limiter.

    A chave de limitação é o IP do cliente, respeitando ``Settings.behind_proxy``
    para só confiar em ``X-Forwarded-For`` quando atrás de um proxy reverso.
    """

    def dependency(request: Request) -> None:
        limiter = request.app.state.rate_limiters.get(limiter_name)
        if limiter is None or not isinstance(limiter, SlidingWindowLimiter):
            return
        key = client_ip(request, trust_proxy=_settings(request).behind_proxy)
        if not limiter.allow(key):
            raise RateLimitError("limite de requisições excedido")

    return dependency
