import { useDarkMode } from '../../../hooks/useDarkMode'

export function KioskThemeToggle() {
  const [dark, setDark] = useDarkMode()

  return (
    <button
      type="button"
      onClick={(e) => {
        e.stopPropagation()
        setDark(!dark)
      }}
      className="min-h-11 rounded-lg border border-line bg-surface/70 px-3 text-xl shadow-soft transition-colors hover:bg-primary-soft focus:outline-none focus:ring-2 focus:ring-primary/30"
      aria-label={dark ? 'Use light mode' : 'Use dark mode'}
      title={dark ? 'Use light mode' : 'Use dark mode'}
    >
      {dark ? '☀' : '☾'}
    </button>
  )
}
