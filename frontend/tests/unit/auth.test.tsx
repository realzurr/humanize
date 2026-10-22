import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { AuthProvider, useAuth } from '@/context/AuthContext';
import { Login } from '@/pages/Login';
import { api, baixarExportacao, definirToken } from '@/services/api';

function PainelTeste() {
  const { usuario, sair } = useAuth();
  return (
    <div>
      <span data-testid="usuario">{usuario ? usuario.username : 'anonimo'}</span>
      {usuario && (
        <button type="button" onClick={() => void sair()}>
          Sair
        </button>
      )}
    </div>
  );
}

describe('Autenticação no frontend', () => {
  afterEach(() => {
    cleanup();
    definirToken(null);
    localStorage.clear();
    sessionStorage.clear();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('definirToken mantém o token apenas em memória e nunca toca localStorage/sessionStorage', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ status: 'ok', app: 'humaniza', version: '0.1.0', environment: 'test' }),
    });
    vi.stubGlobal('fetch', fetchMock);

    definirToken('tok_secreto_em_memoria');
    await api.health();

    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect((init.headers as Record<string, string>).Authorization).toBe(
      'Bearer tok_secreto_em_memoria',
    );

    definirToken(null);
    await api.health();
    const [, initSemToken] = fetchMock.mock.calls[1] as [string, RequestInit];
    expect((initSemToken.headers as Record<string, string>).Authorization).toBeUndefined();
  });

  it('realiza login, carrega o perfil do usuário e limpa a sessão ao sair', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith('/auth/token')) {
        return {
          ok: true,
          json: async () => ({ access_token: 'jwt_memoria_123', token_type: 'bearer' }),
        };
      }
      if (url.endsWith('/auth/me')) {
        return {
          ok: true,
          json: async () => ({ id: 'u1', username: 'pesquisadora' }),
        };
      }
      return { ok: false, status: 404, json: async () => ({}) };
    });
    vi.stubGlobal('fetch', fetchMock);

    render(
      <MemoryRouter initialEntries={['/login']}>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/" element={<PainelTeste />} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>,
    );

    await userEvent.type(screen.getByLabelText('Nome de usuário'), 'pesquisadora');
    await userEvent.type(screen.getByLabelText('Senha'), 'senha-segura-123');
    await userEvent.click(screen.getByRole('button', { name: 'Entrar' }));

    await waitFor(() => {
      expect(screen.getByTestId('usuario')).toHaveTextContent('pesquisadora');
    });

    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);

    await userEvent.click(screen.getByRole('button', { name: 'Sair' }));
    await waitFor(() => {
      expect(screen.getByTestId('usuario')).toHaveTextContent('anonimo');
    });
    const chamadas = fetchMock.mock.calls as unknown as [string, RequestInit][];
    const chamadaLogout = chamadas.find(([url]) => url.endsWith('/auth/logout'));
    expect(chamadaLogout).toBeDefined();
    const initLogout = chamadaLogout?.[1];
    expect((initLogout?.headers as Record<string, string>).Authorization).toBe(
      'Bearer jwt_memoria_123',
    );
  });

  it('encerra a sessão local quando o backend responde 401', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith('/auth/token')) {
        return { ok: true, json: async () => ({ access_token: 'expira', token_type: 'bearer' }) };
      }
      if (url.endsWith('/auth/me')) {
        return { ok: true, json: async () => ({ id: 'u1', username: 'pesquisadora' }) };
      }
      return { ok: false, status: 401, json: async () => ({}) };
    });
    vi.stubGlobal('fetch', fetchMock);

    render(
      <MemoryRouter initialEntries={['/login']}>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/" element={<PainelTeste />} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>,
    );

    await userEvent.type(screen.getByLabelText('Nome de usuário'), 'pesquisadora');
    await userEvent.type(screen.getByLabelText('Senha'), 'senha-segura-123');
    await userEvent.click(screen.getByRole('button', { name: 'Entrar' }));
    await waitFor(() => {
      expect(screen.getByTestId('usuario')).toHaveTextContent('pesquisadora');
    });

    await expect(api.health()).rejects.toThrow();
    await waitFor(() => {
      expect(screen.getByTestId('usuario')).toHaveTextContent('anonimo');
    });
  });

  it('envia o token no download de exportação', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      blob: async () => new Blob(['conteudo']),
    });
    vi.stubGlobal('fetch', fetchMock);
    vi.stubGlobal('URL', { ...URL, createObjectURL: () => 'blob:x', revokeObjectURL: () => {} });
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});

    definirToken('tok_download');
    await baixarExportacao('exp-1', 'arquivo.txt');

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain('/exports/exp-1/download');
    expect((init.headers as Record<string, string>).Authorization).toBe('Bearer tok_download');
  });

  it('permite alternar para registro e exibe erro da API quando falha', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      statusText: 'Unprocessable Entity',
      json: async () => ({ error: { code: 'VALIDATION_ERROR', message: 'Usuário já existe' } }),
    });
    vi.stubGlobal('fetch', fetchMock);

    render(
      <MemoryRouter initialEntries={['/login']}>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/" element={<PainelTeste />} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>,
    );

    await userEvent.click(screen.getByRole('button', { name: 'Criar conta' }));
    await userEvent.type(screen.getByLabelText('Nome de usuário'), 'duplicado');
    await userEvent.type(screen.getByLabelText('Senha'), 'senha-segura-123');
    await userEvent.click(screen.getByRole('button', { name: 'Registrar e entrar' }));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Usuário já existe');
    });
  });

  it('encerra todas as sessões pelo backend e limpa o usuário', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith('/auth/token')) {
        return { ok: true, json: async () => ({ access_token: 'tok_todas', token_type: 'bearer' }) };
      }
      if (url.endsWith('/auth/me')) {
        return { ok: true, json: async () => ({ id: 'u1', username: 'pesquisadora' }) };
      }
      if (url.endsWith('/auth/logout-all')) {
        return { ok: true, status: 204, json: async () => ({}) };
      }
      return { ok: false, status: 404, json: async () => ({}) };
    });
    vi.stubGlobal('fetch', fetchMock);

    render(
      <MemoryRouter initialEntries={['/login']}>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/" element={<Login />} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>,
    );

    await userEvent.type(screen.getByLabelText('Nome de usuário'), 'pesquisadora');
    await userEvent.type(screen.getByLabelText('Senha'), 'senha-segura-123');
    await userEvent.click(screen.getByRole('button', { name: 'Entrar' }));
    await userEvent.click(await screen.findByRole('button', { name: 'Encerrar todas as sessões' }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Entrar' })).toBeInTheDocument();
    });
    const chamadas = fetchMock.mock.calls as unknown as [string, RequestInit][];
    const chamada = chamadas.find(([url]) => url.endsWith('/auth/logout-all'));
    expect((chamada?.[1].headers as Record<string, string>).Authorization).toBe('Bearer tok_todas');
  });
});
