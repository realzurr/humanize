/**
 * Página de autenticação (login e registro).
 *
 * O token de acesso obtido permanece exclusivamente em memória (via
 * `AuthContext` -> `api.definirToken`), nunca em `localStorage` ou
 * `sessionStorage`. No modo local (`AUTH_ENABLED=false` no backend), o uso
 * desta página é opcional.
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import type { FormEvent } from 'react';

import { useAuth } from '@/context/AuthContext';

export function Login() {
  const { usuario, entrar, registrar, sair, sairDeTodasAsSessoes } = useAuth();
  const navigate = useNavigate();

  const [modo, setModo] = useState<'entrar' | 'registrar'>('entrar');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function submeter(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    setErro(null);

    const usuarioLimpo = username.trim();
    if (!usuarioLimpo || !password) {
      setErro('Informe o nome de usuário e a senha.');
      return;
    }

    setCarregando(true);
    try {
      if (modo === 'registrar') {
        await registrar(usuarioLimpo, password);
      } else {
        await entrar(usuarioLimpo, password);
      }
      setPassword('');
      navigate('/');
    } catch (motivo: unknown) {
      setErro(motivo instanceof Error ? motivo.message : 'Falha na autenticação');
    } finally {
      setCarregando(false);
    }
  }

  async function encerrarTodas() {
    setErro(null);
    try {
      await sairDeTodasAsSessoes();
    } catch (motivo: unknown) {
      setErro(
        motivo instanceof Error
          ? motivo.message
          : 'Não foi possível encerrar as outras sessões. Tente novamente.',
      );
    }
  }

  if (usuario) {
    return (
      <section
        aria-labelledby="titulo-login"
        className="mx-auto max-w-md space-y-4 rounded border border-surface-border bg-surface p-6"
      >
        <h2 id="titulo-login" className="text-xl font-semibold">
          Sessão ativa
        </h2>
        <p className="text-sm text-gray-700">
          Conectado como <strong>{usuario.username}</strong>. O token de acesso é mantido
          apenas em memória durante esta sessão.
        </p>
        {erro && (
          <p
            role="alert"
            className="rounded border border-danger/30 bg-danger/10 p-3 text-sm text-danger"
          >
            {erro}
          </p>
        )}
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => void sair()}
            className="rounded border border-danger/30 px-3 py-1.5 text-sm text-danger hover:bg-danger/10"
          >
            Encerrar sessão
          </button>
          <button
            type="button"
            onClick={() => void encerrarTodas()}
            className="rounded border border-danger/30 px-3 py-1.5 text-sm text-danger hover:bg-danger/10"
          >
            Encerrar todas as sessões
          </button>
        </div>
      </section>
    );
  }

  return (
    <section
      aria-labelledby="titulo-login"
      className="mx-auto max-w-md space-y-6 rounded border border-surface-border bg-surface p-6"
    >
      <header>
        <h2 id="titulo-login" className="text-xl font-semibold">
          {modo === 'entrar' ? 'Entrar' : 'Criar conta'}
        </h2>
        <p className="mt-1 text-sm text-gray-600">
          Autenticação para ambientes multiusuário. O token permanece somente em memória
          e nunca é gravado no armazenamento do navegador.
        </p>
      </header>

      <div className="flex gap-2" role="group" aria-label="Modo de autenticação">
        <button
          type="button"
          onClick={() => {
            setModo('entrar');
            setErro(null);
          }}
          aria-pressed={modo === 'entrar'}
          className={`flex-1 rounded border px-3 py-1.5 text-sm ${
            modo === 'entrar'
              ? 'border-brand-600 bg-brand-50 font-medium text-brand-900'
              : 'border-surface-border hover:bg-surface-muted'
          }`}
        >
          Já tenho conta
        </button>
        <button
          type="button"
          onClick={() => {
            setModo('registrar');
            setErro(null);
          }}
          aria-pressed={modo === 'registrar'}
          className={`flex-1 rounded border px-3 py-1.5 text-sm ${
            modo === 'registrar'
              ? 'border-brand-600 bg-brand-50 font-medium text-brand-900'
              : 'border-surface-border hover:bg-surface-muted'
          }`}
        >
          Criar conta
        </button>
      </div>

      {erro && (
        <p
          role="alert"
          className="rounded border border-danger/30 bg-danger/10 p-3 text-sm text-danger"
        >
          {erro}
        </p>
      )}

      <form onSubmit={(e) => void submeter(e)} className="space-y-4">
        <div>
          <label htmlFor="campo-usuario" className="block text-sm font-medium text-gray-700">
            Nome de usuário
          </label>
          <input
            id="campo-usuario"
            aria-label="Nome de usuário"
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            minLength={3}
            required
            className="mt-1 w-full rounded border border-surface-border bg-surface px-3 py-2 text-sm"
          />
        </div>

        <div>
          <label htmlFor="campo-senha" className="block text-sm font-medium text-gray-700">
            Senha
          </label>
          <input
            id="campo-senha"
            aria-label="Senha"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete={modo === 'entrar' ? 'current-password' : 'new-password'}
            minLength={8}
            required
            className="mt-1 w-full rounded border border-surface-border bg-surface px-3 py-2 text-sm"
          />
        </div>

        <button
          type="submit"
          disabled={carregando}
          className="w-full rounded bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
        >
          {carregando
            ? 'Processando…'
            : modo === 'entrar'
              ? 'Entrar'
              : 'Registrar e entrar'}
        </button>
      </form>
    </section>
  );
}
