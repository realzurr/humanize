/**
 * Cliente HTTP da API.
 *
 * Regra de segurança: nenhuma credencial é devolvida ao frontend. A chave de
 * LLM é enviada ao backend por HTTPS e permanece no backend; a API expõe
 * apenas indicadores (`configured`, `last4`). Este módulo nunca grava segredos
 * em `localStorage`/`sessionStorage`.
 */

import type {
  CredencialOut,
  HistoricoDocumento,
  Modelo,
  PerfilNormalizacao,
  PreviaDocumento,
  Provedor,
  RegistroExportacao,
  RelatorioNormalizacao,
  RequisicaoExportacao,
  RequisicaoHumanizacao,
  RequisicaoNormalizacao,
  RequisicaoPreVisualizacao,
  RequisicaoValidacaoAcademica,
  ResolveTemplate,
  RespostaExportacao,
  RespostaHumanizacao,
  RespostaSaude,
  RespostaValidacaoAcademica,
  TemplateResumo,
} from '@/types';

const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? '/api/v1';

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly codigo?: string,
    readonly detalhes?: unknown,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function requisicao<T>(caminho: string, init?: RequestInit): Promise<T> {
  const resposta = await fetch(`${BASE_URL}${caminho}`, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    ...init,
  });

  if (!resposta.ok) {
    let corpo: unknown;
    try {
      corpo = await resposta.json();
    } catch {
      corpo = undefined;
    }
    const erro = corpo as { error?: { code?: string; message?: string; details?: unknown } } | undefined;
    throw new ApiError(
      erro?.error?.message ?? `Falha na requisição: ${resposta.status}`,
      resposta.status,
      erro?.error?.code,
      erro?.error?.details,
    );
  }

  return (await resposta.json()) as T;
}

export const api = {
  health: () => requisicao<RespostaSaude>('/health'),

  normalize: (corpo: RequisicaoNormalizacao) =>
    requisicao<RelatorioNormalizacao>('/normalize', {
      method: 'POST',
      body: JSON.stringify(corpo),
    }),

  normalizePerfis: () => requisicao<PerfilNormalizacao[]>('/normalize/perfis'),

  listarProvedores: () => requisicao<Provedor[]>('/providers'),

  listarModelos: (providerId: string) => requisicao<Modelo[]>(`/providers/${providerId}/models`),

  salvarCredencial: (providerId: string, apiKey: string) =>
    requisicao<CredencialOut>(`/providers/${providerId}/credentials`, {
      method: 'POST',
      body: JSON.stringify({ api_key: apiKey }),
    }),

  removerCredencial: (providerId: string) =>
    requisicao<CredencialOut>(`/providers/${providerId}/credentials`, { method: 'DELETE' }),

  humanizar: (corpo: RequisicaoHumanizacao) =>
    requisicao<RespostaHumanizacao>('/humanize', {
      method: 'POST',
      body: JSON.stringify(corpo),
    }),

  listarTemplates: () => requisicao<TemplateResumo[]>('/templates'),

  detalharTemplate: (templateId: string) =>
    requisicao<Record<string, unknown>>(`/templates/${templateId}`),

  resolverTemplate: (templateId: string, instituicao?: string) => {
    const query = instituicao ? `?instituicao=${encodeURIComponent(instituicao)}` : '';
    return requisicao<ResolveTemplate>(`/templates/${templateId}/resolve${query}`);
  },

  validarAcademico: (corpo: RequisicaoValidacaoAcademica) =>
    requisicao<RespostaValidacaoAcademica>('/academic/validate', {
      method: 'POST',
      body: JSON.stringify(corpo),
    }),

  exportar: (corpo: RequisicaoExportacao) =>
    requisicao<RespostaExportacao>('/exports', {
      method: 'POST',
      body: JSON.stringify(corpo),
    }),

  preVisualizar: (corpo: RequisicaoPreVisualizacao) =>
    requisicao<PreviaDocumento>('/exports/preview', {
      method: 'POST',
      body: JSON.stringify(corpo),
    }),

  listarExportacoes: (documentId?: string) => {
    const query = documentId ? `?document_id=${encodeURIComponent(documentId)}` : '';
    return requisicao<RegistroExportacao[]>(`/exports${query}`);
  },

  consultarHistorico: (documentId: string) =>
    requisicao<HistoricoDocumento>(`/exports/documents/${encodeURIComponent(documentId)}/history`),

  detalharExportacao: (exportId: string) => requisicao<RegistroExportacao>(`/exports/${exportId}`),
};

/** Faz o download binário de uma exportação e dispara o salvamento no navegador. */
export async function baixarExportacao(exportId: string, filename: string): Promise<void> {
  const resposta = await fetch(`${BASE_URL}/exports/${encodeURIComponent(exportId)}/download`);
  if (!resposta.ok) {
    throw new ApiError(`Falha no download: ${resposta.status}`, resposta.status);
  }
  const blob = await resposta.blob();
  const url = URL.createObjectURL(blob);
  const ancora = document.createElement('a');
  ancora.href = url;
  ancora.download = filename;
  document.body.appendChild(ancora);
  ancora.click();
  document.body.removeChild(ancora);
  URL.revokeObjectURL(url);
}
