# ADR-0017 — Endurecimento de segurança pós-Onda 8

- **Status**: Aceita
- **Data**: 2026-10-22
- **Impacto**: Médio
- **Supersede**: — (complementa `ADR-0011` e `ADR-0016`)

## Contexto

Após a Onda 8 e a auditoria de QA, foram implementados: Argon2id, rotação de
chaves, revogação de tokens, backends compartilhados de rate limit, retenção
agendada e um inspetor nativo de PDF. A revisão técnica
(`docs/REVISAO_AJUSTES.md`) encontrou lacunas entre o que a configuração e a
documentação prometiam e o que o código entregava. Este ADR registra as
decisões tomadas ao corrigi-las.

## Decisões

1. **Hash de senha: Argon2id** via `cryptography` (≥ 44, sem dependência
   nova), parâmetros OWASP `m=19456 KiB, t=2, p=1`. PBKDF2-SHA256 permanece
   apenas para verificação de hashes legados; `needs_rehash` também detecta
   parâmetros Argon2 desatualizados. O cálculo roda em `asyncio.to_thread`.
2. **Rotação de chaves**: `PREVIOUS_SECRET_KEYS` / `PREVIOUS_ENCRYPTION_KEYS`
   aceitam CSV ou lista JSON. A chave primária assina/cifra; as anteriores só
   verificam/decifram.
3. **Revogação de tokens em memória por processo.** `jti` revogados são
   guardados com o `exp` e podados quando expiram. A revogação **não** é
   compartilhada entre workers nem sobrevive a reinício — limitação aceita e
   declarada; o TTL curto (`ACCESS_TOKEN_TTL_SECONDS`) limita a janela.
4. **Rate limit: `memory` ou `sqlite`.** O valor `redis` foi **removido** de
   `RATE_LIMIT_BACKEND`: não havia cliente nem dependência Redis, e o backend
   caía silenciosamente para memória. A classe `RedisSlidingWindowLimiter`
   permanece como contrato testado; habilitá-la exige (a) dependência `redis`
   com justificativa (§7 do `AGENTS.md`) e (b) operação atômica
   (`MULTI/EXEC` ou Lua). `build_rate_limiter` agora **falha** quando o backend
   pedido não pode ser construído.
5. **IP do cliente atrás de proxy**: entrada `-TRUSTED_PROXY_HOPS` do
   `X-Forwarded-For` (padrão 1), nunca a primeira, que é controlada pelo
   cliente.
6. **Retenção**: apagar uma exportação expirada remove a linha **e** o arquivo
   em `EXPORT_DIR`. O loop periódico registra falhas e continua.
7. **Inspetor nativo de PDF** (sem `pymupdf`): só afirma contagem de páginas e
   tamanho da primeira página. Margens, páginas vazias e quebras são
   declaradas como **não verificadas** (`ADR-0015`).

## Consequências

- Configurações que antes eram aceitas e ignoradas (`RATE_LIMIT_BACKEND=redis`)
  agora falham na inicialização — comportamento intencional.
- Em implantação com vários nós, rate limit e revogação continuam por nó.
- Nova migração `0002_exports_document_id` alinha `exports.document_id`
  (120 caracteres) ao schema da API.

## Alternativas consideradas

| Alternativa | Motivo da rejeição |
|---|---|
| Adicionar `redis` agora | Dependência e infraestrutura novas sem demanda de implantação multi-nó |
| Revogação persistida no banco | Consulta extra em toda requisição autenticada; adiada para pendência |
| `argon2-cffi` | `cryptography` já é dependência e oferece Argon2id desde a 44 |
