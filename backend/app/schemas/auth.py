"""Schemas de autenticação."""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{3,80}$")


class RegisterRequest(BaseModel):
    """Registro de novo usuário."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("username")
    @classmethod
    def _validar_username(cls, valor: str) -> str:
        if not USERNAME_PATTERN.match(valor):
            raise ValueError("username deve conter apenas letras, números, ponto, hífen ou _")
        return valor


class LoginRequest(BaseModel):
    """Credenciais de login."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    """Representação pública de um usuário (sem hash de senha)."""

    model_config = ConfigDict(frozen=True)

    id: str
    username: str


class TokenResponse(BaseModel):
    """Token de acesso emitido no login."""

    model_config = ConfigDict(frozen=True)

    access_token: str
    token_type: str = "bearer"  # noqa: S105  (tipo de token, não um segredo)
