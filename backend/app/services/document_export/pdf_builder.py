"""Renderização de PDF em processo isolado e comparação estrutural DOCX ↔ PDF.

O PDF é gerado a partir do DOCX por subprocesso isolado (LibreOffice em modo
``--headless``), fora do event loop (`ADR-0012`). Quando o renderizador não
está disponível ou está desabilitado (``pdf_renderer="none"``), a limitação é
declarada explicitamente sem falha silenciosa. Quando disponível, o PDF é
inspecionado via ``pymupdf`` e comparado ao DOCX de origem quanto ao tamanho
de página, margens, paginação, presença de títulos e quebras indevidas.
"""

from __future__ import annotations

import asyncio
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.services.academic.pagination import PageSide, resolve_margins
from app.services.academic.template_model import Margens, Pagina, Template
from app.services.document_export.docx_builder import DocxInspection, inspect_docx

#: Conversão de pontos PostScript (1/72 pol) para centímetros.
_PT_PER_CM = 72.0 / 2.54

#: Tolerância para validação de tamanho de página e margens no PDF (em cm).
_PAGE_SIZE_TOLERANCE_CM = 0.25
_MARGIN_TOLERANCE_CM = 0.6


class PdfComparisonReport(BaseModel):
    """Relatório de validação e comparação entre o PDF renderizado e o DOCX de origem."""

    model_config = ConfigDict(frozen=True)

    page_count: int
    page_width_cm: float
    page_height_cm: float
    page_size_matches_docx: bool
    margins_respected: bool
    pagination_valid: bool
    undue_breaks: tuple[str, ...]
    docx_heading_count: int
    pdf_non_empty_pages: int
    differences: tuple[str, ...]
    limitations: tuple[str, ...]


class PdfBuildResult(BaseModel):
    """Resultado da tentativa de renderização de PDF a partir do DOCX."""

    model_config = ConfigDict(frozen=True)

    available: bool
    content: bytes | None = None
    renderer: str
    comparison: PdfComparisonReport | None = None
    warnings: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()


def is_pdf_renderer_available(
    renderer: str = "libreoffice",
    libreoffice_binary: str = "soffice",
) -> bool:
    """Indica se o renderizador configurado está instalado e acessível no ambiente."""
    if renderer == "none":
        return False
    if renderer == "libreoffice":
        return shutil.which(libreoffice_binary) is not None
    if renderer == "docx2pdf":
        return shutil.which("docx2pdf") is not None
    return False


