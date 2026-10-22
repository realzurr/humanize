/**
 * Configurações de LLM.
 *
 * Lista os provedores com o estado da credencial (apenas `configured` e
 * `last4` — nunca o segredo), permite registrar/remover a chave e listar os
 * modelos disponíveis. A chave nunca é armazenada no navegador.
 */

import { useEffect, useState } from 'react';

import { api } from '@/services/api';
import type { Modelo, Provedor } from '@/types';

export function Llm() {
  const [provedores, setProvedores] = useState<Provedor[]>([]);
  const [modelos, setModelos] = useState<Record<string, Modelo[]>>({});
  const [chaves, setChaves] = useState<Record<string, string>>({});
  const [mensagens, setMensagens] = useState<Record<string, string>>({});
  const [erro, setErro] = useState<string | null>(null);

  async function carregar() {
    try {
      const lista = await api.listarProvedores();
      setProvedores(lista);
    } catch (motivo: unknown) {
      setErro(motivo instanceof Error ? motivo.message : 'Falha ao carregar provedores');
    }
  }

  useEffect(() => {
    void carregar();
  }, []);

  async function listarModelos(providerId: string) {
    try {
      const lista = await api.listarModelos(providerId);
      setModelos((atuais) => ({ ...atuais, [providerId]: lista }));
    } catch {
      setModelos((atuais) => ({ ...atuais, [providerId]: [] }));
    }
  }

  async function salvarChave(providerId: string) {
    const chave = (chaves[providerId] ?? '').trim();
    if (!chave) {
      return;
    }
    try {
      const estado = await api.salvarCredencial(providerId, chave);
      setMensagens((atuais) => ({
        ...atuais,
        [providerId]: `Credencial ${estado.configurado ? 'registrada' : 'não alterada'} (${estado.last4 || '—'})`,
      }));
      setChaves((atuais) => ({ ...atuais, [providerId]: '' }));
      await carregar();
    } catch (motivo: unknown) {
      setMensagens((atuais) => ({
        ...atuais,
        [providerId]: motivo instanceof Error ? motivo.message : 'Falha ao salvar',
      }));
    }
  }

  async function removerChave(providerId: string) {
    try {
      await api.removerCredencial(providerId);
      setMensagens((atuais) => ({ ...atuais, [providerId]: 'Credencial removida' }));
      await carregar();
    } catch (motivo: unknown) {
      setMensagens((atuais) => ({
        ...atuais,
        [providerId]: motivo instanceof Error ? motivo.message : 'Falha ao remover',
      }));
    }
  }

  return (
    <section aria-labelledby="titulo-llm" className="space-y-6">
      <header>
        <h2 id="titulo-llm" className="text-xl font-semibold">
          Configurações de LLM
        </h2>
        <p className="mt-1 max-w-prose text-sm text-gray-600">
          Registre sua própria chave de API. A chave é enviada ao backend por HTTPS e
          permanece no backend — o navegador nunca a armazena nem a recebe de volta.
        </p>
      </header>

      {erro && (
        <p role="alert" className="rounded border border-danger/30 bg-danger/10 p-3 text-sm text-danger">
          {erro}
        </p>
      )}

      <ul className="space-y-3">
        {provedores.map((provedor) => (
          <li key={provedor.id} className="rounded border border-surface-border bg-surface p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <span className="font-medium">{provedor.nome}</span>
                <span className="ml-2 text-xs text-gray-500">{provedor.id}</span>
              </div>
              <span
                className={`rounded-full px-2 py-0.5 text-xs ${
                  provedor.configurado
                    ? 'bg-success/10 text-success'
                    : 'bg-surface-muted text-gray-600'
                }`}
              >
                {provedor.configurado
                  ? `configurado (•••• ${provedor.last4 || '—'})`
                  : provedor.requer_chave
                    ? 'sem chave'
                    : 'não requer chave'}
              </span>
            </div>

            {provedor.requer_chave && (
              <div className="mt-2 flex flex-wrap gap-2">
                <input
                  type="password"
                  aria-label={`Chave da API para ${provedor.nome}`}
                  value={chaves[provedor.id] ?? ''}
                  onChange={(evento) =>
                    setChaves((atuais) => ({ ...atuais, [provedor.id]: evento.target.value }))
                  }
                  placeholder="Cole a chave da API"
                  autoComplete="off"
                  className="rounded border border-surface-border bg-surface px-2 py-1 text-sm"
                />
                <button
                  type="button"
                  onClick={() => void salvarChave(provedor.id)}
                  className="rounded border border-surface-border px-2 py-1 text-xs hover:bg-surface-muted"
                >
                  Salvar
                </button>
                {provedor.configurado && (
                  <button
                    type="button"
                    onClick={() => void removerChave(provedor.id)}
                    className="rounded border border-danger/30 px-2 py-1 text-xs text-danger hover:bg-danger/10"
                  >
                    Remover
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => void listarModelos(provedor.id)}
                  className="rounded border border-surface-border px-2 py-1 text-xs hover:bg-surface-muted"
                >
                  Modelos
                </button>
              </div>
            )}

            {mensagens[provedor.id] && (
              <p className="mt-1 text-xs text-gray-600">{mensagens[provedor.id]}</p>
            )}

            {modelos[provedor.id] && (
              <ul className="mt-2 flex flex-wrap gap-1">
                {modelos[provedor.id]!.map((modelo) => (
                  <li
                    key={modelo.id}
                    title={
                      modelo.janela_contexto
                        ? `contexto ${modelo.janela_contexto.toLocaleString('pt-BR')} tokens`
                        : undefined
                    }
                    className="rounded bg-surface-muted px-2 py-0.5 text-xs text-gray-700"
                  >
                    {modelo.nome || modelo.id}
                    {modelo.obsoleto ? ' (obsoleto)' : ''}
                  </li>
                ))}
              </ul>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
