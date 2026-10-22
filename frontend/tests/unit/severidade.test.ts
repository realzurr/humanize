import { describe, expect, it } from 'vitest';

import { classeSeveridade, rotuloSeveridade } from '@/utils/severidade';

describe('severidade', () => {
  it('mapeia severidades críticas para a cor de perigo', () => {
    expect(classeSeveridade('critical')).toBe('text-danger');
    expect(classeSeveridade('high')).toBe('text-danger');
  });

  it('mapeia severidades médias para a cor de atenção', () => {
    expect(classeSeveridade('medium')).toBe('text-warning');
    expect(classeSeveridade('warning')).toBe('text-warning');
  });

  it('traduz os rótulos para português', () => {
    expect(rotuloSeveridade('critical')).toBe('Crítica');
    expect(rotuloSeveridade('high')).toBe('Alta');
    expect(rotuloSeveridade('info')).toBe('Informativa');
  });

  it('é tolerante a valores desconhecidos', () => {
    expect(rotuloSeveridade('desconhecida')).toBe('desconhecida');
    expect(classeSeveridade('desconhecida')).toBe('text-gray-500');
  });
});
