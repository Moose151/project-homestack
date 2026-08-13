import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

export type SummaryTone = 'neutral' | 'attention' | 'success'

const toneClass: Record<SummaryTone, string> = {
  neutral: 'bg-surface border-line',
  attention: 'bg-warning-soft border-warning/30',
  success: 'bg-success-soft border-success/30',
}

/**
 * Compact status/attention overview — the "Needs attention: 2 maintenance jobs, 1 warranty
 * expiring" style banner used across docs/36 §6's node landing screens (Homestead, Pets, Hub).
 * Deliberately just a title + a short list of lines, not a dashboard widget — the goal is one
 * glance, not a report (docs/36 §3.1: "at most a short summary/status block").
 */
export function MobileSummaryCard({
  title,
  lines,
  tone = 'neutral',
  to,
  className = '',
}: {
  title: ReactNode
  lines: ReactNode[]
  tone?: SummaryTone
  to?: string
  className?: string
}) {
  if (lines.length === 0) return null

  const content = (
    <>
      <div className="text-xs font-bold uppercase tracking-wide text-muted-strong">{title}</div>
      <ul className="mt-1.5 flex flex-col gap-1">
        {lines.map((line, i) => (
          <li key={i} className="text-[15px] font-semibold text-ink">{line}</li>
        ))}
      </ul>
    </>
  )

  const cardClass = `block rounded-2xl border px-4 py-3 shadow-soft ${toneClass[tone]} ${
    to ? 'transition-colors hover:bg-sunken active:scale-[0.99]' : ''
  } ${className}`

  if (to) return <Link to={to} className={cardClass}>{content}</Link>
  return <div className={cardClass}>{content}</div>
}
