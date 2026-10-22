/**
 * Tipos compartilhados com a API.
 *
 * Espelham os schemas Pydantic do backend (`backend/app/schemas/`). O IR
 * completo não é exposto ao frontend; a API devolve apenas o que a interface
 * precisa. Nomes de campos em `snake_case` para casar 1:1 com o JSON da API.
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

// ---------------------------------------------------------------------------
// Provedores de LLM (Onda 2)
// ---------------------------------------------------------------------------

export interface Provedor {
  id: string;
  nome: string;
  requer_chave: boolean;
  configurado: boolean;
  last4: string;
  fonte: string;
}

export interface Modelo {
  id: string;
  nome: string;
  janela_contexto: number | null;
  max_tokens_saida: number | null;
  suporta_streaming: boolean;
  suporta_json: boolean;
  custo_entrada_1k: number | null;
  custo_saida_1k: number | null;
  obsoleto: boolean;
}

export interface CredencialOut {
  provedor: string;
  configurado: boolean;
  last4: string;
  fonte: string;
}

// ---------------------------------------------------------------------------
// Humanização semântica (Onda 3)
// ---------------------------------------------------------------------------

export interface RequisicaoHumanizacao {
  texto: string;
  perfil?: string;
  intensidade?: number;
  provedor?: string;
  modelo?: string;
  owner_id?: string;
  textos_autorais?: string[];
}

export interface AchadoSemantico {
  severidade: string;
  categoria: string;
  entidade_id: string;
  tipo: string;
  nivel: string;
  antes: string;
  depois: string;
  mensagem: string;
  acao_sugerida: string;
}

export interface ValidacaoSemantica {
  achados: AchadoSemantico[];
  entidades_antes: number;
  entidades_depois: number;
  perdas: number;
  alteracoes: number;
  invencoes: number;
  bloqueado: boolean;
}

export interface Uso {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  custo_estimado_usd: number;
}

export interface RelatorioAnalise {
  repeticoes: string[];
  frases_padronizadas: string[];
  transicoes_artificiais: string[];
  coesao: string;
  vaguidade: string[];
  redundancia: string[];
  voz_passiva: string[];
  excesso_conectivos: string[];
}

export interface TracoEstilo {
  formalidade: number;
  vocabulario: string;
  comprimento_medio_frase: number;
  construcao_argumentativa: string;
  conectivos_recorrentes: string[];
  terminologia: string[];
  organizacao_paragrafos: string;
  ritmo: string;
}

export interface RespostaHumanizacao {
  texto: string;
  perfil: string;
  intensidade: number;
  modelo: string;
  provedor: string;
  bloqueado: boolean;
  analise: RelatorioAnalise;
  estilo: TracoEstilo;
  validacao: ValidacaoSemantica;
  uso: Uso | null;
}

// ---------------------------------------------------------------------------
// Templates ABNT (Onda 4)
// ---------------------------------------------------------------------------

export interface TemplateResumo {
  id: string;
  kind: string;
  title: string;
  version: string;
  extends: string | null;
  institution: string | null;
  fontes: number;
}

export interface Conflito {
  path: string;
  message: string;
}

export interface ResolveTemplate {
  template: Record<string, unknown>;
  conflicts: Conflito[];
  overrides: string[];
}

// ---------------------------------------------------------------------------
// Validação acadêmica (Onda 5)
// ---------------------------------------------------------------------------

export interface RequisicaoValidacaoAcademica {
  texto: string;
  consultar_doi?: boolean;
}

export interface AchadoAcademico {
  severidade: string;
  categoria: string;
  veredito: string;
  linha: number | null;
  inicio: number | null;
  fim: number | null;
  mensagem: string;
  acao_sugerida: string;
  confianca: string;
}

export interface RespostaValidacaoAcademica {
  achados: AchadoAcademico[];
  citacoes: number;
  referencias: number;
  associadas: number;
}

// ---------------------------------------------------------------------------
// Exportação (Onda 6)
// ---------------------------------------------------------------------------

export type FormatoExportacao = 'docx' | 'pdf' | 'txt' | 'md';

export type NaturezaDocumento =
  | 'tese'
  | 'dissertacao'
  | 'tcc'
  | 'monografia'
  | 'projeto_pesquisa'
  | 'relatorio'
  | 'artigo'
  | 'trabalho_academico'
  | 'livro';

export interface MetadadosDocumento {
  institution?: string;
  academic_unit?: string;
  program?: string;
  author?: string;
  title?: string;
  subtitle?: string;
  nature?: NaturezaDocumento | null;
  academic_objective?: string;
  advisor?: string;
  co_advisor?: string;
  area_of_concentration?: string;
  city?: string;
  year?: string;
  keywords_pt?: string[];
  keywords_en?: string[];
  language?: string;
  extra?: Record<string, unknown>;
}

export interface RequisicaoExportacao {
  document_id?: string;
  texto: string;
  template_id?: string;
  instituicao?: string;
  metadados?: MetadadosDocumento;
  formatos?: FormatoExportacao[];
  incluir_pre_textual?: boolean;
}

export interface RequisicaoPreVisualizacao {
  document_id?: string;
  texto: string;
  template_id?: string;
  instituicao?: string;
  metadados?: MetadadosDocumento;
}

export interface ItemSumario {
  number: string;
  title: string;
  level: number;
}

export interface BlocoPrevia {
  id: string;
  kind: string;
  style: string;
  text: string;
  level: number;
}

export interface PreviaDocumento {
  document_id: string;
  title: string;
  template_id: string;
  font: string;
  font_size_pt: number;
  line_spacing: number;
  margins_anverso_cm: Record<string, number>;
  margins_verso_cm: Record<string, number>;
  toc_entries: ItemSumario[];
  blocks: BlocoPrevia[];
  revision_count: number;
  current_revision_id: string | null;
}

export interface RegistroExportacao {
  id: string;
  document_id: string;
  revision_id: string | null;
  version_number: number;
  format: FormatoExportacao;
  filename: string;
  sha256: string;
  size_bytes: number;
  template_id: string;
  institution_id: string | null;
  created_at: string;
  warnings: string[];
  limitations: string[];
  docx_inspection: Record<string, unknown> | null;
  pdf_comparison: Record<string, unknown> | null;
}

export interface RespostaExportacao {
  document_id: string;
  revision_id: string;
  template_id: string;
  instituicao: string | null;
  pdf_available: boolean;
  exports: RegistroExportacao[];
  preview: PreviaDocumento;
  warnings: string[];
  limitations: string[];
}

export interface RevisaoHistorico {
  id: string;
  stage: string;
  created_at: string;
  parent_id: string | null;
  transformations: number;
}

export interface HistoricoDocumento {
  document_id: string;
  original_immutable: boolean;
  revisions: RevisaoHistorico[];
  exports: Record<string, unknown>[];
}
