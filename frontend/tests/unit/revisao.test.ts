import { describe, expect, it } from 'vitest';

import { comporTexto, estruturarRevisao } from '@/utils/revisao';

describe('estruturarRevisao', () => {
  it('agrupa uma alteração consecutiva', () => {
    const { grupos } = estruturarRevisao('olá mundo', 'oi mundo');
    expect(grupos).toHaveLength(1);
    expect(grupos[0]!.antes).toBe('olá');
    expect(grupos[0]!.depois).toBe('oi');
  });

  it('não produz grupos quando não há alteração', () => {
    const { grupos } = estruturarRevisao('igual', 'igual');
    expect(grupos).toHaveLength(0);
  });
});

describe('comporTexto', () => {
  it('aceita a sugestão quando a decisão é verdadeira', () => {
    const { partes, grupos } = estruturarRevisao('olá mundo', 'oi mundo');
    const decisoes = Object.fromEntries(grupos.map((g) => [g.id, true]));
    expect(comporTexto(partes, decisoes)).toBe('oi mundo');
  });

  it('restaura o original quando a decisão é falsa', () => {
    const { partes, grupos } = estruturarRevisao('olá mundo', 'oi mundo');
    const decisoes = Object.fromEntries(grupos.map((g) => [g.id, false]));
    expect(comporTexto(partes, decisoes)).toBe('olá mundo');
  });
});
