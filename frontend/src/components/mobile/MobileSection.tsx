import type { ReactNode } from 'react'

/**
 * Consistent section spacing/heading for mobile landing screens (docs/36 §5) — the "Your home",
 * "Coming up", "Rooms & areas" style groupings used throughout the page-by-page redesign in
 * docs/36 §6. Deliberately plain: a label row plus an optional trailing action, and whatever
 * content (usually a stack of MobileListRow) below it.
 */
export function MobileSection({
  title,
  action,
  children,
  className = '',
}: {
  title?: ReactNode
  action?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <section className={`flex flex-col gap-2 ${className}`}>
      {(title || action) && (
        <div className="flex items-center justify-between gap-2 px-1">
          {title && <h2 className="text-xs font-bold uppercase tracking-wide text-muted">{title}</h2>}
          {action && <div className="text-xs font-semibold text-primary">{action}</div>}
        </div>
      )}
      <div className="flex flex-col gap-2">{children}</div>
    </section>
  )
}
