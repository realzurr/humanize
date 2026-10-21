"""Testes do carregamento e resolução de templates (ADR-0007)."""

from __future__ import annotations

import pytest

from app.services.academic.template_model import Pagina, Template, Tipografia
from app.services.academic.templates import TemplateNotFoundError, TemplateRegistry

TIPOS_ABNT = {
    "abnt.general",
    "abnt.artigo",
    "abnt.tcc",
    "abnt.monografia",
    "abnt.dissertacao",
    "abnt.tese",
    "abnt.projeto-pesquisa",
    "abnt.relatorio",
}


def _pagina(template: Template) -> Pagina:
    assert template.page is not None
    return template.page


def _tipografia(template: Template) -> Tipografia:
    assert template.typography is not None
    return template.typography


def test_oito_tipos_de_template_existem(template_registry: TemplateRegistry) -> None:
    ids = set(template_registry.ids())
    assert ids >= TIPOS_ABNT


def test_templates_sao_versionados_e_declaram_fontes(template_registry: TemplateRegistry) -> None:
    for template_id in TIPOS_ABNT:
        template = template_registry.get(template_id)
        assert template.version, template_id
        assert template.sources, template_id
        for fonte in template.sources:
            assert fonte.norm
            assert fonte.edition
            assert fonte.consulted_at
            assert fonte.confidence


def test_margens_anverso_parametrizadas(template_registry: TemplateRegistry) -> None:
    template = template_registry.get("abnt.general")
    margens = _pagina(template).margins_cm
    assert (margens.left_cm, margens.top_cm, margens.right_cm, margens.bottom_cm) == (3, 3, 2, 2)


def test_margens_verso_parametrizadas(template_registry: TemplateRegistry) -> None:
    template = template_registry.get("abnt.general")
    assert _pagina(template).mirror is True
    margens = _pagina(template).margins_verso_cm
    assert margens is not None
    assert (margens.left_cm, margens.top_cm, margens.right_cm, margens.bottom_cm) == (2, 3, 3, 2)


def test_heranca_extends_geral(template_registry: TemplateRegistry) -> None:
    tcc = template_registry.get("abnt.tcc")
    assert tcc.extends == "abnt.general"
    # Herda a formatação do geral.
    assert _tipografia(tcc).font == "Times New Roman"
    assert len(tcc.elements) == len(template_registry.get("abnt.general").elements)


def test_artigo_tem_estrutura_propria(template_registry: TemplateRegistry) -> None:
    artigo = template_registry.get("abnt.artigo")
    kinds = [e.kind for e in artigo.elements]
    assert "cover" not in kinds  # artigo não tem capa
    assert "references" in kinds
    assert any(e.kind == "development" for e in artigo.elements)


def test_perfil_institucional_sobrescreve_apenas_o_que_define(
    template_registry: TemplateRegistry,
) -> None:
    resolvido = template_registry.resolve("abnt.tcc", "inst.ufms.geral")
    # Sobrescreve a fonte.
    assert _tipografia(resolvido.template).font == "Arial"
    # Mas preserva o id e as margens do template base.
    assert resolvido.template.id == "abnt.tcc"
    assert _pagina(resolvido.template).margins_cm.left_cm == 3
    # Registra o conflito da regra sobrescrita.
    assert "typography.font" in resolvido.overrides


def test_conflito_de_fonte_desatualizada_registrado(template_registry: TemplateRegistry) -> None:
    resolvido = template_registry.resolve("abnt.tcc", "inst.ufms.geral")
    conflito_fonte = [c for c in resolvido.conflicts if c.rule_id.startswith("fonte.")]
    assert conflito_fonte
    assert "2011" in conflito_fonte[0].institution_value
    assert resolvido.has_outdated_source


def test_ufgd_desativa_espelhamento(template_registry: TemplateRegistry) -> None:
    resolvido = template_registry.resolve("abnt.tese", "inst.ufgd.geral")
    assert _pagina(resolvido.template).mirror is False
    assert "page.mirror" in resolvido.overrides


def test_sem_instituicao_nao_ha_conflito(template_registry: TemplateRegistry) -> None:
    resolvido = template_registry.resolve("abnt.tcc")
    assert resolvido.conflicts == ()
    assert resolvido.overrides == ()


def test_template_inexistente_levanta_erro(template_registry: TemplateRegistry) -> None:
    with pytest.raises(TemplateNotFoundError):
        template_registry.get("abnt.nao_existe")


def test_ficha_catalografica_reservada(template_registry: TemplateRegistry) -> None:
    template = template_registry.get("abnt.general")
    ficha = next(e for e in template.elements if e.kind == "catalog_record")
    assert ficha.required is False
    assert "RESERVADO" in ficha.note or "reservado" in ficha.note.lower()
