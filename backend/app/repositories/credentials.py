"""Repositório de credenciais persistidas de provedores (cifradas em repouso)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.credential import ProviderCredential


class CredentialRepository:
    """Persistência de ``ProviderCredential`` (apenas ciphertext + ``last4``)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert(
        self,
        provider: str,
        ciphertext: str,
        last4: str,
        *,
        owner_id: str | None = None,
    ) -> ProviderCredential:
        cred = self.get(provider, owner_id)
        if cred is None:
            cred = ProviderCredential(
                provider=provider, owner_id=owner_id, ciphertext=ciphertext, last4=last4
            )
            self._session.add(cred)
        else:
            cred.ciphertext = ciphertext
            cred.last4 = last4
        self._session.commit()
        self._session.refresh(cred)
        return cred

    def get(self, provider: str, owner_id: str | None = None) -> ProviderCredential | None:
        return self._session.scalar(
            select(ProviderCredential).where(
                ProviderCredential.provider == provider,
                ProviderCredential.owner_id == owner_id,
            )
        )

    def delete(self, provider: str, owner_id: str | None = None) -> bool:
        cred = self.get(provider, owner_id)
        if cred is None:
            return False
        self._session.delete(cred)
        self._session.commit()
        return True

    def list_for_owner(self, owner_id: str | None = None) -> list[ProviderCredential]:
        stmt = select(ProviderCredential)
        if owner_id is None:
            stmt = stmt.where(ProviderCredential.owner_id.is_(None))
        else:
            stmt = stmt.where(ProviderCredential.owner_id == owner_id)
        return list(self._session.scalars(stmt))
