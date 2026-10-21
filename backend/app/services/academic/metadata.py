"""Validação de metadados do documento.

Define os campos obrigatórios por natureza de documento e verifica a
presença deles no formulário de metadados. O documento original é imutável; a
validação apenas sinaliza o que falta, nunca preenche por conta própria.
"""

from __future__ import annotations

from app.ir.document import DocumentMetadata

#: Campos obrigatórios por natureza de documento.
REQUIRED_BY_KIND: dict[str, tuple[str, ...]] = {
    "tese": ("institution", "author", "title", "advisor", "year", "city"),
    "dissertacao": ("institution", "author", "title", "advisor", "year", "city"),
    "tcc": ("institution", "author", "title", "advisor", "year"),
    "monografia": ("institution", "author", "title", "year"),
    "artigo": ("author", "title", "year"),
    "projeto_pesquisa": ("institution", "author", "title", "advisor", "year"),
    "relatorio": ("institution", "author", "title", "year"),
}

#: Campos obrigatórios comuns a qualquer trabalho acadêmico.
_COMMON = ("author", "title")


def required_fields(kind: str) -> tuple[str, ...]:
    """Campos obrigatórios para a natureza de documento."""
    campos = REQUIRED_BY_KIND.get(kind, _COMMON)
    return tuple(sorted(set(campos) | set(_COMMON)))


def missing_fields(kind: str, metadata: DocumentMetadata) -> list[str]:
    """Lista os campos obrigatórios ausentes para a natureza informada."""
    return metadata.missing_required(required_fields(kind))
