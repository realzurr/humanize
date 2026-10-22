# ADR-0019 — Chaves de LLM em arquivo e encerramento de todas as sessões

- **Status**: Aceita
- **Data**: 2026-10-22
- **Impacto**: Baixo
- **Supersede**: — (complementa `ADR-0018`)

## Contexto

Pendências registradas após o `ADR-0018`: segredo de LLM em arquivo (padrão
Docker/Kubernetes secrets) e uma forma de usar `revoke_subject` pela API.

## Decisões

1. **`<PROVEDOR>_API_KEY_FILE`**: caminho **absoluto** de um arquivo com a chave,
   lido a cada resolução (rotação sem reinício), limitado a 4 KiB.
   Precedência: `*_API_KEY` > `*_API_KEY_ENV_NAME` > `*_API_KEY_FILE` > sessão.
   Arquivo ausente, ilegível ou grande demais → provedor indisponível.
2. **`POST /auth/logout-all`**: o usuário autenticado revoga **os próprios**
   tokens (`revoke_subject`). Não há rota para revogar terceiros: isso exige um
   papel administrativo, que o sistema não possui — decisão adiada ao
   responsável (ver `ROADMAP.md`).
3. Diferente do logout simples, a falha de `logout-all` é mostrada ao usuário
   no frontend: ele precisa saber se as outras sessões continuam válidas.

## Alternativas consideradas

| Alternativa | Motivo da rejeição |
|---|---|
| Caminho relativo para o arquivo de chave | Dependeria do diretório de trabalho do processo |
| Ler o arquivo uma vez no startup | Impediria rotação sem reinício |
| Criar papel `admin` agora | Mudança de modelo de autorização sem decisão do responsável |
