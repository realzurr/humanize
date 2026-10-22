"""Primitivas de segurança: hash de senha e tokens de acesso assinados.

- Senhas: PBKDF2-SHA256 (via ``cryptography``), com salt aleatório e verificação
  em tempo constante. Nenhuma dependência nova é necessária.
- Tokens: payload JSON compacto assinado com HMAC-SHA256 usando ``secret_key``,
  com expiração embutida e ``jti`` único. Formato ``<body>.<signature>`` em
  base64url.

Nenhum segredo é retornado por estas funções nem registrado em log.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any

from cryptography.exceptions import InvalidKey
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

#: Iterações do PBKDF2 (OWASP recomenda >= 600k para SHA-256).
_PBKDF2_ITERATIONS = 600_000
_SALT_BYTES = 16
_HASH_BYTES = 32

_PASSWORD_ALGORITHM = "pbkdf2_sha256"  # noqa: S105  (nome do algoritmo, não uma senha)


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def hash_password(password: str) -> str:
    """Gera um hash de senha no formato ``pbkdf2_sha256$iters$salt$digest``."""
    salt = os.urandom(_SALT_BYTES)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=_HASH_BYTES,
        salt=salt,
        iterations=_PBKDF2_ITERATIONS,
    )
    digest = kdf.derive(password.encode("utf-8"))
    return f"{_PASSWORD_ALGORITHM}${_PBKDF2_ITERATIONS}${_b64encode(salt)}${_b64encode(digest)}"


def verify_password(password: str, encoded: str) -> bool:
    """Verifica a senha contra o hash, em tempo constante."""
    try:
        algoritmo, iteracoes, salt_b64, digest_b64 = encoded.split("$", 3)
        if algoritmo != _PASSWORD_ALGORITHM:
            return False
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=_HASH_BYTES,
            salt=_b64decode(salt_b64),
            iterations=int(iteracoes),
        )
        kdf.verify(password.encode("utf-8"), _b64decode(digest_b64))
        return True
    except (InvalidKey, ValueError, TypeError, IndexError):
        return False


class TokenService:
    """Emissão e verificação de tokens de acesso assinados (HMAC-SHA256)."""

    def __init__(self, secret_key: str, *, ttl_seconds: int = 3600) -> None:
        if not secret_key:
            raise ValueError("secret_key é obrigatória para emitir tokens")
        self._secret = secret_key.encode("utf-8")
        self._ttl_seconds = ttl_seconds

    def issue(self, subject: str) -> str:
        """Emite um token para o ``subject`` (identificador do usuário)."""
        payload: dict[str, Any] = {
            "sub": subject,
            "exp": int(time.time()) + self._ttl_seconds,
            "jti": secrets.token_hex(8),
        }
        body = _b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        signature = self._sign(body)
        return f"{body}.{signature}"

    def verify(self, token: str) -> str | None:
        """Valida o token e devolve o ``subject``, ou ``None`` se inválido."""
        try:
            body, signature = token.split(".", 1)
        except ValueError:
            return None
        expected = self._sign(body)
        if not hmac.compare_digest(signature, expected):
            return None
        try:
            payload = json.loads(_b64decode(body).decode("utf-8"))
        except (ValueError, TypeError):
            return None
        if not isinstance(payload, dict):
            return None
        subject = payload.get("sub")
        expires_at = payload.get("exp")
        if not isinstance(subject, str) or not isinstance(expires_at, (int, float)):
            return None
        if expires_at < time.time():
            return None
        return subject

    def _sign(self, body: str) -> str:
        digest = hmac.new(self._secret, body.encode("ascii"), hashlib.sha256).digest()
        return _b64encode(digest)
