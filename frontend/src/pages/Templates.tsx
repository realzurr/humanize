/**
 * Templates ABNT.
 *
 * Lista os templates disponíveis (gerais e institucionais), permite resolver
 * um template com um perfil institucional e exibe os conflitos normativos
 * registrados — nunca ocultados.
 */

import { useEffect, useState } from 'react';

import { useDocumento } from '@/context/DocumentoContext';
import { api } from '@/services/api';
import type { Conflito, ResolveTemplate, TemplateResumo } from '@/types';

const INSTITUICOES = [
  { id: 'ufms', nome: 'UFMS — Universidade Federal de Mato Grosso do Sul' },
  { id: 'ufgd', nome: 'UFGD — Universidade Federal da Grande Dourados' },
] as const;

export function Templates() {
  const { templateId, definirTemplate } = useDocumento();

  const [templates, setTemplates] = useState<TemplateResumo[]>([]);
  const [instituicao, setInstituicao] = useState('');
  const [resolvido, setResolvido] = useState<ResolveTemplate | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    api
      .listarTemplates()
      .then(setTemplates)
      .catch((motivo: unknown) => setErro(motivo instanceof Error ? motivo.message : 'Falha ao carregar templates'));
  }, []);

  async function resolver(id: string, inst?: string) {
    setErro(null);
    try {
      const resultado = await api.resolverTemplate(id, inst || undefined);
      setResolvido(resultado);
      definirTemplate(id);
    } catch (motivo: unknown) {
      setErro(motivo instanceof Error ? motivo.message : 'Falha ao resolver o template');
    }
  }

  return (
    <section aria-labelledby="titulo-templates" className="space-y-6">
      <header>
        <h2 id="titulo-templates" className="text-xl font-semibold">
          Templates ABNT
        </h2>
        <p className="mt-1 max-w-prose text-sm text-gray-600">
          Estrutura e regras de formatação parametrizadas por norma. Conflitos entre
          instituição e norma são registrados e exibidos, nunca resolvidos em silêncio.
        </p>
      </header>

      <div className="flex flex-wrap items-end gap-3">
        <div>
          <label htmlFor="instituicao" className="mb-1 block text-sm font-medium">
            Perfil institucional (opcional)
          </label>
          <select
            id="instituicao"
            value={instituicao}
            onChange={(evento) => {
              const valor = evento.target.value;
              setInstituicao(valor);
              if (valor) void resolver(templateId, valor);
            }}
            className="rounded border border-surface-border bg-surface px-2 py-1 text-sm"
          >
            <option value="">— Nenhum (norma geral ABNT) —</option>
            {INSTITUICOES.map((inst) => (
              <option key={inst.id} value={inst.id}>
                {inst.nome}
              </option>
            ))}
          </select>
        </div>
        <span className="text-sm text-gray-600">
          Selecionado:{' '}
          <strong>
            {templates.find((t) => t.id === templateId)?.title ?? templateId}
          </strong>
        </span>
      </div>

      {erro && (
        <p role="alert" className="rounded border border-danger/30 bg-danger/10 p-3 text-sm text-danger">
          {erro}
        </p>
      )}

      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {templates.map((template) => (
          <button
            key={template.id}
            type="button"
            onClick={() => void resolver(template.id, instituicao || undefined)}
            aria-pressed={template.id === templateId}
            className={`rounded border p-3 text-left text-sm ${
              template.id === templateId
                ? 'border-brand-500 bg-brand-50'
                : 'border-surface-border bg-surface hover:border-brand-500'
            }`}
          >
            <span className="block font-medium">{template.title || template.id}</span>
            <span className="block text-xs text-gray-600">
              {template.kind} · v{template.version}
              {template.institution ? ` · ${template.institution}` : ''}
            </span>
            <span className="mt-1 block text-xs text-gray-500">
              {template.fontes} fonte(s) normativa(s)
            </span>
          </button>
        ))}
      </div>

      {resolvido && (
        <section aria-labelledby="titulo-resolvido" className="space-y-3">
          <h3 id="titulo-resolvido" className="text-sm font-medium">
            Template resolvido
          </h3>

          {resolvido.conflicts.length > 0 ? (
            <div className="rounded border border-warning/30 bg-warning/10 p-3">
              <span className="text-sm font-medium text-warning">
                {resolvido.conflicts.length} conflito(s) registrado(s)
              </span>
              <ul className="mt-2 space-y-1">
                {resolvido.conflicts.map((conflito: Conflito, indice: number) => (
                  <li key={indice} className="text-sm text-gray-700">
                    <code className="rounded bg-surface-muted px-1 text-xs">{conflito.path}</code>{' '}
                    {conflito.message}
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <p className="text-sm text-gray-600">Nenhum conflito entre instituição e norma.</p>
          )}

          {resolvido.overrides.length > 0 && (
            <p className="text-sm text-gray-600">
              Regras sobrescritas pela instituição: {resolvido.overrides.length}
            </p>
          )}
        </section>
      )}
    </section>
  );
}
