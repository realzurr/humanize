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
  category: string;
  count: number;
  severity: 'info' | 'warning' | 'critical';
  before?: string;
  after?: string;
}

export interface EntidadeProtegida {
  id: string;
  kind: string;
  text: string;
  start: number;
  end: number;
  level: string;
  fingerprint: string;
}

export interface RelatorioNormalizacao {
  texto: string;
  transformacoes: TransformacaoRegistrada[];
  total_caracteres_antes: number;
  total_caracteres_depois: number;
  entidades_protegidas: EntidadeProtegida[];
  regras_desativadas: string[];
  avisos: string[];
}

export interface OpcoesNormalizacao {
  nfkc: boolean;
  invisiveis: boolean;
  emojis: boolean;
  markdown: boolean;
  espacos: boolean;
}

export interface RequisicaoNormalizacao {
  texto: string;
  perfil?: string;
  opcoes?: Partial<OpcoesNormalizacao>;
  regras_desativadas?: string[];
}

export interface PerfilNormalizacao {
  id: string;
  description: string;
  opcoes: string[];
}

export interface RespostaSaude {
  status: string;
  app: string;
  version: string;
  environment: string;
}
