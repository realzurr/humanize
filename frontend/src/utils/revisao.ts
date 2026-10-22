/**
 * Estrutura de revisão por trechos para o editor comparativo.
 *
 * Converte o diff de palavras em grupos de alteração (sugestões) que podem
 * ser aceitos ou rejeitados individualmente. A composição final do texto
 * respeita as decisões por grupo, permitindo restaurar o original por trecho.
 */

import { diffPalavras } from './diff';

export interface GrupoAlteracao {
  id: string;
  antes: string;
  depois: string;
}

export type ParteRevisao =
  | { tipo: 'igual'; texto: string }
  | { tipo: 'grupo'; id: string; antes: string; depois: string };

export interface EstruturaRevisao {
  partes: ParteRevisao[];
  grupos: GrupoAlteracao[];
}

/** Agrupa alterações consecutivas do diff em sugestões revisáveis. */
export function estruturarRevisao(antes: string, depois: string): EstruturaRevisao {
  const segmentos = diffPalavras(antes, depois);
  const partes: ParteRevisao[] = [];
  const grupos: GrupoAlteracao[] = [];

  let i = 0;
  let contador = 0;
  while (i < segmentos.length) {
    const atual = segmentos[i];
    if (atual === undefined) {
      break;
    }
    if (!atual.removido && !atual.adicionado) {
      partes.push({ tipo: 'igual', texto: atual.texto });
      i += 1;
      continue;
    }

    const tokensAntes: string[] = [];
    const tokensDepois: string[] = [];
    while (i < segmentos.length) {
      const atualGrupo = segmentos[i];
      if (atualGrupo === undefined || (!atualGrupo.removido && !atualGrupo.adicionado)) {
        break;
      }
      if (atualGrupo.removido) {
        tokensAntes.push(atualGrupo.texto);
      }
      if (atualGrupo.adicionado) {
        tokensDepois.push(atualGrupo.texto);
      }
      i += 1;
    }

    const id = `grupo-${contador}`;
    contador += 1;
    const antesGrupo = tokensAntes.join('');
    const depoisGrupo = tokensDepois.join('');
    grupos.push({ id, antes: antesGrupo, depois: depoisGrupo });
    partes.push({ tipo: 'grupo', id, antes: antesGrupo, depois: depoisGrupo });
  }

  return { partes, grupos };
}

/**
 * Compõe o texto final a partir das partes e das decisões por grupo.
 *
 * Uma decisão ``false`` (rejeitada) restaura o trecho original; ``true``
 * (aceita) mantém o trecho proposto.
 */
export function comporTexto(partes: ParteRevisao[], decisoes: Record<string, boolean>): string {
  return partes
    .map((parte) => {
      if (parte.tipo === 'igual') {
        return parte.texto;
      }
      return decisoes[parte.id] === false ? parte.antes : parte.depois;
    })
    .join('');
}
