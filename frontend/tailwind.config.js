/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        display: ['Syne', 'sans-serif'],
        heading: ['Space Grotesk', 'sans-serif'],
        sans: ['Plus Jakarta Sans', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      letterSpacing: {
        tighter: '-0.06em',
        tight: '-0.04em',
        editorial: '-0.02em',
        widest: '0.2em',
      },
      colors: {
        dark: {
          950: '#05070a',
          900: '#090d14',
          850: '#0d131d',
          800: '#131b28',
          700: '#1d283a',
          600: '#2b3a52',
        },
        monochrome: {
          50: '#f8fafc',
          100: '#f1f5f9',
          200: '#e2e8f0',
          300: '#cbd5e1',
          400: '#94a3b8',
          500: '#64748b',
          600: '#475569',
          700: '#334155',
          800: '#1e293b',
          900: '#0f172a',
        },
        accent: {
          cyan: '#38bdf8',
          subtle: 'rgba(56, 189, 248, 0.12)',
          amber: '#fbbf24',
          crimson: '#f43f5e',
        }
      }
    },
  },
  plugins: [],
}
