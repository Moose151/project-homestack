import type { ReactNode } from 'react'

interface Props {
  title?: string
  children: ReactNode
  className?: string
  contentClassName?: string
}

export function Card({ title, children, className = '', contentClassName = '' }: Props) {
  return (
    <div className={`bg-surface rounded-2xl shadow-soft border border-line ${className}`}>
      {title && (
        <div className="px-4 pt-4 pb-2 sm:px-5">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-muted">{title}</h3>
        </div>
      )}
      <div className={contentClassName || 'p-4 pt-3 sm:p-5 sm:pt-3'}>{children}</div>
    </div>
  )
}
