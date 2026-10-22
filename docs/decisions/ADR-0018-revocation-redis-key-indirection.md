# ADR-0018 — Revogação persistida, rate limit Redis e indireção de chaves de LLM

- **Status**: Aceita
- **Data**: 2026-10-22
- **Impacto**: Médio
- **Supersede**: `ADR-0017`, itens 3 (revogação em memória) e 4 (Redis fora da configuração)

## Contexto

O `ADR-0017` deixou como limitação declarada: revogação de tokens por processo,
rate limit sem opção multi-nó e a indireção de chave de LLM por cofre externo
(`*_API_KEY_ENV_NAME`, pendente desde a Onda 8). O responsável autorizou a
implementação das três, além de um teste automatizado dos cabeçalhos do Nginx.

## Decisões

1. **Revogação persistida (`REVOCATION_BACKEND=database`, padrão).**
   - Contrato `RevocationStore` em `app/core/security.py`; implementação SQL em
     `app/repositories/revocations.py` (`core` não importa ORM — `ADR-0002`).
   - Tabelas `revoked_tokens (jti, expires_at)` e
     `revoked_subjects (subject, revoked_before)`, migração `0003`.
   - Instantes em *epoch* `Float`, mesmo formato de `iat`/`exp` do token.
   - Custo aceito: até duas consultas por chave primária em cada requisição
     autenticada. `memory` continua disponível para instância única.
2. **Rate limit Redis (`RATE_LIMIT_BACKEND=redis` + `REDIS_URL`).**
   - Limpeza, contagem e inserção num único script Lua (`EVAL`), atômico no
     servidor; o relógio é o `TIME` do Redis, para nós com relógios
     divergentes compartilharem a mesma janela.
   - Dependência `redis` (MIT) como **extra opcional** (`pip install -e ".[redis]"`),
     importada só quando o backend é selecionado — mesmo padrão do `ADR-0016`.
   - Dev: `fakeredis[lua]` (BSD-3; puxa `lupa` MIT e `sortedcontainers`
     Apache-2.0) para testar o script Lua real, sem servidor.
   - Sem `REDIS_URL` ou sem o extra, a aplicação **não inicia**.
3. **Indireção de chave de LLM (`<PROVEDOR>_API_KEY_ENV_NAME`).**
   - Informa o *nome* da variável em que o cofre injeta a chave; lida a cada
     resolução (rotação sem reinício). O valor direto `*_API_KEY` tem precedência.
   - Nomes reservados (`SECRET_KEY`, `ENCRYPTION_KEY`, `PREVIOUS_*`,
     `DATABASE_URL`, `REDIS_URL`) são rejeitados: apontar para eles enviaria um
     segredo da aplicação ao provedor e exporia seu `last4`.
4. **Cabeçalhos do Nginx**: teste estático (Vitest) que exige os cabeçalhos no
   `server` e em todo `location` com `add_header` próprio.

## Consequências

- `alembic upgrade head` é obrigatório antes do deploy (tabelas de revogação).
- Implantações multi-nó passam a ter limite e revogação globais.
- O teste do Nginx valida a configuração, não um servidor em execução; a
  verificação com contêiner real foi feita manualmente (relatório da rodada).

## Alternativas consideradas

| Alternativa | Motivo da rejeição |
|---|---|
| Revogação em Redis | Exigiria Redis mesmo para quem usa só o banco |
| Cache em memória das consultas de revogação | Reabre a janela de inconsistência entre workers |
| `redis` como dependência obrigatória | A maioria das instalações é de nó único |
| Mock do cliente Redis em Python | Não exercitaria o script Lua real |
| `*_API_KEY_FILE` (segredo em arquivo) | Fora do escopo autorizado; registrado como ideia no ROADMAP |
