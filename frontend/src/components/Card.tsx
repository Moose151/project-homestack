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
          {/* Sentence case: a card title is a heading, not a micro-label. ALL-CAPS is reserved
              for the small field/section labels, so the two stopped reading as the same thing. */}
          <h3 className="text-sm font-bold text-ink">{title}</h3>
        </div>
      )}
      <div className={contentClassName || 'p-4 pt-3 sm:p-5 sm:pt-3'}>{children}</div>
    </div>
  )
}
