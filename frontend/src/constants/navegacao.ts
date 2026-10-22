/**
 * Rotas da aplicação e etapas do pipeline, compartilhadas entre a navegação
 * e o dashboard.
 */

export interface Rota {
  caminho: string;
  rotulo: string;
  descricao: string;
}

export const ROTAS: Rota[] = [
  { caminho: '/', rotulo: 'Dashboard', descricao: 'Visão geral do pipeline' },
  { caminho: '/editor', rotulo: 'Editor', descricao: 'Editor comparativo lado a lado' },
  { caminho: '/normalizacao', rotulo: 'Normalização', descricao: 'Limpeza determinística sem LLM' },
  { caminho: '/humanizacao', rotulo: 'Humanização', descricao: 'Reescrita semântica com proteção' },
  { caminho: '/comparacao', rotulo: 'Comparação', descricao: 'Compare versões do documento' },
  { caminho: '/templates', rotulo: 'Templates ABNT', descricao: 'Estrutura e normas acadêmicas' },
  { caminho: '/validador', rotulo: 'Validador', descricao: 'Citações e referências (NBR 10520/6023)' },
  { caminho: '/historico', rotulo: 'Histórico', descricao: 'Versões exportadas' },
  { caminho: '/perfis', rotulo: 'Perfis autorais', descricao: 'Estilos de escrita' },
  { caminho: '/llm', rotulo: 'Configurações de LLM', descricao: 'Provedores e modelos' },
  { caminho: '/exportacao', rotulo: 'Exportação', descricao: 'DOCX, PDF, TXT e Markdown' },
];
