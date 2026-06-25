import { useEffect, useMemo, useState } from 'react'
import { api } from '../../../api/client'
import type { CalendarEvent, CalendarEventWrite, Person } from '../../../api/types'
import { Button } from '../../../components/Button'

// ---------------------------------------------------------------------------
// Date helpers (no external deps)
// ---------------------------------------------------------------------------

type View = 'month' | 'week' | 'day' | 'agenda'

const errMsg = (e: unknown) => (e instanceof Error ? e.message : 'Something went wrong.')
const startOfDay = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate())
const addDays = (d: Date, n: number) => { const x = new Date(d); x.setDate(x.getDate() + n); return x }
const addMonths = (d: Date, n: number) => { const x = new Date(d); x.setMonth(x.getMonth() + n); return x }
const sameDay = (a: Date, b: Date) => a.toDateString() === b.toDateString()
const isToday = (d: Date) => sameDay(d, new Date())

function startOfWeek(d: Date, weekStart: number) {
  const x = startOfDay(d)
  const diff = (x.getDay() - weekStart + 7) % 7
  return addDays(x, -diff)
}

function monthGrid(anchor: Date, weekStart: number): Date[] {
  const first = new Date(anchor.getFullYear(), anchor.getMonth(), 1)
  const gridStart = startOfWeek(first, weekStart)
  return Array.from({ length: 42 }, (_, i) => addDays(gridStart, i))
}

