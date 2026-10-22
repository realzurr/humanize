/**
 * Estado compartilhado do documento entre as telas do pipeline.
 *
 * A Onda 7 não introduz persistência multiusuário (isso pertence à Onda 8):
 * o documento vive em memória no cliente enquanto o usuário percorre as
 * etapas — colar → normalizar → humanizar → comparar → template → exportar.
 */

import { createContext, useCallback, useContext, useMemo, useState } from 'react';

import type { ReactNode } from 'react';

import type { RelatorioNormalizacao, RespostaHumanizacao } from '@/types';

interface EstadoDocumento {
  textoOriginal: string;
  textoNormalizado: string;
  textoHumanizado: string;
  textoFinal: string;
  relatorioNormalizacao: RelatorioNormalizacao | null;
  respostaHumanizacao: RespostaHumanizacao | null;
  templateId: string;
  provedorId: string;
  modeloId: string;
}

interface AcoesDocumento {
  definirOriginal: (texto: string) => void;
  definirNormalizacao: (relatorio: RelatorioNormalizacao) => void;
  definirHumanizacao: (resposta: RespostaHumanizacao) => void;
  definirTextoFinal: (texto: string) => void;
  definirTemplate: (id: string) => void;
  definirProvedor: (id: string) => void;
  definirModelo: (id: string) => void;
  limpar: () => void;
}

const ESTADO_INICIAL: EstadoDocumento = {
  textoOriginal: '',
  textoNormalizado: '',
  textoHumanizado: '',
  textoFinal: '',
  relatorioNormalizacao: null,
  respostaHumanizacao: null,
  templateId: 'abnt.tcc',
  provedorId: 'openai',
  modeloId: '',
};

const DocumentoContexto = createContext<EstadoDocumento & AcoesDocumento | null>(null);

export function DocumentoProvider({ children }: { children: ReactNode }) {
  const [estado, setEstado] = useState<EstadoDocumento>(ESTADO_INICIAL);

  const definirOriginal = useCallback((texto: string) => {
    setEstado((atual) => ({
      ...atual,
      textoOriginal: texto,
      textoFinal: texto,
      textoNormalizado: '',
      textoHumanizado: '',
      relatorioNormalizacao: null,
      respostaHumanizacao: null,
    }));
  }, []);

  const definirNormalizacao = useCallback((relatorio: RelatorioNormalizacao) => {
    setEstado((atual) => ({
      ...atual,
      textoNormalizado: relatorio.texto,
      textoHumanizado: '',
      respostaHumanizacao: null,
      relatorioNormalizacao: relatorio,
    }));
  }, []);

  const definirHumanizacao = useCallback((resposta: RespostaHumanizacao) => {
    setEstado((atual) => ({
      ...atual,
      textoHumanizado: resposta.texto,
      respostaHumanizacao: resposta,
    }));
  }, []);

  const definirTextoFinal = useCallback((texto: string) => {
    setEstado((atual) => ({ ...atual, textoFinal: texto }));
  }, []);

  const definirTemplate = useCallback((id: string) => {
    setEstado((atual) => ({ ...atual, templateId: id }));
  }, []);

  const definirProvedor = useCallback((id: string) => {
    setEstado((atual) => ({ ...atual, provedorId: id }));
  }, []);

  const definirModelo = useCallback((id: string) => {
    setEstado((atual) => ({ ...atual, modeloId: id }));
  }, []);

  const limpar = useCallback(() => setEstado(ESTADO_INICIAL), []);

  const valor = useMemo<EstadoDocumento & AcoesDocumento>(
    () => ({
      ...estado,
      definirOriginal,
      definirNormalizacao,
      definirHumanizacao,
      definirTextoFinal,
      definirTemplate,
      definirProvedor,
      definirModelo,
      limpar,
    }),
    [estado, definirOriginal, definirNormalizacao, definirHumanizacao, definirTextoFinal, definirTemplate, definirProvedor, definirModelo, limpar],
  );

  return <DocumentoContexto.Provider value={valor}>{children}</DocumentoContexto.Provider>;
}

export function useDocumento(): EstadoDocumento & AcoesDocumento {
  const contexto = useContext(DocumentoContexto);
  if (!contexto) {
    throw new Error('useDocumento deve ser usado dentro de um DocumentoProvider');
  }
  return contexto;
}
