"""Configuração da aplicação.

Somente variáveis de ambiente (ou um arquivo ``.env`` local, ignorado pelo
git) alimentam a configuração. **Nenhuma chave de API tem valor padrão no
código**: o campo ``api_key`` é opcional e, quando ausente, o provedor
correspondente é tratado como indisponível.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

#: Raiz do repositório (backend/ -> ..).
BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_ROOT.parent


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

    encryption_key: str = ""
    """Chave de criptografia autenticada para credenciais persistidas.

    Deve ter 32 bytes codificados em base64. Sem valor padrão.
    """

    credential_encryption_enabled: bool = False
    """Habilita a criptografia de credenciais persistidas (Onda 8)."""

    auth_enabled: bool = False
    """Habilita autenticação e isolamento por usuário (obrigatório em produção)."""

    access_token_ttl_seconds: int = 3600
    """Tempo de vida do token de acesso (segundos)."""

    rate_limit_login_per_minute: int = 10
    """Limite de tentativas de login por minuto (por IP)."""

    rate_limit_humanize_per_minute: int = 30
    """Limite de requisições de humanização por minuto (por IP)."""

    behind_proxy: bool = False
    """Indica que a aplicação está atrás de um proxy reverso confiável.

    Quando ``True``, o rate limiter confia no cabeçalho ``X-Forwarded-For``;
    quando ``False`` (padrão), usa o IP direto da conexão (`GAP-04`).
    """

    document_retention_days: int = 30
    """Prazo de retenção de documentos (dias)."""

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
