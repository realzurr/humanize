import { defineConfig, devices } from '@playwright/test';

/**
 * Configuração do Playwright para os testes E2E da Onda 7.
 *
 * O fluxo principal é exercitado contra o servidor de desenvolvimento do
 * Vite, com as respostas da API interceptadas via `page.route` — nenhuma
 * chamada real a provedores de LLM é feita e nenhum segredo é persistido.
 */
export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: 'http://127.0.0.1:5173',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: 'npm run dev -- --port 5173 --strictPort',
    url: 'http://127.0.0.1:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
