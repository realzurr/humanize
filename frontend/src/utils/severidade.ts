/**
 * Mapeamento de severidade para classes visuais.
 *
 * A API usa severidades em inglês: `critical`, `high`, `medium`, `low`,
 * `info` (validação) e `warning` (normalização). A interface as traduz para
 * cores de alto contraste, preservando a legibilidade (WCAG AA).
 */

export function rotuloSeveridade(severidade: string): string {
  const mapa: Record<string, string> = {
    critical: 'Crítica',
    high: 'Alta',
    medium: 'Média',
    warning: 'Atenção',
    low: 'Baixa',
    info: 'Informativa',
  };
  return mapa[severidade.toLowerCase()] ?? severidade;
}

export function classeSeveridade(severidade: string): string {
  const sev = severidade.toLowerCase();
  if (sev === 'critical' || sev === 'high') {
    return 'text-danger';
  }
  if (sev === 'medium' || sev === 'warning') {
    return 'text-warning';
  }
  if (sev === 'low') {
    return 'text-gray-600';
  }
  return 'text-gray-500';
}

export function classeBordaSeveridade(severidade: string): string {
  const sev = severidade.toLowerCase();
  if (sev === 'critical' || sev === 'high') {
    return 'border-danger/30 bg-danger/10';
  }
  if (sev === 'medium' || sev === 'warning') {
    return 'border-warning/30 bg-warning/10';
  }
  return 'border-surface-border bg-surface-muted';
}
