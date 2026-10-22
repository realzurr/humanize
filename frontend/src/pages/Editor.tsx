/**
 * Editor — editor comparativo lado a lado.
 *
 * Centraliza a revisão: compara o original com a versão proposta
 * (normalizada ou humanizada), permite aceitar/rejeitar sugestões por trecho,
 * restaurar o original e compor o texto final que segue para exportação.
 */

import { useState } from 'react';

import { Link } from 'react-router-dom';

import { RevisorDiff } from '@/components/RevisorDiff';
import { useDocumento } from '@/context/DocumentoContext';

type VersaoProposta = 'normalizado' | 'humanizado';

export function Editor() {
  const {
    textoOriginal,
    textoNormalizado,
    textoHumanizado,
    textoFinal,
    definirOriginal,
    definirTextoFinal,
  } = useDocumento();

  const [proposta, setProposta] = useState<VersaoProposta>('normalizado');

  const textoProposto = proposta === 'normalizado' ? textoNormalizado : textoHumanizado;
  const semProposta = textoProposto === '';

  return (
    <section aria-labelledby="titulo-editor" className="space-y-6">
      <header>
        <h2 id="titulo-editor" className="text-xl font-semibold">
          Editor comparativo
        </h2>
        <p className="mt-1 max-w-prose text-sm text-gray-600">
          Compare o original com a versão proposta e revise cada alteração. Números,
          fórmulas, citações e DOIs são preservados pelo backend.
        </p>
      </header>

      <div>
        <label htmlFor="texto-original" className="mb-1 block text-sm font-medium">
          Texto original
          <span className="ml-2 font-normal text-gray-500">
            {textoOriginal.length.toLocaleString('pt-BR')} caracteres
          </span>
        </label>
        <textarea
          id="texto-original"
          value={textoOriginal}
          onChange={(evento) => definirOriginal(evento.target.value)}
          placeholder="Cole aqui o documento a revisar…"
          className="h-40 w-full rounded border border-surface-border bg-surface p-3 font-mono text-sm"
        />
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <label htmlFor="versao-proposta" className="text-sm font-medium">
          Comparar com:
        </label>
        <select
          id="versao-proposta"
          value={proposta}
          onChange={(evento) => setProposta(evento.target.value as VersaoProposta)}
          className="rounded border border-surface-border bg-surface px-2 py-1 text-sm"
        >
          <option value="normalizado" disabled={textoNormalizado === ''}>
            Texto normalizado
          </option>
          <option value="humanizado" disabled={textoHumanizado === ''}>
            Texto humanizado
          </option>
        </select>

        {semProposta && (
          <span className="text-sm text-gray-600">
            {proposta === 'normalizado' ? (
              <>
                Nada normalizado ainda —{' '}
                <Link to="/normalizacao" className="text-brand-700 underline">
                  execute a normalização
                </Link>
                .
              </>
            ) : (
              <>
                Nada humanizado ainda —{' '}
                <Link to="/humanizacao" className="text-brand-700 underline">
                  execute a humanização
                </Link>
                .
              </>
            )}
          </span>
        )}
      </div>

      {!semProposta ? (
        <RevisorDiff
          antes={textoOriginal}
          depois={textoProposto}
          onTextoFinalChange={definirTextoFinal}
        />
      ) : (
        <p className="rounded border border-surface-border bg-surface p-4 text-sm text-gray-600">
          Cole um texto e execute a normalização ou a humanização para visualizar a
          comparação lado a lado.
        </p>
      )}

      <section aria-labelledby="titulo-texto-final">
        <h3 id="titulo-texto-final" className="mb-1 text-sm font-medium">
          Texto final a exportar
          <span className="ml-2 font-normal text-gray-500">
            {textoFinal.length.toLocaleString('pt-BR')} caracteres
          </span>
        </h3>
        <div className="max-h-48 overflow-auto whitespace-pre-wrap rounded border border-surface-border bg-surface p-3 font-mono text-sm">
          {textoFinal || '—'}
        </div>
        <p className="mt-1 text-xs text-gray-500">
          O texto final é sincronizado com as decisões acima e usado na{' '}
          <Link to="/exportacao" className="text-brand-700 underline">
            exportação
          </Link>
          .
        </p>
      </section>
    </section>
  );
}
