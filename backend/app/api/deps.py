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


def make_rate_limit_dependency(
    limiter_name: str,
    *,
    key_extractor: Callable[[Request], str] = client_ip,
) -> Callable[[Request], None]:
    """Cria uma dependência de limite de requisições apontando para um limiter."""

    def dependency(request: Request) -> None:
        limiter = request.app.state.rate_limiters.get(limiter_name)
        if limiter is None:
            return
        if not isinstance(limiter, SlidingWindowLimiter):
            return
        if not limiter.allow(key_extractor(request)):
            raise RateLimitError("limite de requisições excedido")

    return dependency
