import type { ReactNode } from 'react'

interface Props {
  title?: string
  children: ReactNode
  className?: string
}

export function Card({ title, children, className = '' }: Props) {
  return (
    <div className={`bg-surface rounded-2xl shadow-soft border border-line ${className}`}>
      {title && (
        <div className="px-5 pt-4 pb-2">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-muted">{title}</h3>
        </div>
      )}
      <div className="p-5 pt-3">{children}</div>
    </div>
  )
}
