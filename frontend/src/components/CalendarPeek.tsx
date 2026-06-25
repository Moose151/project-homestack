import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { CalendarEvent } from '../api/types'

function whenLabel(iso: string, allDay: boolean) {
  const d = new Date(iso)
  const today = new Date()
  const tomorrow = new Date(today); tomorrow.setDate(today.getDate() + 1)
  const day = d.toDateString() === today.toDateString() ? 'Today'
    : d.toDateString() === tomorrow.toDateString() ? 'Tomorrow'
    : d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
  const time = allDay ? '' : ` · ${d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })}`
  return day + time
}

/** Lightweight "peek" at the calendar from any page: next few events + quick-add. */
export function CalendarPeek() {
  const [open, setOpen] = useState(false)
  const [events, setEvents] = useState<CalendarEvent[]>([])
  const [title, setTitle] = useState('')
  const [when, setWhen] = useState('')
  const [saving, setSaving] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  const load = () => api.getEvents({ upcoming: true }).then(e => setEvents(e.slice(0, 5))).catch(() => {})

  useEffect(() => {
    const onClick = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false) }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [])

  const toggle = () => { const next = !open; setOpen(next); if (next) load() }

  const quickAdd = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim() || !when) return
    setSaving(true)
    try {
      await api.createEvent({ title: title.trim(), start_at: new Date(when).toISOString() })
      setTitle(''); setWhen('')
      load()
    } catch { /* surfaced on the full calendar page */ } finally {
      setSaving(false)
    }
  }

  return (
    <div className="relative" ref={ref}>
      <button onClick={toggle}
        className="w-10 h-10 grid place-items-center rounded-xl hover:bg-sunken text-muted-strong"
        aria-label="Calendar">
        <span className="text-lg">📅</span>
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-80 bg-surface rounded-2xl shadow-soft border border-line z-30">
          <div className="flex items-center justify-between px-4 py-2.5 border-b border-line">
            <span className="text-sm font-semibold text-ink">Up next</span>
            <Link to="/calendar" onClick={() => setOpen(false)} className="text-xs text-primary hover:underline">Open calendar</Link>
          </div>

          {events.length === 0 ? (
            <p className="text-sm text-muted text-center py-4">Nothing upcoming.</p>
          ) : (
            <ul className="divide-y divide-line/60 max-h-64 overflow-auto">
              {events.map(e => (
                <li key={e.id} className="px-4 py-2.5">
                  <p className="text-sm font-medium text-ink truncate">{e.title}</p>
                  <p className="text-xs text-muted">{whenLabel(e.start_at, e.is_all_day)}</p>
                </li>
              ))}
            </ul>
          )}

          <form onSubmit={quickAdd} className="flex flex-col gap-2 p-3 border-t border-line">
            <input
              value={title}
              onChange={e => setTitle(e.target.value)}
              placeholder="Quick add event…"
              className="px-3 py-2 rounded-xl border border-line bg-raised text-sm text-ink outline-none focus:ring-2 focus:ring-primary"
            />
            <div className="flex gap-2">
              <input
                type="datetime-local"
                value={when}
                onChange={e => setWhen(e.target.value)}
                className="flex-1 px-2 py-1.5 rounded-xl border border-line bg-raised text-xs text-muted-strong outline-none focus:ring-2 focus:ring-primary"
              />
              <button type="submit" disabled={!title.trim() || !when || saving}
                className="px-3 py-1.5 rounded-xl bg-primary text-white text-sm font-semibold disabled:opacity-40">
                Add
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  )
}
