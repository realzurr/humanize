import { expect, test } from '@playwright/test';

import type { Page } from '@playwright/test';

/**
 * Fluxo principal da Onda 7: colar → normalizar → selecionar provedor →
 * humanizar → comparar → template → exportar.
 *
 * As respostas da API são interceptadas via `page.route` — nenhuma chamada
 * real a provedores de LLM é feita e nenhum segredo é persistido.
 */

const TEXTO_ORIGINAL = 'O  valor  foi  de 45,5 % conforme Silva (2020).';
const TEXTO_HUMANIZADO = 'O valor foi de 45,5% conforme Silva (2020), conforme apontado.';

async function mockApi(page: Page) {
  await page.route('**/api/v1/**', async (route) => {
    const url = new URL(route.request().url());
    const metodo = route.request().method();
    const caminho = url.pathname;

    if (metodo === 'GET' && caminho.endsWith('/health')) {
      await route.fulfill({ json: { status: 'ok', app: 'humaniza', version: '0.1.0', environment: 'test' } });
      return;
    }

    if (metodo === 'POST' && caminho.endsWith('/normalize')) {
      const corpo = route.request().postDataJSON() as { texto: string };
      await route.fulfill({
        json: {
          texto: corpo.texto,
          transformacoes: [
            { stage: 'normalize', rule_id: 'norm.whitespace.collapse', description: 'Espaços repetidos', category: 'espaços', count: 2, severity: 'info' },
          ],
          total_caracteres_antes: corpo.texto.length,
          total_caracteres_depois: corpo.texto.length,
          entidades_protegidas: [],
          regras_desativadas: [],
          avisos: [],
        },
      });
      return;
    }

    if (metodo === 'GET' && caminho.endsWith('/providers')) {
      await route.fulfill({
        json: [
          { id: 'openai', nome: 'OpenAI', requer_chave: true, configurado: true, last4: 'abcd', fonte: 'session' },
          { id: 'ollama', nome: 'Ollama', requer_chave: false, configurado: false, last4: '', fonte: '' },
        ],
      });
      return;
    }

    if (metodo === 'GET' && caminho.endsWith('/models')) {
      await route.fulfill({
        json: [{ id: 'gpt-4o', nome: 'GPT-4o', janela_contexto: 128000, max_tokens_saida: 16384, suporta_streaming: true, suporta_json: true, custo_entrada_1k: 0.0025, custo_saida_1k: 0.01, obsoleto: false }],
      });
      return;
    }

    if (metodo === 'POST' && caminho.endsWith('/humanize')) {
      await route.fulfill({
        json: {
          texto: TEXTO_HUMANIZADO,
          perfil: 'academico_cientifico',
          intensidade: 50,
          modelo: 'gpt-4o',
          provedor: 'openai',
          bloqueado: false,
          analise: { repeticoes: [], frases_padronizadas: [], transicoes_artificiais: [], coesao: 'boa', vaguidade: [], redundancia: [], voz_passiva: [], excesso_conectivos: [] },
          estilo: { formalidade: 0.8, vocabulario: 'formal', comprimento_medio_frase: 12, construcao_argumentativa: 'simples', conectivos_recorrentes: [], terminologia: [], organizacao_paragrafos: 'simples', ritmo: 'regular' },
          validacao: { achados: [], entidades_antes: 1, entidades_depois: 1, perdas: 0, alteracoes: 0, invencoes: 0, bloqueado: false },
          uso: { prompt_tokens: 12, completion_tokens: 20, total_tokens: 32, custo_estimado_usd: 0.0003 },
        },
      });
      return;
    }

    if (metodo === 'GET' && caminho.endsWith('/templates')) {
      await route.fulfill({
        json: [
          { id: 'abnt.tcc', kind: 'tcc', title: 'TCC Geral', version: '1.0.0', extends: null, institution: null, fontes: 1 },
          { id: 'abnt.articles', kind: 'article', title: 'Artigo', version: '1.0.0', extends: null, institution: null, fontes: 1 },
        ],
      });
      return;
    }

    if (metodo === 'GET' && caminho.endsWith('/resolve')) {
      await route.fulfill({ json: { template: { id: 'abnt.tcc' }, conflicts: [], overrides: [] } });
      return;
    }

    if (metodo === 'POST' && caminho.endsWith('/exports')) {
      await route.fulfill({
        json: {
          document_id: 'doc-local',
          revision_id: 'rev_test',
          template_id: 'abnt.tcc',
          instituicao: null,
          pdf_available: false,
          exports: [
            { id: 'exp_test', document_id: 'doc-local', revision_id: 'rev_test', version_number: 1, format: 'docx', filename: 'doc_v1_exp_test.docx', sha256: 'abc', size_bytes: 1024, template_id: 'abnt.tcc', institution_id: null, created_at: new Date().toISOString(), warnings: [], limitations: ['PDF indisponível neste ambiente'], docx_inspection: null, pdf_comparison: null },
          ],
          preview: {
            document_id: 'doc-local', title: 'Documento sem título', template_id: 'abnt.tcc', font: 'Times New Roman', font_size_pt: 12, line_spacing: 1.5, margins_anverso_cm: { top: 3, bottom: 2, left: 3, right: 2 }, margins_verso_cm: { top: 3, bottom: 2, left: 2, right: 3 }, toc_entries: [], blocks: [], revision_count: 1, current_revision_id: 'rev_test',
          },
          warnings: [],
          limitations: ['PDF indisponível neste ambiente'],
        },
      });
      return;
    }

    if (metodo === 'GET' && caminho.endsWith('/exports')) {
      await route.fulfill({ json: [] });
      return;
    }

    await route.fulfill({ status: 404, json: { error: { message: 'rota não mockada' } } });
  });
}

test('fluxo completo sem segredos no navegador', async ({ page }) => {
  await mockApi(page);

  const navegacao = page.getByRole('navigation', { name: 'Navegação principal' });

  await page.goto('/');

  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();

  await navegacao.getByRole('link', { name: 'Normalização' }).click();
  await page.locator('#entrada').fill(TEXTO_ORIGINAL);
  await expect(page.getByText('Estatísticas por regra')).toBeVisible();

  await navegacao.getByRole('link', { name: 'Humanização' }).click();
  await page.locator('#texto-humanizar').fill(TEXTO_ORIGINAL);
  await page.getByRole('button', { name: 'Humanizar' }).click();
  await expect(page.getByText('Resultado')).toBeVisible();
  await expect(page.getByText(TEXTO_HUMANIZADO)).toBeVisible();

  await navegacao.getByRole('link', { name: 'Comparação' }).click();
  await expect(page.getByRole('heading', { name: 'Comparação de versões' })).toBeVisible();

  await navegacao.getByRole('link', { name: 'Templates ABNT' }).click();
  await expect(page.getByRole('heading', { name: 'Templates ABNT' })).toBeVisible();
  await page.getByRole('button', { name: /TCC Geral/ }).click();

  await navegacao.getByRole('link', { name: 'Exportação' }).click();
  await page.getByRole('button', { name: 'Exportar' }).click();
  await expect(page.getByText('Resultado da exportação')).toBeVisible();

  const segredosNoArmazenamento = await page.evaluate(() => {
    const chaves = [...Object.keys(localStorage), ...Object.keys(sessionStorage)];
    return chaves.some((chave) => /api[_ -]?key|secret|token|credencial/i.test(chave));
  });
  expect(segredosNoArmazenamento).toBe(false);
});
