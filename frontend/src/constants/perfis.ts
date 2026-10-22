/**
 * Catálogo de perfis autorais exibido na interface.
 *
 * Espelha `app/services/humanizer/profiles.py` (os seis perfis fixos mais o
 * perfil autoral personalizado). O backend não expõe uma rota de listagem de
 * perfis, portanto o frontend mantém os rótulos e descrições para a UI; os
 * identificadores precisam casar exatamente com o serviço.
 */

export interface PerfilAutoral {
  id: string;
  nome: string;
  descricao: string;
}

export const PERFIS_AUTORAIS: PerfilAutoral[] = [
  {
    id: 'academico_cientifico',
    nome: 'Acadêmico científico',
    descricao: 'Registro formal, impessoal e técnico, típico de artigos e teses.',
  },
  {
    id: 'academico_acessivel',
    nome: 'Acadêmico acessível',
    descricao: 'Clareza e didática para público amplo, sem perder o rigor.',
  },
  {
    id: 'profissional',
    nome: 'Profissional',
    descricao: 'Tom objetivo e executivo, adequado a relatórios e pareceres.',
  },
  {
    id: 'institucional',
    nome: 'Institucional',
    descricao: 'Formal e impessoal, adequado a documentos oficiais e normativos.',
  },
  {
    id: 'narrativo',
    nome: 'Narrativo',
    descricao: 'Fluxo narrativo e coeso, sem perder a precisão factual.',
  },
  {
    id: 'conversacional',
    nome: 'Conversacional',
    descricao: 'Linguagem próxima e natural, sem jargão.',
  },
  {
    id: 'autoral_personalizado',
    nome: 'Autoral personalizado',
    descricao: 'Estilo derivado exclusivamente dos textos do próprio autor.',
  },
];

export const AUTORAL_ID = 'autoral_personalizado';

export const INTENSIDADES = [0, 25, 50, 75, 100] as const;
