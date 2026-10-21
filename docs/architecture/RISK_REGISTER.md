# Registro de Riscos

- **Onda de origem**: 0
- **Atualizado**: 2026-10-21
- **Responsável pelo registro**: responsável pelo projeto

Escala: **Probabilidade** (Baixa / Média / Alta / Crítica) × **Impacto**
(Baixo / Médio / Alto / Crítico) → severidade resultante.

---

## 1. Riscos técnicos de conteúdo (normalização)

| ID | Risco | Prob. | Impacto | Sev. | Mitigação | Onda | Status |
|---|---|---|---|---|---|---|---|
| R-01 | NFKC converte `10⁻⁶` → `10-6`, `x²` → `x2`, `CO₂` → `CO2` | Crítica | Crítico | **Crítica** | `norm.unicode.nfkc` desligada por padrão; lista de exceções; teste de regressão obrigatório | 1 | Aberto |
| R-02 | Remoção de emoji apaga `©`, `®`, `™` (todos em `Extended_Pictographic`) | Alta | Alto | **Alta** | Lista de exceção; remoção só de pictogramas decorativos | 1 | Aberto |
| R-03 | Conversão de pseudo-gráficos transforma `→` (reação química) em `>` | Alta | Crítico | **Alta** | Regra não alcança `U+2190–U+21FF`; setas como entidade protegida | 1 | Aberto |
| R-04 | Limpeza de Markdown destrói subíndices (`F _i_`) | Alta | Alto | **Alta** | `norm.markdown` só fora de trecho protegido; detector de subíndice | 1 | Aberto |
| R-05 | U+2212 (sinal de menos) convertido em hífen | Média | Alto | **Alta** | Regra de traços exclui U+2212; sinal como entidade protegida | 1 | Aberto |
| R-06 | Aspas curvas convertidas → citação literal deixa de ser detectável | Média | Médio | **Média** | Preservar aspas curvas; marcar citação literal | 1, 3 | Aberto |
| R-07 | Tabelas em ASCII/Unicode deformadas por fonte proporcional | Média | Médio | **Média** | Tabela como bloco atômico (`TableData`) | 1, 4 | Aberto |
| R-08 | Hífen opcional (U+00AD) removido no meio de palavra | Média | Baixo | **Baixa** | Posição detectada; remoção só quando segura | 1 | Aberto |
| R-09 | Caracteres bidi de controle invertem a ordem visual | Baixa | Alto | **Média** | `norm.invisible.bidi` com alerta `warning`, não remoção silenciosa | 1 | Aberto |
| R-10 | NFKC e limpeza de Markdown interferem entre si (não idempotente) | Média | Médio | **Média** | Ordem fixa documentada; teste de idempotência por regra | 1 | Aberto |

---

## 2. Riscos de integridade científica (humanização)

| ID | Risco | Prob. | Impacto | Sev. | Mitigação | Onda | Status |
|---|---|---|---|---|---|---|---|
| R-11 | LLM altera números, percentuais ou resultados | Crítica | Crítico | **Crítica** | Catálogo de entidades protegidas + máscara + validação semântica + portão de aprovação | 3 | Aberto |
| R-12 | LLM inventa autor, artigo, DOI ou fonte bibliográfica | Média | Crítico | **Alta** | Prompt restritivo + validação de citação/DOI; nenhuma metadado inventado | 3, 5 | Aberto |
| R-13 | LLM altera o sentido de uma afirmação (sem alterar números) | Média | Crítico | **Alta** | Validação semântica com alerta `high`; revisão humana obrigatória na Onda 7 | 3 | Aberto |
| R-14 | Detecção de entidades protegidas é heurística → falso negativo | Média | Alto | **Alta** | Múltiplas heurísticas; relatório lista também o que **não** foi verificável | 3 | Aberto |
| R-15 | Texto importado contém instrução (prompt injection) | Alta | Alto | **Alta** | Texto é conteúdo delimitado, nunca instrução; prompt de sistema explícito | 2, 3 | Aberto |
| R-16 | Intensidade interpretada como "% de alteração garantida" | Média | Médio | **Média** | Documentada como parâmetro de orientação; UI mostra a diferença real | 3, 7 | Aberto |
| R-17 | Perfil autoral usa texto de outro usuário | Baixa | Alto | **Média** | `owner_id` obrigatório; verificação em teste | 3 | Aberto |

