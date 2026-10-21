# Templates de Formatação

Cada template é um arquivo YAML **versionado** que parametriza as regras de
formatação acadêmica. Nenhuma regra de layout está hard-coded no código
Python: o formatador lê o template, resolve a herança e aplica.

## Estrutura

```
templates/
├── abnt/                    # Templates por tipo de documento
│   ├── general/             # Base (trabalho acadêmico geral)
│   ├── articles/            # Artigo científico — NBR 6022:2018
│   ├── tcc/                 # Trabalho de conclusão de curso
│   ├── monographs/          # Monografia — NBR 6029:2023
│   ├── dissertations/        # Dissertação — NBR 14724:2024
│   ├── theses/              # Tese — NBR 14724:2024
│   ├── research_projects/   # Projeto de pesquisa — NBR 15287:2025
│   └── reports/             # Relatório — NBR 10719:2025
├── institutions/            # Perfis institucionais
│   ├── ufms/
│   └── ufgd/
└── schemas/
    └── template.schema.json # JSON Schema que valida todo template
```

## Regras

1. **Toda regra declara sua fonte.** `norm`, `edition`, `section`, `url`,
   `consulted_at` e `confidence`. Uma regra sem fonte não entra em produção.
2. **Precedência:** `instituição > template do tipo de documento > norma
   geral ABNT`. Conflitos são **registrados**, nunca resolvidos em silêncio
   (ver [`../docs/decisions/ADR-0007`](../docs/decisions/ADR-0007-template-precedence.md)).
3. **Herança por `extends`.** Um template declara apenas o que muda.
4. **Norma não é reproduzida.** Os arquivos contêm *parâmetros* e
   *referências*, nunca texto de norma.
5. **Ficha catalográfica é campo reservado.** Nunca é preenchida com dados
   fictícios.
6. **Grau de confiabilidade** (`confidence`) reflete a verificação da
   **fonte**, não o conhecimento do produto:
   - `high` — norma oficial lida, ou regra confirmada por mais de uma fonte;
   - `medium` — resumo institucional ou fonte única não oficial;
   - `low` — inferida por analogia, sem fonte direta.
7. Regras com `confidence: low` são aplicadas como **sugestão** e sinalizadas
   no relatório de conformidade.

## Estado atual

Apenas o esqueleto `abnt/general/general.yaml` existe, como referência de
estrutura. **Os templates completos são implementados na Onda 4**, após
revalidação das edições vigentes (ver
[`../docs/standards/ABNT_NORMS_RESEARCH.md`](../docs/standards/ABNT_NORMS_RESEARCH.md)).

## Validação

```bash
# Validar um template contra o schema
python -c "import json, yaml, jsonschema; \
  schema=json.load(open('templates/schemas/template.schema.json')); \
  data=yaml.safe_load(open('templates/abnt/general/general.yaml')); \
  jsonschema.validate(data, schema); print('válido')"
```

> `jsonschema` ainda não está declarado em `pyproject.toml`; será adicionado
> na Onda 4, junto com o carregador de templates.
