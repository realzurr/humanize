"""Resolução e armazenamento de credenciais de provedores.

As chaves de API seguem uma cadeia de precedência fixa:

1. variável de ambiente / configuração local (``Settings``): o valor direto
   (``*_API_KEY``) ou, se vazio, a variável indicada por ``*_API_KEY_ENV_NAME``
   (indireção para cofre externo) ou, por fim, o arquivo ``*_API_KEY_FILE``
   (Docker/K8s secrets) — ambos lidos a cada resolução;
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
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import Settings
from app.core.logging import get_logger
from app.services.providers.base import ProviderId

#: Mapeamento provedor -> campo de chave em ``Settings``.
logger = get_logger(__name__)

_ENV_FIELDS: dict[ProviderId, str] = {
    ProviderId.OPENAI: "openai_api_key",
    ProviderId.ANTHROPIC: "anthropic_api_key",
    ProviderId.GEMINI: "gemini_api_key",
    ProviderId.OPENAI_COMPATIBLE: "openai_compatible_api_key",
}

#: Uma chave de API real tem algumas centenas de bytes; o limite evita carregar
#: um arquivo arbitrário apontado por engano.
_MAX_KEY_FILE_BYTES = 4096

#: Tamanho obrigatório da chave AES-GCM (32 bytes).
_KEY_BYTES = 32


def _decode_aes_key(raw: str) -> bytes | None:
    if not raw:
        return None
    try:
        key = base64.b64decode(raw, validate=True)
    except (ValueError, TypeError):
        return None
    return key if len(key) == _KEY_BYTES else None


def _ler_arquivo_chave(caminho: Path) -> str | None:
    """Lê a chave do arquivo; ausente, ilegível ou grande demais → indisponível.

    O caminho nunca é registrado em log junto do conteúdo, e o conteúdo nunca é logado.
    """
    try:
        if caminho.stat().st_size > _MAX_KEY_FILE_BYTES:
            logger.warning("credencial.arquivo_grande_demais", provider_file=caminho.name)
            return None
        return caminho.read_text(encoding="utf-8").strip() or None
    except (OSError, UnicodeDecodeError):
        return None


class SecretCipher:
    """Cifra autenticada AES-GCM para credenciais, com suporte a rotação de chave."""

    def __init__(
        self,
        key: bytes | None,
        *,
        previous_keys: tuple[bytes, ...] = (),
    ) -> None:
        self._key = key
        self._previous_keys = previous_keys

    @classmethod
    def from_settings(cls, settings: Settings) -> SecretCipher:
        """Constrói a cifra a partir de ``encryption_key`` e ``previous_encryption_keys``."""
        primary = _decode_aes_key(settings.encryption_key)
        anteriores = tuple(
            decoded
            for item in settings.previous_encryption_keys
            if (decoded := _decode_aes_key(item)) is not None
        )
        return cls(primary, previous_keys=anteriores)

    @property
    def available(self) -> bool:
        """Indica se a cifra pode ser usada (chave primária configurada)."""
        return self._key is not None

    def encrypt(self, plaintext: str) -> str:
        """Cifra o texto com a chave primária e devolve ``v1:<base64(nonce+ciphertext)>``."""
        if self._key is None:
            raise RuntimeError("cifra indisponível: encryption_key não configurada")
        nonce = os.urandom(12)
        ciphertext = AESGCM(self._key).encrypt(nonce, plaintext.encode("utf-8"), None)
        return "v1:" + base64.b64encode(nonce + ciphertext).decode("ascii")

    def decrypt(self, token: str) -> str:
        """Decifra um token tentando a chave primária e, em seguida, as chaves em rotação."""
        if self._key is None:
            raise RuntimeError("cifra indisponível: encryption_key não configurada")
        versao, _, payload = token.partition(":")
        if versao != "v1":
            raise ValueError("versão de token desconhecida")
        dados = base64.b64decode(payload.encode("ascii"), validate=True)
        nonce, ciphertext = dados[:12], dados[12:]
        for key in (self._key, *self._previous_keys):
            try:
                return AESGCM(key).decrypt(nonce, ciphertext, None).decode("utf-8")
            except InvalidTag:
                continue
        raise InvalidTag()

    def rotate(self, token: str) -> str:
        """Decifra um token (com chave atual ou anterior) e recifra com a chave primária."""
        return self.encrypt(self.decrypt(token))


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
        if valor:
            return str(valor)
        nome_variavel = getattr(self._settings, f"{field}_env_name", "")
        if nome_variavel:
            return os.environ.get(nome_variavel, "").strip() or None
        arquivo = getattr(self._settings, f"{field}_file", None)
        if arquivo is None:
            return None
        return _ler_arquivo_chave(arquivo)
