/**
 * Dashboard — visão geral do pipeline e atalhos para cada etapa.
 *
 * A Onda 7 entrega a experiência visual unificada: o dashboard orienta o
 * usuário pelo fluxo sem exigir comandos técnicos.
 */

import { Link } from 'react-router-dom';

import { ROTAS } from '@/constants/navegacao';
import { useSaude } from '@/hooks/useSaude';
import { useDocumento } from '@/context/DocumentoContext';

const ETAPAS = [
  'Importar ou colar',
  'Normalizar',
  'Humanizar',
  'Comparar e revisar',
  'Selecionar template',
  'Validar citações',
  'Exportar',
] as const;

export function Dashboard() {
  const { dados, carregando, erro } = useSaude();
  const { textoOriginal, textoFinal } = useDocumento();

  return (
    <section aria-labelledby="titulo-dashboard" className="space-y-6">
      <header>
        <h2 id="titulo-dashboard" className="text-xl font-semibold">
          Dashboard
        </h2>
        <p className="mt-1 max-w-prose text-sm text-gray-600">
          Normalize, humanize, valide e exporte seu documento acadêmico em etapas
          independentes — sem que a LLM defina layout e sem alterar números, fórmulas,
          citações ou DOIs.
        </p>
      </header>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <PainelEstado
          titulo="API"
          valor={carregando ? 'Verificando…' : erro ? 'Indisponível' : `v${dados?.version ?? '—'}`}
          detalhe={erro ?? dados?.environment ?? ''}
          saudavel={!erro && !carregando}
        />
        <PainelEstado
          titulo="Documento original"
          valor={textoOriginal ? `${textoOriginal.length.toLocaleString('pt-BR')} caracteres` : 'Vazio'}
          detalhe="Imutável ao longo do pipeline"
          saudavel
        />
        <PainelEstado
          titulo="Texto final"
          valor={textoFinal ? `${textoFinal.length.toLocaleString('pt-BR')} caracteres` : 'Ainda não gerado'}
          detalhe="Resultado da revisão para exportar"
          saudavel={textoFinal.length > 0}
        />
      </div>

      <section aria-labelledby="titulo-etapas">
        <h3 id="titulo-etapas" className="mb-2 text-sm font-medium">
          Etapas do fluxo
        </h3>
        <ol className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {ETAPAS.map((etapa, indice) => (
            <li
              key={etapa}
              className="rounded border border-surface-border bg-surface px-3 py-2 text-sm"
            >
              <span className="mr-2 font-medium text-brand-700">{indice + 1}.</span>
              {etapa}
            </li>
          ))}
        </ol>
      </section>

      <section aria-labelledby="titulo-atalhos">
        <h3 id="titulo-atalhos" className="mb-2 text-sm font-medium">
          Comece por aqui
        </h3>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {ROTAS.filter((rota) => rota.caminho !== '/').map((rota) => (
            <Link
              key={rota.caminho}
              to={rota.caminho}
              className="rounded border border-surface-border bg-surface p-3 text-sm hover:border-brand-500"
            >
              <span className="block font-medium text-brand-900">{rota.rotulo}</span>
              <span className="text-gray-600">{rota.descricao}</span>
            </Link>
          ))}
        </div>
      </section>
    </section>
  );
}

function PainelEstado({
  titulo,
  valor,
  detalhe,
  saudavel,
}: {
  titulo: string;
  valor: string;
  detalhe: string;
  saudavel: boolean;
}) {
  return (
    <div className="rounded border border-surface-border bg-surface p-3">
      <span className="block text-xs uppercase tracking-wide text-gray-500">{titulo}</span>
      <span className="mt-1 block text-lg font-semibold">{valor}</span>
      <span className={`block text-sm ${saudavel ? 'text-success' : 'text-danger'}`}>
        {detalhe}
      </span>
    </div>
  );
}
