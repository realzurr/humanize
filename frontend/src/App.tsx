/**
 * Raiz da aplicação.
 *
 * A Onda 0 entrega apenas o esqueleto de navegação. As onze telas
 * funcionais são implementadas na Onda 7.
 */
import { NavLink, Route, Routes } from 'react-router-dom';

const PAGINAS_PREVISTAS = [
  { caminho: '/', rotulo: 'Dashboard' },
  { caminho: '/editor', rotulo: 'Editor' },
  { caminho: '/normalizacao', rotulo: 'Normalização' },
  { caminho: '/humanizacao', rotulo: 'Humanização' },
  { caminho: '/comparacao', rotulo: 'Comparação' },
  { caminho: '/templates', rotulo: 'Templates ABNT' },
  { caminho: '/validador', rotulo: 'Validador' },
  { caminho: '/historico', rotulo: 'Histórico' },
  { caminho: '/perfis', rotulo: 'Perfis autorais' },
  { caminho: '/llm', rotulo: 'Configurações de LLM' },
  { caminho: '/exportacao', rotulo: 'Exportação' },
] as const;

export function App() {
  return (
    <div className="min-h-screen bg-surface-muted text-gray-900">
      <header className="border-b border-surface-border bg-surface px-4 py-3">
        <h1 className="text-lg font-semibold">Humaniza Acadêmico</h1>
        <p className="text-sm text-gray-600">
          Onda 0 concluida: arquitetura, contratos e ferramentas. As telas
          funcionais chegam na Onda 7.
        </p>
      </header>

      <div className="flex">
        <nav aria-label="Navegação principal" className="w-64 shrink-0 border-r border-surface-border bg-surface p-3">
          <ul className="space-y-1">
            {PAGINAS_PREVISTAS.map((pagina) => (
              <li key={pagina.caminho}>
                <NavLink
                  to={pagina.caminho}
                  end={pagina.caminho === '/'}
                  className={({ isActive }) =>
                    `block rounded px-3 py-2 text-sm ${
                      isActive ? 'bg-brand-50 font-medium text-brand-900' : 'hover:bg-surface-muted'
                    }`
                  }
                >
                  {pagina.rotulo}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        <main className="flex-1 p-6">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="*" element={<EmConstrucao />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

function Dashboard() {
  return (
    <section aria-labelledby="titulo-dashboard">
      <h2 id="titulo-dashboard" className="text-xl font-semibold">
        Dashboard
      </h2>
      <p className="mt-2 max-w-prose text-sm text-gray-700">
        Fluxo do produto: documento original, normalização textual, identificação da
        estrutura, extração de elementos protegidos, seleção do perfil autoral,
        humanização por LLM, validação semântica, comparação e revisão, seleção do
        template ABNT, formatação determinística, validação acadêmica e exportação.
      </p>
      <p className="mt-4 text-sm text-gray-600">
        Cada etapa é independente. Normalização e formatação não exigem chave de LLM.
      </p>
    </section>
  );
}

function EmConstrucao() {
  return (
    <section aria-labelledby="titulo-construcao" className="rounded border border-surface-border bg-surface p-6">
      <h2 id="titulo-construcao" className="text-lg font-semibold">
        Em construção
      </h2>
      <p className="mt-2 text-sm text-gray-700">
        Esta tela sera implementada em ondas posteriores. Consulte
        <code className="mx-1 rounded bg-surface-muted px-1">docs/ROADMAP.md</code>
        para o escopo previsto.
      </p>
    </section>
  );
}
