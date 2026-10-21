# ADR-0004 — Abstração `LLMProvider` com adaptadores por fornecedor

- **Status**: Aceita
- **Data**: 2026-10-21
- **Impacto**: Alto

## Contexto

O produto precisa suportar OpenAI, Anthropic Claude, Google Gemini, Ollama
(modelos locais) e endpoints compatíveis com a API da OpenAI (LM Studio,
vLLM, gateways corporativos). Cada fornecedor tem:

- formato de requisição e resposta próprio;
- sistema de erros próprio (429 vs. 529 vs. 503);
- mecanismos distintos de contagem de tokens e preço;
- suporte desigual a streaming, modo JSON e prompt de sistema;
-politicas distintas de limite de taxa e de `Retry-After`.

## Decisão

Definir um único contrato em `app/services/providers/base.py`:

```python
class LLMProvider(abc.ABC):
    provider_id: ProviderId
    requires_key: bool = True

    async def list_models(self) -> Sequence[ModelInfo]: ...
    async def check_credentials(self) -> CredentialCheck: ...
    async def generate(self, request: LLMRequest) -> LLMResponse: ...
    async def stream(self, request: LLMRequest) -> AsyncIterator[str]: ...
    async def cancel(self, request_id: str) -> bool: ...
    def estimate_cost(self, model, prompt_tokens, completion_tokens) -> float: ...
```

### Invariantes do contrato

1. Entrada e saida são **independentes do fornecedor** (`LLMRequest`,
   `LLMResponse`, `ChatMessage`).
2. Credenciais **nunca** aparecem em log, exceção ou resposta de API.
3. Todo erro é normalizado em `ProviderError` com `code`
   (`AUTH`, `RATE_LIMIT`, `TIMEOUT`, `NETWORK`, `QUOTA`, `MODEL_NOT_FOUND`,
   `INVALID_RESPONSE`, `CONTENT_FILTER`, `UNSUPPORTED`, `CANCELLED`,
   `SERVER_ERROR`, `UNKNOWN`), `retryable` e `retry_after_seconds`.
4. `ProviderError.to_public_dict()` é a **única** forma de expor erro ao
   cliente.
5. Custos são **estimados**, nunca cobrados.

### Adendo (Onda 2) — transporte via `httpx` em vez de SDKs oficiais

O texto original previa "SDK oficial" para cada adaptador. A implementação
da Onda 2 optou por **HTTP direto via `httpx`** (já presente no manifesto de
dependências, junto com `tenacity` e `cryptography`), pelas razões:

- evita três dependências pesadas (`openai`, `anthropic`,
  `google-generativeai`), reduzindo a superfície de fornecimento;
- permite testes determinísticos com `httpx.MockTransport` (sem rede, sem
  custo e sem mocks de SDK);
- centraliza a normalização de erro em `resilience.py` (o SDK não normaliza
  `429`/`Retry-After`/`529` de forma uniforme);
- o contrato neutro (`LLMRequest`/`LLMResponse`) já isola o sistema dos
  detalhes de cada fornecedor.

O trade-off (perda de recursos específicos como `seed` e cache de prompt) já
era listado como negativo da própria decisão original e permanece coberto por
`LLMRequest.metadata`. A tabela "Adaptadores" acima mantém a nomenclatura dos
arquivos, trocando "SDK oficial" por "HTTP direto".

### Adaptadores

| Adaptador | Observação |
|---|---|
| `openai_provider.py` | HTTP direto (`/chat/completions`); base do `openai_compat.py` |
| `anthropic_provider.py` | HTTP direto; `max_tokens` obrigatório |
| `gemini_provider.py` | HTTP direto; `systemInstruction` + `generationConfig` |
| `ollama_provider.py` | Sem chave; modelos locais (`/api/chat`) |
| `openai_compat.py` | Endpoint configurável + lista de modelos declarada |

`resilience.py` centraliza timeout, retry com backoff exponencial e jitter,
respeito a `Retry-After` e tratamento de rate limit. `usage.py` centraliza
contagem de tokens e estimativa de custo.

## Consequências

### Positivas

- Trocar ou adicionar fornecedor não afeta o resto do sistema.
- Testes usam *fake providers*, sem rede e sem custo.
- Resiliência (retry, rate limit) implementada uma vez.
- `Ollama` permite uso totalmente offline, sem chave externa.

### Negativas

- Um modelo comum que expressa o mínimo comum dos fornecedores perde
  recurso específico (ex.: `seed`, cache de prompt da Anthropic). Recursos
  específicos ficam em `LLMRequest.metadata`, com validação no adaptador.
- O SDK oficial de cada fornecedor é uma dependência a mais.

## Alternativas consideradas

| Alternativa | Motivo da rejeição |
|---|---|
| Usar `litellm` como única dependência | resolve o problema, mas da menos controle sobre normalização de erro, cancelamento e estimativa de custo; e uma dependência grande e de licença MIT, aceitável, mas não necessaria |
| Chamar as APIs por HTTP cru | Mais código, mais frágil de manter, perde modo JSON e contagem de tokens |
| Acoplamento direto no `humanizer` | Difícil de testar, impossível de trocar de fornecedor |
