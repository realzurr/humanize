/**
 * Cliente HTTP da API.
 *
 * Regra de segurança: nenhuma credencial é enviada por este módulo.
 * Chaves de LLM são informadas ao backend por HTTPS e permanecem no
 * backend; o frontend nunca recebe o valor da chave de volta.
 */

import type { RespostaSaude } from '@/types';

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
};
