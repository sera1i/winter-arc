/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './templates/**/*.html',
    './**/templates/**/*.html',
  ],
  theme: {
    extend: {
      colors: {
        ink: {
          DEFAULT: '#05070a',
          deep: '#030407',
          surface: '#0b0e14',
          card: '#0f141c',
          border: 'rgba(223,231,224,0.08)',
          hover: '#161c26',
        },
        bone: {
          DEFAULT: '#f4f1ec',
          dim: '#dfe7e0',
          muted: '#94a3b8',
        },
        vermilion: {
          DEFAULT: '#e0231c',
          dark: '#b81b15',
          glow: 'rgba(224,35,28,0.35)',
        },
        ember: '#ff5a3c',
        gold: '#c9a24a',
        ice: '#60a5fa',
      },
      fontFamily: {
        sans: ['Onest', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      boxShadow: {
        'glow-vermilion': '0 0 25px rgba(224, 35, 28, 0.45)',
        'glow-subtle': '0 0 15px rgba(223, 231, 224, 0.05)',
        'card-elevated': '0 8px 32px rgba(0, 0, 0, 0.6)',
      },
      borderRadius: {
        'xl': '12px',
        '2xl': '16px',
        '3xl': '24px',
      }
    },
  },
  plugins: [],
}
