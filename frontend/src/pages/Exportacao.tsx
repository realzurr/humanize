/**
 * Exportação de documentos.
 *
 * Configura os metadados, o template, a instituição e os formatos desejados,
 * e gera DOCX, PDF, TXT e/ou Markdown com pré-visualização e histórico.
 */

import { useEffect, useState } from 'react';

import { useDocumento } from '@/context/DocumentoContext';
import { api, baixarExportacao } from '@/services/api';
import type {
  FormatoExportacao,
  MetadadosDocumento,
  NaturezaDocumento,
  RespostaExportacao,
  TemplateResumo,
} from '@/types';

const NATUREZAS: { id: NaturezaDocumento; rotulo: string }[] = [
  { id: 'tcc', rotulo: 'TCC' },
  { id: 'monografia', rotulo: 'Monografia' },
  { id: 'dissertacao', rotulo: 'Dissertação' },
  { id: 'tese', rotulo: 'Tese' },
  { id: 'projeto_pesquisa', rotulo: 'Projeto de pesquisa' },
  { id: 'relatorio', rotulo: 'Relatório' },
  { id: 'artigo', rotulo: 'Artigo' },
  { id: 'trabalho_academico', rotulo: 'Trabalho acadêmico' },
  { id: 'livro', rotulo: 'Livro' },
];

const FORMATOS: { id: FormatoExportacao; rotulo: string }[] = [
  { id: 'docx', rotulo: 'DOCX (Word)' },
  { id: 'pdf', rotulo: 'PDF' },
  { id: 'txt', rotulo: 'TXT' },
  { id: 'md', rotulo: 'Markdown' },
];

