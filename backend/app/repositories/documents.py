"""Repositório de documentos persistidos, com isolamento por dono e retenção."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document


class DocumentRepository:
    """Acesso a dados de ``Document`` com isolamento ``owner_id``."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, original_text: str, *, owner_id: str | None = None) -> Document:
        document = Document(owner_id=owner_id, original_text=original_text)
        self._session.add(document)
        self._session.commit()
        self._session.refresh(document)
        return document

    def get(self, document_id: str, owner_id: str | None = None) -> Document | None:
        document = self._session.get(Document, document_id)
        if document is None:
            return None
        # Isolamento: um documento só é visível para o próprio dono.
        if document.owner_id != owner_id:
            return None
        return document

    def list_for_owner(self, owner_id: str | None = None) -> list[Document]:
        stmt = select(Document)
        if owner_id is None:
            stmt = stmt.where(Document.owner_id.is_(None))
        else:
            stmt = stmt.where(Document.owner_id == owner_id)
        return list(self._session.scalars(stmt).unique())

    def delete(self, document_id: str, owner_id: str | None = None) -> bool:
        document = self.get(document_id, owner_id)
        if document is None:
            return False
        self._session.delete(document)
        self._session.commit()
        return True

    def prune_expired(
        self,
        *,
        now: datetime,
        retention_days: int,
        owner_id: str | None = None,
    ) -> int:
        """Remove documentos cuja última atualização excede o prazo de retenção."""
        limite = now - timedelta(days=retention_days)
        stmt = select(Document).where(Document.updated_at < limite)
        if owner_id is None:
            stmt = stmt.where(Document.owner_id.is_(None))
        else:
            stmt = stmt.where(Document.owner_id == owner_id)
        expirados = list(self._session.scalars(stmt).unique())
        for documento in expirados:
            self._session.delete(documento)
        self._session.commit()
        return len(expirados)
