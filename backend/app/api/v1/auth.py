"""Rotas de autenticação (v1).

Registro, login (com rate limiting para mitigar força bruta) e consulta do
usuário atual. O token é assinado com HMAC-SHA256 e tem validade configurável.
Nenhum hash de senha ou token é exposto nos logs ou nas respostas.
"""

from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, make_rate_limit_dependency
from app.core.database import get_session
from app.core.errors import ConflictError, UnauthorizedError
from app.core.security import TokenService, hash_password, needs_rehash, verify_password
from app.models.user import User
from app.repositories.users import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut

router = APIRouter(tags=["autenticação"])

login_rate_limit = make_rate_limit_dependency("login")


@router.post("/auth/register", response_model=UserOut, status_code=201)
async def registrar(
    corpo: RegisterRequest,
    session: Annotated[Session, Depends(get_session)],
) -> UserOut:
    """Registra um novo usuário com senha hasheada (Argon2id)."""
    repo = UserRepository(session)
    if repo.get_by_username(corpo.username) is not None:
        raise ConflictError(f"username já em uso: {corpo.username}")
    # Argon2id é intencionalmente custoso (CPU + 19 MiB): fora do event loop.
    senha_hash = await asyncio.to_thread(hash_password, corpo.password)
    user = repo.create(corpo.username, senha_hash)
    return UserOut(id=user.id, username=user.username)


@router.post("/auth/token", response_model=TokenResponse)
async def login(
    corpo: LoginRequest,
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    _: Annotated[None, Depends(login_rate_limit)],
) -> TokenResponse:
    """Autentica, atualiza hashes legados (PBKDF2 -> Argon2id) e emite um token."""
    token_service: TokenService | None = request.app.state.token_service
    if token_service is None:
        raise UnauthorizedError("autenticação não configurada")

    user = UserRepository(session).get_by_username(corpo.username)
    if user is None or not await asyncio.to_thread(
        verify_password, corpo.password, user.password_hash
    ):
        raise UnauthorizedError("credenciais inválidas")

    if needs_rehash(user.password_hash):
        user.password_hash = await asyncio.to_thread(hash_password, corpo.password)
        session.commit()

    token = token_service.issue(user.id)
    return TokenResponse(access_token=token)


@router.post("/auth/logout", status_code=204)
async def logout(
    request: Request,
    _usuario: Annotated[User | None, Depends(get_current_user)],
) -> Response:
    """Revoga o token de acesso atual (se enviado no cabeçalho Authorization)."""
    token_service: TokenService | None = request.app.state.token_service
    auth_header = request.headers.get("authorization", "")
    if token_service is not None and auth_header.lower().startswith("bearer "):
        raw_token = auth_header[7:].strip()
        token_service.revoke_token(raw_token)
    return Response(status_code=204)


@router.post("/auth/logout-all", status_code=204)
async def logout_todas_as_sessoes(
    request: Request,
    usuario: Annotated[User | None, Depends(get_current_user)],
) -> Response:
    """Revoga todos os tokens do próprio usuário (ex.: após suspeita de vazamento).

    Atua apenas sobre o usuário autenticado; revogar outros usuários exige um
    papel administrativo que ainda não existe (ver ``docs/ROADMAP.md``).
    """
    token_service: TokenService | None = request.app.state.token_service
    if usuario is None or token_service is None:
        raise UnauthorizedError("autenticação necessária para encerrar todas as sessões")
    token_service.revoke_subject(usuario.id)
    return Response(status_code=204)


@router.get("/auth/me", response_model=UserOut)
async def eu(
    usuario: Annotated[User | None, Depends(get_current_user)],
) -> UserOut:
    """Devolve o usuário autenticado (ou 401 no modo com autenticação)."""
    if usuario is None:
        raise UnauthorizedError("autenticação necessária")
    return UserOut(id=usuario.id, username=usuario.username)
