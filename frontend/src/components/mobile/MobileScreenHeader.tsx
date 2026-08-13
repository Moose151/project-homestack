import type { ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'

/**
 * Title/subtitle/actions for a focused mobile subscreen (detail/edit/create) — docs/36_Mobile_
 * UX_Strategy_and_Implementation_Plan.md §5. The app shell (`AppShell.tsx`) is the normal owner
 * of mobile Back/navigation context — it already renders a contextual Back button whenever the
 * route is nested below its stack's base route, with a safe fallback to that base route when
 * there's no in-app history to go back to (cold deep link, PWA launch, a push-notification
 * link). This component does **not** duplicate that by default; it renders as a plain
 * title/subtitle/actions row.
 *
 * Pass `showBack` only for the exceptional case where a screen needs its own Back control in
 * addition to (or narrower than) the shell's — e.g. a multi-step in-page flow the shell's
 * route-level Back doesn't know about. Two Back buttons on one screen is the failure mode this
 * guards against, so treat `showBack` as an explicit, considered opt-in, not a default.
 */
export function MobileScreenHeader({
  title,
  subtitle,
  showBack = false,
  onBack,
  actions,
  className = '',
}: {
  title: ReactNode
  subtitle?: ReactNode
  /** Opt-in: render this screen's own Back control instead of relying on the shell's. */
  showBack?: boolean
  /** Only used when `showBack` is true. A route string always goes to a fixed parent; a
   * function is custom behaviour; omitted falls back to router history (-1). */
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
      {showBack && (
        <button
          onClick={goBack}
          aria-label="Back"
          className="grid h-11 w-11 flex-shrink-0 place-items-center rounded-xl text-xl text-muted transition-colors hover:bg-sunken hover:text-ink"
        >
          ‹
        </button>
      )}
      <div className="min-w-0 flex-1">
        <h1 className="truncate text-lg font-extrabold tracking-tight text-ink">{title}</h1>
        {subtitle && <p className="truncate text-xs text-muted">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-shrink-0 items-center gap-1">{actions}</div>}
    </div>
  )
}
