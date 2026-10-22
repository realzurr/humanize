"""Rotas de exportação de documentos acadêmicos (v1).

Orquestra a geração de DOCX (com estilos e campos nativos do Word), PDF (em
processo isolado via LibreOffice), TXT e Markdown, além de pré-visualização e
histórico de versões. Sem renderizador de PDF disponível, a limitação é
declarada na resposta e apenas DOCX/TXT/Markdown são gerados (`ADR-0012`).
"""

from __future__ import annotations

import asyncio
import json
import re
import uuid
from datetime import UTC
from typing import Annotated, cast

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, owner_id_of
from app.core.config import Settings
from app.core.database import get_session
from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.ir.document import AcademicDocument, DocumentRevision, PipelineStage
from app.models.export import Export
from app.models.user import User
from app.repositories.exports import ExportRepository
from app.schemas.exports import (
    DocumentHistoryResponse,
    ExportPreviewRequest,
    ExportRequest,
    ExportResponse,
)
from app.services.academic.template_model import Template
from app.services.academic.templates import TemplateNotFoundError, TemplateRegistry
from app.services.document_export.docx_builder import build_docx, parse_text_to_blocks
from app.services.document_export.pdf_builder import build_pdf_from_docx
from app.services.document_export.writer import (
    MEDIA_TYPES,
    DocumentPreview,
    ExportFormat,
    ExportHistoryStore,
    ExportRecord,
    export_markdown,
    export_txt,
    generate_preview,
)

router = APIRouter(tags=["exportação"])

logger = get_logger(__name__)


def _template_registry(request: Request) -> TemplateRegistry:
    return cast(TemplateRegistry, request.app.state.template_registry)


def _export_store(request: Request) -> ExportHistoryStore:
    return cast(ExportHistoryStore, request.app.state.export_store)


def _settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def _resolver_template(
    registry: TemplateRegistry,
    template_id: str,
    instituicao: str | None,
) -> Template:
    try:
        resolvido = registry.resolve(template_id, instituicao)
    except TemplateNotFoundError as exc:
        raise NotFoundError(str(exc)) from exc
    return resolvido.template


_VERSION_RE = re.compile(r"_v(\d+)_exp_")


def _orm_to_record(exp: Export) -> ExportRecord:
    """Reconstrói um ``ExportRecord`` a partir da linha persistida no ORM."""
    match = _VERSION_RE.search(exp.filename)
    versao = int(match.group(1)) if match else 1
    criado = exp.created_at.replace(tzinfo=UTC) if exp.created_at.tzinfo is None else exp.created_at
    avisos = tuple(str(x) for x in json.loads(exp.warnings_json or "[]"))
    limitacoes = tuple(str(x) for x in json.loads(exp.limitations_json or "[]"))
    return ExportRecord(
        id=exp.id,
        document_id=exp.document_id or "documento",
        revision_id=None,
        version_number=versao,
        format=ExportFormat(exp.format),
        filename=exp.filename,
        sha256=exp.sha256,
        size_bytes=exp.size_bytes,
        template_id=exp.template_id,
        institution_id=exp.institution_id,
        owner_id=exp.owner_id,
        created_at=criado,
        warnings=avisos,
        limitations=limitacoes,
    )


def _persistir_registros(session: Session, registros: list[ExportRecord]) -> None:
    repo = ExportRepository(session)
    try:
        for rec in registros:
            repo.save(
                export_id=rec.id,
                document_id=rec.document_id,
                owner_id=rec.owner_id,
                fmt=rec.format.value,
                filename=rec.filename,
                sha256=rec.sha256,
                size_bytes=rec.size_bytes,
                template_id=rec.template_id,
                institution_id=rec.institution_id,
                warnings=rec.warnings,
                limitations=rec.limitations,
                created_at=rec.created_at.replace(tzinfo=None),
            )
    except OperationalError:
        session.rollback()


def _listar_persistidos(
    session: Session, owner_id: str | None, document_id: str | None = None
) -> list[Export]:
    try:
        return ExportRepository(session).list_for_owner(owner_id, document_id=document_id)
    except OperationalError:
        session.rollback()
        return []


def _buscar_persistido(session: Session, export_id: str, owner_id: str | None) -> Export | None:
    try:
        return ExportRepository(session).get(export_id, owner_id)
    except OperationalError:
        session.rollback()
        return None


