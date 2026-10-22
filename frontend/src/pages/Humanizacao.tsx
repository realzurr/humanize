/**
 * Humanização semântica.
 *
 * Seleção de perfil autoral, intensidade e provedor/modelo, com exibição do
 * resultado, dos achados de validação semântica, da análise estilística e do
 * consumo estimado de tokens/custo.
 */

import { useEffect, useMemo, useState } from 'react';

import { Link } from 'react-router-dom';

import { AUTORAL_ID, INTENSIDADES, PERFIS_AUTORAIS } from '@/constants/perfis';
import { useDocumento } from '@/context/DocumentoContext';
import { api } from '@/services/api';
import type { Modelo, Provedor, RespostaHumanizacao } from '@/types';
import { classeSeveridade, rotuloSeveridade } from '@/utils/severidade';

export function Humanizacao() {
  const {
    textoOriginal,
    textoNormalizado,
    respostaHumanizacao,
    provedorId,
    modeloId,
    definirProvedor,
    definirModelo,
    definirHumanizacao,
  } = useDocumento();

  const [texto, setTexto] = useState(textoNormalizado || textoOriginal);
  const [perfil, setPerfil] = useState('academico_cientifico');
  const [intensidade, setIntensidade] = useState<number>(50);
  const [ownerId, setOwnerId] = useState('');
  const [textosAutorais, setTextosAutorais] = useState('');

  const [provedores, setProvedores] = useState<Provedor[]>([]);
  const [modelos, setModelos] = useState<Modelo[]>([]);
  const [processando, setProcessando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    api
      .listarProvedores()
      .then(setProvedores)
      .catch(() => setProvedores([]));
  }, []);

  useEffect(() => {
    let ativo = true;
    api
      .listarModelos(provedorId)
      .then((lista) => {
        if (ativo) {
          setModelos(lista);
          if (!lista.some((modelo) => modelo.id === modeloId) && lista.length > 0) {
            definirModelo(lista[0]!.id);
          }
        }
      })
      .catch(() => {
        if (ativo) setModelos([]);
      });
    return () => {
      ativo = false;
    };
  }, [provedorId, modeloId, definirModelo]);

  const perfilAutoral = perfil === AUTORAL_ID;

  async function executar() {
    setErro(null);
    setProcessando(true);
    try {
      const resposta = await api.humanizar({
        texto,
        perfil,
        intensidade,
        provedor: provedorId,
        modelo: modeloId,
        ...(perfilAutoral ? { owner_id: ownerId, textos_autorais: [textosAutorais] } : {}),
      });
      definirHumanizacao(resposta);
    } catch (motivo: unknown) {
      setErro(motivo instanceof Error ? motivo.message : 'Falha ao humanizar o texto');
    } finally {
      setProcessando(false);
    }
  }

  const perfilSelecionado = useMemo(
    () => PERFIS_AUTORAIS.find((perfilItem) => perfilItem.id === perfil),
    [perfil],
  );

  return (
    <section aria-labelledby="titulo-humanizacao" className="space-y-6">
      <header>
        <h2 id="titulo-humanizacao" className="text-xl font-semibold">
          Humanização semântica
        </h2>
        <p className="mt-1 max-w-prose text-sm text-gray-600">
          Reescreva o texto com clareza e naturalidade preservando números, datas,
          citações e DOIs. A aprovação é bloqueada se um dado protegido for perdido.
        </p>
      </header>

      <div>
        <label htmlFor="texto-humanizar" className="mb-1 block text-sm font-medium">
          Texto a humanizar
          <span className="ml-2 font-normal text-gray-500">
            {texto.length.toLocaleString('pt-BR')} caracteres
          </span>
        </label>
        <textarea
          id="texto-humanizar"
          value={texto}
          onChange={(evento) => setTexto(evento.target.value)}
          className="h-40 w-full rounded border border-surface-border bg-surface p-3 font-mono text-sm"
        />
        {textoNormalizado && textoNormalizado !== texto && (
          <button
            type="button"
            onClick={() => setTexto(textoNormalizado)}
            className="mt-1 text-xs text-brand-700 underline"
          >
            Usar texto normalizado
          </button>
        )}
      </div>

      <fieldset className="space-y-4 rounded border border-surface-border bg-surface p-4">
        <legend className="px-1 text-sm font-medium">Configuração</legend>

        <div>
          <label htmlFor="perfil" className="mb-1 block text-sm font-medium">
            Perfil autoral
          </label>
          <select
            id="perfil"
            value={perfil}
            onChange={(evento) => setPerfil(evento.target.value)}
            className="w-full max-w-md rounded border border-surface-border bg-surface px-2 py-1 text-sm"
          >
            {PERFIS_AUTORAIS.map((perfilItem) => (
              <option key={perfilItem.id} value={perfilItem.id}>
                {perfilItem.nome}
              </option>
            ))}
          </select>
          {perfilSelecionado && (
            <p className="mt-1 text-xs text-gray-600">{perfilSelecionado.descricao}</p>
          )}
        </div>

        {perfilAutoral && (
          <div className="space-y-3 rounded border border-brand-100 bg-brand-50 p-3">
            <div>
              <label htmlFor="owner-id" className="mb-1 block text-sm font-medium">
                Identificador do autor
              </label>
              <input
                id="owner-id"
                value={ownerId}
                onChange={(evento) => setOwnerId(evento.target.value)}
                placeholder="Ex.: seu e-mail ou identificador"
                className="w-full max-w-md rounded border border-surface-border bg-surface px-2 py-1 text-sm"
              />
            </div>
            <div>
              <label htmlFor="textos-autorais" className="mb-1 block text-sm font-medium">
                Textos do próprio autor (referência de estilo)
              </label>
              <textarea
                id="textos-autorais"
                value={textosAutorais}
                onChange={(evento) => setTextosAutorais(evento.target.value)}
                className="h-24 w-full rounded border border-surface-border bg-surface p-2 text-sm"
              />
            </div>
          </div>
        )}

        <div>
          <span className="mb-1 block text-sm font-medium">
            Intensidade ({intensidade})
          </span>
          <div className="flex flex-wrap gap-2" role="group" aria-label="Intensidade da revisão">
            {INTENSIDADES.map((nivel) => (
              <label key={nivel} className="flex items-center gap-1 text-sm">
                <input
                  type="radio"
                  name="intensidade"
                  value={nivel}
                  checked={intensidade === nivel}
                  onChange={() => setIntensidade(nivel)}
                  className="h-4 w-4"
                />
                {nivel}
              </label>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <label htmlFor="provedor" className="mb-1 block text-sm font-medium">
              Provedor
            </label>
            <select
              id="provedor"
              value={provedorId}
              onChange={(evento) => definirProvedor(evento.target.value)}
              className="w-full rounded border border-surface-border bg-surface px-2 py-1 text-sm"
            >
              {provedores.map((prov) => (
                <option key={prov.id} value={prov.id}>
                  {prov.nome}
                  {prov.configurado ? '' : prov.requer_chave ? ' (sem chave)' : ''}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="modelo" className="mb-1 block text-sm font-medium">
              Modelo
            </label>
            <select
              id="modelo"
              value={modeloId}
              onChange={(evento) => definirModelo(evento.target.value)}
              className="w-full rounded border border-surface-border bg-surface px-2 py-1 text-sm"
            >
              {modelos.map((modelo) => (
                <option key={modelo.id} value={modelo.id}>
                  {modelo.nome || modelo.id}
                </option>
              ))}
            </select>
          </div>
        </div>

        <button
          type="button"
          onClick={executar}
          disabled={processando || texto.trim() === ''}
          className="rounded bg-brand-500 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
        >
          {processando ? 'Humanizando…' : 'Humanizar'}
        </button>
      </fieldset>

      {erro && (
        <p role="alert" className="rounded border border-danger/30 bg-danger/10 p-3 text-sm text-danger">
          {erro}
        </p>
      )}

      {respostaHumanizacao && <ResultadoHumanizacao resposta={respostaHumanizacao} />}
    </section>
  );
}

function ResultadoHumanizacao({ resposta }: { resposta: RespostaHumanizacao }) {
  const { analise, estilo, validacao, uso } = resposta;

  return (
    <div className="space-y-6">
      <section aria-labelledby="titulo-resultado-humanizacao">
        <h3 id="titulo-resultado-humanizacao" className="mb-2 text-sm font-medium">
          Resultado
        </h3>
        {resposta.bloqueado && (
          <p role="alert" className="mb-2 rounded border border-danger/30 bg-danger/10 p-3 text-sm text-danger">
            Aprovação bloqueada: foram detectadas perdas ou alterações de dados protegidos.
            Revise o texto antes de prosseguir.
          </p>
        )}
        <div className="max-h-80 overflow-auto whitespace-pre-wrap rounded border border-surface-border bg-surface p-3 font-mono text-sm">
          {resposta.texto}
        </div>
        <div className="mt-2 flex flex-wrap gap-3 text-sm text-gray-600">
          {uso && (
            <span>
              Tokens: <strong>{uso.total_tokens.toLocaleString('pt-BR')}</strong> · custo
              estimado: <strong>US$ {uso.custo_estimado_usd.toFixed(4)}</strong>
            </span>
          )}
          <Link to="/editor" className="text-brand-700 underline">
            Revisar no editor comparativo
          </Link>
        </div>
      </section>

      <section aria-labelledby="titulo-validacao-semantica">
        <h3 id="titulo-validacao-semantica" className="mb-2 text-sm font-medium">
          Validação semântica
        </h3>
        <dl className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <ItemMetrica rotulo="Entidades antes" valor={validacao.entidades_antes} />
          <ItemMetrica rotulo="Entidades depois" valor={validacao.entidades_depois} />
          <ItemMetrica rotulo="Perdas" valor={validacao.perdas} alerta={validacao.perdas > 0} />
          <ItemMetrica rotulo="Alterações" valor={validacao.alteracoes} alerta={validacao.alteracoes > 0} />
        </dl>
        {validacao.achados.length > 0 && (
          <ul className="mt-2 space-y-2">
            {validacao.achados.map((achado, indice) => (
              <li
                key={indice}
                className="rounded border border-surface-border bg-surface p-3 text-sm"
              >
                <span className={`font-medium ${classeSeveridade(achado.severidade)}`}>
                  {rotuloSeveridade(achado.severidade)}
                </span>
                <span className="ml-2 text-gray-700">{achado.mensagem}</span>
                {achado.acao_sugerida && (
                  <span className="block text-xs text-gray-500">{achado.acao_sugerida}</span>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-labelledby="titulo-analise-estilo">
        <h3 id="titulo-analise-estilo" className="mb-2 text-sm font-medium">
          Análise e estilo
        </h3>
        <div className="grid grid-cols-1 gap-2 text-sm sm:grid-cols-2">
          <span>
            Formalidade estimada: <strong>{Math.round(estilo.formalidade * 100)}%</strong>
          </span>
          <span>
            Vocabulário: <strong>{estilo.vocabulario}</strong>
          </span>
          <span>
            Média de palavras por frase: <strong>{estilo.comprimento_medio_frase}</strong>
          </span>
          <span>
            Coesão: <strong>{analise.coesao}</strong>
          </span>
        </div>
        {analise.repeticoes.length > 0 && (
          <p className="mt-2 text-xs text-gray-600">
            Palavras repetidas: {analise.repeticoes.join(', ')}
          </p>
        )}
      </section>
    </div>
  );
}

function ItemMetrica({
  rotulo,
  valor,
  alerta = false,
}: {
  rotulo: string;
  valor: number;
  alerta?: boolean;
}) {
  return (
    <div className="rounded border border-surface-border bg-surface p-2">
      <dt className="text-xs text-gray-500">{rotulo}</dt>
      <dd className={`text-lg font-semibold ${alerta ? 'text-danger' : ''}`}>{valor}</dd>
    </div>
  );
}
