/**
 * Editor comparativo lado a lado com aceitação/rejeição por trecho.
 *
 * Recurso central da Onda 7: destaca as alterações entre o texto original e o
 * proposto, permite aceitar ou rejeitar cada sugestão individualmente,
 * restaurar o original e compor o texto final para exportação.
 */

import { useEffect, useMemo, useState } from 'react';

import { comporTexto, estruturarRevisao } from '@/utils/revisao';

interface Props {
  antes: string;
  depois: string;
  onTextoFinalChange?: (texto: string) => void;
}

export function RevisorDiff({ antes, depois, onTextoFinalChange }: Props) {
  const estrutura = useMemo(() => estruturarRevisao(antes, depois), [antes, depois]);

  const [decisoes, setDecisoes] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(estrutura.grupos.map((grupo) => [grupo.id, true])),
  );

  useEffect(() => {
    setDecisoes(Object.fromEntries(estrutura.grupos.map((grupo) => [grupo.id, true])));
  }, [estrutura]);

  const textoFinal = useMemo(
    () => comporTexto(estrutura.partes, decisoes),
    [estrutura, decisoes],
  );

  useEffect(() => {
    onTextoFinalChange?.(textoFinal);
  }, [textoFinal, onTextoFinalChange]);

  const aceitas = estrutura.grupos.filter((grupo) => decisoes[grupo.id] !== false).length;

  function aplicarTodas(aceitar: boolean) {
    setDecisoes(Object.fromEntries(estrutura.grupos.map((grupo) => [grupo.id, aceitar])));
  }

  function alternarGrupo(id: string) {
    setDecisoes((atuais) => ({ ...atuais, [id]: atuais[id] === false }));
  }

  return (
    <section aria-label="Comparação de versões" className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2 rounded border border-surface-border bg-surface p-2">
        <div className="text-sm text-gray-700">
          {estrutura.grupos.length === 0 ? (
            <span>Nenhuma alteração entre as versões.</span>
          ) : (
            <span>
              <strong>{estrutura.grupos.length}</strong> alterações ·{' '}
              <strong>{aceitas}</strong> aceitas
            </span>
          )}
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => aplicarTodas(true)}
            className="rounded border border-surface-border px-2 py-1 text-xs hover:bg-surface-muted"
          >
            Aceitar todas
          </button>
          <button
            type="button"
            onClick={() => aplicarTodas(false)}
            className="rounded border border-surface-border px-2 py-1 text-xs hover:bg-surface-muted"
          >
            Rejeitar todas
          </button>
          <button
            type="button"
            onClick={() => aplicarTodas(false)}
            className="rounded border border-danger/30 px-2 py-1 text-xs text-danger hover:bg-danger/10"
          >
            Restaurar original
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div>
          <span className="mb-1 block text-sm font-medium">Original</span>
          <div className="max-h-[28rem] overflow-auto whitespace-pre-wrap rounded border border-surface-border bg-surface p-3 font-mono text-sm">
            {estrutura.partes.map((parte, indice) =>
              parte.tipo === 'igual' ? (
                <span key={indice}>{parte.texto}</span>
              ) : (
                <mark key={indice} className="bg-danger/10 text-danger line-through">
                  {parte.antes}
                </mark>
              ),
            )}
          </div>
        </div>

        <div>
          <span className="mb-1 block text-sm font-medium">
            Texto final (clique num trecho para aceitar/rejeitar)
          </span>
          <div className="max-h-[28rem] overflow-auto whitespace-pre-wrap rounded border border-surface-border bg-surface p-3 font-mono text-sm">
            {estrutura.partes.map((parte, indice) =>
              parte.tipo === 'igual' ? (
                <span key={indice}>{parte.texto}</span>
              ) : (
                <button
                  key={indice}
                  type="button"
                  onClick={() => alternarGrupo(parte.id)}
                  aria-pressed={decisoes[parte.id] !== false}
                  aria-label={
                    decisoes[parte.id] === false
                      ? `Sugestão rejeitada: ${parte.antes}`
                      : `Sugestão aceita: ${parte.depois}`
                  }
                  className={
                    decisoes[parte.id] === false
                      ? 'bg-danger/10 text-danger line-through'
                      : 'bg-brand-50 text-brand-900'
                  }
                >
                  {decisoes[parte.id] === false ? parte.antes : parte.depois}
                </button>
              ),
            )}
          </div>
        </div>
      </div>

      <button
        type="button"
        onClick={() => onTextoFinalChange?.(textoFinal)}
        className="rounded border border-surface-border px-3 py-1.5 text-sm hover:bg-surface-muted"
      >
        Usar texto final
      </button>
    </section>
  );
}