@router.post("/exports", response_model=ExportResponse)
async def exportar_documento(
    corpo: ExportRequest,
    request: Request,
    usuario: Annotated[User | None, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> ExportResponse:
    """Gera as exportações solicitadas (DOCX, PDF, TXT, Markdown) e registra no histórico."""
    registry = _template_registry(request)
    store = _export_store(request)
    settings = _settings(request)
    template = _resolver_template(registry, corpo.template_id, corpo.instituicao)
    owner_id = owner_id_of(usuario)

    # Recupera ou cria o AcademicDocument preservando original_text imutável
    existente = store.get_document(corpo.document_id, owner_id)
    blocos = parse_text_to_blocks(corpo.texto)
    if existente is None:
        base_doc = AcademicDocument(
            id=corpo.document_id,
            original_text=corpo.texto,
            blocks=blocos,
            metadata=corpo.metadados,
            owner_id=owner_id,
        )
    else:
        base_doc = existente.model_copy(update={"metadata": corpo.metadados})

    rev_id = f"rev_{uuid.uuid4().hex[:10]}"
    docx_result = await asyncio.to_thread(
        build_docx,
        base_doc.model_copy(update={"blocks": blocos}),
        template,
        include_pre_textual=corpo.incluir_pre_textual,
    )

    revisao = DocumentRevision(
        id=rev_id,
        stage=PipelineStage.EXPORT,
        text=corpo.texto,
        blocks=blocos,
        transformations=docx_result.transformations,
        parent_id=base_doc.current_revision_id,
        metadata={"template_id": corpo.template_id, "instituicao": corpo.instituicao},
    )
    doc_atualizado = base_doc.with_revision(revisao)
    store.register_document(doc_atualizado)

    registros: list[ExportRecord] = []
    avisos: list[str] = list(docx_result.warnings)
    limitacoes: list[str] = []
    pdf_disponivel = False

    formatos_pedidos = list(dict.fromkeys(corpo.formatos))

    if ExportFormat.DOCX in formatos_pedidos:
        rec_docx = store.record_export(
            document_id=doc_atualizado.id,
            revision_id=rev_id,
            fmt=ExportFormat.DOCX,
            content=docx_result.content,
            template_id=template.id,
            institution_id=corpo.instituicao,
            owner_id=owner_id,
            warnings=docx_result.warnings,
            docx_inspection=docx_result.inspection,
        )
        registros.append(rec_docx)

    if ExportFormat.PDF in formatos_pedidos:
        pdf_res = await build_pdf_from_docx(
            docx_result.content,
            template,
            renderer=settings.pdf_renderer,
            libreoffice_binary=settings.libreoffice_binary,
        )
        pdf_disponivel = pdf_res.available
        for w in pdf_res.warnings:
            if w not in avisos:
                avisos.append(w)
        for lim in pdf_res.limitations:
            if lim not in limitacoes:
                limitacoes.append(lim)

        if pdf_res.available and pdf_res.content is not None:
            rec_pdf = store.record_export(
                document_id=doc_atualizado.id,
                revision_id=rev_id,
                fmt=ExportFormat.PDF,
                content=pdf_res.content,
                template_id=template.id,
                institution_id=corpo.instituicao,
                owner_id=owner_id,
                warnings=pdf_res.warnings,
                limitations=pdf_res.limitations,
                pdf_comparison=pdf_res.comparison,
            )
            registros.append(rec_pdf)
        else:
            # Garante que se o usuário pediu apenas PDF e o renderizador não está disponível,
            # os formatos alternativos (DOCX, TXT, Markdown) sejam entregues conforme ADR-0012.
            for alt in (ExportFormat.DOCX, ExportFormat.TXT, ExportFormat.MARKDOWN):
                if alt not in formatos_pedidos:
                    formatos_pedidos.append(alt)
            if ExportFormat.DOCX not in {r.format for r in registros}:
                registros.append(
                    store.record_export(
                        document_id=doc_atualizado.id,
                        revision_id=rev_id,
                        fmt=ExportFormat.DOCX,
                        content=docx_result.content,
                        template_id=template.id,
                        institution_id=corpo.instituicao,
                        owner_id=owner_id,
                        warnings=docx_result.warnings,
                        limitations=tuple(limitacoes),
                        docx_inspection=docx_result.inspection,
                    )
                )

    if ExportFormat.TXT in formatos_pedidos:
        txt_bytes = export_txt(
            doc_atualizado,
            template,
            include_pre_textual=corpo.incluir_pre_textual,
        )
        registros.append(
            store.record_export(
                document_id=doc_atualizado.id,
                revision_id=rev_id,
                fmt=ExportFormat.TXT,
                content=txt_bytes,
                template_id=template.id,
                institution_id=corpo.instituicao,
                owner_id=owner_id,
            )
        )

    if ExportFormat.MARKDOWN in formatos_pedidos:
        md_bytes = export_markdown(
            doc_atualizado,
            template,
            include_pre_textual=corpo.incluir_pre_textual,
        )
        registros.append(
            store.record_export(
                document_id=doc_atualizado.id,
                revision_id=rev_id,
                fmt=ExportFormat.MARKDOWN,
                content=md_bytes,
                template_id=template.id,
                institution_id=corpo.instituicao,
                owner_id=owner_id,
            )
        )

    _persistir_registros(session, registros)
    preview = generate_preview(doc_atualizado, template)

    logger.info(
        "exportacao.concluida",
        documento=doc_atualizado.id,
        revisao=rev_id,
        formatos=[r.format.value for r in registros],
        pdf_disponivel=pdf_disponivel,
    )

    return ExportResponse(
        document_id=doc_atualizado.id,
        revision_id=rev_id,
        template_id=template.id,
        instituicao=corpo.instituicao,
        pdf_available=pdf_disponivel,
        exports=registros,
        preview=preview,
        warnings=avisos,
        limitations=limitacoes,
    )


@router.post("/exports/preview", response_model=DocumentPreview)
async def pre_visualizar_documento(
    corpo: ExportPreviewRequest,
    request: Request,
    _usuario: Annotated[User | None, Depends(get_current_user)],
) -> DocumentPreview:
    """Gera a pré-visualização estruturada do documento sem gravar arquivos em disco."""
    registry = _template_registry(request)
    template = _resolver_template(registry, corpo.template_id, corpo.instituicao)
    doc = AcademicDocument(
        id=corpo.document_id,
        original_text=corpo.texto,
        blocks=parse_text_to_blocks(corpo.texto),
        metadata=corpo.metadados,
    )
    return generate_preview(doc, template)


@router.get("/exports", response_model=list[ExportRecord])
async def listar_exportacoes(
    request: Request,
    usuario: Annotated[User | None, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    document_id: str | None = None,
) -> list[ExportRecord]:
    """Lista o histórico de exportações do usuário (memória + banco relacional)."""
    store = _export_store(request)
    owner = owner_id_of(usuario)
    em_memoria = {r.id: r for r in store.list_records(document_id=document_id, owner_id=owner)}
    for exp in _listar_persistidos(session, owner, document_id=document_id):
        if exp.id not in em_memoria:
            em_memoria[exp.id] = _orm_to_record(exp)
    return sorted(em_memoria.values(), key=lambda r: r.created_at, reverse=True)


@router.get("/exports/documents/{document_id}/history", response_model=DocumentHistoryResponse)
async def consultar_historico_documento(
    document_id: str,
    request: Request,
    usuario: Annotated[User | None, Depends(get_current_user)],
) -> DocumentHistoryResponse:
    """Devolve o histórico de revisões e versões exportadas de um documento."""
    store = _export_store(request)
    resumo = store.summary_for_document(document_id, owner_id_of(usuario))
    return DocumentHistoryResponse(**resumo)


@router.get("/exports/{export_id}", response_model=ExportRecord)
async def detalhar_exportacao(
    export_id: str,
    request: Request,
    usuario: Annotated[User | None, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> ExportRecord:
    """Devolve os metadados e o relatório de inspeção de uma exportação."""
    store = _export_store(request)
    owner = owner_id_of(usuario)
    record = store.get(export_id, owner)
    if record is None:
        persistido = _buscar_persistido(session, export_id, owner)
        if persistido is not None:
            record = _orm_to_record(persistido)
    if record is None:
        raise NotFoundError(f"Exportação não encontrada: {export_id}")
    return record


@router.get("/exports/{export_id}/download")
async def baixar_exportacao(
    export_id: str,
    request: Request,
    usuario: Annotated[User | None, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    """Faz o download do arquivo exportado."""
    store = _export_store(request)
    settings = _settings(request)
    owner = owner_id_of(usuario)
    record = store.get(export_id, owner)
    conteudo = store.read_bytes(export_id, owner)
    if record is None:
        persistido = _buscar_persistido(session, export_id, owner)
        if persistido is not None:
            record = _orm_to_record(persistido)
            caminho = (settings.export_dir.resolve() / record.filename).resolve()
            if caminho.is_relative_to(settings.export_dir.resolve()) and caminho.exists():
                conteudo = caminho.read_bytes()
    if record is None:
        raise NotFoundError(f"Exportação não encontrada: {export_id}")
    if conteudo is None:
        raise NotFoundError(f"Arquivo da exportação {export_id} não encontrado em disco.")
    media_type = MEDIA_TYPES[record.format]
    headers = {"Content-Disposition": f'attachment; filename="{record.filename}"'}
    return Response(content=conteudo, media_type=media_type, headers=headers)
