/**
 * Comparação de versões.
 *
 * Compara duas versões do documento (original, normalizada, humanizada ou
 * final) lado a lado, com destaque das alterações por palavra.
 */

import { useState } from 'react';

import { useDocumento } from '@/context/DocumentoContext';
import { diffPalavras } from '@/utils/diff';

interface Versao {
  id: string;
  rotulo: string;
}

export function Comparacao() {
  const { textoOriginal, textoNormalizado, textoHumanizado, textoFinal } = useDocumento();

  const versoes: Versao[] = [
    { id: 'original', rotulo: 'Original' },
    { id: 'normalizado', rotulo: 'Normalizado' },
    { id: 'humanizado', rotulo: 'Humanizado' },
    { id: 'final', rotulo: 'Final (revisado)' },
  ];

  const [ladoA, setLadoA] = useState('original');
  const [ladoB, setLadoB] = useState('humanizado');

  const textoDe = (id: string): string => {
    if (id === 'normalizado') return textoNormalizado;
    if (id === 'humanizado') return textoHumanizado;
    if (id === 'final') return textoFinal;
    return textoOriginal;
  };

  const antes = textoDe(ladoA);
  const depois = textoDe(ladoB);
  const segmentos = diffPalavras(antes, depois);

  return (
    <section aria-labelledby="titulo-comparacao" className="space-y-6">
      <header>
        <h2 id="titulo-comparacao" className="text-xl font-semibold">
          Comparação de versões
        </h2>
        <p className="mt-1 max-w-prose text-sm text-gray-600">
          Confronte duas versões do documento para verificar as alterações antes de exportar.
        </p>
      </header>

      <div className="flex flex-wrap items-end gap-3">
        <div>
          <label htmlFor="lado-a" className="mb-1 block text-sm font-medium">
            Versão A (base)
          </label>
          <select
            id="lado-a"
            value={ladoA}
            onChange={(evento) => setLadoA(evento.target.value)}
            className="rounded border border-surface-border bg-surface px-2 py-1 text-sm"
          >
            {versoes.map((versao) => (
              <option key={versao.id} value={versao.id} disabled={textoDe(versao.id) === ''}>
                {versao.rotulo}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="lado-b" className="mb-1 block text-sm font-medium">
            Versão B (comparada)
          </label>
          <select
            id="lado-b"
            value={ladoB}
            onChange={(evento) => setLadoB(evento.target.value)}
            className="rounded border border-surface-border bg-surface px-2 py-1 text-sm"
          >
            {versoes.map((versao) => (
              <option key={versao.id} value={versao.id} disabled={textoDe(versao.id) === ''}>
                {versao.rotulo}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div>
          <span className="mb-1 block text-sm font-medium">
            {versoes.find((v) => v.id === ladoA)?.rotulo}
          </span>
          <div className="max-h-[30rem] overflow-auto whitespace-pre-wrap rounded border border-surface-border bg-surface p-3 font-mono text-sm">
            {segmentos.map((segmento, indice) =>
              segmento.removido ? (
                <mark key={indice} className="bg-danger/10 text-danger line-through">
                  {segmento.texto}
                </mark>
              ) : (
                <span key={indice}>{segmento.texto}</span>
              ),
            )}
          </div>
        </div>
        <div>
          <span className="mb-1 block text-sm font-medium">
            {versoes.find((v) => v.id === ladoB)?.rotulo}
          </span>
          <div className="max-h-[30rem] overflow-auto whitespace-pre-wrap rounded border border-surface-border bg-surface p-3 font-mono text-sm">
            {segmentos.map((segmento, indice) =>
              segmento.adicionado ? (
                <mark key={indice} className="bg-brand-50 text-brand-900">
                  {segmento.texto}
                </mark>
              ) : (
                <span key={indice}>{segmento.texto}</span>
              ),
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
