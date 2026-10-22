"""Testes da persistência durável de credenciais (AES-GCM em repouso)."""

from __future__ import annotations

import pytest

from app.core.errors import ValidationError
from app.repositories.credentials import CredentialRepository
from app.services.providers.credentials import SecretCipher
from app.services.providers.persistent_credentials import PersistentCredentialStore


def _store() -> PersistentCredentialStore:
    return PersistentCredentialStore(SecretCipher(b"0" * 32))


def test_save_armazena_ciphertext_e_nao_o_segredo(db_session) -> None:
    store = _store()
    status = store.save(db_session, "openai", "sk-abcdef123456", owner_id="u1")
    assert status.configured
    assert status.last4 == "3456"

    cred = CredentialRepository(db_session).get("openai", "u1")
    assert cred is not None
    assert "sk-abcdef123456" not in cred.ciphertext
    assert cred.ciphertext.startswith("v1:")


def test_status_e_delete(db_session) -> None:
    store = _store()
    store.save(db_session, "openai", "sk-abcdef123456", owner_id="u1")
    assert store.status(db_session, "openai", owner_id="u1").configured

    store.delete(db_session, "openai", owner_id="u1")
    assert not store.status(db_session, "openai", owner_id="u1").configured


def test_isolamento_por_owner(db_session) -> None:
    store = _store()
    store.save(db_session, "openai", "sk-abcdef123456", owner_id="u1")
    assert not store.status(db_session, "openai", owner_id="u2").configured


def test_save_sem_cifra_lanca_erro(db_session) -> None:
    store = PersistentCredentialStore(SecretCipher(None))
    with pytest.raises(ValidationError):
        store.save(db_session, "openai", "sk-abcdef123456")


def test_upsert_atualiza_e_lista_por_owner(db_session) -> None:
    store = _store()
    store.save(db_session, "openai", "sk-1111aaaa", owner_id="u1")
    store.save(db_session, "openai", "sk-2222bbbb", owner_id="u1")
    assert store.status(db_session, "openai", owner_id="u1").last4 == "bbbb"
    assert len(CredentialRepository(db_session).list_for_owner("u1")) == 1