def _render_pdf_sync(
    docx_bytes: bytes,
    libreoffice_binary: str,
    timeout_seconds: float,
) -> tuple[bytes | None, str | None]:
    """Executa a conversão DOCX → PDF em subprocesso isolado com perfil temporário."""
    binary_path = shutil.which(libreoffice_binary)
    if binary_path is None:
        return None, (
            f"Binário '{libreoffice_binary}' (LibreOffice) não encontrado no ambiente; "
            "apenas DOCX, TXT e Markdown foram gerados."
        )

    with tempfile.TemporaryDirectory(prefix="humaniza_pdf_") as tmp_dir:
        tmp_path = Path(tmp_dir)
        docx_path = tmp_path / "documento.docx"
        pdf_path = tmp_path / "documento.pdf"
        profile_uri = (tmp_path / "lo_profile").as_uri()
        docx_path.write_bytes(docx_bytes)

        cmd = [
            binary_path,
            f"-env:UserInstallation={profile_uri}",
            "--headless",
            "--nologo",
            "--nodefault",
            "--nofirststartwizard",
            "--nolockcheck",
            "--convert-to",
            "pdf",
            "--outdir",
            str(tmp_path),
            str(docx_path),
        ]
        try:
            proc = subprocess.run(  # noqa: S603
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return None, (
                f"Renderização de PDF excedeu o tempo limite de {timeout_seconds:.0f}s no "
                "processo isolado."
            )
        except OSError as exc:
            return None, f"Falha ao iniciar o processo de renderização de PDF: {exc}"

        if proc.returncode != 0 or not pdf_path.exists():
            detalhe = (proc.stderr or proc.stdout or "código de saída não zero").strip()
            return None, f"LibreOffice não produziu o PDF esperado ({detalhe})."

        return pdf_path.read_bytes(), None


async def build_pdf_from_docx(
    docx_bytes: bytes,
    template: Template,
    *,
    renderer: str = "libreoffice",
    libreoffice_binary: str = "soffice",
    timeout_seconds: float = 60.0,
) -> PdfBuildResult:
    """Renderiza PDF em processo isolado (`asyncio.to_thread`) e valida contra o DOCX."""
    if renderer == "none" or not is_pdf_renderer_available(renderer, libreoffice_binary):
        motivo = (
            "Renderizador de PDF desabilitado por configuração (pdf_renderer='none'); "
            "apenas DOCX, TXT e Markdown são gerados."
            if renderer == "none"
            else (
                f"Renderizador de PDF ('{libreoffice_binary}') indisponível no sistema; "
                "apenas DOCX, TXT e Markdown são gerados."
            )
        )
        return PdfBuildResult(
            available=False,
            content=None,
            renderer=renderer,
            comparison=None,
            warnings=(motivo,),
            limitations=(motivo,),
        )

    pdf_bytes, erro = await asyncio.to_thread(
        _render_pdf_sync,
        docx_bytes,
        libreoffice_binary,
        timeout_seconds,
    )
    if pdf_bytes is None:
        mensagem = erro or "Renderização de PDF indisponível."
        return PdfBuildResult(
            available=False,
            content=None,
            renderer=renderer,
            comparison=None,
            warnings=(mensagem,),
            limitations=(mensagem,),
        )

    comparacao = await asyncio.to_thread(
        compare_docx_and_pdf,
        docx_bytes,
        pdf_bytes,
        template,
    )
    return PdfBuildResult(
        available=True,
        content=pdf_bytes,
        renderer=renderer,
        comparison=comparacao,
        warnings=comparacao.undue_breaks,
        limitations=comparacao.limitations,
    )


_LIMITACAO_INSPETOR_NATIVO = (
    "Inspetor nativo (sem pymupdf): margens, páginas vazias e quebras indevidas não foram "
    "verificadas; apenas contagem de páginas e tamanho da primeira página."
)
_LIMITACAO_PDF_COMPRIMIDO = (
    "Estrutura do PDF comprimida não inspecionável sem pymupdf; contagem de páginas indisponível."
)
_PDF_PAGE_RE = re.compile(rb"/Type\s*/Page\b")
_PDF_MEDIABOX_RE = re.compile(
    rb"/MediaBox\s*\[\s*([-+]?\d+(?:\.\d+)?)\s+([-+]?\d+(?:\.\d+)?)\s+"
    rb"([-+]?\d+(?:\.\d+)?)\s+([-+]?\d+(?:\.\d+)?)\s*\]"
)


def _inspecionar_pdf_nativo(
    pdf_bytes: bytes,
    inspecao: DocxInspection,
) -> PdfComparisonReport:
    """Inspeção estrutural nativa em Python puro (sem depender de ``pymupdf``/AGPL)."""
    if not pdf_bytes.startswith(b"%PDF-"):
        return PdfComparisonReport(
            page_count=0,
            page_width_cm=0.0,
            page_height_cm=0.0,
            page_size_matches_docx=False,
            margins_respected=False,
            pagination_valid=False,
            undue_breaks=(),
            docx_heading_count=inspecao.heading_count,
            pdf_non_empty_pages=0,
            differences=("Conteúdo PDF inválido.",),
            limitations=KNOWN_RENDERER_LIMITATIONS,
        )

    page_count = len(_PDF_PAGE_RE.findall(pdf_bytes))
    m_box = _PDF_MEDIABOX_RE.search(pdf_bytes)
    if m_box is not None:
        x0, y0, x1, y1 = (float(g) for g in m_box.groups())
        width_cm = round((x1 - x0) / _PT_PER_CM, 2)
        height_cm = round((y1 - y0) / _PT_PER_CM, 2)
    else:
        width_cm = 0.0
        height_cm = 0.0

    size_matches = (
        page_count > 0
        and abs(width_cm - inspecao.page_width_cm) <= _PAGE_SIZE_TOLERANCE_CM
        and abs(height_cm - inspecao.page_height_cm) <= _PAGE_SIZE_TOLERANCE_CM
    )
    differences: list[str] = []
    # O inspetor nativo não extrai texto nem posições: nada pode ser afirmado sobre
    # margens, quebras ou páginas vazias (AGENTS.md §5 — conformidade só por regra validada).
    limitacoes: list[str] = [*KNOWN_RENDERER_LIMITATIONS, _LIMITACAO_INSPETOR_NATIVO]
    if page_count == 0:
        differences.append(
            "Nenhuma página localizada pelo inspetor nativo; o PDF pode usar object streams "
            "comprimidos (PDF 1.5+)."
        )
        limitacoes.append(_LIMITACAO_PDF_COMPRIMIDO)
    if inspecao.has_toc_field:
        differences.append(
            "O campo TOC requer atualização prévia no Word/LibreOffice para listar os números "
            "finais de página no PDF."
        )
    return PdfComparisonReport(
        page_count=page_count,
        page_width_cm=width_cm,
        page_height_cm=height_cm,
        page_size_matches_docx=size_matches,
        margins_respected=False,
        pagination_valid=page_count >= 1,
        undue_breaks=(),
        docx_heading_count=inspecao.heading_count,
        pdf_non_empty_pages=0,
        differences=tuple(differences),
        limitations=tuple(limitacoes),
    )


def _abrir_pdf(pdf_bytes: bytes) -> Any | None:
    """Abre o PDF via ``pymupdf``, degradando para o inspetor nativo se indisponível.

    ``pymupdf`` é uma dependência opcional (extra ``pdf``) para mitigar o risco
    de licenciamento AGPL em um projeto MIT (`GAP-09`).
    """
    try:
        import pymupdf

        return pymupdf.open(stream=pdf_bytes, filetype="pdf")  # type: ignore[no-untyped-call]
    except ImportError:
        return None


def compare_docx_and_pdf(
    docx_bytes: bytes,
    pdf_bytes: bytes,
    template: Template,
    *,
    docx_inspection: DocxInspection | None = None,
) -> PdfComparisonReport:
    """Compara o PDF gerado com o DOCX de origem (tamanho, margens, paginação e quebras)."""
    inspecao = docx_inspection or inspect_docx(docx_bytes)
    page_cfg = template.page or Pagina(
        size="A4",
        mirror=True,
        margins_cm=Margens(top_cm=3.0, bottom_cm=2.0, left_cm=3.0, right_cm=2.0),
    )
    margens_anverso = resolve_margins(page_cfg, PageSide.ANVERSO)
    margens_verso = resolve_margins(page_cfg, PageSide.VERSO)

    pdf_doc = _abrir_pdf(pdf_bytes)
    if pdf_doc is None:
        return _inspecionar_pdf_nativo(pdf_bytes, inspecao)

    try:
        page_count = len(pdf_doc)
        if page_count == 0:
            return PdfComparisonReport(
                page_count=0,
                page_width_cm=0.0,
                page_height_cm=0.0,
                page_size_matches_docx=False,
                margins_respected=False,
                pagination_valid=False,
                undue_breaks=("PDF gerado sem páginas.",),
                docx_heading_count=inspecao.heading_count,
                pdf_non_empty_pages=0,
                differences=("PDF vazio.",),
                limitations=KNOWN_RENDERER_LIMITATIONS,
            )

        first_rect = pdf_doc[0].rect
        width_cm = round(first_rect.width / _PT_PER_CM, 2)
        height_cm = round(first_rect.height / _PT_PER_CM, 2)

        size_matches = (
            abs(width_cm - inspecao.page_width_cm) <= _PAGE_SIZE_TOLERANCE_CM
            and abs(height_cm - inspecao.page_height_cm) <= _PAGE_SIZE_TOLERANCE_CM
        )

        margins_ok = True
        non_empty_pages = 0
        undue_breaks: list[str] = []
        differences: list[str] = []

        for page_idx in range(page_count):
            page = pdf_doc[page_idx]
            blocks = page.get_text("blocks")
            text_blocks = [b for b in blocks if len(b) >= 5 and str(b[4]).strip()]
            if text_blocks:
                non_empty_pages += 1

            margem_esperada = margens_anverso if page_idx % 2 == 0 else margens_verso
            # Filtra blocos do corpo (ignora o cabeçalho de paginação no topo < 2.2 cm)
            body_blocks = [b for b in text_blocks if (float(b[1]) / _PT_PER_CM) >= 2.2]
            for b in body_blocks:
                x0_cm = float(b[0]) / _PT_PER_CM
                y1_cm = float(b[3]) / _PT_PER_CM
                if x0_cm + _MARGIN_TOLERANCE_CM < min(
                    margem_esperada.left_cm, margem_esperada.right_cm
                ):
                    margins_ok = False
                if (height_cm - y1_cm) + _MARGIN_TOLERANCE_CM < margem_esperada.bottom_cm:
                    margins_ok = False

            # Verifica se o último bloco da página parece um título numerado órfão no rodapé
            if body_blocks:
                ultimo = body_blocks[-1]
                texto_ultimo = str(ultimo[4]).strip()
                y0_ultimo_cm = float(ultimo[1]) / _PT_PER_CM
                if (
                    y0_ultimo_cm > (height_cm - margem_esperada.bottom_cm - 2.0)
                    and len(texto_ultimo) < 90
                    and texto_ultimo[:1].isdigit()
                    and "\n" not in texto_ultimo
                ):
                    undue_breaks.append(
                        f"Possível título órfão no fim da página {page_idx + 1}: '{texto_ultimo}'"
                    )

        if inspecao.has_toc_field:
            differences.append(
                "O campo TOC requer atualização prévia no Word/LibreOffice para listar os números "
                "finais de página no PDF."
            )

        pagination_valid = page_count >= 1 and non_empty_pages >= 1
    finally:
        pdf_doc.close()

    return PdfComparisonReport(
        page_count=page_count,
        page_width_cm=width_cm,
        page_height_cm=height_cm,
        page_size_matches_docx=size_matches,
        margins_respected=margins_ok,
        pagination_valid=pagination_valid,
        undue_breaks=tuple(undue_breaks),
        docx_heading_count=inspecao.heading_count,
        pdf_non_empty_pages=non_empty_pages,
        differences=tuple(differences),
        limitations=KNOWN_RENDERER_LIMITATIONS,
    )


#: Limitações conhecidas e documentadas do renderizador LibreOffice Headless.
KNOWN_RENDERER_LIMITATIONS: tuple[str, ...] = (
    "Campos dinâmicos (TOC) exibem o texto de espaço reservado no PDF até que o índice seja "
    "atualizado no editor (Word ou LibreOffice Writer).",
    "Em ambientes Linux sem as fontes proprietárias da Microsoft (Times New Roman / Arial), o "
    "LibreOffice aplica substituição métrica (Liberation Serif / Liberation Sans), o que pode "
    "alterar quebras de linha em frações de milímetro.",
    "Cabeçalhos espelhados (anverso/verso) dependem do suporte do perfil de página do conversor "
    "headless.",
)
