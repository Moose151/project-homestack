import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

/**
 * Label + description/value + switch-or-chevron row for settings directories (docs/36 §5,
 * §6.14, §6.15 — "Manage HomeStack" and "Notifications" both move to this shape). Two mutually
 * exclusive modes: pass `checked`/`onToggle` for an immediate-save switch row, or `to`/`onClick`
 * for a row that navigates to a deeper settings subpage. docs/36 §7.4: simple switches save
 * immediately — this component has no Save button, the toggle *is* the save.
 */
export function MobileSettingsRow({
  label,
  description,
  value,
  checked,
  onToggle,
  to,
  onClick,
  disabled = false,
  className = '',
}: {
  label: ReactNode
  description?: ReactNode
  /** A short trailing value shown on a navigable row, e.g. "10pm-7am". */
  value?: ReactNode
  checked?: boolean
  onToggle?: (next: boolean) => void
  to?: string
  onClick?: () => void
  disabled?: boolean
  className?: string
}) {
  const isSwitch = onToggle !== undefined
  const isNav = Boolean(to || onClick)

  const inner = (
    <>
      <div className="min-w-0 flex-1">
        <div className="text-[15px] font-semibold text-ink">{label}</div>
        {description && <div className="mt-0.5 text-sm text-muted">{description}</div>}
      </div>
      {isSwitch ? (
        <Switch checked={Boolean(checked)} onChange={onToggle} label={typeof label === 'string' ? label : 'Toggle'} disabled={disabled} />
      ) : (
        <div className="flex flex-shrink-0 items-center gap-1.5 text-sm text-muted-strong">
          {value}
          {isNav && <span className="text-lg text-muted" aria-hidden="true">›</span>}
        </div>
      )}
    </>
  )

  const rowClass = `flex min-h-[44px] w-full items-center gap-3 rounded-2xl bg-surface px-4 py-3 text-left shadow-soft border border-line ${
    isNav ? 'transition-colors hover:bg-sunken active:scale-[0.99]' : ''
  } ${className}`

  if (to) return <Link to={to} className={rowClass}>{inner}</Link>
  if (onClick) return <button type="button" onClick={onClick} className={rowClass}>{inner}</button>
  return <div className={rowClass}>{inner}</div>
}

function Switch({
  checked, onChange, label, disabled,
}: { checked: boolean; onChange?: (next: boolean) => void; label: string; disabled?: boolean }) {
  // The 44px touch-target baseline applies to the *hit area*, not necessarily the visible
  // control (docs/36 §3.3) — the switch stays a compact 24px-tall pill, centred inside a
  // 44x44 button so the tap target meets the baseline without the switch looking oversized.
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange?.(!checked)}
      className="grid h-11 w-11 flex-shrink-0 place-items-center disabled:opacity-50"
    >
      <span className={`relative h-6 w-11 rounded-full transition-colors ${checked ? 'bg-success' : 'bg-line-strong'}`}>
        <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-all ${checked ? 'left-5' : 'left-0.5'}`} />
      </span>
    </button>
  )
}
