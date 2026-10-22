"""Rotas de exportação de documentos acadêmicos (v1).

Orquestra a geração de DOCX (com estilos e campos nativos do Word), PDF (em
processo isolado via LibreOffice), TXT e Markdown, além de pré-visualização e
histórico de versões. Sem renderizador de PDF disponível, a limitação é
declarada na resposta e apenas DOCX/TXT/Markdown são gerados (`ADR-0012`).
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Annotated, cast

from fastapi import APIRouter, Depends, Request, Response

from app.api.deps import get_current_user, owner_id_of
from app.core.config import Settings
from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.ir.document import AcademicDocument, DocumentRevision, PipelineStage
from app.models.user import User
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


@router.post("/exports", response_model=ExportResponse)
async def exportar_documento(
    corpo: ExportRequest,
    request: Request,
    usuario: Annotated[User | None, Depends(get_current_user)],
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
    document_id: str | None = None,
) -> list[ExportRecord]:
    """Lista o histórico de exportações do usuário."""
    store = _export_store(request)
    return store.list_records(document_id=document_id, owner_id=owner_id_of(usuario))


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
) -> ExportRecord:
    """Devolve os metadados e o relatório de inspeção de uma exportação."""
    store = _export_store(request)
    record = store.get(export_id, owner_id_of(usuario))
    if record is None:
        raise NotFoundError(f"Exportação não encontrada: {export_id}")
    return record


@router.get("/exports/{export_id}/download")
async def baixar_exportacao(
    export_id: str,
    request: Request,
    usuario: Annotated[User | None, Depends(get_current_user)],
) -> Response:
    """Faz o download do arquivo exportado."""
    store = _export_store(request)
    record = store.get(export_id, owner_id_of(usuario))
    if record is None:
        raise NotFoundError(f"Exportação não encontrada: {export_id}")
    conteudo = store.read_bytes(export_id, owner_id_of(usuario))
    if conteudo is None:
        raise NotFoundError(f"Arquivo da exportação {export_id} não encontrado em disco.")
    media_type = MEDIA_TYPES[record.format]
    headers = {"Content-Disposition": f'attachment; filename="{record.filename}"'}
    return Response(content=conteudo, media_type=media_type, headers=headers)
