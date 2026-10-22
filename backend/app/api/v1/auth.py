"""Rotas de autenticação (v1).

Registro, login (com rate limiting para mitigar força bruta) e consulta do
usuário atual. O token é assinado com HMAC-SHA256 e tem validade configurável.
Nenhum hash de senha ou token é exposto nos logs ou nas respostas.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, make_rate_limit_dependency
from app.core.database import get_session
from app.core.errors import ConflictError, UnauthorizedError
from app.core.security import TokenService, hash_password, verify_password
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
    """Registra um novo usuário com senha hasheada (PBKDF2)."""
    repo = UserRepository(session)
    if repo.get_by_username(corpo.username) is not None:
        raise ConflictError(f"username já em uso: {corpo.username}")
    user = repo.create(corpo.username, hash_password(corpo.password))
    return UserOut(id=user.id, username=user.username)


@router.post("/auth/token", response_model=TokenResponse)
async def login(
    corpo: LoginRequest,
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    _: Annotated[None, Depends(login_rate_limit)],
) -> TokenResponse:
    """Autentica e emite um token de acesso."""
    token_service: TokenService | None = request.app.state.token_service
    if token_service is None:
        raise UnauthorizedError("autenticação não configurada")

    user = UserRepository(session).get_by_username(corpo.username)
    if user is None or not verify_password(corpo.password, user.password_hash):
        raise UnauthorizedError("credenciais inválidas")

    token = token_service.issue(user.id)
    return TokenResponse(access_token=token)


@router.get("/auth/me", response_model=UserOut)
async def eu(
    usuario: Annotated[User | None, Depends(get_current_user)],
) -> UserOut:
    """Devolve o usuário autenticado (ou 401 no modo com autenticação)."""
    if usuario is None:
        raise UnauthorizedError("autenticação necessária")
    return UserOut(id=usuario.id, username=usuario.username)
