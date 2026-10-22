"""Testes de credenciais (AES-GCM, resolução env/sessão, indicador last4)."""

from __future__ import annotations

import base64
import os
from pathlib import Path

import pytest

from app.core.config import Settings
from app.services.providers.credentials import CredentialResolver, SecretCipher


@pytest.fixture
def chave_32() -> bytes:
    return os.urandom(32)


def test_cipher_roundtrip(chave_32: bytes) -> None:
    cipher = SecretCipher(chave_32)
    token = cipher.encrypt("sk-segredo-123")
    assert "sk-segredo-123" not in token
    assert cipher.decrypt(token) == "sk-segredo-123"


def test_cipher_indisponivel_sem_chave() -> None:
    cipher = SecretCipher(None)
    assert not cipher.available
    with pytest.raises(RuntimeError):
        cipher.encrypt("x")


def test_cipher_indisponivel_com_chave_invalida() -> None:
    settings = Settings(encryption_key=base64.b64encode(b"curta").decode())
    assert not SecretCipher.from_settings(settings).available


def test_resolver_le_do_ambiente() -> None:
    settings = Settings(openai_api_key="sk-env-12345678")
    resolver = CredentialResolver(settings)
    assert resolver.resolve("openai") == "sk-env-12345678"
    status = resolver.status("openai")
    assert status.configured
    assert status.last4 == "5678"
    assert status.source == "env"


def test_resolver_store_devolve_last4() -> None:
    resolver = CredentialResolver(Settings())
    status = resolver.store("openai", "sk-sessao-abcd")
    assert status.configured
    assert status.last4 == "abcd"
    assert status.source == "session"
    assert resolver.resolve("openai") == "sk-sessao-abcd"


def test_resolver_delete_remove_sessao() -> None:
    resolver = CredentialResolver(Settings())
    resolver.store("openai", "sk-sessao-abcd")
    status = resolver.delete("openai")
    assert not status.configured
    assert resolver.resolve("openai") is None


def test_resolver_delete_preserva_ambiente() -> None:
    resolver = CredentialResolver(Settings(openai_api_key="sk-env-12345678"))
    resolver.store("openai", "sk-sessao-abcd")
    status = resolver.delete("openai")
    assert status.configured
    assert status.source == "env"


def test_resolver_ollama_sem_chave() -> None:
    resolver = CredentialResolver(Settings())
    assert resolver.resolve("ollama") is None
    assert not resolver.status("ollama").configured


def test_resolver_sessao_cifrada(chave_32: bytes) -> None:
    key_b64 = base64.b64encode(chave_32).decode()
    resolver = CredentialResolver(Settings(encryption_key=key_b64))
    resolver.store("openai", "sk-segredo-123456")
    # O valor em memória não deve estar em claro.
    token = resolver._session[(None, "openai")]
    assert "sk-segredo-123456" not in token
    assert resolver.resolve("openai") == "sk-segredo-123456"


def test_status_nunca_expõe_a_chave() -> None:
    resolver = CredentialResolver(Settings(openai_api_key="sk-env-abcdefgh"))
    status = resolver.status("openai")
    payload = {
        "configurado": status.configured,
        "last4": status.last4,
        "fonte": status.source,
    }
    assert "sk-env-abcdefgh" not in str(payload)


def test_secret_cipher_rotacao_de_chave() -> None:
    chave_antiga = os.urandom(32)
    chave_nova = os.urandom(32)
    cipher_antigo = SecretCipher(chave_antiga)
    token_antigo = cipher_antigo.encrypt("sk-chave-rotacionada-9999")

    settings = Settings(
        encryption_key=base64.b64encode(chave_nova).decode(),
        previous_encryption_keys=[base64.b64encode(chave_antiga).decode()],
    )
    cipher_novo = SecretCipher.from_settings(settings)
    assert cipher_novo.decrypt(token_antigo) == "sk-chave-rotacionada-9999"

    token_recifrado = cipher_novo.rotate(token_antigo)
    assert SecretCipher(chave_nova).decrypt(token_recifrado) == "sk-chave-rotacionada-9999"