---

## 3. Riscos de segurança

| ID | Risco | Prob. | Impacto | Sev. | Mitigação | Onda | Status |
|---|---|---|---|---|---|---|---|
| R-18 | Chave de API vaza em log | Média | Crítico | **Alta** | `redact_secrets` obrigatório; teste automatizado de varredura | 0, 2 | Mitigado (filtro implementado) |
| R-19 | Chave de API devolvida ao frontend | Média | Crítico | **Alta** | API expõe apenas `configured`/`last4` | 2 | Aberto |
| R-20 | Segredo em `localStorage` | Média | Alto | **Alta** | Segredos apenas no backend; teste automatizado | 2, 7 | Aberto |
| R-21 | Upload malicioso (path traversal, MIME falso) | Média | Alto | **Alta** | Limite de tamanho, magic bytes, nome sanitizado | 8 | Aberto |
| R-22 | SSRF em consulta de DOI | Baixa | Alto | **Média** | Allowlist de hosts, opt-in, timeout | 5 | Aberto |
| R-23 | Credencial persistida em texto claro no banco | Média | Crítico | **Alta** | AES-GCM com chave fora do banco | 2, 8 | Aberto |
| R-24 | Acesso a documento de outro usuário | Baixa | Crítico | **Alta** | `owner_id` em toda consulta | 8 | Aberto |
| R-25 | Custo de API descontrolado | Média | Médio | **Média** | Estimativa exibida + limites de requisição e de tokens | 2, 8 | Aberto |

---

## 4. Riscos de conformidade ABNT

| ID | Risco | Prob. | Impacto | Sev. | Mitigação | Onda | Status |
|---|---|---|---|---|---|---|---|
| R-26 | Declarar "em conformidade com a ABNT" de forma genérica | Média | Crítico | **Alta** | Conformidade **por regra**, com fonte e confiança (`ADR-0015`) | 4, 5 | Aberto |
| R-27 | Reproduzir texto de norma protegida por direitos autorais | Baixa | Alto | **Média** | Apenas parâmetros + referência; nenhum texto integral | 4 | Aberto |
| R-28 | Ficha catalográfica gerada com dados fictícios | Média | Crítico | **Alta** | Campo **reservado**; exigida emissão pelo serviço competente | 4 | Aberto |
| R-29 | Manuais institucionais desatualizados (UFMS em 14724:2011 e 6023:2018) | **Crítica** | Alto | **Alta** | Conflito registrado com a norma vigente; recomendação de atualização ao usuário | 4 | **Aberto — materializar já na Onda 4** |
| R-30 | Erro na edição da norma por material institucional antigo | Média | Alto | **Alta** | Fonte com `edition` + `consulted_at` + `confidence`; revalidação na Onda 4 | 4 | Aberto |
| R-31 | Regra institucional codificada como se fosse norma geral | Média | Alto | **Alta** | Perfil institucional separado; precedência explícita (`ADR-0007`) | 4 | Aberto |
| R-32 | Sumário é campo do Word e aparece vazio até ser atualizado | **Crítica** | Baixo | **Média** | Tutorial na UI; opção de pré-renderização; limitação declarada | 6, 7 | Aberto |
| R-33 | PDF diverge do DOCX (renderizador ≠ Word) | **Crítica** | Médio | **Alta** | Comparador automático + `PDF_RENDERER_NOTES.md` | 6 | Aberto |
| R-34 | Normas não citadas com URL/ID oficial verificável | Média | Médio | **Média** | Pendência P-01 do levantamento; confirmar no Catálogo ABNT | 4 | Aberto |

---

## 5. Riscos de engenharia e processo

