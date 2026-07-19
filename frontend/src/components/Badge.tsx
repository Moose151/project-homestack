import type { ReactNode } from 'react'

export type BadgeTone = 'neutral' | 'primary' | 'success' | 'warning' | 'danger'

const toneClass: Record<BadgeTone, string> = {
  neutral: 'bg-sunken text-muted-strong',
  primary: 'bg-primary-soft text-primary',
  success: 'bg-success-soft text-success',
  warning: 'bg-warning-soft text-warning',
  danger: 'bg-danger-soft text-danger',
}

/** Small status pill. `tone` maps to a semantic colour so status is never colour-only (a11y §11). */
export function Badge({
  tone = 'neutral',
  children,
  className = '',
}: {
  tone?: BadgeTone
  children: ReactNode
  className?: string
}) {
  return (
    <span
      className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-semibold ${toneClass[tone]} ${className}`}
    >
      {children}
    </span>
  )
}
