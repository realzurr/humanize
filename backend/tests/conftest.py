"""Fixtures compartilhadas dos testes."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.academic.templates import TemplateRegistry

#: Diretório de templates do repositório (backend/tests -> repo).
TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates"


@pytest.fixture
def template_registry() -> TemplateRegistry:
    """Catálogo de templates apontando para o diretório real do repositório."""
    return TemplateRegistry(TEMPLATES_DIR)
