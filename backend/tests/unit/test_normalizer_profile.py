"""Testes dos perfis de normalização."""

from __future__ import annotations

from app.services.normalizer.profile import (
    DEFAULT_OPTIONS,
    OPTION_KEYS,
    OPTION_RULES,
    NormalizationProfile,
    get_profile,
)


def test_perfil_padrao_nao_liga_nfkc() -> None:
    perfil = get_profile("padrao")
    assert perfil.is_enabled("norm.unicode.nfkc", default_enabled=False) is False


def test_perfil_padrao_liga_regras_padrao() -> None:
    perfil = get_profile("padrao")
    assert perfil.is_enabled("norm.whitespace.collapse", default_enabled=True) is True


def test_perfil_desconhecido_cai_no_padrao() -> None:
    assert get_profile("nao-existe").id == "padrao"


def test_opcao_nfkc_liga_regra() -> None:
    perfil = get_profile("padrao").with_options({"nfkc": True})
    assert perfil.is_enabled("norm.unicode.nfkc", default_enabled=False) is True


def test_opcao_markdown_desliga_regras() -> None:
    perfil = get_profile("padrao").with_options({"markdown": False})
    assert perfil.is_enabled("norm.markdown.emphasis", default_enabled=True) is False


def test_opcao_desconhecida_e_ignorada() -> None:
    perfil = get_profile("padrao").with_options({"inexistente": False})
    assert perfil.is_enabled("norm.whitespace.collapse", default_enabled=True) is True


def test_regra_desligada_ganha_da_opcao() -> None:
    perfil = get_profile("padrao").with_options({"markdown": True})
    perfil = NormalizationProfile(disabled_rules=frozenset({"norm.markdown.emphasis"}))
    assert perfil.is_enabled("norm.markdown.emphasis", default_enabled=True) is False


def test_todas_as_opcoes_tem_regras() -> None:
    for chave in OPTION_KEYS:
        assert OPTION_RULES[chave], chave
        assert chave in DEFAULT_OPTIONS
