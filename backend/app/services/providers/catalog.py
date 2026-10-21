"""Catálogo estático de modelos por provedor.

Os modelos e os preços são **aproximados** e servem apenas para estimativa
de custo e para a lista de modelos na interface. Não há cobrança; a tabela
deve ser revista periodicamente. Preços em USD por 1 000 tokens.
"""

from __future__ import annotations

from app.services.providers.base import ModelInfo, ProviderId


def _modelo(
    provider: ProviderId,
    model_id: str,
    *,
    nome: str = "",
    janela: int | None = None,
    saida: int | None = None,
    streaming: bool = True,
    json_mode: bool = True,
    entrada: float | None = None,
    saida_preco: float | None = None,
    obsoleto: bool = False,
) -> ModelInfo:
    return ModelInfo(
        id=model_id,
        provider=provider,
        display_name=nome or model_id,
        context_window=janela,
        max_output_tokens=saida,
        supports_streaming=streaming,
        supports_json_mode=json_mode,
        input_cost_per_1k=entrada,
        output_cost_per_1k=saida_preco,
        deprecated=obsoleto,
    )


def openai_models() -> tuple[ModelInfo, ...]:
    """Modelos OpenAI (preços aproximados)."""
    return (
        _modelo(
            ProviderId.OPENAI,
            "gpt-4.1",
            nome="GPT-4.1",
            janela=1_000_000,
            saida=32768,
            entrada=0.002,
            saida_preco=0.008,
        ),
        _modelo(
            ProviderId.OPENAI,
            "gpt-4.1-mini",
            nome="GPT-4.1 mini",
            janela=1_000_000,
            saida=32768,
            entrada=0.0004,
            saida_preco=0.0016,
        ),
        _modelo(
            ProviderId.OPENAI,
            "gpt-4o",
            nome="GPT-4o",
            janela=128000,
            saida=16384,
            entrada=0.0025,
            saida_preco=0.01,
        ),
        _modelo(
            ProviderId.OPENAI,
            "gpt-4o-mini",
            nome="GPT-4o mini",
            janela=128000,
            saida=16384,
            entrada=0.00015,
            saida_preco=0.0006,
        ),
    )


def anthropic_models() -> tuple[ModelInfo, ...]:
    """Modelos Anthropic (preços aproximados)."""
    return (
        _modelo(
            ProviderId.ANTHROPIC,
            "claude-sonnet-4-5",
            nome="Claude Sonnet 4.5",
            janela=200000,
            saida=64000,
            entrada=0.003,
            saida_preco=0.015,
        ),
        _modelo(
            ProviderId.ANTHROPIC,
            "claude-opus-4",
            nome="Claude Opus 4",
            janela=200000,
            saida=32000,
            entrada=0.015,
            saida_preco=0.075,
        ),
        _modelo(
            ProviderId.ANTHROPIC,
            "claude-3-5-haiku",
            nome="Claude 3.5 Haiku",
            janela=200000,
            saida=8192,
            entrada=0.0008,
            saida_preco=0.004,
            obsoleto=True,
        ),
    )


def gemini_models() -> tuple[ModelInfo, ...]:
    """Modelos Gemini (preços aproximados)."""
    return (
        _modelo(
            ProviderId.GEMINI,
            "gemini-2.5-pro",
            nome="Gemini 2.5 Pro",
            janela=1_000_000,
            saida=65536,
            entrada=0.00125,
            saida_preco=0.01,
        ),
        _modelo(
            ProviderId.GEMINI,
            "gemini-2.5-flash",
            nome="Gemini 2.5 Flash",
            janela=1_000_000,
            saida=65536,
            entrada=0.0003,
            saida_preco=0.0025,
        ),
        _modelo(
            ProviderId.GEMINI,
            "gemini-2.0-flash",
            nome="Gemini 2.0 Flash",
            janela=1_000_000,
            saida=8192,
            entrada=0.0001,
            saida_preco=0.0004,
            obsoleto=True,
        ),
    )


def ollama_models() -> tuple[ModelInfo, ...]:
    """Modelos locais comuns do Ollama (sem custo, rodam na máquina)."""
    return (
        _modelo(ProviderId.OLLAMA, "llama3.1", nome="Llama 3.1", janela=128000, json_mode=False),
        _modelo(ProviderId.OLLAMA, "llama3.2", nome="Llama 3.2", janela=128000, json_mode=False),
        _modelo(ProviderId.OLLAMA, "mistral", nome="Mistral 7B", janela=32768, json_mode=False),
        _modelo(ProviderId.OLLAMA, "qwen2.5", nome="Qwen 2.5", janela=128000, json_mode=False),
        _modelo(ProviderId.OLLAMA, "phi4", nome="Phi-4", janela=16384, json_mode=False),
    )


def openai_compatible_models(declared: list[str] | None) -> tuple[ModelInfo, ...]:
    """Modelos declarados de um endpoint compatível com OpenAI."""
    nomes = declared or []
    return tuple(_modelo(ProviderId.OPENAI_COMPATIBLE, nome, nome=nome) for nome in nomes)


#: Catálogo por provedor. Ollama e OpenAI-compatível dependem do ambiente.
STATIC_CATALOG: dict[ProviderId, tuple[ModelInfo, ...]] = {
    ProviderId.OPENAI: openai_models(),
    ProviderId.ANTHROPIC: anthropic_models(),
    ProviderId.GEMINI: gemini_models(),
    ProviderId.OLLAMA: ollama_models(),
}
