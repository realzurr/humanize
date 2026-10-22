"""Resolução e armazenamento de credenciais de provedores.

As chaves de API seguem uma cadeia de precedência fixa:

1. variável de ambiente / configuração local (``Settings``);
2. armazenamento de sessão (em memória), cifrado com AES-GCM quando a chave
   de criptografia está configurada.

A persistência cifrada em banco é da Onda 8; aqui a cifra AES-GCM já é
implementada e usada para o armazenamento de sessão, de modo que o valor da
chave nunca trafega em claro nem aparece em logs ou respostas.

A API só expõe o **indicador** ``configured`` e o sufixo ``last4`` — nunca o
valor da chave.
"""

from __future__ import annotations

import base64
import os
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import Settings
from app.services.providers.base import ProviderId

#: Mapeamento provedor -> campo de chave em ``Settings``.
_ENV_FIELDS: dict[ProviderId, str] = {
    ProviderId.OPENAI: "openai_api_key",
    ProviderId.ANTHROPIC: "anthropic_api_key",
    ProviderId.GEMINI: "gemini_api_key",
    ProviderId.OPENAI_COMPATIBLE: "openai_compatible_api_key",
}

#: Tamanho obrigatório da chave AES-GCM (32 bytes).
_KEY_BYTES = 32


class SecretCipher:
    """Cifra autenticada AES-GCM para credenciais."""

    def __init__(self, key: bytes | None) -> None:
        self._key = key

    @classmethod
    def from_settings(cls, settings: Settings) -> SecretCipher:
        """Constrói a cifra a partir de ``settings.encryption_key`` (base64)."""
        if not settings.encryption_key:
            return cls(None)
        try:
            key = base64.b64decode(settings.encryption_key, validate=True)
        except (ValueError, TypeError):
            return cls(None)
        if len(key) != _KEY_BYTES:
            return cls(None)
        return cls(key)

    @property
    def available(self) -> bool:
        """Indica se a cifra pode ser usada (chave configurada)."""
        return self._key is not None

    def encrypt(self, plaintext: str) -> str:
        """Cifra o texto e devolve um token ``v1:<base64(nonce+ciphertext)>``."""
        if self._key is None:
            raise RuntimeError("cifra indisponível: encryption_key não configurada")
        nonce = os.urandom(12)
        ciphertext = AESGCM(self._key).encrypt(nonce, plaintext.encode("utf-8"), None)
        return "v1:" + base64.b64encode(nonce + ciphertext).decode("ascii")

    def decrypt(self, token: str) -> str:
        """Decifra um token produzido por :meth:`encrypt`."""
        if self._key is None:
            raise RuntimeError("cifra indisponível: encryption_key não configurada")
        versao, _, payload = token.partition(":")
        if versao != "v1":
            raise ValueError("versão de token desconhecida")
        dados = base64.b64decode(payload.encode("ascii"), validate=True)
        nonce, ciphertext = dados[:12], dados[12:]
        return AESGCM(self._key).decrypt(nonce, ciphertext, None).decode("utf-8")


@dataclass(frozen=True, slots=True)
class CredentialStatus:
    """Indicador público do estado de uma credencial (sem a chave)."""

    provider: str
    configured: bool
    last4: str = ""
    source: str = ""
    """``env`` | ``session`` | ``""`` (não configurada)."""


def last4(chave: str) -> str:
    return chave[-4:] if len(chave) >= 4 else ""


class CredentialResolver:
    """Resolve chaves de provedores combinando ambiente e sessão (isolada por dono).

    A sessão em memória é indexada por ``(owner_id, provider)``, de modo que
    um usuário nunca enxerga nem sobrescreve a credencial de sessão de outro
    (`GAP-01`). A chave de ambiente é global (não depende de dono).
    """

    def __init__(self, settings: Settings, cipher: SecretCipher | None = None) -> None:
        self._settings = settings
        self._cipher = cipher or SecretCipher.from_settings(settings)
        self._session: dict[tuple[str | None, str], str] = {}

    def resolve(self, provider_id: ProviderId | str, *, owner_id: str | None = None) -> str | None:
        """Devolve a chave em claro (uso interno, nunca registrada)."""
        provider = str(provider_id)
        env = self._env_value(provider)
        if env:
            return env
        token = self._session.get((owner_id, provider))
        if token is None:
            return None
        if self._cipher.available:
            return self._cipher.decrypt(token)
        return token

    def status(
        self, provider_id: ProviderId | str, *, owner_id: str | None = None
    ) -> CredentialStatus:
        """Devolve o indicador público (configured/last4) sem a chave."""
        provider = str(provider_id)
        env = self._env_value(provider)
        if env:
            return CredentialStatus(
                provider=provider, configured=True, last4=last4(env), source="env"
            )
        token = self._session.get((owner_id, provider))
        if token is not None:
            chave = self._cipher.decrypt(token) if self._cipher.available else token
            return CredentialStatus(
                provider=provider, configured=True, last4=last4(chave), source="session"
            )
        return CredentialStatus(provider=provider, configured=False)

    def store(
        self,
        provider_id: ProviderId | str,
        chave: str,
        *,
        owner_id: str | None = None,
    ) -> CredentialStatus:
        """Armazena a chave na sessão (cifrada, quando possível), isolada por dono."""
        provider = str(provider_id)
        token = self._cipher.encrypt(chave) if self._cipher.available else chave
        self._session[(owner_id, provider)] = token
        return CredentialStatus(
            provider=provider, configured=True, last4=last4(chave), source="session"
        )

    def delete(
        self,
        provider_id: ProviderId | str,
        *,
        owner_id: str | None = None,
    ) -> CredentialStatus:
        """Remove a credencial de sessão do dono. A credencial de ambiente permanece."""
        provider = str(provider_id)
        self._session.pop((owner_id, provider), None)
        return self.status(provider, owner_id=owner_id)

    def _env_value(self, provider: str) -> str | None:
        try:
            provider_enum = ProviderId(provider)
        except ValueError:
            return None
        field = _ENV_FIELDS.get(provider_enum)
        if field is None:
            return None
        valor = getattr(self._settings, field, "")
        return valor or None
