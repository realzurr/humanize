/**
 * Raiz da aplicação.
 *
 * Define o layout com navegação lateral e registra as onze rotas da Onda 7.
 * O estado compartilhado do documento é provido pelo `DocumentoProvider`
 * (em `main.tsx`).
 */
import { Link, NavLink, Route, Routes } from 'react-router-dom';

import { ROTAS } from '@/constants/navegacao';
import { useAuth } from '@/context/AuthContext';
import { Comparacao } from '@/pages/Comparacao';
import { Dashboard } from '@/pages/Dashboard';
import { Editor } from '@/pages/Editor';
import { Exportacao } from '@/pages/Exportacao';
import { Historico } from '@/pages/Historico';
import { Humanizacao } from '@/pages/Humanizacao';
import { Llm } from '@/pages/Llm';
import { Login } from '@/pages/Login';
import { Normalizacao } from '@/pages/Normalizacao';
import { Perfis } from '@/pages/Perfis';
import { Templates } from '@/pages/Templates';
import { Validador } from '@/pages/Validador';

export function App() {
  const { usuario, sair } = useAuth();

  return (
    <div className="min-h-screen bg-surface-muted text-gray-900">
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-surface-border bg-surface px-4 py-3">
        <div>
          <h1 className="text-lg font-semibold">Humaniza Acadêmico</h1>
          <p className="text-sm text-gray-600">
            Normalize, humanize, valide e exporte seu trabalho acadêmico com proteção de
            dados científicos e conformidade ABNT.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {usuario ? (
            <button
              type="button"
              onClick={() => void sair()}
              className="rounded border border-surface-border px-3 py-1 text-xs font-medium hover:bg-surface-muted"
            >
              Sair · {usuario.username}
            </button>
          ) : (
            <Link
              to="/login"
              className="rounded border border-surface-border px-3 py-1 text-xs font-medium hover:bg-surface-muted"
            >
              Entrar
            </Link>
          )}
        </div>
      </header>

      <div className="flex flex-col md:flex-row">
        <nav
          aria-label="Navegação principal"
          className="shrink-0 border-b border-surface-border bg-surface p-3 md:w-64 md:border-b-0 md:border-r"
        >
          <ul className="flex flex-wrap gap-1 md:block md:space-y-1">
            {ROTAS.map((pagina) => (
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
            <Route path="/login" element={<Login />} />
            <Route path="/editor" element={<Editor />} />
            <Route path="/normalizacao" element={<Normalizacao />} />
            <Route path="/humanizacao" element={<Humanizacao />} />
            <Route path="/comparacao" element={<Comparacao />} />
            <Route path="/templates" element={<Templates />} />
            <Route path="/validador" element={<Validador />} />
            <Route path="/historico" element={<Historico />} />
            <Route path="/perfis" element={<Perfis />} />
            <Route path="/llm" element={<Llm />} />
            <Route path="/exportacao" element={<Exportacao />} />
            <Route path="*" element={<NaoEncontrada />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

function NaoEncontrada() {
  return (
    <section aria-labelledby="titulo-404" className="rounded border border-surface-border bg-surface p-6">
      <h2 id="titulo-404" className="text-lg font-semibold">
        Página não encontrada
      </h2>
      <p className="mt-2 text-sm text-gray-700">
        A rota solicitada não existe. Use a navegação lateral para retornar ao fluxo.
      </p>
    </section>
  );
}
