"""Testes dos perfis autorais."""

from __future__ import annotations

import pytest

from app.services.humanizer.profiles import (
    AUTORAL_ID,
    PROFILES,
    build_autoral_profile,
    get_profile,
    list_profiles,
)


def test_sete_perfis_distintos() -> None:
    """Os sete perfis têm instruções de sistema visivelmente distintas."""
    fixos = list_profiles()
    autoral = build_autoral_profile("dono-1", ("meu texto autoral",))
    instrucoes = [p.system_instruction for p in fixos] + [autoral.system_instruction]
    assert len(set(instrucoes)) == 7


def test_seis_perfis_fixos() -> None:
    assert len(PROFILES) == 6
    assert set(PROFILES) == {
        "academico_cientifico",
        "academico_acessivel",
        "profissional",
        "institucional",
        "narrativo",
        "conversacional",
    }


def test_get_profile_existente() -> None:
    assert get_profile("academico_cientifico") is not None


def test_get_profile_desconhecido() -> None:
    assert get_profile("nao_existe") is None


def test_perfil_autoral_exige_owner_id() -> None:
    with pytest.raises(ValueError):
        build_autoral_profile("", ("texto",))


def test_perfil_autoral_exige_textos() -> None:
    with pytest.raises(ValueError):
        build_autoral_profile("dono-1", ())


def test_perfil_autoral_registra_owner_id() -> None:
    perfil = build_autoral_profile("dono-42", ("meu texto",))
    assert perfil.owner_id == "dono-42"
    assert perfil.is_personalizado
    assert perfil.id == AUTORAL_ID
    assert perfil.base_texts == ("meu texto",)


def test_perfis_fixos_nao_sao_personalizados() -> None:
    for perfil in list_profiles():
        assert not perfil.is_personalizado
        assert perfil.owner_id is None
