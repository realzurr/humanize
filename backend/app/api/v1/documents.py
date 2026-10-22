"""Rotas de documentos persistidos (v1), com isolamento por dono e retenção.

O ``original_text`` é imutável: estas rotas apenas criam, listam, consultam e
excluem documentos do próprio usuário, e aplicam a política de retenção.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, owner_id_of
from app.core.config import Settings
from app.core.database import get_session
from app.core.errors import NotFoundError
from app.models.document import Document
from app.models.user import User
from app.repositories.documents import DocumentRepository
from app.repositories.exports import ExportRepository
from app.schemas.documents import DocumentCreateRequest, DocumentOut, PruneResponse

router = APIRouter(tags=["documentos"])


def _to_out(documento: Document) -> DocumentOut:
    return DocumentOut(
        id=documento.id,
        owner_id=documento.owner_id,
        tamanho_caracteres=len(documento.original_text),
        created_at=documento.created_at,
        updated_at=documento.updated_at,
    )


@router.post("/documents", response_model=DocumentOut, status_code=201)
async def criar_documento(
    corpo: DocumentCreateRequest,
    usuario: Annotated[User | None, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> DocumentOut:
    """Cria um documento cujo texto original é imutável."""
    documento = DocumentRepository(session).create(corpo.texto, owner_id=owner_id_of(usuario))
    return _to_out(documento)


@router.get("/documents", response_model=list[DocumentOut])
async def listar_documentos(
    usuario: Annotated[User | None, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> list[DocumentOut]:
    """Lista os documentos do próprio usuário."""
    documentos = DocumentRepository(session).list_for_owner(owner_id_of(usuario))
    return [_to_out(doc) for doc in documentos]


@router.get("/documents/{document_id}", response_model=DocumentOut)
async def obter_documento(
    document_id: str,
    usuario: Annotated[User | None, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> DocumentOut:
    """Consulta um documento próprio (nunca o de outro usuário)."""
    documento = DocumentRepository(session).get(document_id, owner_id_of(usuario))
    if documento is None:
        raise NotFoundError(f"documento não encontrado: {document_id}")
    return _to_out(documento)


@router.delete("/documents/{document_id}", status_code=204)
async def excluir_documento(
    document_id: str,
    usuario: Annotated[User | None, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    """Exclui um documento próprio (com suas revisões)."""
    if not DocumentRepository(session).delete(document_id, owner_id_of(usuario)):
        raise NotFoundError(f"documento não encontrado: {document_id}")
    return Response(status_code=204)


@router.post("/documents/prune", response_model=PruneResponse)
async def aplicar_retencao(
    request: Request,
    usuario: Annotated[User | None, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> PruneResponse:
    """Aplica a política de retenção sobre documentos e exportações do usuário."""
    settings: Settings = request.app.state.settings
    owner = owner_id_of(usuario)
    agora_naive = datetime.now(UTC).replace(tzinfo=None)
    docs_removidos = DocumentRepository(session).prune_expired(
        now=agora_naive,
        retention_days=settings.document_retention_days,
        owner_id=owner,
    )
    exports_removidos = ExportRepository(session).prune_expired(
        now=agora_naive,
        retention_days=settings.document_retention_days,
        owner_id=owner,
        export_dir=settings.export_dir,
    )
    return PruneResponse(
        removidos=docs_removidos + exports_removidos,
        documentos=docs_removidos,
        exportacoes=exports_removidos,
    )
