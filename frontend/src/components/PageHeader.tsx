import type { ReactNode } from 'react'

/** Consistent page title + optional subtitle + right-aligned actions, used by every node page. */
export function PageHeader({
  title,
  subtitle,
  icon,
  actions,
  className = '',
  mobile = 'hide',
}: {
  title: ReactNode
  subtitle?: ReactNode
  icon?: ReactNode
  actions?: ReactNode
  className?: string
  /** The mobile shell already names the destination. Show only when the page adds useful context. */
  mobile?: 'hide' | 'show'
}) {
  return (
    <div className={`${mobile === 'show' ? 'flex' : 'hidden sm:flex'} flex-wrap items-center justify-between gap-3 border-b border-line/70 pb-4 sm:pb-5 ${className}`}>
      <div className="flex min-w-0 items-center gap-3 sm:gap-3.5">
        {icon && <span className="grid h-11 w-11 flex-shrink-0 place-items-center rounded-2xl border border-line bg-surface text-xl leading-none shadow-soft sm:h-12 sm:w-12 sm:text-2xl">{icon}</span>}
        <div className="min-w-0">
          <h1 className="truncate text-xl font-black tracking-tight text-ink sm:text-[1.65rem]">{title}</h1>
          {subtitle && <p className="mt-0.5 line-clamp-2 text-xs leading-relaxed text-muted sm:text-sm">{subtitle}</p>}
        </div>
      </div>
      {actions && <div className="ml-auto flex max-w-full flex-shrink-0 items-center gap-2 overflow-x-auto">{actions}</div>}
    </div>
  )
}