| ID | Risco | Prob. | Impacto | Sev. | Mitigação | Onda | Status |
|---|---|---|---|---|---|---|---|
| R-35 | Avanço de onda sem autorização | Baixa | Alto | **Média** | Regra dura no `AGENTS.md`; relatórios por onda | 0–8 | Mitigado |
| R-36 | Dívida de testes cresce entre ondas | Média | Alto | **Alta** | Cobertura ≥ 80% como critério de aceite; `filterwarnings = ["error"]` | 1–8 | Aberto |
| R-37 | Acoplamento acidental entre LLM e formatação | Média | Alto | **Alta** | Proibições P1–P7 (`ADR-0002`); teste de arquitetura na Onda 8 | 8 | Aberto |
| R-38 | `PyMuPDF` (AGPL-3.0) em produto de licença proprietária | Alta | Alto | **Alta** | Resolver antes da Onda 6: avaliar `pypdf`/`pdfplumber` | 6 | **Aberto — bloqueia a Onda 6** |
| R-39 | Ausência de renderizador de PDF no ambiente | Alta | Médio | **Alta** | Limitação declarada; fallback DOCX/TXT/Markdown | 6 | Aberto |
| R-40 | Mudança de schema sem migração | Baixa | Alto | **Média** | Alembic obrigatório; `create_all` proibido em produção | 1–8 | Mitigado |
| R-41 | Custo de_tokens/linhas de contexto estoura em documentos longos | Alta | Médio | **Alta** | Chunking por bloco; resumo de trecho; limite de tokens por requisição | 2, 3 | Aberto |
| R-42 | Instalação em servidor externo sem autorização | Baixa | Crítico | **Alta** | Proibido pelo `AGENTS.md`; `docker-compose` só local | 0–8 | Mitigado |

---

## 6. Riscos de produto

| ID | Risco | Prob. | Impacto | Sev. | Mitigação | Onda | Status |
|---|---|---|---|---|---|---|---|
| R-43 | Usuário interpreta o produto como "evasor de detector de IA" | Alta | Alto | **Alta** | Declaração explícita nas telas e na documentação; escopo limitado à qualidade de escrita | 3, 7 | Aberto |
| R-44 | Usuário confia no relatório de conformidade como certificação | Média | Crítico | **Alta** | Relatório declara regra, fonte, confiança e **pendências**; nunca "certificado" | 5, 7 | Aberto |
| R-45 | Custo percebido como alto (múltiplas chamadas de LLM) | Média | Médio | **Média** | Estimativa antes da execução; cache de extração de entidades | 2, 3, 7 | Aberto |

---

## 7. Riscos de licença

| ID | Risco | Prob. | Impacto | Sev. | Mitigação | Onda | Status |
|---|---|---|---|---|---|---|---|
| R-46 | Contágio GPL-3.0 por contato com o repositório de referência | Baixa | Crítico | **Média** | Reimplementação *clean-room* (`ADR-0001`); nenhum arquivo copiado | 0 | Mitigado |
| R-47 | Dependência AGPL no `backend/` | Alta | Alto | **Alta** | `PyMuPDF` → avaliar alternativa permissiva antes da Onda 6 | 6 | **Aberto** |
| R-48 | Licença do projeto indefinida atrasa distribuição | Média | Alto | **Média** | `ADR-0014` marcado como *Proposta*; decisão do responsável | 0 | **Aberto — requer decisão** |
| R-49 | Templates/redistribuição com licença incompatível | Baixa | Médio | **Baixa** | Licença dos templates definida em conjunto com a do código | 4 | Aberto |

---

## 8. Itens de risco já materializados na Onda 0

| Item | Constatação | Tratamento |
|---|---|---|
| TestClient do Starlette passou a exigir `httpx2` | Detectado por `filterwarnings = ["error"]` na primeira execução da suíte | `httpx2` adicionado às dependências de desenvolvimento |
| `normalize_fingerprint` não unificava separador decimal (`45,5%` ≠ `45.5%`) | Detectado por teste próprio do IR | Heurística revisada: milhar (3 dígitos) vs. decimal; documentada a ambiguidade `1.000` |
| `mypy --strict` rejeitou `__iter__` em modelo Pydantic | Conflito com `BaseModel.__iter__` | Renomeado para `iter_entities()` |
| `mypy --strict` rejeitou o processor `structlog` | Incompatibilidade de contravariância de `dict` vs. `MutableMapping` | Assinatura ajustada para `MutableMapping[str, Any]` |

---

## 9. Como usar este registro

- **Antes de cada onda**, revise os itens com `Status: Aberto` que a onda
  pretende tratar e registre o resultado no relatório da onda.
- **Risco materializado** → mover para a seção 8 com a constatação e o
  tratamento.
- **Risco residual** → manter aberto e repetir a avaliação.
- **Novo risco** → acrescentar com ID sequencial, sem renumerar os
  existentes (o ID é referenciado em relatórios e ADRs).
