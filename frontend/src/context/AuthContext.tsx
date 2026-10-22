/**
 * Contexto de autenticação.
 *
 * O token de acesso fica **apenas em memória** (via `api.definirToken`), nunca
 * em `localStorage`/`sessionStorage`. O modo local (sem autenticação) continua
 * funcionando: sem token, as requisições simplesmente não enviam `Authorization`.
 */

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

import type { ReactNode } from 'react';

import { api, definirAoSessaoExpirar, definirToken } from '@/services/api';
import type { UsuarioOut } from '@/types';

interface AuthContexto {
  usuario: UsuarioOut | null;
  entrar: (username: string, password: string) => Promise<void>;
  registrar: (username: string, password: string) => Promise<void>;
  sair: () => Promise<void>;
  /** Revoga todos os tokens do usuário (outros navegadores/dispositivos inclusive). */
  sairDeTodasAsSessoes: () => Promise<void>;
}

const Contexto = createContext<AuthContexto | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<UsuarioOut | null>(null);

  useEffect(() => {
    definirAoSessaoExpirar(() => setUsuario(null));
    return () => definirAoSessaoExpirar(null);
  }, []);

  const entrar = useCallback(async (username: string, password: string) => {
    const token = await api.entrar({ username, password });
    definirToken(token.access_token);
    const eu = await api.me();
    setUsuario(eu);
  }, []);

  const registrar = useCallback(async (username: string, password: string) => {
    await api.registrar({ username, password });
    await entrar(username, password);
  }, [entrar]);

  const sair = useCallback(async () => {
    try {
      await api.sair();
    } catch {
      // A sessão local é encerrada mesmo se o backend estiver indisponível;
      // o token expira naturalmente pelo TTL.
    } finally {
      definirToken(null);
      setUsuario(null);
    }
  }, []);

  const sairDeTodasAsSessoes = useCallback(async () => {
    // Diferente de `sair`, a falha é propagada: o usuário precisa saber se as
    // outras sessões continuam válidas.
    await api.sairDeTodasAsSessoes();
    definirToken(null);
    setUsuario(null);
  }, []);

  const valor = useMemo<AuthContexto>(
    () => ({ usuario, entrar, registrar, sair, sairDeTodasAsSessoes }),
    [usuario, entrar, registrar, sair, sairDeTodasAsSessoes],
  );

  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}

export function useAuth(): AuthContexto {
  const contexto = useContext(Contexto);
  if (!contexto) {
    throw new Error('useAuth deve ser usado dentro de um AuthProvider');
  }
  return contexto;
}
