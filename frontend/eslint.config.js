import js from '@eslint/js';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';
import globals from 'globals';
import tseslint from 'typescript-eslint';

export default tseslint.config(
  {
    ignores: ['dist', 'node_modules', 'playwright-report', 'test-results', 'blob-report'],
  },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      ecmaVersion: 2022,
      globals: globals.browser,
    },
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      // A regra de "set-state-in-effect" conflita com padrões legítimos já
      // adotados (debounce da normalização e reajuste de decisões na revisão).
      'react-hooks/set-state-in-effect': 'off',
      // Fast refresh é DX de desenvolvimento, não correção: arquivos de
      // contexto/hooks exportam provedor e hook no mesmo módulo.
      'react-refresh/only-export-components': 'off',
    },
  },
);
