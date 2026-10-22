/**
 * Histórico de exportações.
 *
 * Lista as versões exportadas com metadados (formato, tamanho, hash) e
 * permite baixar cada arquivo. A persistência relacional multiusuário
 * pertence à Onda 8; aqui o histórico em memória/arquivo é exposto.
 */

import { useEffect, useState } from 'react';

import { Link } from 'react-router-dom';

import { baixarExportacao, api } from '@/services/api';
import type { RegistroExportacao } from '@/types';

export function Historico() {
  const [registros, setRegistros] = useState<RegistroExportacao[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    api
      .listarExportacoes()
      .then(setRegistros)
      .catch((motivo: unknown) => setErro(motivo instanceof Error ? motivo.message : 'Falha ao carregar histórico'))
      .finally(() => setCarregando(false));
  }, []);

  return (
    <section aria-labelledby="titulo-historico" className="space-y-6">
      <header>
        <h2 id="titulo-historico" className="text-xl font-semibold">
          Histórico de exportações
        </h2>
        <p className="mt-1 max-w-prose text-sm text-gray-600">
          Versões exportadas do documento com hash SHA-256 para rastreabilidade.
        </p>
      </header>

      {erro && (
        <p role="alert" className="rounded border border-danger/30 bg-danger/10 p-3 text-sm text-danger">
          {erro}
        </p>
      )}

      {carregando ? (
        <p className="text-sm text-gray-500">Carregando…</p>
      ) : registros.length === 0 ? (
        <p className="rounded border border-surface-border bg-surface p-4 text-sm text-gray-600">
          Nenhuma exportação registrada ainda. Gere um documento na página de{' '}
          <Link to="/exportacao" className="text-brand-700 underline">
            exportação
          </Link>
          .
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <caption className="sr-only">Lista de exportações</caption>
            <thead>
              <tr className="border-b border-surface-border text-left">
                <th className="px-2 py-2 font-medium">Formato</th>
                <th className="px-2 py-2 font-medium">Arquivo</th>
                <th className="px-2 py-2 font-medium">Tamanho</th>
                <th className="px-2 py-2 font-medium">Versão</th>
                <th className="px-2 py-2 font-medium">Data</th>
                <th className="px-2 py-2 font-medium">Ações</th>
              </tr>
            </thead>
            <tbody>
              {registros.map((registro) => (
                <tr key={registro.id} className="border-b border-surface-border">
                  <td className="px-2 py-2 uppercase">{registro.format}</td>
                  <td className="px-2 py-2 font-mono text-xs">{registro.filename}</td>
                  <td className="px-2 py-2">{(registro.size_bytes / 1024).toFixed(1)} KB</td>
                  <td className="px-2 py-2">v{registro.version_number}</td>
                  <td className="px-2 py-2 text-xs text-gray-600">
                    {new Date(registro.created_at).toLocaleString('pt-BR')}
                  </td>
                  <td className="px-2 py-2">
                    <button
                      type="button"
                      onClick={() => void baixarExportacao(registro.id, registro.filename)}
                      className="rounded border border-surface-border px-2 py-1 text-xs hover:bg-surface-muted"
                    >
                      Baixar
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
