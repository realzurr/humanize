import { useEffect, useState } from 'react';

import { api } from '@/services/api';
import type { RespostaSaude } from '@/types';

interface Estado {
  dados: RespostaSaude | null;
  carregando: boolean;
  erro: string | null;
}

/** Verifica a disponibilidade da API. */
export function useSaude(): Estado {
  const [estado, setEstado] = useState<Estado>({
    dados: null,
    carregando: true,
    erro: null,
  });

  useEffect(() => {
    let ativo = true;

    api
      .health()
      .then((dados) => {
        if (ativo) setEstado({ dados, carregando: false, erro: null });
      })
      .catch((erro: unknown) => {
        if (ativo) {
          setEstado({
            dados: null,
            carregando: false,
            erro: erro instanceof Error ? erro.message : 'Falha desconhecida',
          });
        }
      });

    return () => {
      ativo = false;
    };
  }, []);

  return estado;
}
