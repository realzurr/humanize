"""Schemas da API de templates.

A listagem devolve um resumo; o detalhe e a resolução devolvem o modelo de
template do serviço acadêmico, incluindo as fontes de cada regra e os
conflitos institucionais registrados (nunca ocultados).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.services.academic.template_model import Conflito, Template


class TemplateSummary(BaseModel):
    """Resumo de um template para a listagem."""

    model_config = ConfigDict(frozen=True)

    id: str
    kind: str
    title: str = ""
    version: str
    extends: str | None = None
    institution: str | None = None
    fontes: int = Field(ge=0)
    """Quantidade de fontes normativas declaradas."""


class ResolveOut(BaseModel):
    """Resultado da resolução de um template com perfil institucional."""

    model_config = ConfigDict(frozen=True)

    template: Template
    """Template final, já com herança e sobreposições aplicadas."""

    conflicts: list[Conflito] = Field(default_factory=list)
    """Conflitos registrados (instituição vs. norma)."""

    overrides: list[str] = Field(default_factory=list)
    """Caminhos das regras sobrescritas pela instituição."""
