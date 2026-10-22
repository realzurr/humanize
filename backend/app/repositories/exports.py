"""Repositório de exportações persistidas, com isolamento por ``owner_id``."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.export import Export


class ExportRepository:
    """Acesso a dados de ``Export`` com isolamento por proprietário."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(
        self,
        *,
        export_id: str,
        document_id: str | None,
        owner_id: str | None,
        fmt: str,
        filename: str,
        sha256: str,
        size_bytes: int,
        template_id: str,
        institution_id: str | None = None,
        warnings: tuple[str, ...] | list[str] = (),
        limitations: tuple[str, ...] | list[str] = (),
        created_at: datetime | None = None,
    ) -> Export:
        """Grava ou atualiza os metadados de uma exportação no banco."""
        existente = self._session.get(Export, export_id)
        if existente is None:
            registro = Export(
                id=export_id,
                document_id=document_id,
                owner_id=owner_id,
                format=fmt,
                filename=filename,
                sha256=sha256,
                size_bytes=size_bytes,
                template_id=template_id,
                institution_id=institution_id,
                warnings_json=json.dumps(list(warnings), ensure_ascii=False),
                limitations_json=json.dumps(list(limitations), ensure_ascii=False),
            )
            if created_at is not None:
                registro.created_at = created_at
            self._session.add(registro)
        else:
            registro = existente
            registro.sha256 = sha256
            registro.size_bytes = size_bytes
            registro.warnings_json = json.dumps(list(warnings), ensure_ascii=False)
            registro.limitations_json = json.dumps(list(limitations), ensure_ascii=False)
        self._session.commit()
        self._session.refresh(registro)
        return registro

    def get(self, export_id: str, owner_id: str | None = None) -> Export | None:
        registro = self._session.get(Export, export_id)
        if registro is None:
            return None
        if registro.owner_id != owner_id:
            return None
        return registro

    def list_for_owner(
        self,
        owner_id: str | None = None,
        *,
        document_id: str | None = None,
    ) -> list[Export]:
        stmt = select(Export)
        if owner_id is None:
            stmt = stmt.where(Export.owner_id.is_(None))
        else:
            stmt = stmt.where(Export.owner_id == owner_id)
        if document_id is not None:
            stmt = stmt.where(Export.document_id == document_id)
        stmt = stmt.order_by(Export.created_at.desc())
        return list(self._session.scalars(stmt))

    def prune_expired(
        self,
        *,
        now: datetime,
        retention_days: int,
        owner_id: str | None = None,
        all_owners: bool = False,
        export_dir: Path | None = None,
    ) -> int:
        """Remove exportações expiradas (linha e, se ``export_dir`` vier, o arquivo).

        Sem ``all_owners``, restringe a ``owner_id`` (``None`` = modo local). O arquivo
        só é apagado após o commit, para não perder o binário se a transação falhar.
        """
        limite = now - timedelta(days=retention_days)
        stmt = select(Export).where(Export.created_at < limite)
        if not all_owners:
            if owner_id is None:
                stmt = stmt.where(Export.owner_id.is_(None))
            else:
                stmt = stmt.where(Export.owner_id == owner_id)
        expirados = list(self._session.scalars(stmt))
        nomes = [item.filename for item in expirados]
        for item in expirados:
            self._session.delete(item)
        self._session.commit()
        if export_dir is not None:
            _remover_arquivos(export_dir, nomes)
        return len(expirados)


def _remover_arquivos(export_dir: Path, nomes: list[str]) -> None:
    raiz = export_dir.resolve()
    for nome in nomes:
        caminho = (raiz / nome).resolve()
        if caminho.is_relative_to(raiz):
            caminho.unlink(missing_ok=True)
