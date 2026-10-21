/**
 * Tela de normalização textual (Onda 1).
 *
 * Editor de entrada, opções por grupo de regras, painel de saída lado a
 * lado com destaque das alterações e estatísticas por regra. O
 * processamento é ao vivo, com debounce de 420 ms (mesmo comportamento do
 * repositório de referência, herdado como requisito de UX).
 */
import { useEffect, useState } from 'react';

import { api } from '@/services/api';
import type {
  OpcoesNormalizacao,
  RelatorioNormalizacao,
} from '@/types';
import { diffPalavras } from '@/utils/diff';

const OPCOES_INICIAIS: OpcoesNormalizacao = {
  nfkc: false,
  invisiveis: true,
  emojis: true,
  markdown: true,
  espacos: true,
};

const ROTULOS: Record<keyof OpcoesNormalizacao, string> = {
  nfkc: 'NFKC (normalização Unicode agressiva)',
  invisiveis: 'Remover caracteres invisíveis',
  emojis: 'Remover emojis',
  markdown: 'Limpar marcação Markdown',
  espacos: 'Limpar espaços em branco',
};

const DEBOUNCE_MS = 420;

export function Normalizacao() {
  const [texto, setTexto] = useState('');
  const [opcoes, setOpcoes] = useState<OpcoesNormalizacao>(OPCOES_INICIAIS);
  const [resultado, setResultado] = useState<RelatorioNormalizacao | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [processando, setProcessando] = useState(false);
  const [copiado, setCopiado] = useState(false);

  useEffect(() => {
    if (texto.trim() === '') {
      setResultado(null);
      setErro(null);
      return undefined;
    }

    setProcessando(true);
    const temporizador = window.setTimeout(() => {
      api
        .normalize({ texto, opcoes })
        .then((relatorio) => {
          setResultado(relatorio);
          setErro(null);
        })
        .catch((motivo: unknown) => {
          setErro(motivo instanceof Error ? motivo.message : 'Falha ao normalizar o texto');
        })
        .finally(() => setProcessando(false));
    }, DEBOUNCE_MS);

    return () => window.clearTimeout(temporizador);
  }, [texto, opcoes]);

  function alternarOpcao(chave: keyof OpcoesNormalizacao) {
    setOpcoes((atuais) => ({ ...atuais, [chave]: !atuais[chave] }));
  }

  async function copiar() {
    if (!resultado) {
      return;
    }
    try {
      await navigator.clipboard.writeText(resultado.texto);
    } catch {
      const area = document.createElement('textarea');
      area.value = resultado.texto;
      document.body.appendChild(area);
      area.select();
      document.execCommand('copy');
      document.body.removeChild(area);
    }
    setCopiado(true);
    window.setTimeout(() => setCopiado(false), 1500);
  }

  function exportar(formato: 'txt' | 'md') {
    if (!resultado) {
      return;
    }
    const blob = new Blob([resultado.texto], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const ancora = document.createElement('a');
    ancora.href = url;
    ancora.download = `texto-normalizado.${formato}`;
    document.body.appendChild(ancora);
    ancora.click();
    document.body.removeChild(ancora);
    URL.revokeObjectURL(url);
  }

  const trechos = resultado ? diffPalavras(texto, resultado.texto) : [];

  return (
    <section aria-labelledby="titulo-normalizacao" className="space-y-6">
      <header>
        <h2 id="titulo-normalizacao" className="text-xl font-semibold">
          Normalização textual
        </h2>
        <p className="mt-1 text-sm text-gray-600">
          Limpeza determinística do texto — sem LLM e sem alterar números, fórmulas,
          citações, DOIs, tabelas ou código.
        </p>
      </header>

      <fieldset className="rounded border border-surface-border bg-surface p-4">
        <legend className="px-1 text-sm font-medium">Opções</legend>
        <div className="flex flex-wrap gap-x-6 gap-y-2">
          {(Object.keys(ROTULOS) as Array<keyof OpcoesNormalizacao>).map((chave) => (
            <label key={chave} className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={opcoes[chave]}
                onChange={() => alternarOpcao(chave)}
                className="h-4 w-4 rounded border-surface-border"
              />
              {ROTULOS[chave]}
            </label>
          ))}
        </div>
      </fieldset>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div>
          <label
            htmlFor="entrada"
            className="mb-1 block text-sm font-medium"
          >
            Texto original
            <span className="ml-2 font-normal text-gray-500">
              {texto.length.toLocaleString('pt-BR')} caracteres
            </span>
          </label>
          <textarea
            id="entrada"
            value={texto}
            onChange={(evento) => setTexto(evento.target.value)}
            placeholder="Cole aqui o texto a normalizar…"
            className="h-80 w-full rounded border border-surface-border bg-surface p-3 font-mono text-sm"
          />
        </div>

        <div>
          <div className="mb-1 flex items-center justify-between">
            <span className="text-sm font-medium">
              Texto normalizado
              {resultado && (
                <span className="ml-2 font-normal text-gray-500">
                  {resultado.total_caracteres_depois.toLocaleString('pt-BR')} caracteres
                </span>
              )}
            </span>
            {resultado && (
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={copiar}
                  className="rounded border border-surface-border px-2 py-1 text-xs hover:bg-surface-muted"
                >
                  {copiado ? 'Copiado' : 'Copiar'}
                </button>
                <button
                  type="button"
                  onClick={() => exportar('txt')}
                  className="rounded border border-surface-border px-2 py-1 text-xs hover:bg-surface-muted"
                >
                  TXT
                </button>
                <button
                  type="button"
                  onClick={() => exportar('md')}
                  className="rounded border border-surface-border px-2 py-1 text-xs hover:bg-surface-muted"
                >
                  Markdown
                </button>
              </div>
            )}
          </div>

          <div
            aria-live="polite"
            className="h-80 overflow-auto whitespace-pre-wrap rounded border border-surface-border bg-surface p-3 font-mono text-sm"
          >
            {processando && !resultado ? (
              <span className="text-gray-400">Processando…</span>
            ) : (
              trechos.map((trecho, indice) =>
                trecho.removido || trecho.adicionado ? (
                  <mark
                    key={indice}
                    className={
                      trecho.adicionado ? 'bg-brand-50 text-brand-900' : 'bg-danger/10 text-danger line-through'
                    }
                  >
                    {trecho.texto}
                  </mark>
                ) : (
                  <span key={indice}>{trecho.texto}</span>
                ),
              )
            )}
          </div>
        </div>
      </div>

      {erro && (
        <p role="alert" className="rounded border border-danger/30 bg-danger/10 p-3 text-sm text-danger">
          {erro}
        </p>
      )}

      {resultado && resultado.avisos.length > 0 && (
        <aside aria-label="Avisos" className="rounded border border-warning/30 bg-warning/10 p-3 text-sm">
          <h3 className="font-medium text-warning">Avisos</h3>
          <ul className="mt-1 list-inside list-disc space-y-1">
            {resultado.avisos.map((aviso) => (
              <li key={aviso}>{aviso}</li>
            ))}
          </ul>
        </aside>
      )}

      {resultado && resultado.transformacoes.length > 0 && (
        <section aria-labelledby="titulo-estatisticas">
          <h3 id="titulo-estatisticas" className="mb-2 text-sm font-medium">
            Estatísticas por regra
          </h3>
          <ul className="divide-y divide-surface-border rounded border border-surface-border">
            {resultado.transformacoes.map((transformacao) => (
              <li
                key={transformacao.rule_id}
                className="flex items-center justify-between px-3 py-2 text-sm"
              >
                <span>
                  <code className="mr-2 rounded bg-surface-muted px-1 text-xs">
                    {transformacao.rule_id}
                  </code>
                  {transformacao.description}
                </span>
                <span className="ml-4 shrink-0 text-gray-600">
                  {transformacao.count} ×{' '}
                  <span className={severidadeCor(transformacao.severity)}>
                    {transformacao.severity}
                  </span>
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {resultado && resultado.entidades_protegidas.length > 0 && (
        <section aria-labelledby="titulo-protegidas">
          <h3 id="titulo-protegidas" className="mb-2 text-sm font-medium">
            Entidades protegidas ({resultado.entidades_protegidas.length})
          </h3>
          <div className="flex flex-wrap gap-2">
            {resultado.entidades_protegidas.map((entidade) => (
              <span
                key={entidade.id}
                title={`${entidade.kind} · nível ${entidade.level}`}
                className="rounded-full border border-surface-border bg-surface px-2 py-0.5 text-xs"
              >
                {entidade.text}
              </span>
            ))}
          </div>
        </section>
      )}
    </section>
  );
}

function severidadeCor(severidade: 'info' | 'warning' | 'critical'): string {
  if (severidade === 'critical') {
    return 'text-danger font-medium';
  }
  if (severidade === 'warning') {
    return 'text-warning';
  }
  return 'text-gray-500';
}