function toLocalInput(d: Date) {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function fmtTime(iso: string, time24: boolean) {
  return new Date(iso).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit', hour12: !time24 })
}

const NODE_COLOUR: Record<string, string> = { atlas: '#6366F1', meridian: '#F59E0B' }
const DEFAULT_COLOUR = '#9CA3AF'

// ---------------------------------------------------------------------------
// Event modal (create / edit standalone events)
// ---------------------------------------------------------------------------

function EventModal({
  event, defaultDate, people, onClose, onSaved, onError,
}: {
  event: CalendarEvent | null
  defaultDate: Date | null
  people: Person[]
  onClose: () => void
  onSaved: () => void
  onError: (m: string) => void
}) {
  const synced = !!event?.is_synced
  const base = event ? new Date(event.start_at) : (defaultDate ?? new Date())
  const [f, setF] = useState({
    title: event?.title ?? '',
    start_at: toLocalInput(base),
    end_at: event?.end_at ? toLocalInput(new Date(event.end_at)) : '',
    is_all_day: event?.is_all_day ?? false,
    location: event?.location ?? '',
    colour: event?.colour ?? '',
    assigned_to_person_id: event?.assigned_to_person_id ?? 0,
    visibility: event?.visibility ?? 'household',
  })
  const [saving, setSaving] = useState(false)
  const set = (k: string, v: unknown) => setF(prev => ({ ...prev, [k]: v }))

  const save = async () => {
    if (!f.title.trim()) return
    setSaving(true)
    try {
      const payload: CalendarEventWrite = {
        title: f.title.trim(),
        start_at: new Date(f.start_at).toISOString(),
        end_at: f.end_at ? new Date(f.end_at).toISOString() : null,
        is_all_day: f.is_all_day,
        location: f.location,
        colour: f.colour,
        assigned_to_person_id: f.assigned_to_person_id || null,
        visibility: f.visibility,
      }
      if (event) await api.updateEvent(event.id, payload)
      else await api.createEvent(payload)
      onSaved()
    } catch (e) {
      onError(errMsg(e))
    } finally {
      setSaving(false)
    }
  }

  const remove = async () => {
    if (!event || !confirm(`Delete "${event.title}"?`)) return
    try { await api.deleteEvent(event.id); onSaved() } catch (e) { onError(errMsg(e)) }
  }

  const input = 'w-full px-3 py-2 rounded-xl border border-line bg-raised text-sm text-ink outline-none focus:ring-2 focus:ring-primary'

  return (
    <div className="fixed inset-0 z-40 bg-black/40 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-surface rounded-2xl shadow-card border border-line w-full max-w-md p-6 flex flex-col gap-3" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-ink">{event ? (synced ? 'Event' : 'Edit event') : 'New event'}</h2>
          <button onClick={onClose} className="text-muted hover:text-ink text-xl leading-none">×</button>
        </div>

        {synced ? (
          <div className="flex flex-col gap-2 text-sm">
            <p className="font-medium text-ink">{event!.title}</p>
            <p className="text-muted">{new Date(event!.start_at).toLocaleString()}</p>
            <p className="text-xs text-muted">
              This event comes from <span className="capitalize font-medium">{event!.source_node}</span> and is edited there, not on the calendar.
            </p>
          </div>
        ) : (
          <>
            <input className={input} placeholder="Title" value={f.title} onChange={e => set('title', e.target.value)} autoFocus />
            <label className="flex items-center gap-2 text-sm text-ink">
              <input type="checkbox" checked={f.is_all_day} onChange={e => set('is_all_day', e.target.checked)} /> All day
            </label>
            <div className="grid grid-cols-2 gap-2">
              <label className="flex flex-col gap-1 text-xs text-muted">Start
                <input type="datetime-local" className={input} value={f.start_at} onChange={e => set('start_at', e.target.value)} />
              </label>
              <label className="flex flex-col gap-1 text-xs text-muted">End (optional)
                <input type="datetime-local" className={input} value={f.end_at} onChange={e => set('end_at', e.target.value)} />
              </label>
            </div>
            <input className={input} placeholder="Location (optional)" value={f.location} onChange={e => set('location', e.target.value)} />
            <div className="grid grid-cols-2 gap-2">
              <select className={input} value={f.assigned_to_person_id} onChange={e => set('assigned_to_person_id', Number(e.target.value))}>
                <option value={0}>Unassigned</option>
                {people.map(p => <option key={p.id} value={p.id}>{p.display_name}</option>)}
              </select>
              <select className={input} value={f.visibility} onChange={e => set('visibility', e.target.value)}>
                <option value="household">Household</option>
                <option value="private">Private</option>
              </select>
            </div>
            <label className="flex items-center gap-2 text-sm text-ink">
              Colour <input type="color" value={f.colour || '#6366F1'} onChange={e => set('colour', e.target.value)} />
              {f.colour && <button type="button" onClick={() => set('colour', '')} className="text-xs text-muted hover:text-danger">clear</button>}
            </label>
            <div className="flex items-center justify-between mt-1">
              {event ? <button onClick={remove} className="text-sm text-danger hover:underline">Delete</button> : <span />}
              <Button onClick={save} loading={saving} disabled={!f.title.trim()}>Save</Button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Event chip
// ---------------------------------------------------------------------------

function EventChip({ event, colour, time24, onClick }: { event: CalendarEvent; colour: string; time24: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left flex items-center gap-1.5 px-1.5 py-0.5 rounded-md hover:bg-sunken text-xs truncate"
      style={{ borderLeft: `3px solid ${colour}` }}
    >
      {!event.is_all_day && <span className="text-muted tabular-nums flex-shrink-0">{fmtTime(event.start_at, time24)}</span>}
      <span className="truncate text-ink">{event.title}</span>
    </button>
  )
}

// ---------------------------------------------------------------------------
// Agenda view
// ---------------------------------------------------------------------------

function AgendaView({ events, colourFor, time24, onOpen }: {
  events: CalendarEvent[]
  colourFor: (e: CalendarEvent) => string
  time24: boolean
  onOpen: (e: CalendarEvent) => void
}) {
  const grouped = useMemo(() => {
    const m = new Map<string, CalendarEvent[]>()
    for (const e of events) {
      const k = new Date(e.start_at).toDateString()
      if (!m.has(k)) m.set(k, [])
      m.get(k)!.push(e)
    }
    return [...m.entries()]
  }, [events])

  if (events.length === 0) return <p className="text-sm text-muted text-center py-10">No upcoming events.</p>

  return (
    <div className="flex flex-col gap-5">
      {grouped.map(([dateStr, evs]) => (
        <div key={dateStr}>
          <h2 className="text-sm font-semibold text-muted uppercase tracking-wide mb-2">
            {sameDay(new Date(dateStr), new Date()) ? 'Today' : new Date(dateStr).toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' })}
          </h2>
          <div className="flex flex-col gap-2">
            {evs.map(e => (
              <button key={e.id} onClick={() => onOpen(e)} className="flex items-start gap-4 p-3 rounded-xl border border-line hover:bg-sunken text-left">
                <div className="w-16 text-xs text-primary font-semibold tabular-nums flex-shrink-0">{e.is_all_day ? 'All day' : fmtTime(e.start_at, time24)}</div>
                <div className="flex-1 min-w-0" style={{ borderLeft: `3px solid ${colourFor(e)}`, paddingLeft: 10 }}>
                  <p className="font-medium text-ink">{e.title}</p>
                  {e.source_node && <span className="text-xs text-muted capitalize">{e.source_node}</span>}
                </div>
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Calendar page
// ---------------------------------------------------------------------------

const lsGet = (k: string, d: string) => localStorage.getItem(k) ?? d
const linkedDate = () => {
  const raw = new URLSearchParams(window.location.search).get('date')
  if (!raw) return null
  const d = new Date(`${raw}T00:00:00`)
  return Number.isNaN(d.getTime()) ? null : d
}

export function CalendarPage() {
  const initialLinkedDate = linkedDate()
  const [view, setView] = useState<View>(() => initialLinkedDate ? 'day' : lsGet('hs_cal_view', 'month') as View)
  const [weekStart, setWeekStart] = useState<number>(() => Number(lsGet('hs_cal_weekstart', '1')))
  const [time24, setTime24] = useState<boolean>(() => lsGet('hs_cal_24h', '0') === '1')
  const [anchor, setAnchor] = useState(() => initialLinkedDate ?? new Date())
  const [events, setEvents] = useState<CalendarEvent[]>([])
  const [people, setPeople] = useState<Person[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [nodeFilter, setNodeFilter] = useState('')
  const [personFilter, setPersonFilter] = useState(0)
  const [modal, setModal] = useState<{ event: CalendarEvent | null; date: Date | null } | null>(null)

  useEffect(() => { localStorage.setItem('hs_cal_view', view) }, [view])
  useEffect(() => { localStorage.setItem('hs_cal_weekstart', String(weekStart)) }, [weekStart])
  useEffect(() => { localStorage.setItem('hs_cal_24h', time24 ? '1' : '0') }, [time24])
  useEffect(() => { api.getPeople().then(setPeople).catch(() => {}) }, [])

  // Window to fetch for the current view.
  const win = useMemo(() => {
    if (view === 'month') {
      const g = monthGrid(anchor, weekStart)
      return { start: g[0], end: addDays(g[41], 1) }
    }
    if (view === 'week') {
      const s = startOfWeek(anchor, weekStart)
      return { start: s, end: addDays(s, 7) }
    }
    if (view === 'day') return { start: startOfDay(anchor), end: addDays(startOfDay(anchor), 1) }
    return { start: startOfDay(new Date()), end: addDays(new Date(), 60) } // agenda
  }, [view, anchor, weekStart])

  const winStart = win.start.getTime()
  const winEnd = win.end.getTime()

  const reload = () => {
    setLoading(true)
    api.getEvents({
      start: new Date(winStart).toISOString(),
      end: new Date(winEnd).toISOString(),
      node: nodeFilter || undefined,
      person: personFilter || undefined,
    })
      .then(setEvents)
      .catch(e => setError(errMsg(e)))
      .finally(() => setLoading(false))
  }
  useEffect(reload, [winStart, winEnd, nodeFilter, personFilter])

  const personColour = useMemo(() => {
    const m: Record<number, string> = {}
    for (const p of people) if (p.colour) m[p.id] = p.colour
    return m
  }, [people])

  const colourFor = (e: CalendarEvent) =>
    e.colour || (e.assigned_to_person_id ? personColour[e.assigned_to_person_id] : '') ||
    (e.source_node ? NODE_COLOUR[e.source_node] : '') || DEFAULT_COLOUR

  const eventsByDay = useMemo(() => {
    const m = new Map<string, CalendarEvent[]>()
    for (const e of events) {
      const k = new Date(e.start_at).toDateString()
      if (!m.has(k)) m.set(k, [])
      m.get(k)!.push(e)
    }
    return m
  }, [events])
  const dayEvents = (d: Date) => (eventsByDay.get(d.toDateString()) ?? [])

  const nodesPresent = useMemo(
    () => [...new Set(events.map(e => e.source_node).filter(Boolean))] as string[],
    [events],
  )

  const step = (dir: -1 | 1) => {
    if (view === 'month') setAnchor(a => addMonths(a, dir))
    else if (view === 'week') setAnchor(a => addDays(a, 7 * dir))
    else setAnchor(a => addDays(a, dir))
  }
  const periodLabel = () => {
    if (view === 'month') return anchor.toLocaleDateString(undefined, { month: 'long', year: 'numeric' })
    if (view === 'day') return anchor.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' })
    if (view === 'week') {
      const s = startOfWeek(anchor, weekStart)
      return `${s.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })} – ${addDays(s, 6).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}`
    }
    return 'Upcoming'
  }

  const openEvent = (e: CalendarEvent) => setModal({ event: e, date: null })
  const openNew = (d: Date | null) => setModal({ event: null, date: d })

  const weekdayNames = useMemo(() => {
    const base = startOfWeek(new Date(), weekStart)
    return Array.from({ length: 7 }, (_, i) => addDays(base, i).toLocaleDateString(undefined, { weekday: 'short' }))
  }, [weekStart])

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <h1 className="text-2xl font-extrabold tracking-tight text-ink">Calendar</h1>
        <Button size="sm" onClick={() => openNew(view === 'day' ? anchor : new Date())}>+ New event</Button>
      </div>

      {/* Toolbar */}
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-1">
          <button onClick={() => step(-1)} className="px-2 py-1 rounded-lg hover:bg-sunken text-muted-strong" aria-label="Previous">‹</button>
          <button onClick={() => setAnchor(new Date())} className="px-3 py-1 rounded-lg hover:bg-sunken text-sm font-medium text-ink">Today</button>
          <button onClick={() => step(1)} className="px-2 py-1 rounded-lg hover:bg-sunken text-muted-strong" aria-label="Next">›</button>
          <span className="ml-2 text-sm font-semibold text-ink">{periodLabel()}</span>
        </div>
        <div className="flex gap-1 bg-sunken p-1 rounded-xl">
          {(['month', 'week', 'day', 'agenda'] as View[]).map(v => (
            <button key={v} onClick={() => setView(v)}
              className={`px-3 py-1 rounded-lg text-xs font-semibold capitalize transition-colors ${view === v ? 'bg-raised text-ink shadow-soft' : 'text-muted hover:text-ink'}`}>
              {v}
            </button>
          ))}
        </div>
      </div>

      {/* Filters + prefs */}
      <div className="flex items-center gap-2 flex-wrap text-sm">
        <select value={nodeFilter} onChange={e => setNodeFilter(e.target.value)} className="px-2 py-1 rounded-lg border border-line bg-raised text-ink text-xs capitalize">
          <option value="">All sources</option>
          {nodesPresent.map(n => <option key={n} value={n}>{n}</option>)}
        </select>
        <select value={personFilter} onChange={e => setPersonFilter(Number(e.target.value))} className="px-2 py-1 rounded-lg border border-line bg-raised text-ink text-xs">
          <option value={0}>Everyone</option>
          {people.map(p => <option key={p.id} value={p.id}>{p.display_name}</option>)}
        </select>
        <button onClick={() => setWeekStart(w => (w === 1 ? 0 : 1))} className="px-2 py-1 rounded-lg border border-line text-xs text-muted hover:text-ink">
          Week starts {weekStart === 1 ? 'Mon' : 'Sun'}
        </button>
        <button onClick={() => setTime24(t => !t)} className="px-2 py-1 rounded-lg border border-line text-xs text-muted hover:text-ink">
          {time24 ? '24h' : '12h'}
        </button>
      </div>

      {error && (
        <div className="flex items-center justify-between gap-3 px-4 py-2.5 rounded-xl bg-danger-soft text-danger text-sm">
          <span>{error}</span>
          <button onClick={() => setError(null)} aria-label="Dismiss">×</button>
        </div>
      )}

      {loading ? (
        <div className="h-64 rounded-2xl bg-sunken animate-pulse" />
      ) : view === 'month' ? (
        <div className="rounded-2xl border border-line overflow-hidden">
          <div className="grid grid-cols-7 bg-sunken">
            {weekdayNames.map(d => <div key={d} className="px-2 py-1.5 text-xs font-semibold text-muted text-center">{d}</div>)}
          </div>
          <div className="grid grid-cols-7">
            {monthGrid(anchor, weekStart).map((d, i) => {
              const inMonth = d.getMonth() === anchor.getMonth()
              const evs = dayEvents(d)
              return (
                <div key={i} onClick={() => openNew(d)}
                  className={`min-h-[92px] border-b border-r border-line p-1 cursor-pointer hover:bg-sunken/50 ${inMonth ? '' : 'bg-sunken/30'}`}>
                  <div className={`text-xs font-semibold mb-1 w-6 h-6 flex items-center justify-center rounded-full ${isToday(d) ? 'bg-primary text-white' : inMonth ? 'text-ink' : 'text-muted'}`}>
                    {d.getDate()}
                  </div>
                  <div className="flex flex-col gap-0.5">
                    {evs.slice(0, 3).map(e => (
                      <div key={e.id} onClick={ev => { ev.stopPropagation(); openEvent(e) }}>
                        <EventChip event={e} colour={colourFor(e)} time24={time24} onClick={() => {}} />
                      </div>
                    ))}
                    {evs.length > 3 && <span className="text-[10px] text-muted pl-1">+{evs.length - 3} more</span>}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      ) : view === 'week' ? (
        <div className="grid grid-cols-1 sm:grid-cols-7 gap-2">
          {Array.from({ length: 7 }, (_, i) => addDays(startOfWeek(anchor, weekStart), i)).map(d => (
            <div key={d.toDateString()} className="rounded-xl border border-line p-2 min-h-[120px]">
              <div className={`text-xs font-semibold mb-2 ${isToday(d) ? 'text-primary' : 'text-muted-strong'}`}>
                {d.toLocaleDateString(undefined, { weekday: 'short', day: 'numeric' })}
              </div>
              <div className="flex flex-col gap-1">
                {dayEvents(d).map(e => <EventChip key={e.id} event={e} colour={colourFor(e)} time24={time24} onClick={() => openEvent(e)} />)}
              </div>
            </div>
          ))}
        </div>
      ) : view === 'day' ? (
        <div className="flex flex-col gap-2">
          {dayEvents(anchor).length === 0 ? (
            <p className="text-sm text-muted text-center py-10">Nothing scheduled. Tap “New event” to add something.</p>
          ) : dayEvents(anchor).map(e => (
            <button key={e.id} onClick={() => openEvent(e)} className="flex items-start gap-4 p-4 rounded-xl border border-line hover:bg-sunken text-left">
              <div className="w-16 text-xs text-primary font-semibold tabular-nums flex-shrink-0">{e.is_all_day ? 'All day' : fmtTime(e.start_at, time24)}</div>
              <div className="flex-1 min-w-0" style={{ borderLeft: `3px solid ${colourFor(e)}`, paddingLeft: 10 }}>
                <p className="font-medium text-ink">{e.title}</p>
                {e.location && <p className="text-xs text-muted">{e.location}</p>}
                {e.source_node && <span className="text-xs text-muted capitalize">{e.source_node}</span>}
              </div>
            </button>
          ))}
        </div>
      ) : (
        <AgendaView events={events} colourFor={colourFor} time24={time24} onOpen={openEvent} />
      )}

      {/* Legend */}
      {people.some(p => p.colour) && (
        <div className="flex flex-wrap gap-3 text-xs text-muted pt-1">
          {people.filter(p => p.colour).map(p => (
            <span key={p.id} className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded-full" style={{ backgroundColor: p.colour }} /> {p.display_name}
            </span>
          ))}
        </div>
      )}

      {modal && (
        <EventModal
          event={modal.event}
          defaultDate={modal.date}
          people={people}
          onClose={() => setModal(null)}
          onError={setError}
          onSaved={() => { setModal(null); reload() }}
        />
      )}
    </div>
  )
}