def test_chave_lida_da_variavel_indicada_pelo_cofre(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VAULT_OPENAI_TOKEN", "sk-do-cofre-1234")
    resolver = CredentialResolver(
        Settings(_env_file=None, openai_api_key_env_name="VAULT_OPENAI_TOKEN")  # type: ignore[call-arg]
    )

    assert resolver.resolve("openai") == "sk-do-cofre-1234"
    estado = resolver.status("openai")
    assert estado.configured is True
    assert estado.source == "env"
    assert estado.last4 == "1234"

    # Rotação no cofre é vista sem reiniciar a aplicação.
    monkeypatch.setenv("VAULT_OPENAI_TOKEN", "sk-rotacionada-9999")
    assert resolver.resolve("openai") == "sk-rotacionada-9999"


def test_valor_direto_tem_precedencia_sobre_indirecao(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VAULT_GEMINI", "do-cofre")
    resolver = CredentialResolver(
        Settings(  # type: ignore[call-arg]
            _env_file=None, gemini_api_key="direta-abcd", gemini_api_key_env_name="VAULT_GEMINI"
        )
    )
    assert resolver.resolve("gemini") == "direta-abcd"


def test_indirecao_para_variavel_ausente_deixa_provedor_indisponivel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("VAULT_INEXISTENTE", raising=False)
    resolver = CredentialResolver(
        Settings(_env_file=None, anthropic_api_key_env_name="VAULT_INEXISTENTE")  # type: ignore[call-arg]
    )
    assert resolver.resolve("anthropic") is None
    assert resolver.status("anthropic").configured is False


@pytest.mark.parametrize(
    "nome", ["SECRET_KEY", "encryption_key", "DATABASE_URL", "1INVALIDO", "a-b"]
)
def test_indirecao_rejeita_variaveis_reservadas_ou_invalidas(nome: str) -> None:
    with pytest.raises(ValueError):
        Settings(_env_file=None, openai_api_key_env_name=nome)  # type: ignore[call-arg]


def test_chave_lida_de_arquivo_de_segredo(tmp_path: Path) -> None:
    segredo = tmp_path / "openai_api_key"
    segredo.write_text("sk-do-arquivo-5678\n")
    resolver = CredentialResolver(
        Settings(_env_file=None, openai_api_key_file=str(segredo))  # type: ignore[call-arg]
    )
    assert resolver.resolve("openai") == "sk-do-arquivo-5678"
    assert resolver.status("openai").last4 == "5678"

    segredo.write_text("sk-rotacionada-0000")
    assert resolver.resolve("openai") == "sk-rotacionada-0000"


def test_arquivo_de_segredo_ausente_ou_grande_fica_indisponivel(tmp_path: Path) -> None:
    grande = tmp_path / "grande"
    grande.write_text("x" * 5000)
    resolver = CredentialResolver(
        Settings(  # type: ignore[call-arg]
            _env_file=None,
            gemini_api_key_file=str(tmp_path / "nao-existe"),
            anthropic_api_key_file=str(grande),
        )
    )
    assert resolver.resolve("gemini") is None
    assert resolver.resolve("anthropic") is None


def test_indirecao_por_variavel_tem_precedencia_sobre_arquivo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    arquivo = tmp_path / "chave"
    arquivo.write_text("do-arquivo")
    monkeypatch.setenv("VAULT_X", "da-variavel")
    resolver = CredentialResolver(
        Settings(  # type: ignore[call-arg]
            _env_file=None, openai_api_key_env_name="VAULT_X", openai_api_key_file=str(arquivo)
        )
    )
    assert resolver.resolve("openai") == "da-variavel"


def test_arquivo_de_segredo_exige_caminho_absoluto() -> None:
    with pytest.raises(ValueError, match="absoluto"):
        Settings(_env_file=None, openai_api_key_file="segredos/chave")  # type: ignore[call-arg]
