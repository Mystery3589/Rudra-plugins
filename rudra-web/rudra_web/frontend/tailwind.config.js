/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        canvas: '#07090e',
        surface: '#0c101a',
        'surface-elevated': '#121826',
        'card-bg': 'rgba(16, 23, 38, 0.75)',
        'card-hover': 'rgba(24, 34, 56, 0.9)',
        brand: {
          50: '#eef2ff',
          100: '#e0e7ff',
          400: '#818cf8',
          500: '#6366f1',
          600: '#4f46e5',
        },
        neon: {
          cyan: '#00f0ff',
          green: '#00ff9f',
          purple: '#b5179e',
          amber: '#f59e0b',
          rose: '#f43f5e',
        }
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"Fira Code"', 'monospace'],
      },
      boxShadow: {
        glow: '0 0 25px rgba(99, 102, 241, 0.35)',
        'glow-cyan': '0 0 25px rgba(0, 240, 255, 0.35)',
        'glow-green': '0 0 25px rgba(0, 255, 159, 0.35)',
      }
    },
  },
  plugins: [],
}
