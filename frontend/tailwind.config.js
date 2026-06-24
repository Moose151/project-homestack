/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['system-ui', 'sans-serif'],
      },
      // Semantic HomeStack palette — backed by CSS variables in index.css so
      // light/dark switch centrally. Shared by every node (UI/UX §5).
      colors: {
        paper: 'var(--hs-bg)',
        'paper-soft': 'var(--hs-bg-soft)',
        surface: 'var(--hs-surface)',
        raised: 'var(--hs-surface-raised)',
        sunken: 'var(--hs-surface-muted)',
        line: 'var(--hs-border)',
        'line-strong': 'var(--hs-border-strong)',
        ink: 'var(--hs-text)',
        muted: 'var(--hs-muted)',
        'muted-strong': 'var(--hs-muted-strong)',
        primary: {
          DEFAULT: 'var(--hs-primary)',
          hover: 'var(--hs-primary-hover)',
          soft: 'var(--hs-primary-soft)',
        },
        success: {
          DEFAULT: 'var(--hs-success)',
          soft: 'var(--hs-success-soft)',
        },
        warning: {
          DEFAULT: 'var(--hs-warning)',
          soft: 'var(--hs-warning-soft)',
        },
        danger: {
          DEFAULT: 'var(--hs-danger)',
          soft: 'var(--hs-danger-soft)',
        },
      },
      borderRadius: {
        xl: '1rem',
        '2xl': '1.25rem',
      },
      boxShadow: {
        soft: '0 0.4rem 1.25rem rgba(83, 67, 45, 0.06)',
        card: '0 0.7rem 2rem rgba(83, 67, 45, 0.08)',
      },
    },
  },
  plugins: [],
}
