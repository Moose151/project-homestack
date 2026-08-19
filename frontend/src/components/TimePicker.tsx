import { useEffect, useId, useMemo, useRef, useState } from 'react'
import { fieldClass } from './Field'

const pad = (value: number) => String(value).padStart(2, '0')
const MINUTE_QUICK_PICKS = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55]

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
 * desktops get a fast text-entry + one-click-grid popover instead of scrolling a 60-row list.
 * Values stay in the API's existing 24-hour HH:mm shape regardless of how the locale displays
 * them.
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
  const hourInputRef = useRef<HTMLInputElement>(null)
  const minuteInputRef = useRef<HTMLInputElement>(null)
  const hour12 = useMemo(localeUses12Hours, [])
  const selected = normalise(value)
  const [hourText, minuteText] = selected.split(':')
  const hour = Number(hourText)
  const minute = Number(minuteText)
  const period = hour >= 12 ? 'PM' : 'AM'
  const displayHour = hour12 ? (hour % 12 || 12) : hour

  // Local text buffers so a partial keystroke ("1" on the way to "12") isn't clobbered by the
  // committed value re-rendering mid-type.
  const [hourDraft, setHourDraft] = useState(String(displayHour))
  const [minuteDraft, setMinuteDraft] = useState(pad(minute))

  useEffect(() => {
    if (document.activeElement !== hourInputRef.current) setHourDraft(String(displayHour))
    if (document.activeElement !== minuteInputRef.current) setMinuteDraft(pad(minute))
  }, [displayHour, minute])

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
    const frame = requestAnimationFrame(() => hourInputRef.current?.select())
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
  const commitHourDraft = (raw: string) => {
    const parsed = Number(raw)
    const max = hour12 ? 12 : 23
    const min = hour12 ? 1 : 0
    if (raw.trim() === '' || Number.isNaN(parsed)) { setHourDraft(String(displayHour)); return }
    selectDisplayHour(Math.min(max, Math.max(min, Math.round(parsed))))
  }
  const commitMinuteDraft = (raw: string) => {
    const parsed = Number(raw)
    if (raw.trim() === '' || Number.isNaN(parsed)) { setMinuteDraft(pad(minute)); return }
    emit(hour, Math.min(59, Math.max(0, Math.round(parsed))))
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
          className="absolute right-0 z-40 mt-2 w-72 rounded-2xl border border-line bg-surface p-3 shadow-card"
        >
          {/* Fast path: type the time directly. */}
          <div className="flex items-center justify-center gap-1.5">
            <input
              ref={hourInputRef}
              type="text"
              inputMode="numeric"
              maxLength={2}
              value={hourDraft}
              aria-label="Hour"
              onFocus={event => event.currentTarget.select()}
              onChange={event => setHourDraft(event.target.value.replace(/\D/g, '').slice(0, 2))}
              onBlur={event => commitHourDraft(event.target.value)}
              onKeyDown={event => {
                if (event.key === 'Enter') { commitHourDraft(hourDraft); minuteInputRef.current?.select() }
                if (event.key === ':' || event.key === 'ArrowRight') { event.preventDefault(); commitHourDraft(hourDraft); minuteInputRef.current?.select() }
              }}
              className="h-11 w-14 rounded-xl border border-line bg-sunken text-center text-lg font-bold tabular-nums text-ink outline-none focus:ring-2 focus:ring-primary/30"
            />
            <span aria-hidden className="text-lg font-bold text-muted">:</span>
            <input
              ref={minuteInputRef}
              type="text"
              inputMode="numeric"
              maxLength={2}
              value={minuteDraft}
              aria-label="Minute"
              onFocus={event => event.currentTarget.select()}
              onChange={event => setMinuteDraft(event.target.value.replace(/\D/g, '').slice(0, 2))}
              onBlur={event => commitMinuteDraft(event.target.value)}
              onKeyDown={event => { if (event.key === 'Enter') commitMinuteDraft(minuteDraft) }}
              className="h-11 w-14 rounded-xl border border-line bg-sunken text-center text-lg font-bold tabular-nums text-ink outline-none focus:ring-2 focus:ring-primary/30"
            />
            {hour12 && (
              <div className="ml-1 flex flex-col gap-1" role="group" aria-label="AM or PM">
                {(['AM', 'PM'] as const).map(option => (
                  <button
                    key={option}
                    type="button"
                    aria-pressed={period === option}
                    onClick={() => selectPeriod(option)}
                    className={`min-h-5 rounded-md px-2 text-[11px] font-bold leading-tight ${period === option ? 'bg-primary text-white' : 'bg-sunken text-muted-strong hover:text-ink'}`}
                  >
                    {option}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* One-click common values — avoids scrolling a 60-row list for the usual cases. */}
          <div className="mt-3">
            <div className="mb-1 text-center text-[11px] font-bold uppercase tracking-wide text-muted-strong">Hour</div>
            <div className={`grid gap-1 ${hour12 ? 'grid-cols-6' : 'grid-cols-6'}`}>
              {Array.from({ length: hour12 ? 12 : 24 }, (_, index) => hour12 ? index + 1 : index).map(option => (
                <button
                  key={option}
                  type="button"
                  aria-pressed={displayHour === option}
                  onClick={() => selectDisplayHour(option)}
                  className={`min-h-8 rounded-lg text-xs font-bold tabular-nums ${displayHour === option ? 'bg-primary text-white' : 'bg-sunken text-muted-strong hover:text-ink'}`}
                >
                  {pad(option)}
                </button>
              ))}
            </div>
            <div className="mb-1 mt-2 text-center text-[11px] font-bold uppercase tracking-wide text-muted-strong">Minute</div>
            <div className="grid grid-cols-6 gap-1">
              {MINUTE_QUICK_PICKS.map(option => (
                <button
                  key={option}
                  type="button"
                  aria-pressed={minute === option}
                  onClick={() => emit(hour, option)}
                  className={`min-h-8 rounded-lg text-xs font-bold tabular-nums ${minute === option ? 'bg-primary text-white' : 'bg-sunken text-muted-strong hover:text-ink'}`}
                >
                  {pad(option)}
                </button>
              ))}
            </div>
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
