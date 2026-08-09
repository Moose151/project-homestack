import type { ReactNode } from 'react'
import { useLocation } from 'react-router-dom'
import { STACKS } from '../config/stacks'

/**
 * Page title + optional subtitle + right-aligned actions.
 *
 * On desktop the app shell's top bar already names the destination and describes it, so a
 * page whose title just repeats that name renders its actions only — otherwise every page
 * opened with the same words twice, one above the other (owner, 2026-08-09).
 *
 * A page whose title is genuinely different context — a room name, a greeting, a book club —
 * still shows its heading, because that is information the top bar does not carry.
 */
function duplicatesDestination(title: ReactNode, pathname: string): boolean {
  if (typeof title !== 'string') return false
  const current = STACKS.find(stack => pathname.startsWith(stack.route))
  if (!current) return false
  const name = title.trim().toLowerCase()
  return name === current.navLabel.toLowerCase() || name === current.label.toLowerCase()
}

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
  const { pathname } = useLocation()
  const redundant = duplicatesDestination(title, pathname)

  // Nothing left to render once the heading is redundant and there are no actions.
  if (redundant && !actions) return null

  if (redundant) {
    return (
      <div className={`${mobile === 'show' ? 'flex' : 'hidden sm:flex'} flex-wrap items-center justify-end gap-2 ${className}`}>
        {actions}
      </div>
    )
  }

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
