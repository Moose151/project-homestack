import { useEffect, useId, useMemo, useRef, useState } from 'react'
import { fieldClass } from './Field'

const pad = (value: number) => String(value).padStart(2, '0')

function normalise(value: string, fallback = '09:00') {
  const match = /^(\d{1,2}):(\d{2})/.exec(value)
  if (!match) return fallback
  const hour = Math.min(23, Math.max(0, Number(match[1])))
  const minute = Math.min(59, Math.max(0, Number(match[2])))
  return `${pad(hour)}:${pad(minute)}`
}

function localeUses12Hours() {
  return new Intl.DateTimeFormat(undefined, { hour: 'numeric' }).resolvedOptions().hour12 === true
}

/**
 * Reusable time-of-day picker. Touch-first devices keep the operating system picker; pointer
 * desktops get visible hour/minute columns. Values stay in the API's existing 24-hour HH:mm
 * shape regardless of how the locale displays them.
 */
export function TimePicker({
  value,
  onChange,
  disabled = false,
  ariaLabel = 'Time',
  id,
  className = '',
}: {
  value: string
  onChange: (value: string) => void
  disabled?: boolean
  ariaLabel?: string
  id?: string
  className?: string
}) {
  const generatedId = useId()
  const panelId = `${id || generatedId}-time-panel`
  const [open, setOpen] = useState(false)
  const [coarsePointer, setCoarsePointer] = useState(() => window.matchMedia('(pointer: coarse)').matches)
  const rootRef = useRef<HTMLDivElement>(null)
  const hourRef = useRef<HTMLSelectElement>(null)
  const hour12 = useMemo(localeUses12Hours, [])
  const selected = normalise(value)
  const [hourText, minuteText] = selected.split(':')
  const hour = Number(hourText)
  const minute = Number(minuteText)
  const period = hour >= 12 ? 'PM' : 'AM'
  const displayHour = hour12 ? (hour % 12 || 12) : hour

  useEffect(() => {
    const query = window.matchMedia('(pointer: coarse)')
    const update = () => setCoarsePointer(query.matches)
    query.addEventListener('change', update)
    return () => query.removeEventListener('change', update)
  }, [])

  useEffect(() => {
    if (!open) return
    const closeOutside = (event: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) setOpen(false)
    }
    const closeEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { event.preventDefault(); setOpen(false) }
    }
    document.addEventListener('mousedown', closeOutside)
    document.addEventListener('keydown', closeEscape)
    const frame = requestAnimationFrame(() => hourRef.current?.focus())
    return () => {
      cancelAnimationFrame(frame)
      document.removeEventListener('mousedown', closeOutside)
      document.removeEventListener('keydown', closeEscape)
    }
  }, [open])

  const emit = (nextHour: number, nextMinute: number) => onChange(`${pad(nextHour)}:${pad(nextMinute)}`)
  const selectDisplayHour = (next: number) => {
    if (!hour12) { emit(next, minute); return }
    const converted = (next % 12) + (period === 'PM' ? 12 : 0)
    emit(converted, minute)
  }
  const selectPeriod = (next: 'AM' | 'PM') => {
    const base = hour % 12
    emit(base + (next === 'PM' ? 12 : 0), minute)
  }
  const displayValue = value
    ? new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' })
      .format(new Date(2000, 0, 1, hour, minute))
    : 'Select time'

  if (coarsePointer) {
    return (
      <input
        id={id}
        type="time"
        className={`${fieldClass} ${className}`}
        value={value}
        onChange={event => onChange(event.target.value)}
        disabled={disabled}
        aria-label={ariaLabel}
      />
    )
  }

  return (
    <div ref={rootRef} className={`relative ${className}`}>
      <button
        id={id}
        type="button"
        disabled={disabled}
        aria-label={ariaLabel}
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen(current => !current)}
        className={`${fieldClass} flex items-center justify-between gap-3 text-left disabled:cursor-not-allowed`}
      >
        <span className={value ? 'text-ink' : 'text-muted'}>{displayValue}</span>
        <span aria-hidden className="text-base text-muted">◷</span>
      </button>
      {open && (
        <div
          id={panelId}
          role="dialog"
          aria-label="Choose a time"
          className="absolute right-0 z-40 mt-2 w-64 rounded-2xl border border-line bg-surface p-3 shadow-card"
        >
          <div className={`grid gap-2 ${hour12 ? 'grid-cols-[1fr_1fr_auto]' : 'grid-cols-2'}`}>
            <label className="text-center text-xs font-bold uppercase tracking-wide text-muted-strong">
              Hour
              <select
                ref={hourRef}
                size={6}
                value={displayHour}
                onChange={event => selectDisplayHour(Number(event.target.value))}
                className="mt-1.5 w-full rounded-xl border border-line bg-sunken p-1 text-center text-sm text-ink outline-none focus:ring-2 focus:ring-primary/30"
                aria-label="Hour"
              >
                {Array.from({ length: hour12 ? 12 : 24 }, (_, index) => hour12 ? index + 1 : index).map(option => (
                  <option key={option} value={option}>{pad(option)}</option>
                ))}
              </select>
            </label>
            <label className="text-center text-xs font-bold uppercase tracking-wide text-muted-strong">
              Minute
              <select
                size={6}
                value={minute}
                onChange={event => emit(hour, Number(event.target.value))}
                className="mt-1.5 w-full rounded-xl border border-line bg-sunken p-1 text-center text-sm text-ink outline-none focus:ring-2 focus:ring-primary/30"
                aria-label="Minute"
              >
                {Array.from({ length: 60 }, (_, option) => (
                  <option key={option} value={option}>{pad(option)}</option>
                ))}
              </select>
            </label>
            {hour12 && (
              <div className="flex flex-col gap-2 pt-5" role="group" aria-label="AM or PM">
                {(['AM', 'PM'] as const).map(option => (
                  <button
                    key={option}
                    type="button"
                    aria-pressed={period === option}
                    onClick={() => selectPeriod(option)}
                    className={`min-h-10 rounded-xl px-2 text-xs font-bold ${period === option ? 'bg-primary text-white' : 'bg-sunken text-muted-strong hover:text-ink'}`}
                  >
                    {option}
                  </button>
                ))}
              </div>
            )}
          </div>
          <div className="mt-3 flex gap-2">
            {value && <button type="button" onClick={() => { onChange(''); setOpen(false) }} className="min-h-10 flex-1 rounded-xl text-sm font-bold text-muted-strong hover:bg-sunken">Clear</button>}
            <button type="button" onClick={() => setOpen(false)} className="min-h-10 flex-1 rounded-xl bg-primary-soft text-sm font-bold text-primary hover:bg-primary/15">Done</button>
          </div>
        </div>
      )}
    </div>
  )
}
