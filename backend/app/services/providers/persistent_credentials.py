"""Persistência de credenciais de provedores em banco (AES-GCM em repouso).

Complementa o :class:`CredentialResolver` (ambiente + sessão em memória) com a
camada durável: o ciphertext é gravado na tabela ``provider_credentials`` e a
chave de criptografia fica **fora** do banco (``Settings.encryption_key``).
Apenas ``last4`` é exposto, nunca o valor em claro.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.errors import ValidationError
from app.repositories.credentials import CredentialRepository
from app.services.providers.credentials import CredentialStatus, SecretCipher, last4


class PersistentCredentialStore:
    """Armazenamento durável de credenciais cifradas, isolado por ``owner_id``."""

    def __init__(self, cipher: SecretCipher) -> None:
        self._cipher = cipher

    @property
    def available(self) -> bool:
        return self._cipher.available

    def save(
        self,
        session: Session,
        provider: str,
        key: str,
        *,
        owner_id: str | None = None,
    ) -> CredentialStatus:
        if not self._cipher.available:
            raise ValidationError("criptografia de credenciais não configurada")
        token = self._cipher.encrypt(key)
        CredentialRepository(session).upsert(provider, token, last4(key), owner_id=owner_id)
        return CredentialStatus(
            provider=provider, configured=True, last4=last4(key), source="database"
        )

    def status(
        self,
        session: Session,
        provider: str,
        *,
        owner_id: str | None = None,
    ) -> CredentialStatus:
        cred = CredentialRepository(session).get(provider, owner_id)
        if cred is None:
            return CredentialStatus(provider=provider, configured=False)
        return CredentialStatus(
            provider=provider, configured=True, last4=cred.last4, source="database"
        )

    def delete(
        self,
        session: Session,
        provider: str,
        *,
        owner_id: str | None = None,
    ) -> CredentialStatus:
        CredentialRepository(session).delete(provider, owner_id)
        return CredentialStatus(provider=provider, configured=False)
