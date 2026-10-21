# ADR-0011 — SQLAlchemy 2.0 + Alembic; SQLite em dev, PostgreSQL em prod

- **Status**: Aceita
- **Data**: 2026-10-21
- **Impacto**: Médio

## Contexto

O sistema precisa persistir: documentos (com texto original e revisões),
registros de transformação, credenciais de provedor (cifradas), perfis
autorais, exports e relatórios de validação.

A instalação inicial é **somente local**. O `docker-compose.yml` compoe
serviços, mas nada é instalado em servidor externo sem autorização.

## Decisão

- **SQLAlchemy 2.0** com estilo `Mapped[]` / `mapped_column`.
- **Alembic** para migrações. `create_all` é **proibido** em produção.
- **SQLite** em desenvolvimento; **PostgreSQL** em produção. O
  `database_url` vem da variável de ambiente.
- `original_text` é armazenado em coluna separada e **nunca** é atualizado.
- Revisões são append-only.
- Entidades de origem externa (credenciais, perfis autorais) carregam
  `owner_id`, para suportar o isolamento multiusuário da Onda 8.

### Tabelas previstas

| Tabela | Conteúdo | Notas |
|---|---|---|
| `documents` | original, revisão corrente, metadados, `owner_id` | `original_text` imutável |
| `revisions` | texto, estágio, `parent_id`, metadados | append-only |
| `transformations` | `rule_id`, contagem, localização | linked a `revisions` |
| `provider_credentials` | chave cifrada (AES-GCM), `last4`, `owner_id` | nunca serializada a API |
| `author_profiles` | traços de estilo derivados, `owner_id` | só do próprio usuário |
| `exports` | formato, caminho, hash, `owner_id` | retenção por política |
| `validation_reports` | achados por regra, severidade, local | linked a `revisions` |

### Cifragem de credenciais

Credenciais persistidas usam **criptografia autenticada** (AES-GCM, via
`cryptography`), com a chave **fora do banco** (`encryption_key` na
configuração/ambiente). A API expoe apenas `configured: bool` e `last4`.

## Consequências

### Positivas

- Zero configuração para desenvolvimento local.
- Portabilidade para produção sem reescrever o modelo.
- Alembic garante que o schema evolui de forma versionada e reversível.
- `owner_id` desde o início evita uma migração dolorosa na Onda 8.

### Negativas

- SQLite não suporta todos os tipos do PostgreSQL (ex.: `JSONB`); o código
  deve abstrair o tipo de coluna portável ou declarar a dependência.
- Alembic exige disciplina: toda mudança de modelo gera migração.

## Alternativas consideradas

| Alternativa | Motivo da rejeição |
|---|---|
| Apenas arquivos (JSON/SQLite direto) | Sem integridade referencial nem migrações |
| `create_all` em produção | Perde histórico de schema; irreversível |
| MongoDB | Modelo relacional é mais natural para revisões e relatórios; adiciona dependência de serviço |
| Postgres desde o início | Exige serviço externo para desenvolvimento local |
