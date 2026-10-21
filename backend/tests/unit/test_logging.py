"""Testes do filtro de segredos e da configuração de logging (Onda 0)."""

from __future__ import annotations

import json
from collections.abc import Iterator

import pytest
import structlog

from app.core.config import Settings
from app.core.logging import configure_logging, redact, redact_secrets


@pytest.fixture(autouse=True)
def _restaura_configuracao_de_logging() -> Iterator[None]:
    """Restaura a configuração de logging ao final de cada teste."""
    yield
    configure_logging(Settings(environment="test"))


def test_redact_substitui_chaves_sensiveis() -> None:
    evento = redact_secrets(None, "info", {"api_key": "sk-abc123", "user": "ana"})
    assert evento["api_key"] == "***"
    assert evento["user"] == "ana"


def test_redact_cobre_variacoes_de_nome_de_chave() -> None:
    evento = redact_secrets(None, "info", {"Authorization": "Bearer x", "TOKEN": "y"})
    assert evento["Authorization"] == "***"
    assert evento["TOKEN"] == "***"


def test_redact_trata_segredos_em_texto_livre() -> None:
    assert "[REDACTED]" in redact("usando api_key=sk-1234567890abcdef")
    assert "[REDACTED]" in redact("Authorization: Bearer abcdefghijklmnop")
    assert "[REDACTED]" in redact("chave sk-abcdefghijklmnopqrstuvwxyz012345")


def test_redact_preserva_texto_comum() -> None:
    assert redact("texto sem segredo") == "texto sem segredo"


def test_redact_secrets_devolve_o_event_dict() -> None:
    """O processor deve devolver o dicionário, não a tupla do wrapper.

    Devolver a tupla ``(logger, method_name, event_dict)`` corromperia a
    cadeia de processors e derrubava o startup da aplicação.
    """
    resultado = redact_secrets(None, "info", {"mensagem": "ok"})
    assert resultado == {"mensagem": "ok"}


def test_cadeia_com_renderer_renderiza_json(capsys: pytest.CaptureFixture[str]) -> None:
    """A cadeia de produção deve renderizar uma linha JSON válida.

    É este teste que reproduz o defeito encontrado no startup: um processor
    que devolve a tupla do wrapper faz o renderer receber um objeto que não
    é ``event_dict``.
    """
    configure_logging(Settings(environment="test"))

    structlog.get_logger("teste").info("mensagem", api_key="sk-secreto")

    saida = capsys.readouterr().out.strip()
    payload = json.loads(saida)
    assert payload["api_key"] == "***"
    assert payload["event"] == "mensagem"
    assert payload["level"] == "info"


def test_configure_logging_nao_vaza_segredo(capsys: pytest.CaptureFixture[str]) -> None:
    """A configuração de produção não pode vazar credenciais no stdout."""
    configure_logging(Settings(environment="test"))

    structlog.get_logger("teste").info(
        "conectando com api_key=sk-1234567890abcdef", token="segredo"
    )

    saida = capsys.readouterr().out
    assert "sk-1234567890abcdef" not in saida
    assert "segredo" not in saida
    assert "[REDACTED]" in saida