export function Exportacao() {
  const { textoFinal, textoOriginal, templateId, definirTemplate } = useDocumento();

  const [templates, setTemplates] = useState<TemplateResumo[]>([]);
  const [formatos, setFormatos] = useState<FormatoExportacao[]>(['docx', 'pdf', 'txt', 'md']);
  const [metadados, setMetadados] = useState<MetadadosDocumento>({});
  const [instituicao, setInstituicao] = useState('');
  const [resultado, setResultado] = useState<RespostaExportacao | null>(null);
  const [processando, setProcessando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    api
      .listarTemplates()
      .then(setTemplates)
      .catch(() => setTemplates([]));
  }, []);

  function atualizarMetadado(campo: keyof MetadadosDocumento, valor: string) {
    setMetadados((atuais) => ({ ...atuais, [campo]: valor }));
  }

  function alternarFormato(formato: FormatoExportacao) {
    setFormatos((atuais) =>
      atuais.includes(formato)
        ? atuais.filter((item) => item !== formato)
        : [...atuais, formato],
    );
  }

  async function exportar() {
    setErro(null);
    setProcessando(true);
    try {
      const resposta = await api.exportar({
        texto: textoFinal || textoOriginal,
        template_id: templateId,
        metadados,
        formatos,
        ...(instituicao ? { instituicao } : {}),
      });
      setResultado(resposta);
    } catch (motivo: unknown) {
      setErro(motivo instanceof Error ? motivo.message : 'Falha ao exportar');
    } finally {
      setProcessando(false);
    }
  }

  return (
    <section aria-labelledby="titulo-exportacao" className="space-y-6">
      <header>
        <h2 id="titulo-exportacao" className="text-xl font-semibold">
          Exportação
        </h2>
        <p className="mt-1 max-w-prose text-sm text-gray-600">
          Gere o documento acadêmico em DOCX (estilos nativos do Word), PDF, TXT e
          Markdown. A ficha catalográfica é reservada — nunca preenchida com dados fictícios.
        </p>
      </header>

      <fieldset className="space-y-4 rounded border border-surface-border bg-surface p-4">
        <legend className="px-1 text-sm font-medium">Metadados do documento</legend>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Campo
            id="autor"
            rotulo="Autor(a)"
            valor={metadados.author ?? ''}
            onChange={(valor) => atualizarMetadado('author', valor)}
          />
          <Campo
            id="instituicao-meta"
            rotulo="Instituição"
            valor={metadados.institution ?? ''}
            onChange={(valor) => atualizarMetadado('institution', valor)}
          />
          <Campo
            id="titulo"
            rotulo="Título"
            valor={metadados.title ?? ''}
            onChange={(valor) => atualizarMetadado('title', valor)}
          />
          <Campo
            id="subtitulo"
            rotulo="Subtítulo"
            valor={metadados.subtitle ?? ''}
            onChange={(valor) => atualizarMetadado('subtitle', valor)}
          />
          <Campo
            id="orientador"
            rotulo="Orientador(a)"
            valor={metadados.advisor ?? ''}
            onChange={(valor) => atualizarMetadado('advisor', valor)}
          />
          <Campo
            id="cidade"
            rotulo="Cidade"
            valor={metadados.city ?? ''}
            onChange={(valor) => atualizarMetadado('city', valor)}
          />
          <Campo
            id="ano"
            rotulo="Ano"
            valor={metadados.year ?? ''}
            onChange={(valor) => atualizarMetadado('year', valor)}
          />
          <div>
            <label htmlFor="natureza" className="mb-1 block text-sm font-medium">
              Natureza
            </label>
            <select
              id="natureza"
              value={metadados.nature ?? ''}
              onChange={(evento) =>
                setMetadados((atuais) => ({
                  ...atuais,
                  nature: (evento.target.value || null) as NaturezaDocumento | null,
                }))
              }
              className="w-full rounded border border-surface-border bg-surface px-2 py-1 text-sm"
            >
              <option value="">—</option>
              {NATUREZAS.map((natureza) => (
                <option key={natureza.id} value={natureza.id}>
                  {natureza.rotulo}
                </option>
              ))}
            </select>
          </div>
        </div>
      </fieldset>

      <fieldset className="space-y-3 rounded border border-surface-border bg-surface p-4">
        <legend className="px-1 text-sm font-medium">Template e formato</legend>
        <div>
          <label htmlFor="template" className="mb-1 block text-sm font-medium">
            Template ABNT
          </label>
          <select
            id="template"
            value={templateId}
            onChange={(evento) => definirTemplate(evento.target.value)}
            className="w-full max-w-md rounded border border-surface-border bg-surface px-2 py-1 text-sm"
          >
            {templates.map((template) => (
              <option key={template.id} value={template.id}>
                {template.title || template.id} (v{template.version})
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="instituicao-export" className="mb-1 block text-sm font-medium">
            Perfil institucional (opcional)
          </label>
          <select
            id="instituicao-export"
            value={instituicao}
            onChange={(evento) => setInstituicao(evento.target.value)}
            className="w-full max-w-md rounded border border-surface-border bg-surface px-2 py-1 text-sm"
          >
            <option value="">— Nenhum —</option>
            <option value="ufms">UFMS</option>
            <option value="ufgd">UFGD</option>
          </select>
        </div>

        <div>
          <span className="mb-1 block text-sm font-medium">Formatos</span>
          <div className="flex flex-wrap gap-4">
            {FORMATOS.map((formato) => (
              <label key={formato.id} className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={formatos.includes(formato.id)}
                  onChange={() => alternarFormato(formato.id)}
                  className="h-4 w-4 rounded border-surface-border"
                />
                {formato.rotulo}
              </label>
            ))}
          </div>
        </div>

        <button
          type="button"
          onClick={exportar}
          disabled={processando || (textoFinal || textoOriginal) === '' || formatos.length === 0}
          className="rounded bg-brand-500 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
        >
          {processando ? 'Exportando…' : 'Exportar'}
        </button>
      </fieldset>

      {erro && (
        <p role="alert" className="rounded border border-danger/30 bg-danger/10 p-3 text-sm text-danger">
          {erro}
        </p>
      )}

      {resultado && (
        <section aria-labelledby="titulo-resultado-exportacao" className="space-y-3">
          <h3 id="titulo-resultado-exportacao" className="text-sm font-medium">
            Resultado da exportação
          </h3>

          {resultado.limitations.length > 0 && (
            <aside className="rounded border border-warning/30 bg-warning/10 p-3 text-sm">
              <span className="font-medium text-warning">Limitações</span>
              <ul className="mt-1 list-inside list-disc space-y-1 text-gray-700">
                {resultado.limitations.map((limitacao) => (
                  <li key={limitacao}>{limitacao}</li>
                ))}
              </ul>
            </aside>
          )}

          <ul className="space-y-2">
            {resultado.exports.map((registro) => (
              <li
                key={registro.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded border border-surface-border bg-surface p-3 text-sm"
              >
                <span>
                  <span className="font-medium uppercase">{registro.format}</span>{' '}
                  <span className="font-mono text-xs text-gray-600">{registro.filename}</span>
                  <span className="ml-2 text-xs text-gray-500">
                    {(registro.size_bytes / 1024).toFixed(1)} KB
                  </span>
                </span>
                <button
                  type="button"
                  onClick={() => void baixarExportacao(registro.id, registro.filename)}
                  className="rounded border border-surface-border px-2 py-1 text-xs hover:bg-surface-muted"
                >
                  Baixar
                </button>
              </li>
            ))}
          </ul>

          <div className="rounded border border-surface-border bg-surface p-3">
            <span className="block text-sm font-medium">
              Pré-visualização — {resultado.preview.title}
            </span>
            <span className="block text-xs text-gray-600">
              {resultado.preview.font} {resultado.preview.font_size_pt}pt · espaçamento{' '}
              {resultado.preview.line_spacing} · {resultado.preview.toc_entries.length} itens de
              sumário
            </span>
            {resultado.preview.toc_entries.length > 0 && (
              <ol className="mt-2 list-inside list-decimal text-sm text-gray-700">
                {resultado.preview.toc_entries.slice(0, 12).map((item, indice) => (
                  <li key={indice}>
                    {item.number ? `${item.number} ` : ''}
                    {item.title}
                  </li>
                ))}
              </ol>
            )}
          </div>
        </section>
      )}
    </section>
  );
}

function Campo({
  id,
  rotulo,
  valor,
  onChange,
}: {
  id: string;
  rotulo: string;
  valor: string;
  onChange: (valor: string) => void;
}) {
  return (
    <div>
      <label htmlFor={id} className="mb-1 block text-sm font-medium">
        {rotulo}
      </label>
      <input
        id={id}
        value={valor}
        onChange={(evento) => onChange(evento.target.value)}
        className="w-full rounded border border-surface-border bg-surface px-2 py-1 text-sm"
      />
    </div>
  );
}
