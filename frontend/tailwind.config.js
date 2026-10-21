/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Paleta de alto contraste, compatível com os requisitos de
        // acessibilidade (WCAG AA) validados na Onda 7.
        brand: {
          50: '#eef4ff',
          100: '#d9e5ff',
          500: '#2563eb',
          700: '#1d4ed8',
          900: '#1e3a8a',
        },
        surface: {
          DEFAULT: '#ffffff',
          muted: '#f6f7f9',
          border: '#d8dce3',
        },
        danger: '#b91c1c',
        warning: '#b45309',
        success: '#15803d',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        serif: ['Times New Roman', 'Georgia', 'serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },
    },
  },
  plugins: [],
};
