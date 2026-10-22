"""Primitivas de segurança: hash de senha e tokens de acesso assinados.

- Senhas: Argon2id (padrão) e PBKDF2-SHA256 (retrocompatível, via ``cryptography``),
  com salt aleatório e verificação em tempo constante. Nenhuma dependência externa
  adicional é necessária.
- Tokens: payload JSON compacto assinado com HMAC-SHA256 usando ``secret_key``
  (e suporte a ``previous_keys`` para rotação sem queda), com expiração embutida,
  ``iat``, ``jti`` único e revogação explícita em memória.

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
from typing import Any, Protocol

from cryptography.exceptions import InvalidKey
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

#: Iterações do PBKDF2 legado (OWASP recomenda >= 600k para SHA-256).
_PBKDF2_ITERATIONS = 600_000
#: Parâmetros OWASP para Argon2id (m=19456 KiB, t=2, p=1).
_ARGON2_MEMORY_KIB = 19_456
_ARGON2_ITERATIONS = 2
_ARGON2_LANES = 1
_SALT_BYTES = 16
_HASH_BYTES = 32

_ARGON2_ALGORITHM = "argon2id"
_PBKDF2_ALGORITHM = "pbkdf2_sha256"


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def hash_password(password: str, *, algorithm: str = _ARGON2_ALGORITHM) -> str:
    """Gera um hash de senha com Argon2id (padrão) ou PBKDF2-SHA256."""
    salt = os.urandom(_SALT_BYTES)
    raw = password.encode("utf-8")
    if algorithm == _ARGON2_ALGORITHM:
        kdf_argon = Argon2id(
            salt=salt,
            length=_HASH_BYTES,
            iterations=_ARGON2_ITERATIONS,
            lanes=_ARGON2_LANES,
            memory_cost=_ARGON2_MEMORY_KIB,
        )
        digest = kdf_argon.derive(raw)
        return (
            f"{_ARGON2_ALGORITHM}${_ARGON2_PARAMS_ATUAIS}${_b64encode(salt)}${_b64encode(digest)}"
        )

    if algorithm == _PBKDF2_ALGORITHM:
        kdf_pbkdf2 = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=_HASH_BYTES,
            salt=salt,
            iterations=_PBKDF2_ITERATIONS,
        )
        digest = kdf_pbkdf2.derive(raw)
        return f"{_PBKDF2_ALGORITHM}${_PBKDF2_ITERATIONS}${_b64encode(salt)}${_b64encode(digest)}"

    raise ValueError(f"algoritmo de hash não suportado: {algorithm}")


def verify_password(password: str, encoded: str) -> bool:
    """Verifica a senha contra o hash (Argon2id ou PBKDF2 legado) em tempo constante."""
    try:
        algoritmo, param_str, salt_b64, digest_b64 = encoded.split("$", 3)
        salt = _b64decode(salt_b64)
        expected = _b64decode(digest_b64)
        raw = password.encode("utf-8")

        if algoritmo == _ARGON2_ALGORITHM:
            kv = dict(item.split("=", 1) for item in param_str.split(","))
            kdf_argon = Argon2id(
                salt=salt,
                length=len(expected),
                iterations=int(kv["t"]),
                lanes=int(kv["p"]),
                memory_cost=int(kv["m"]),
            )
            kdf_argon.verify(raw, expected)
            return True

        if algoritmo == _PBKDF2_ALGORITHM:
            kdf_pbkdf2 = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=len(expected),
                salt=salt,
                iterations=int(param_str),
            )
            kdf_pbkdf2.verify(raw, expected)
            return True

        return False
    except (InvalidKey, ValueError, TypeError, KeyError, IndexError):
        return False


_ARGON2_PARAMS_ATUAIS = f"m={_ARGON2_MEMORY_KIB},t={_ARGON2_ITERATIONS},p={_ARGON2_LANES}"


def needs_rehash(encoded: str) -> bool:
    """Indica se o hash deve ser refeito: algoritmo legado ou parâmetros Argon2 desatualizados."""
    algoritmo, _, resto = encoded.partition("$")
    if algoritmo != _ARGON2_ALGORITHM:
        return True
    params, _, _ = resto.partition("$")
    return params != _ARGON2_PARAMS_ATUAIS


class RevocationStore(Protocol):
    """Armazenamento de revogações de tokens.

    Mantido como contrato em ``core`` para que a segurança não dependa do ORM;
    a implementação persistida fica em ``app.repositories.revocations``.
    """

    def revoke_jti(self, jti: str, expires_at: float) -> None:
        """Revoga um ``jti`` até ``expires_at`` (epoch)."""

    def is_jti_revoked(self, jti: str) -> bool:
        """Indica se o ``jti`` foi revogado."""

    def revoke_subject(self, subject: str, before: float) -> None:
        """Invalida tokens de ``subject`` emitidos até ``before`` (epoch)."""

    def subject_revoked_before(self, subject: str) -> float | None:
        """Instante de corte de ``subject``, ou ``None``."""

    def prune(self, *, now: float, max_token_age: float) -> None:
        """Remove revogações que não podem mais afetar nenhum token válido."""


class InMemoryRevocationStore:
    """Revogações em memória do processo (testes e instância única)."""

    def __init__(self) -> None:
        self._jtis: dict[str, float] = {}
        self._subjects: dict[str, float] = {}

    def revoke_jti(self, jti: str, expires_at: float) -> None:
        self._jtis[jti] = expires_at

    def is_jti_revoked(self, jti: str) -> bool:
        return jti in self._jtis

    def revoke_subject(self, subject: str, before: float) -> None:
        self._subjects[subject] = before

    def subject_revoked_before(self, subject: str) -> float | None:
        return self._subjects.get(subject)

    def prune(self, *, now: float, max_token_age: float) -> None:
        self._jtis = {jti: exp for jti, exp in self._jtis.items() if exp >= now}
        limite = now - max_token_age
        self._subjects = {s: corte for s, corte in self._subjects.items() if corte >= limite}

    def __len__(self) -> int:
        return len(self._jtis)


class TokenService:
    """Emissão, verificação, rotação de chave e revogação de tokens HMAC-SHA256."""

    def __init__(
        self,
        secret_key: str,
        *,
        ttl_seconds: int = 3600,
        previous_keys: tuple[str, ...] | list[str] = (),
        revocation_store: RevocationStore | None = None,
    ) -> None:
        if not secret_key:
            raise ValueError("secret_key é obrigatória para emitir tokens")
        self._secret = secret_key.encode("utf-8")
        self._previous_secrets: tuple[bytes, ...] = tuple(
            k.encode("utf-8") for k in previous_keys if k
        )
        self._ttl_seconds = ttl_seconds
        self._revocations: RevocationStore = (
            revocation_store if revocation_store is not None else InMemoryRevocationStore()
        )

    def issue(self, subject: str) -> str:
        """Emite um token para o ``subject`` assinado com a chave primária."""
        now = time.time()
        payload: dict[str, Any] = {
            "sub": subject,
            "iat": now,
            "exp": int(now) + self._ttl_seconds,
            "jti": secrets.token_hex(8),
        }
        body = _b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        signature = self._sign(body, self._secret)
        return f"{body}.{signature}"

    def verify(self, token: str) -> str | None:
        """Valida o token (incluindo chaves em rotação e lista de revogação)."""
        payload = self._decode_verified_payload(token)
        if payload is None:
            return None
        subject = payload.get("sub")
        expires_at = payload.get("exp")
        jti = payload.get("jti")
        issued_at = payload.get("iat", 0.0)
        if not isinstance(subject, str) or not isinstance(expires_at, (int, float)):
            return None
        if expires_at < time.time():
            return None
        if isinstance(jti, str) and self._revocations.is_jti_revoked(jti):
            return None
        cutoff = self._revocations.subject_revoked_before(subject)
        if cutoff is not None and isinstance(issued_at, (int, float)) and issued_at <= cutoff:
            return None
        return subject

    def revoke_token(self, token: str) -> bool:
        """Revoga individualmente um token válido pelo seu ``jti``."""
        payload = self._decode_verified_payload(token)
        if payload is None:
            return False
        jti = payload.get("jti")
        expires_at = payload.get("exp")
        if not isinstance(jti, str) or not jti or not isinstance(expires_at, (int, float)):
            return False
        self._prune_revoked()
        self._revocations.revoke_jti(jti, float(expires_at))
        return True

    def revoke_subject(self, subject: str) -> None:
        """Invalida todos os tokens emitidos até o instante atual para ``subject``.

        Uso administrativo (ex.: desativar usuário); não há rota HTTP que o exponha.
        """
        self._prune_revoked()
        self._revocations.revoke_subject(subject, time.time())

    def _prune_revoked(self) -> None:
        self._revocations.prune(now=time.time(), max_token_age=self._ttl_seconds)

    def _decode_verified_payload(self, token: str) -> dict[str, Any] | None:
        try:
            body, signature = token.split(".", 1)
        except ValueError:
            return None
        if not self._signature_matches(body, signature):
            return None
        try:
            payload = json.loads(_b64decode(body).decode("utf-8"))
        except (ValueError, TypeError):
            return None
        return payload if isinstance(payload, dict) else None

    def _signature_matches(self, body: str, signature: str) -> bool:
        for secret in (self._secret, *self._previous_secrets):
            expected = self._sign(body, secret)
            if hmac.compare_digest(signature, expected):
                return True
        return False

    @staticmethod
    def _sign(body: str, secret: bytes) -> str:
        digest = hmac.new(secret, body.encode("ascii"), hashlib.sha256).digest()
        return _b64encode(digest)
