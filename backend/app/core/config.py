"""Configuração da aplicação.

Somente variáveis de ambiente (ou um arquivo ``.env`` local, ignorado pelo
git) alimentam a configuração. **Nenhuma chave de API tem valor padrão no
código**: o campo ``api_key`` é opcional e, quando ausente, o provedor
correspondente é tratado como indisponível.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

#: Raiz do repositório (backend/ -> ..).
BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_ROOT.parent


_NOME_VARIAVEL_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,127}")
_VARIAVEIS_PROIBIDAS_PARA_INDIRECAO = frozenset(
    {
        "SECRET_KEY",
        "PREVIOUS_SECRET_KEYS",
        "ENCRYPTION_KEY",
        "PREVIOUS_ENCRYPTION_KEYS",
        "DATABASE_URL",
        "REDIS_URL",
    }
)


class Settings(BaseSettings):
    """Configuração global da aplicação."""

    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Aplicação -------------------------------------------------------
    app_name: str = "Humaniza Acadêmico"
    app_version: str = "0.1.0"
    environment: Literal["local", "development", "test", "production"] = "local"
    debug: bool = False
    api_prefix: str = "/api/v1"

    # --- Servidor --------------------------------------------------------
    host: str = "127.0.0.1"
    port: int = 8000
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    # --- Persistência ----------------------------------------------------
    database_url: str = f"sqlite:///{BACKEND_ROOT / 'data' / 'app.db'}"
    sql_echo: bool = False

    # --- Armazenamento de arquivos --------------------------------------
    storage_dir: Path = BACKEND_ROOT / "data"
    max_upload_bytes: int = 10 * 1024 * 1024
    """Limite padrão de upload (10 MiB)."""

    # --- LLM -------------------------------------------------------------
    default_provider: str = "ollama"
    default_model: str = ""
    llm_timeout_seconds: float = 120.0
    llm_max_retries: int = 3
    llm_max_output_tokens: int = 8192

    openai_api_key: str = ""
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    ollama_base_url: str = "http://127.0.0.1:11434"

    openai_compatible_base_url: str = ""
    openai_compatible_api_key: str = ""

    # Indireção para cofre externo: em vez da chave, informa-se o NOME da variável
    # de ambiente em que o cofre (Vault Agent, External Secrets, Docker/K8s) a injeta.
    # A variável é lida a cada resolução, o que permite rotação sem reiniciar.
    openai_api_key_env_name: str = ""
    anthropic_api_key_env_name: str = ""
    gemini_api_key_env_name: str = ""
    openai_compatible_api_key_env_name: str = ""

    # Segredo em arquivo (Docker/Kubernetes secrets): caminho absoluto, lido a
    # cada resolução. Usado só quando o valor direto e o ``*_env_name`` estão vazios.
    openai_api_key_file: Path | None = None
    anthropic_api_key_file: Path | None = None
    gemini_api_key_file: Path | None = None
    openai_compatible_api_key_file: Path | None = None
    openai_compatible_models: list[str] = Field(default_factory=list)

    #: Quando ``True``, o sistema pode consultar o Crossref/DataCite para
    #: metadados de DOI. Desligado por padrão (exige rede externa).
    enable_doi_lookup: bool = False
    doi_lookup_timeout_seconds: float = 15.0
    doi_user_agent: str = "HumanizaAcademico/0.1 (+mailto:contato@example.org)"

    # --- Documentos ------------------------------------------------------
    templates_dir: Path = REPO_ROOT / "templates"
    export_dir: Path = BACKEND_ROOT / "data" / "exports"
    pdf_renderer: Literal["libreoffice", "docx2pdf", "none"] = "libreoffice"
    libreoffice_binary: str = "soffice"

    # --- Segurança -------------------------------------------------------
    secret_key: str = ""
    """Chave de assinatura de sessão. Sem valor padrão."""

    previous_secret_keys: Annotated[list[str], NoDecode] = Field(default_factory=list)
    """Chaves de assinatura anteriores aceitas na verificação durante rotação."""

    encryption_key: str = ""
    """Chave de criptografia autenticada para credenciais persistidas.

    Deve ter 32 bytes codificados em base64. Sem valor padrão.
    """

    previous_encryption_keys: Annotated[list[str], NoDecode] = Field(default_factory=list)
    """Chaves AES-GCM anteriores (base64, 32 bytes) aceitas na decifragem durante rotação."""

    credential_encryption_enabled: bool = False
    """Habilita a criptografia de credenciais persistidas (Onda 8)."""

    auth_enabled: bool = False
    """Habilita autenticação e isolamento por usuário (obrigatório em produção)."""

    access_token_ttl_seconds: int = 3600
    """Tempo de vida do token de acesso (segundos)."""

    revocation_backend: Literal["memory", "database"] = "database"
    """Onde ficam as revogações de token: ``database`` (compartilhada entre workers e
    persistente) ou ``memory`` (por processo, perdida ao reiniciar)."""

    rate_limit_login_per_minute: int = 10
    """Limite de tentativas de login por minuto (por IP)."""

    rate_limit_humanize_per_minute: int = 30
    """Limite de requisições de humanização por minuto (por IP)."""

    rate_limit_backend: Literal["memory", "sqlite", "redis"] = "memory"
    """Backend do rate limiter: ``memory`` (por processo), ``sqlite`` (workers do mesmo
    host) ou ``redis`` (vários nós; exige ``redis_url`` e o extra ``redis``)."""

    redis_url: str = ""
    """URL do Redis (ex.: ``redis://redis:6379/0``) para ``rate_limit_backend=redis``."""

    behind_proxy: bool = False
    """Indica que a aplicação está atrás de um proxy reverso confiável.

    Quando ``True``, o rate limiter confia no cabeçalho ``X-Forwarded-For``;
    quando ``False`` (padrão), usa o IP direto da conexão (`GAP-04`).
    """

    trusted_proxy_hops: int = Field(default=1, ge=1, le=10)
    """Quantidade de proxies confiáveis que anexam entradas ao ``X-Forwarded-For``.

    O IP do cliente é a entrada na posição ``-trusted_proxy_hops``; as entradas à
    esquerda são fornecidas pelo próprio cliente e podem ser falsificadas.
    """

    document_retention_days: int = 30
    """Prazo de retenção de documentos (dias)."""

    retention_sweep_interval_seconds: int = 0
    """Intervalo (segundos) da rotina automática de retenção em background (0 = desligada)."""

    @field_validator("previous_secret_keys", "previous_encryption_keys", mode="before")
    @classmethod
    def _parse_lista_chaves(cls, value: object) -> object:
        """Aceita lista JSON ou CSV, pois chaves em rotação vêm de variáveis de ambiente."""
        if not isinstance(value, str):
            return value
        bruto = value.strip()
        if not bruto:
            return []
        if bruto.startswith("["):
            return json.loads(bruto)
        return [item.strip() for item in bruto.split(",") if item.strip()]

    @field_validator(
        "openai_api_key_env_name",
        "anthropic_api_key_env_name",
        "gemini_api_key_env_name",
        "openai_compatible_api_key_env_name",
    )
    @classmethod
    def _validar_nome_variavel_chave(cls, value: str) -> str:
        """Impede que a indireção aponte para segredos da própria aplicação.

        Sem esta trava, ``OPENAI_API_KEY_ENV_NAME=SECRET_KEY`` enviaria a chave de
        assinatura ao provedor de LLM e exporia seus 4 últimos caracteres na API.
        """
        nome = value.strip()
        if not nome:
            return ""
        if not _NOME_VARIAVEL_RE.fullmatch(nome):
            raise ValueError(f"nome de variável de ambiente inválido: {nome!r}")
        if nome.upper() in _VARIAVEIS_PROIBIDAS_PARA_INDIRECAO:
            raise ValueError(f"a variável {nome} é reservada e não pode conter chave de LLM")
        return nome

    @field_validator(
        "openai_api_key_file",
        "anthropic_api_key_file",
        "gemini_api_key_file",
        "openai_compatible_api_key_file",
        mode="before",
    )
    @classmethod
    def _validar_arquivo_chave(cls, value: object) -> object:
        """Exige caminho absoluto: um relativo dependeria do diretório de trabalho do processo."""
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        caminho = Path(str(value)).expanduser()
        if not caminho.is_absolute():
            raise ValueError(f"o arquivo de chave deve ter caminho absoluto: {value}")
        return caminho

    @field_validator("secret_key", "encryption_key")
    @classmethod
    def _warn_empty_secrets(cls, value: str) -> str:
        # Sem valor padrão proposital: a aplicação deve funcionar em modo local
        # sem autenticação (Onda 0-7) e habilitar a autenticação na Onda 8.
        return value

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Instância única de :class:`Settings` (cacheada)."""
    return Settings()
