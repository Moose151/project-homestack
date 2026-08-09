import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

/**
 * One headline number with its label.
 *
 * The app had three arrangements of the same idea — label above the number, number above the
 * label with a badge, and value with a coloured "View" pill — so a summary row read
 * differently on every page (owner, 2026-08-09). This is the single arrangement: label first
 * so the number is read in context, value, then an optional supporting line.
 *
 * Pass `to` or `onClick` to make the whole tile the target rather than adding a button inside
 * it, which is what produced the pill soup on the finance page.
 */
export function StatCard({
  label,
  value,
  hint,
  badge,
  to,
  onClick,
  className = '',
}: {
  label: string
  value: ReactNode
  hint?: ReactNode
  badge?: ReactNode
  to?: string
  onClick?: () => void
  className?: string
}) {
  const body = (
    <>
      <p className="flex items-center justify-between gap-2 text-xs font-bold uppercase tracking-wide text-muted">
        <span className="truncate">{label}</span>
        {badge}
      </p>
      <p className="mt-1.5 text-2xl font-extrabold tracking-tight text-ink">{value}</p>
      {hint && <p className="mt-1 text-xs text-muted">{hint}</p>}
    </>
  )

  const shell = `rounded-2xl border border-line bg-surface p-4 text-left ${
    to || onClick ? 'transition-colors hover:border-primary/40 hover:bg-sunken/40' : ''
  } ${className}`

  if (to) return <Link to={to} className={`block ${shell}`}>{body}</Link>
  if (onClick) return <button type="button" onClick={onClick} className={`w-full ${shell}`}>{body}</button>
  return <div className={shell}>{body}</div>
}

/** A row of stat cards that wraps rather than squeezing on narrow screens. */
export function StatRow({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div className={`grid grid-cols-2 gap-3 lg:grid-cols-4 ${className}`}>{children}</div>
  )
}
