import { describe, expect, it } from 'vitest';

import { diffPalavras } from '@/utils/diff';

describe('diffPalavras', () => {
  it('não marca alterações quando os textos são idênticos', () => {
    const segmentos = diffPalavras('olá mundo', 'olá mundo');
    expect(segmentos.every((s) => !s.removido && !s.adicionado)).toBe(true);
  });

  it('marca a remoção e a adição de uma palavra', () => {
    const segmentos = diffPalavras('olá mundo', 'oi mundo');
    expect(segmentos.some((s) => s.removido && s.texto === 'olá')).toBe(true);
    expect(segmentos.some((s) => s.adicionado && s.texto === 'oi')).toBe(true);
  });

  it('retorna lista vazia para textos vazios', () => {
    expect(diffPalavras('', '')).toEqual([]);
  });

  it('preserva o texto ao concatenar os segmentos', () => {
    const segmentos = diffPalavras('a b c', 'a x c');
    const remontado = segmentos.map((s) => s.texto).join('');
    expect(remontado).toContain('a');
    expect(remontado).toContain('x');
  });
});
