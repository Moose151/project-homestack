import { useMemo } from 'react'

interface Props {
  value: string | null // ISO datetime, or null when unset
  allDay: boolean
  onChange: (next: { value: string | null; allDay: boolean }) => void
  allowAllDay?: boolean // false → always show the time field (e.g. timed classes)
  allDayDefaultTime?: string // time used when a date is picked but no time given
  className?: string
}

const inputCls =
  'rounded-xl border border-line bg-surface px-3 py-2.5 text-sm text-ink ' +
  'outline-none focus:ring-2 focus:ring-primary/40 min-h-[44px]'

const pad = (n: number) => String(n).padStart(2, '0')

/** Split an ISO datetime into local `yyyy-mm-dd` + `hh:mm` parts for the inputs. */
function splitLocal(iso: string | null): { date: string; time: string } {
  if (!iso) return { date: '', time: '' }
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return { date: '', time: '' }
  return {
    date: `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`,
    time: `${pad(d.getHours())}:${pad(d.getMinutes())}`,
  }
}

/** Recombine a local date + time into an ISO string (or null when no date is chosen). */
function combine(date: string, time: string, allDay: boolean, fallbackTime: string): string | null {
  if (!date) return null
  const t = allDay ? '00:00' : time || fallbackTime
  const d = new Date(`${date}T${t}`)
  return Number.isNaN(d.getTime()) ? null : d.toISOString()
}

/**
 * Date + time entry with an "All day" toggle. Pick a date (native calendar), then either
 * enter a time (native clock) or check "All day" for a date with no set time. Emits an ISO
 * string plus the all-day flag so callers can persist both.
 */
export function DateTimeField({
  value, allDay, onChange, allowAllDay = true, allDayDefaultTime = '09:00', className = '',
}: Props) {
  const { date, time } = useMemo(() => splitLocal(value), [value])

  const emit = (nextDate: string, nextTime: string, nextAllDay: boolean) =>
    onChange({ value: combine(nextDate, nextTime, nextAllDay, allDayDefaultTime), allDay: nextAllDay })

  return (
    <div className={`flex flex-col gap-2 ${className}`}>
      <div className="flex flex-wrap gap-2">
        <input
          type="date"
          className={`${inputCls} flex-1 min-w-[9rem]`}
          value={date}
          onChange={e => emit(e.target.value, time, allDay)}
          aria-label="Date"
        />
        {!allDay && (
          <input
            type="time"
            className={`${inputCls} w-32`}
            value={time}
            onChange={e => emit(date, e.target.value, allDay)}
            aria-label="Time"
          />
        )}
      </div>
      {allowAllDay && (
        <label className="flex items-center gap-2 text-sm text-muted-strong select-none">
          <input
            type="checkbox"
            checked={allDay}
            onChange={e => emit(date, time, e.target.checked)}
          />
          All day (no set time)
        </label>
      )}
    </div>
  )
}
