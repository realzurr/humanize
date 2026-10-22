/**
 * Perfis autorais.
 *
 * Apresenta os sete perfis de escrita. O perfil autoral personalizado é
 * construído exclusivamente com textos do próprio usuário (verificado por
 * ``owner_id``) durante a humanização — nenhum texto de terceiros é aceito.
 */

import { Link } from 'react-router-dom';

import { AUTORAL_ID, PERFIS_AUTORAIS } from '@/constants/perfis';

export function Perfis() {
  return (
    <section aria-labelledby="titulo-perfis" className="space-y-6">
      <header>
        <h2 id="titulo-perfis" className="text-xl font-semibold">
          Perfis autorais
        </h2>
        <p className="mt-1 max-w-prose text-sm text-gray-600">
          Sete perfis orientam a reescrita. O perfil autoral personalizado é derivado
          apenas dos textos do próprio autor — nunca de fontes de terceiros.
        </p>
      </header>

      <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {PERFIS_AUTORAIS.map((perfil) => (
          <li key={perfil.id} className="rounded border border-surface-border bg-surface p-3">
            <div className="flex items-start justify-between gap-2">
              <span className="font-medium">{perfil.nome}</span>
              {perfil.id === AUTORAL_ID && (
                <span className="rounded-full bg-brand-50 px-2 py-0.5 text-xs text-brand-900">
                  pessoal
                </span>
              )}
            </div>
            <p className="mt-1 text-sm text-gray-600">{perfil.descricao}</p>
          </li>
        ))}
      </ul>

      <p className="text-sm text-gray-600">
        Selecione o perfil desejado na{' '}
        <Link to="/humanizacao" className="text-brand-700 underline">
          humanização
        </Link>
        .
      </p>
    </section>
  );
}
