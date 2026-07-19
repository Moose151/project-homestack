import type { ReactNode } from 'react'

/** Consistent page title + optional subtitle + right-aligned actions, used by every node page. */
export function PageHeader({
  title,
  subtitle,
  icon,
  actions,
  className = '',
}: {
  title: ReactNode
  subtitle?: ReactNode
  icon?: ReactNode
  actions?: ReactNode
  className?: string
}) {
  return (
    <div className={`flex flex-wrap items-start justify-between gap-3 ${className}`}>
      <div className="flex items-center gap-3 min-w-0">
        {icon && <span className="text-2xl leading-none">{icon}</span>}
        <div className="min-w-0">
          <h1 className="truncate text-2xl font-extrabold tracking-tight text-ink">{title}</h1>
          {subtitle && <p className="mt-0.5 text-sm text-muted">{subtitle}</p>}
        </div>
      </div>
      {actions && <div className="flex flex-shrink-0 items-center gap-2">{actions}</div>}
    </div>
  )
}
