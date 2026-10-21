# ADR-0001 — Reimplementacao *clean-room* do repositório de referência

- **Status**: Aceita
- **Data**: 2026-10-21
- **Impacto**: Alto
- **Decisores**: Responsável pelo projeto

## Contexto

A especificação do projeto indica como referência o repositório
[`takumar-x/AI-Humanizer`](https://github.com/takumar-x/AI-Humanizer), uma
ferramenta web de limpeza de texto sob licença **GPL-3.0**.

Análise técnica e juridica do repositório:

| Item | Constatação |
|---|---|
| Escopo | Arquivo único `index.html` (1080 linhas), HTML + CSS + JS vanilla |
| Licença | GNU GPL v3 (arquivo `LICENSE` íntegro, 674 linhas) |
| Aviso de copyright | **Ausente** — o `LICENSE` é o modelo GPL sem linha de copyright do projeto; `index.html` não tem cabeçalho SPDX |
| Histórico | 9 commits, 1 branch, 3 estrelas, 0 forks, 0 issues |
| Titular do direito | Não identificável a partir dos arquivos (commit único: `takumar-x <mikhail.medvedev@gmail.com>`) |
| Dependências | Nenhuma (executa offline, no navegador) |

A GPL-3.0 é copyleft forte. Copiar, traduzir, adaptar ou incorporar o código
torna o produto uma **obra derivada**, com obrigação de distribuir sob GPL-3.0.
Isso conflita com o uso previsto (implantação institucional/comercial) e com a
possibilidade de licenciamento proprietário.

## Decisão

**Reimplementar os requisitos funcionais do zero (*clean-room*), sem copiar,
traduzir ou adaptar o código do repositório de referência.**

A especificação funcional (remover caracteres invisiveis, normalizar Unicode,
limpar Markdown, remover emojis, exibir antes/depois, exportar) e expressável
de forma independente, a partir de requisitos técnicos e do padrão Unicode.
Não há necessidade de copiar implementação.

## Consequências

### Positivas

- Licença do projeto permanece livre (ver `ADR-0014`).
- Nenhuma dependência de um projeto com baixa atividade e sem identificação
  clara de titular.
- oportunidade de corrigir as **regressiones acadêmicas** graves do original
  (NFKC destruindo superindices, setas quimicas convertidas em `>`, remoção
  de `©`/`®`/`™`, subindices comidos pelo limpador de Markdown) — catálogo
  completo em `../architecture/REFERENCE_REPO_ANALYSIS.md`.
- Execução 100% assincrona e testável, em vez de processamento no navegador.

### Negativas

- A funcionalidade basica precisa ser reescrita (custo de uma onda).
- Não se aproveita o suporte multil-inguete/UI já pronta do original — o
  produto alvo e em pt-BR e tera interface propriá (Onda 7).

### Neutras

- O repositório de referência permanece uma **fonte de requisitos funcionais**
  e de **teste comparativo** (a Onda 1 pode validar o motor novo contra o
  comportamento antigo em textos acadêmicos, exatamente para detectar as
  regressões).

## Alternativas consideradas

| Alternativa | Motivo da rejeição |
|---|---|
| Copiar o `index.html` e estender | Obra derivada => GPL-3.0 obrigatoria. Bloqueia licenciamento proprietário |
| Fork do repositório | Mesmo problema de copyleft; além disso, impoe Heroku/JS para um produto Python |
| Usar como serviço externo (subprocesso) | A GPL não se propaga por separação de processo, mas imporia a manutenção de um runtime JS e um frontend Node desnecessario; ganho de funcionalidade é nulo |
| Fazer link para o site hospedado | Dependência de terceiros, sem controle de dados nem de privacidade; impossível embutir no produto |
| Pedir permissão ao autor | Titular não identificável no repositório; Processo lento e sem garantia de resultado |

## Verificação

- Nenhum arquivo do repositório de referência foi copiado para este repositório.
- As únicas referências a ele são documentais (URL, análise, comparação de
  comportamento).
- A busca por trechos do original no código é feita na Onda 1, com a
  verificação registrada no relatório da onda.
