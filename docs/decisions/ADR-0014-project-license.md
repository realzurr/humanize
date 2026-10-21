# ADR-0014 — Licença do projeto e atribuição de autoria/créditos

- **Status**: Aceita
- **Data**: 2026-10-21
- **Impacto**: Alto
- **Decisor**: Renato Lemes Peixoto (`realzurr`)

## Contexto

O projeto **Humaniza Acadêmico** foi concebido e desenvolvido por **Renato Lemes
Peixoto (`realzurr`)** como uma implementação *clean-room* (`ADR-0001`), tendo
como inspiração funcional inicial para o módulo de limpeza textual o projeto
[`takumar-x/AI-Humanizer`](https://github.com/takumar-x/AI-Humanizer) (de
`takumar-x` / Mikhail Medvedev, sob GPL-3.0).

Como nenhuma linha de código do repositório de referência foi copiada ou
adaptada, o titular do projeto (**Renato Lemes Peixoto — `realzurr`**) detém
plena liberdade para definir a licença oficial do repositório, mantendo os
devidos créditos conceituais ao autor da referência.

## Decisão

1. **Licença oficial**: o projeto **Humaniza Acadêmico** é licenciado sob a
   **MIT License**, formalizada no arquivo [`LICENSE`](../../LICENSE) na raiz do
   repositório, em `backend/pyproject.toml` e em `frontend/package.json`.
2. **Autoria**: a titularidade e autoria do projeto são registradas em nome de
   **Renato Lemes Peixoto (`realzurr`)**.
3. **Créditos à referência de origem**: o arquivo `LICENSE` e o `README.md`
   declaram explicitamente os créditos de inspiração conceitual ao projeto
   [`takumar-x/AI-Humanizer`](https://github.com/takumar-x/AI-Humanizer) e ao
   seu autor (`takumar-x` / Mikhail Medvedev).
4. **Dependências de terceiros**: todas as dependências são utilizadas sem
   modificação via pacote padrão; `PyMuPDF` é empregado exclusivamente para
   inspeção local de métricas de página/margem na validação de testes e
   comparação DOCX↔PDF.

## Consequências

### Positivas

- Licença permissiva clara (MIT) facilita adoção acadêmica, institucional e
  contribuições externas.
- Transparência ética e técnica ao creditar formalmente o repositório de
  referência que inspirou o módulo inicial de normalização.
- Autoria claramente identificada em todos os manifestos do projeto.
