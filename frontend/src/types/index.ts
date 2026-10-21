/**
 * Tipos compartilhados com a API.
 *
 * Espelham os schemas Pydantic do backend (`backend/app/schemas/`).
 * O IR completo não é exposto ao frontend; a API devolve apenas o que a
 * interface precisa.
 */

export type EtapaPipeline =
  | 'import'
  | 'normalize'
  | 'structure'
  | 'protect'
  | 'humanize'
  | 'semantic_validate'
  | 'review'
  | 'template'
  | 'format'
  | 'academic_validate'
  | 'export';

export interface TransformacaoRegistrada {
  stage: EtapaPipeline;
  rule_id: string;
  description: string;
  count: number;
  severity: 'info' | 'warning' | 'critical';
  before?: string;
  after?: string;
}

export interface RelatorioNormalizacao {
  texto: string;
  transformacoes: TransformacaoRegistrada[];
  total_caracteres_antes: number;
  total_caracteres_depois: number;
}

export interface RespostaSaude {
  status: string;
  app: string;
  version: string;
  environment: string;
}
