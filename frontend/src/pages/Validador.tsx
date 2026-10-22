/**
 * Validador acadêmico.
 *
 * Valida citações (NBR 10520:2023) e referências (NBR 6023:2025) e exibe o
 * relatório auditável, com localização, severidade, veredito e ação sugerida
 * para cada achado.
 */

import { useState } from 'react';

import { useDocumento } from '@/context/DocumentoContext';
import { api } from '@/services/api';
import type { RespostaValidacaoAcademica } from '@/types';
import { classeBordaSeveridade, classeSeveridade, rotuloSeveridade } from '@/utils/severidade';

export function Validador() {
  const { textoFinal, textoOriginal } = useDocumento();

  const [texto, setTexto] = useState(textoFinal || textoOriginal);
  const [consultarDoi, setConsultarDoi] = useState(false);
  const [resultado, setResultado] = useState<RespostaValidacaoAcademica | null>(null);
  const [processando, setProcessando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function validar() {
    setErro(null);
    setProcessando(true);
    try {
      const resposta = await api.validarAcademico({ texto, consultar_doi: consultarDoi });
      setResultado(resposta);
    } catch (motivo: unknown) {
      setErro(motivo instanceof Error ? motivo.message : 'Falha ao validar o documento');
    } finally {
      setProcessando(false);
    }
  }

  return (
    <section aria-labelledby="titulo-validador" className="space-y-6">
      <header>
        <h2 id="titulo-validador" className="text-xl font-semibold">
          Validador acadêmico
        </h2>
        <p className="mt-1 max-w-prose text-sm text-gray-600">
          Verifique a integridade de citações e referências. Metadados ausentes são
          reportados, nunca inventados.
        </p>
      </header>

      <div>
        <label htmlFor="texto-validar" className="mb-1 block text-sm font-medium">
          Documento a validar
          <span className="ml-2 font-normal text-gray-500">
            {texto.length.toLocaleString('pt-BR')} caracteres
          </span>
        </label>
        <textarea
          id="texto-validar"
          value={texto}
          onChange={(evento) => setTexto(evento.target.value)}
          className="h-40 w-full rounded border border-surface-border bg-surface p-3 font-mono text-sm"
        />
        {textoFinal && textoFinal !== texto && (
          <button
            type="button"
            onClick={() => setTexto(textoFinal)}
            className="mt-1 text-xs text-brand-700 underline"
          >
            Usar texto final
          </button>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-4">
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={consultarDoi}
            onChange={(evento) => setConsultarDoi(evento.target.checked)}
            className="h-4 w-4 rounded border-surface-border"
          />
          Consultar metadados de DOI (opt-in)
        </label>
        <button
          type="button"
          onClick={validar}
          disabled={processando || texto.trim() === ''}
          className="rounded bg-brand-500 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
        >
          {processando ? 'Validando…' : 'Validar'}
        </button>
      </div>

      {erro && (
        <p role="alert" className="rounded border border-danger/30 bg-danger/10 p-3 text-sm text-danger">
          {erro}
        </p>
      )}

      {resultado && (
        <section aria-labelledby="titulo-relatorio-validacao" className="space-y-3">
          <h3 id="titulo-relatorio-validacao" className="text-sm font-medium">
            Relatório de validação
          </h3>
          <dl className="grid grid-cols-3 gap-2 text-sm">
            <Metrica rotulo="Citações" valor={resultado.citacoes} />
            <Metrica rotulo="Referências" valor={resultado.referencias} />
            <Metrica rotulo="Associadas" valor={resultado.associadas} />
          </dl>

          {resultado.achados.length === 0 ? (
            <p className="text-sm text-gray-600">Nenhum achado — estrutura consistente.</p>
          ) : (
            <ul className="space-y-2">
              {resultado.achados.map((achado, indice) => (
                <li
                  key={indice}
                  className={`rounded border p-3 text-sm ${classeBordaSeveridade(achado.severidade)}`}
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`font-medium ${classeSeveridade(achado.severidade)}`}>
                      {rotuloSeveridade(achado.severidade)}
                    </span>
                    <span className="text-xs text-gray-500">
                      {achado.veredito.replaceAll('_', ' ')}
                      {achado.linha !== null ? ` · linha ${achado.linha}` : ''}
                      {achado.confianca ? ` · confiança ${achado.confianca}` : ''}
                    </span>
                  </div>
                  <p className="mt-1 text-gray-700">{achado.mensagem}</p>
                  {achado.acao_sugerida && (
                    <p className="mt-1 text-xs text-gray-600">{achado.acao_sugerida}</p>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
    </section>
  );
}

function Metrica({ rotulo, valor }: { rotulo: string; valor: number }) {
  return (
    <div className="rounded border border-surface-border bg-surface p-2">
      <dt className="text-xs text-gray-500">{rotulo}</dt>
      <dd className="text-lg font-semibold">{valor}</dd>
    </div>
  );
}
