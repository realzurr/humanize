/**
 * Diff por palavras para destacar alterações da normalização.
 *
 * Usa a maior subsequência comum (LCS) entre as duas sequências de palavras.
 * Para textos muito grandes, cai em uma comparação ingênua de "tudo mudou",
 * evitando a explosão quadrática de memória.
 */

export interface DiffTrecho {
  texto: string;
  removido: boolean;
  adicionado: boolean;
}

const LIMITE_CELULAS = 25_000_000;

function tokenizar(texto: string): string[] {
  return texto.split(/(\s+)/).filter((token) => token.length > 0);
}

export function diffPalavras(antes: string, depois: string): DiffTrecho[] {
  const a = tokenizar(antes);
  const b = tokenizar(depois);

  if (a.length === 0 && b.length === 0) {
    return [];
  }

  if (a.length * b.length > LIMITE_CELULAS) {
    return [
      { texto: antes, removido: true, adicionado: false },
      { texto: depois, removido: false, adicionado: true },
    ];
  }

  const dp: number[][] = Array.from({ length: a.length + 1 }, () =>
    new Array<number>(b.length + 1).fill(0),
  );

  for (let i = a.length - 1; i >= 0; i -= 1) {
    for (let j = b.length - 1; j >= 0; j -= 1) {
      dp[i]![j] =
        a[i] === b[j]
          ? dp[i + 1]![j + 1]! + 1
          : Math.max(dp[i + 1]![j]!, dp[i]![j + 1]!);
    }
  }

  const segmentos: DiffTrecho[] = [];
  let i = 0;
  let j = 0;

  while (i < a.length && j < b.length) {
    if (a[i] === b[j]) {
      segmentos.push({ texto: a[i]!, removido: false, adicionado: false });
      i += 1;
      j += 1;
    } else if (dp[i + 1]![j]! >= dp[i]![j + 1]!) {
      segmentos.push({ texto: a[i]!, removido: true, adicionado: false });
      i += 1;
    } else {
      segmentos.push({ texto: b[j]!, removido: false, adicionado: true });
      j += 1;
    }
  }

  while (i < a.length) {
    segmentos.push({ texto: a[i]!, removido: true, adicionado: false });
    i += 1;
  }
  while (j < b.length) {
    segmentos.push({ texto: b[j]!, removido: false, adicionado: true });
    j += 1;
  }

  return segmentos;
}
