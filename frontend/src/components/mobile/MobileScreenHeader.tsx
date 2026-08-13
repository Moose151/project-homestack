import type { ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'

/**
 * Header for a focused mobile subscreen (detail/edit/create) — docs/36_Mobile_UX_Strategy_and_
 * Implementation_Plan.md §5. Distinct from the app shell's own top bar: this is content the
 * *page* renders when it needs its own Back control and title, e.g. a record detail screen
 * reached by drilling into a list. `onBack` defaults to browser/router history (-1) so Back
 * returns to whatever the user actually came from, matching §7.1's "Back returns to a
 * meaningful previous context."
 */
export function MobileScreenHeader({
  title,
  subtitle,
  onBack,
  actions,
  className = '',
}: {
  title: ReactNode
  subtitle?: ReactNode
  /** Pass a route string to always go to a fixed parent, or a function for custom behaviour.
   * Omit to fall back to history back. */
  onBack?: string | (() => void)
  actions?: ReactNode
  className?: string
}) {
  const navigate = useNavigate()

  const goBack = () => {
    if (typeof onBack === 'function') { onBack(); return }
    if (typeof onBack === 'string') { navigate(onBack); return }
    navigate(-1)
  }

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <button
        onClick={goBack}
        aria-label="Back"
        className="grid h-11 w-11 flex-shrink-0 place-items-center rounded-xl text-xl text-muted transition-colors hover:bg-sunken hover:text-ink"
      >
        ‹
      </button>
      <div className="min-w-0 flex-1">
        <h1 className="truncate text-lg font-extrabold tracking-tight text-ink">{title}</h1>
        {subtitle && <p className="truncate text-xs text-muted">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-shrink-0 items-center gap-1">{actions}</div>}
    </div>
  )
}
