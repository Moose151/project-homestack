import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

/**
 * Large whole-row navigation/action target (docs/36 §5): leading icon/avatar, primary text,
 * secondary metadata, trailing value/status/chevron. This is the base unit of the index/list
 * screens throughout docs/36 §6 ("Rooms & areas", "Assignments", "Treatments", etc) — reuse this
 * rather than each node inventing its own row markup.
 *
 * Renders a `<Link>` when `to` is given, a `<button>` when `onClick` is given, or a plain `<div>`
 * for a non-interactive row (e.g. a read-only summary line).
 */
export function MobileListRow({
  icon,
  title,
  subtitle,
  trailing,
  to,
  onClick,
  chevron,
  compact = false,
  className = '',
}: {
  icon?: ReactNode
  title: ReactNode
  subtitle?: ReactNode
  trailing?: ReactNode
  to?: string
  onClick?: () => void
  /** Defaults to true whenever the row is interactive (to/onClick given). */
  chevron?: boolean
  /** Real content — an assignment, a maintenance job, a book title — rarely fits one line
   * without losing the information that made it worth reading. Title/subtitle wrap to ~2 lines
   * by default; pass `compact` for rows that genuinely need one line (a dense settings list, a
   * short fixed-format value) rather than truncating everywhere out of habit. */
  compact?: boolean
  className?: string
}) {
  const interactive = Boolean(to || onClick)
  const showChevron = chevron ?? interactive
  const textClamp = compact ? 'truncate' : 'line-clamp-2'

  const content = (
    <>
      {icon && (
        <span className="grid h-11 w-11 flex-shrink-0 place-items-center rounded-xl bg-sunken text-xl leading-none">
          {icon}
        </span>
      )}
      <div className="min-w-0 flex-1">
        <div className={`${textClamp} text-[15px] font-semibold text-ink`}>{title}</div>
        {subtitle && <div className={`${textClamp} text-sm text-muted`}>{subtitle}</div>}
      </div>
      {trailing && <div className="flex-shrink-0 text-sm text-muted-strong">{trailing}</div>}
      {showChevron && <span className="flex-shrink-0 text-lg text-muted" aria-hidden="true">›</span>}
    </>
  )

  const rowClass = `flex min-h-[44px] w-full items-center gap-3 rounded-2xl bg-surface px-3 py-2.5 text-left shadow-soft border border-line ${
    interactive ? 'transition-colors hover:bg-sunken active:scale-[0.99]' : ''
  } ${className}`

  if (to) {
    return (
      <Link to={to} className={rowClass}>
        {content}
      </Link>
    )
  }

  if (onClick) {
    return (
      <button type="button" onClick={onClick} className={rowClass}>
        {content}
      </button>
    )
  }

  return <div className={rowClass}>{content}</div>
}
