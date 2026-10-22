// @vitest-environment node
/**
 * Garante que os cabeçalhos de segurança do `nginx.conf` valem para todas as
 * respostas. No Nginx, um `add_header` dentro de um `location` descarta todos
 * os herdados do `server` — erro fácil de reintroduzir ao editar um bloco.
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

import { describe, expect, it } from 'vitest';

const CABECALHOS_SEGURANCA = [
  'X-Content-Type-Options',
  'X-Frame-Options',
  'Referrer-Policy',
  'Content-Security-Policy',
];

interface Bloco {
  nome: string;
  cabecalhos: string[];
}

function semComentarios(conf: string): string {
  return conf
    .split('\n')
    .map((linha) => linha.replace(/#.*$/, ''))
    .join('\n');
}

/** Separa o nível `server` dos blocos `location` (sem aninhamento, como no arquivo). */
function extrairBlocos(conf: string): { server: string[]; locations: Bloco[] } {
  const locations: Bloco[] = [];
  const reLocation = /location\s+([^{]+)\{([^}]*)\}/g;
  const cabecalhosDe = (trecho: string) =>
    [...trecho.matchAll(/add_header\s+([\w-]+)/g)].map((m) => m[1] ?? '');

  for (const m of conf.matchAll(reLocation)) {
    locations.push({ nome: (m[1] ?? '').trim(), cabecalhos: cabecalhosDe(m[2] ?? '') });
  }
  const nivelServer = conf.replace(reLocation, '');
  return { server: cabecalhosDe(nivelServer), locations };
}

const conf = semComentarios(
  readFileSync(fileURLToPath(new URL('../../nginx.conf', import.meta.url)), 'utf-8'),
);
const { server, locations } = extrairBlocos(conf);

describe('nginx.conf — cabeçalhos de segurança', () => {
  it('declara os cabeçalhos no nível do server', () => {
    expect(server).toEqual(expect.arrayContaining(CABECALHOS_SEGURANCA));
  });

  it('identifica os blocos location do arquivo', () => {
    expect(locations.map((l) => l.nome)).toEqual(expect.arrayContaining(['/', '/assets/']));
  });

  it.each(locations.filter((l) => l.cabecalhos.length > 0).map((l) => [l.nome, l] as const))(
    'location %s com add_header próprio repete todos os cabeçalhos',
    (_nome, bloco) => {
      expect(bloco.cabecalhos).toEqual(expect.arrayContaining(CABECALHOS_SEGURANCA));
    },
  );
});
