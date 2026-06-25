import { useEffect, useMemo, useState } from 'react'
import { api } from '../../../api/client'
import type {
  AuthUser, HubWidget, AtlasListItem as ListItem, AtlasReminder as Reminder,
  MeridianTask, PointsSummaryRow, MeridianReward, MeridianRoutine,
  MeridianGoal, MeridianWishlistItem, PersonBadge, CalendarEvent,
} from '../../../api/types'
import { isImageAvatar } from '../../../components/Avatar'
import { KioskThemeToggle } from '../components/KioskThemeToggle'
import { useInactivityTimeout } from '../hooks/useInactivityTimeout'

interface Props {
  authUser: AuthUser
  onLogout: () => void
}

type DashboardView = 'home' | 'calendar'
type KioskCalendarMode = 'month' | 'week' | 'day' | 'agenda'

const panelClass = 'rounded-2xl border-2 border-line-strong bg-raised p-6 shadow-card'
const itemButtonClass = 'rounded-xl border-2 border-line bg-surface px-4 py-4 text-left shadow-soft transition-colors hover:border-primary hover:bg-primary-soft disabled:opacity-60'
const headingClass = 'mb-4 text-lg font-bold text-muted-strong'
const emptyClass = 'text-sm text-muted'
const pointsClass = 'font-extrabold text-warning'

const startOfDay = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate())
const addDays = (d: Date, days: number) => {
  const next = new Date(d)
  next.setDate(next.getDate() + days)
  return next
}
const addMonths = (d: Date, months: number) => {
  const next = new Date(d)
  next.setMonth(next.getMonth() + months)
  return next
}
const sameDay = (a: Date, b: Date) =>
  a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate()
const eventStartsOn = (event: CalendarEvent, day: Date) => sameDay(new Date(event.start_at), day)
const startOfWeek = (d: Date) => {
  const day = startOfDay(d)
  const diff = (day.getDay() + 6) % 7
  return addDays(day, -diff)
}
const monthGrid = (anchor: Date) => {
  const first = new Date(anchor.getFullYear(), anchor.getMonth(), 1)
  const gridStart = startOfWeek(first)
  return Array.from({ length: 42 }, (_, i) => addDays(gridStart, i))
}
const periodTitle = (mode: KioskCalendarMode, anchor: Date) => {
  if (mode === 'month') return anchor.toLocaleDateString(undefined, { month: 'long', year: 'numeric' })
  if (mode === 'day') return anchor.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' })
  if (mode === 'week') {
    const start = startOfWeek(anchor)
    const end = addDays(start, 6)
    return `${start.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })} - ${end.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}`
  }
  return 'Upcoming'
}
const eventTime = (event: CalendarEvent) => {
  if (event.is_all_day) return 'All day'
  return new Date(event.start_at).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
}
const sourceLabel = (event: CalendarEvent) =>
  event.source_node ? event.source_node.replace(/_/g, ' ') : 'Household'

function TodosWidget({ widget }: { widget: HubWidget }) {
  const items = widget.items as ListItem[]
  return (
    <div className={`${panelClass} flex-1 min-w-[280px]`}>
      <h2 className={headingClass}>{widget.name}</h2>
      {items.length === 0 ? (
        <p className={emptyClass}>Nothing to do 🎉</p>
      ) : (
        <ul className="space-y-3">
          {items.map((item) => (
            <li key={item.id} className="flex items-start gap-3">
              <span className="mt-1 w-4 h-4 rounded border border-line-strong flex-shrink-0" />
              <span>{item.title}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function RemindersWidget({ widget }: { widget: HubWidget }) {
  const items = widget.items as Reminder[]

  const fmt = (dt: string) =>
    new Date(dt).toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' })

  return (
    <div className={`${panelClass} flex-1 min-w-[280px]`}>
      <h2 className={headingClass}>{widget.name}</h2>
      {items.length === 0 ? (
        <p className={emptyClass}>No upcoming reminders</p>
      ) : (
        <ul className="space-y-3">
          {items.map((item) => (
            <li key={item.id} className="flex flex-col gap-0.5">
              <span>{item.title}</span>
              {item.due_at && <span className="text-xs text-muted">{fmt(item.due_at)}</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

// --- Meridian kiosk widgets (kid-facing, interactive) ---

function Celebration({ label, onDone }: { label: string; onDone: () => void }) {
  useEffect(() => {
    const id = setTimeout(onDone, 2200)
    return () => clearTimeout(id)
  }, [onDone])
  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-black/70 animate-[fadeIn_0.2s_ease]">
      <div className="text-7xl animate-bounce">🎉</div>
      <p className="mt-4 text-2xl font-bold text-white">{label}</p>
      <p className="mt-1 text-lg text-warning">Great job!</p>
    </div>
  )
}

function MeridianTasksWidget({ widget }: { widget: HubWidget }) {
  const [tasks, setTasks] = useState<MeridianTask[]>(widget.items as MeridianTask[])
  const [busy, setBusy] = useState<number | null>(null)
  const [celebrate, setCelebrate] = useState<string | null>(null)

  const complete = async (task: MeridianTask) => {
    setBusy(task.id)
    try {
      await api.completeMeridianTask(task.id)
      setTasks(prev => prev.filter(t => t.id !== task.id))
      setCelebrate(`+${task.award_value ?? task.points} points!`)
    } catch {
      /* ignore — card stays */
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className={`${panelClass} flex-1 min-w-[280px]`}>
      <h2 className={headingClass}>{widget.name}</h2>
      {celebrate && <Celebration label={celebrate} onDone={() => setCelebrate(null)} />}
      {tasks.length === 0 ? (
        <p className={emptyClass}>All done — nice! 🎉</p>
      ) : (
        <ul className="space-y-3">
          {tasks.map(task => (
            <li key={task.id}>
              <button
                onClick={() => complete(task)}
                disabled={busy === task.id || task.status === 'pending'}
                className={`${itemButtonClass} w-full flex items-center justify-between gap-3 min-h-[64px]`}
              >
                <span className="flex items-center gap-2 text-lg font-semibold">
                  {task.is_hot && <span>🔥</span>}
                  {task.title}
                </span>
                <span className="flex items-center gap-2 flex-shrink-0">
                  <span className={pointsClass}>★ {task.award_value ?? task.points}</span>
                  {task.status === 'pending'
                    ? <span className="text-xs text-muted">Waiting...</span>
                    : <span className="text-2xl text-muted">○</span>}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function MeridianPointsWidget({ widget }: { widget: HubWidget }) {
  const rows = widget.items as PointsSummaryRow[]
  return (
    <div className={`${panelClass} flex-1 min-w-[280px]`}>
      <h2 className={headingClass}>{widget.name}</h2>
      {rows.length === 0 ? (
        <p className={emptyClass}>No points yet — complete a task!</p>
      ) : (
        <ul className="space-y-3">
          {rows.map(row => (
            <li key={row.person_id} className="flex items-center justify-between">
              <span>{row.display_name || `Person ${row.person_id}`}</span>
              <span className="text-2xl font-extrabold text-warning">★ {row.balance}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

// Kiosk badges — a celebratory strip of what the child has earned.
function KioskBadges() {
  const [badges, setBadges] = useState<PersonBadge[]>([])
  useEffect(() => { api.getMyBadges().then(setBadges).catch(() => {}) }, [])
  if (badges.length === 0) return null
  return (
    <div className={`${panelClass} w-full`}>
      <h2 className={headingClass}>My badges</h2>
      <div className="flex flex-wrap gap-4">
        {badges.map(b => (
          <div key={b.id} title={b.badge.description} className="flex flex-col items-center w-20 text-center">
            <span className="text-4xl">{b.badge.icon}</span>
            <span className="text-xs text-muted-strong mt-1 leading-tight">{b.badge.name}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// Kiosk goals + wishlist — progress bars with quick-contribute buttons.
function KioskBar({ pct }: { pct: number }) {
  return (
    <div className="h-3 rounded-full bg-sunken overflow-hidden mt-2 border border-line-strong">
      <div className="h-full bg-warning" style={{ width: `${Math.min(100, pct)}%` }} />
    </div>
  )
}

function KioskGoalsWishlist() {
  const [goals, setGoals] = useState<MeridianGoal[]>([])
  const [items, setItems] = useState<MeridianWishlistItem[]>([])
  const [balance, setBalance] = useState(0)
  const [busy, setBusy] = useState<string | null>(null)

  const load = async () => {
    const [g, w, km] = await Promise.all([
      api.getMeridianGoals(true).catch(() => []),
      api.getWishlistItems().catch(() => []),
      api.kioskMeridian().catch(() => ({ points_balance: 0 } as { points_balance: number })),
    ])
    setGoals(g.filter(x => x.status === 'active'))
    setItems(w.filter(x => x.status === 'active'))
    setBalance(km.points_balance)
  }
  useEffect(() => { load() }, [])

  const give = async (key: string, fn: () => Promise<unknown>) => {
    setBusy(key)
    try { await fn(); await load() } catch { /* ignore */ } finally { setBusy(null) }
  }

  if (goals.length === 0 && items.length === 0) return null
  const amounts = [5, 10]

  const row = (key: string, title: string, pct: number, saved: number, target: number, contribute: (n: number) => Promise<unknown>) => (
    <div key={key} className="rounded-xl border-2 border-line bg-surface p-4 shadow-soft">
      <p className="font-semibold">{title}</p>
      <KioskBar pct={pct} />
      <p className="text-xs text-muted mt-1">★ {saved} / {target}</p>
      <div className="flex gap-2 mt-2">
        {amounts.map(n => (
          <button key={n} disabled={busy === key || balance < n}
            onClick={() => give(key, () => contribute(n))}
            className="rounded-lg bg-warning px-3 py-1 text-sm font-bold text-white transition-colors hover:bg-warning/90 disabled:opacity-40">
            +{n}
          </button>
        ))}
      </div>
    </div>
  )

  return (
    <div className={`${panelClass} w-full`}>
      <h2 className={headingClass}>Goals &amp; Wishlist · ★ {balance}</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {goals.map(g => row(`g${g.id}`, `🎯 ${g.title}`, g.progress_percentage, g.total_contributed, g.target_points,
          n => api.contributeToGoal(g.id, n)))}
        {items.map(it => row(`w${it.id}`, `🎁 ${it.name}`, it.progress_percentage, it.total_saved, it.point_cost,
          n => api.contributeToWishlist(it.id, n)))}
      </div>
    </div>
  )
}

// Kiosk routines — daily habits, tap to mark done, shows streak (mirrors legacy kiosk_routines).
function KioskRoutines() {
  const [routines, setRoutines] = useState<MeridianRoutine[]>([])
  const [busy, setBusy] = useState<number | null>(null)
  const [celebrate, setCelebrate] = useState<string | null>(null)

  const load = () => api.getMeridianRoutines().then(setRoutines).catch(() => {})
  useEffect(() => { load() }, [])

  const complete = async (r: MeridianRoutine) => {
    setBusy(r.id)
    try {
      await api.completeMeridianRoutine(r.id)
      setCelebrate(`+${r.points} points!`)
      await load()
    } catch { /* ignore */ } finally { setBusy(null) }
  }

  if (routines.length === 0) return null

  return (
    <div className={`${panelClass} w-full`}>
      {celebrate && <Celebration label={celebrate} onDone={() => setCelebrate(null)} />}
      <h2 className={headingClass}>Routines</h2>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {routines.map(r => (
          <button
            key={r.id}
            onClick={() => complete(r)}
            disabled={busy === r.id || !!r.done_today}
            className={`flex min-h-[96px] flex-col rounded-xl border px-4 py-4 text-left shadow-soft transition-colors disabled:opacity-60
              ${r.done_today ? 'border-success bg-success-soft' : 'border-line-strong bg-surface hover:border-primary hover:bg-primary-soft'}`}
          >
            <span className="text-lg font-semibold">{r.done_today && '✅ '}{r.title}</span>
            <span className="mt-auto pt-2 flex items-center gap-2">
              <span className={pointsClass}>+{r.points}</span>
              {(r.streak ?? 0) > 0 && <span className="text-warning text-sm">🔥 {r.streak}</span>}
              {r.done_today && <span className="text-success text-sm ml-auto">Done</span>}
            </span>
          </button>
        ))}
      </div>
    </div>
  )
}

// Kiosk reward shop — big tap-to-request cards (mirrors legacy kiosk_rewards).
function KioskShop() {
  const [rewards, setRewards] = useState<MeridianReward[]>([])
  const [balance, setBalance] = useState(0)
  const [busy, setBusy] = useState<number | null>(null)
  const [celebrate, setCelebrate] = useState<string | null>(null)

  const load = () => api.kioskMeridian()
    .then(d => { setRewards(d.rewards); setBalance(d.points_balance) })
    .catch(() => {})
  useEffect(() => { load() }, [])

  const request = async (r: MeridianReward) => {
    setBusy(r.id)
    try {
      await api.requestMeridianReward(r.id)
      setCelebrate(`Requested ${r.name}!`)
      await load()
    } catch {
      /* not enough points / out of stock — ignore */
    } finally {
      setBusy(null)
    }
  }

  if (rewards.length === 0) return null

  return (
    <div className={`${panelClass} w-full`}>
      {celebrate && <Celebration label={celebrate} onDone={() => setCelebrate(null)} />}
      <h2 className={headingClass}>Reward shop · ★ {balance}</h2>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {rewards.map(r => {
          const cant = balance < r.cost_points || (r.remaining_stock !== null && r.remaining_stock <= 0)
          return (
            <button
              key={r.id}
              onClick={() => request(r)}
              disabled={busy === r.id || cant}
              className="flex flex-col overflow-hidden rounded-xl border-2 border-line bg-surface text-left shadow-soft transition-colors hover:border-primary hover:bg-primary-soft disabled:opacity-50"
            >
              {r.image_url && <img src={r.image_url} alt="" className="h-24 w-full object-cover" />}
              <div className="p-3">
                <p className="font-semibold leading-tight">{r.name}</p>
                <p className="font-extrabold text-warning mt-1">★ {r.cost_points}</p>
                {cant && <p className="text-xs text-muted mt-1">{balance < r.cost_points ? 'Not enough' : 'Out of stock'}</p>}
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}

function ClockWidget({ widget }: { widget: HubWidget }) {
  const [now, setNow] = useState(new Date())
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(id)
  }, [])
  return (
    <div className={`${panelClass} flex-1 min-w-[280px] text-center`}>
      <h2 className="text-lg font-bold text-muted-strong mb-2">{widget.name}</h2>
      <p className="text-5xl font-thin tabular-nums text-ink">
        {now.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })}
      </p>
      <p className="text-muted mt-2">
        {now.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' })}
      </p>
    </div>
  )
}

function UpcomingWidget({ widget }: { widget: HubWidget }) {
  const items = widget.items as CalendarEvent[]
  const fmt = (dt: string, allDay: boolean) => {
    const d = new Date(dt)
    return allDay
      ? d.toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' })
      : d.toLocaleString('en-GB', { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
  }
  return (
    <div className={`${panelClass} flex-1 min-w-[280px]`}>
      <h2 className={headingClass}>{widget.name}</h2>
      {items.length === 0 ? (
        <p className={emptyClass}>Nothing upcoming</p>
      ) : (
        <ul className="space-y-3">
          {items.map((e) => (
            <li key={e.id} className="flex flex-col gap-0.5">
              <span>{e.title}</span>
              <span className="text-xs text-muted">{fmt(e.start_at, e.is_all_day)}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function KioskCalendarView() {
  const [mode, setMode] = useState<KioskCalendarMode>('week')
  const [anchor, setAnchor] = useState(() => new Date())
  const [events, setEvents] = useState<CalendarEvent[]>([])
  const [error, setError] = useState<string | null>(null)

  const windowRange = useMemo(() => {
    if (mode === 'month') {
      const grid = monthGrid(anchor)
      return { start: grid[0], end: addDays(grid[41], 1) }
    }
    if (mode === 'week') {
      const start = startOfWeek(anchor)
      return { start, end: addDays(start, 7) }
    }
    if (mode === 'day') {
      const start = startOfDay(anchor)
      return { start, end: addDays(start, 1) }
    }
    const start = startOfDay(new Date())
    return { start, end: addDays(start, 60) }
  }, [anchor, mode])

  const windowStart = windowRange.start.getTime()
  const windowEnd = windowRange.end.getTime()

  useEffect(() => {
    api.getEvents({ start: new Date(windowStart).toISOString(), end: new Date(windowEnd).toISOString() })
      .then((data) => {
        setEvents(data.sort((a, b) => new Date(a.start_at).getTime() - new Date(b.start_at).getTime()))
        setError(null)
      })
      .catch(() => setError('Could not load calendar.'))
  }, [windowStart, windowEnd])

  const today = startOfDay(new Date())
  const daysForMode = mode === 'month'
    ? monthGrid(anchor)
    : mode === 'week'
      ? Array.from({ length: 7 }, (_, i) => addDays(startOfWeek(anchor), i))
      : [startOfDay(anchor)]
  const eventCount = events.length

  const step = (dir: -1 | 1) => {
    if (mode === 'month') setAnchor(prev => addMonths(prev, dir))
    else if (mode === 'week') setAnchor(prev => addDays(prev, 7 * dir))
    else if (mode === 'day') setAnchor(prev => addDays(prev, dir))
  }

  const eventCard = (event: CalendarEvent, compact = false) => (
    <article
      key={event.id}
      className={`rounded-xl border-2 border-line bg-surface shadow-soft ${compact ? 'p-3' : 'p-4'}`}
      style={{ borderLeftColor: event.colour || '#3f6f8f', borderLeftWidth: 8 }}
    >
      <p className="text-sm font-extrabold text-primary">{eventTime(event)}</p>
      <h3 className={`${compact ? 'text-base' : 'text-lg'} mt-1 font-bold leading-tight`}>{event.title}</h3>
      <div className="mt-2 flex flex-wrap items-center gap-2 text-xs font-semibold text-muted">
        <span className="rounded-full bg-sunken px-2 py-1 capitalize">{sourceLabel(event)}</span>
        {event.location && <span className="rounded-full bg-sunken px-2 py-1">{event.location}</span>}
      </div>
    </article>
  )

  return (
    <section className="space-y-6">
      <div className={`${panelClass} flex flex-wrap items-center justify-between gap-4`}>
        <div>
          <h1 className="text-3xl font-extrabold">Calendar</h1>
          <p className="mt-1 text-muted">{periodTitle(mode, anchor)}</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {mode !== 'agenda' && (
            <div className="flex rounded-xl border border-line-strong bg-sunken p-1">
              <button onClick={() => step(-1)} className="min-h-11 rounded-lg px-4 text-2xl font-bold text-muted-strong hover:bg-surface" aria-label="Previous period">‹</button>
              <button onClick={() => setAnchor(new Date())} className="min-h-11 rounded-lg px-4 text-sm font-bold text-muted-strong hover:bg-surface">Today</button>
              <button onClick={() => step(1)} className="min-h-11 rounded-lg px-4 text-2xl font-bold text-muted-strong hover:bg-surface" aria-label="Next period">›</button>
            </div>
          )}
          <div className="flex rounded-xl border border-line-strong bg-sunken p-1">
            {(['month', 'week', 'day', 'agenda'] as KioskCalendarMode[]).map(v => (
              <button
                key={v}
                onClick={() => setMode(v)}
                className={`min-h-11 rounded-lg px-4 text-sm font-bold capitalize transition-colors ${
                  mode === v ? 'bg-raised text-primary shadow-soft' : 'text-muted-strong hover:bg-surface'
                }`}
              >
                {v}
              </button>
            ))}
          </div>
          <div className="rounded-2xl border-2 border-primary/40 bg-primary-soft px-5 py-3 text-center">
            <p className="text-sm font-bold uppercase tracking-wide text-primary">Events</p>
            <p className="text-2xl font-extrabold text-primary">{eventCount}</p>
          </div>
        </div>
      </div>

      {error && <p className="rounded-xl border border-danger bg-danger-soft px-4 py-3 text-danger">{error}</p>}

      {mode === 'agenda' ? (
        <div className="space-y-4">
          {events.length === 0 ? (
            <div className={`${panelClass} text-center text-muted`}>Nothing upcoming.</div>
          ) : events.map(event => (
            <div key={event.id} className="grid grid-cols-[8rem_1fr] gap-4">
              <div className="pt-4 text-right">
                <p className="text-sm font-extrabold text-muted-strong">
                  {new Date(event.start_at).toLocaleDateString(undefined, { weekday: 'short' })}
                </p>
                <p className="text-2xl font-extrabold text-ink">{new Date(event.start_at).getDate()}</p>
                <p className="text-xs font-semibold text-muted">
                  {new Date(event.start_at).toLocaleDateString(undefined, { month: 'short' })}
                </p>
              </div>
              {eventCard(event)}
            </div>
          ))}
        </div>
      ) : mode === 'month' ? (
        <div className="grid grid-cols-7 gap-3">
          {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map(day => (
            <div key={day} className="px-2 text-center text-sm font-extrabold uppercase tracking-wide text-muted">{day}</div>
          ))}
          {daysForMode.map(day => {
            const dayEvents = events.filter(event => eventStartsOn(event, day))
            const inMonth = day.getMonth() === anchor.getMonth()
            return (
              <section key={day.toISOString()} className={`${panelClass} min-h-[150px] ${inMonth ? '' : 'opacity-55'}`}>
                <div className="mb-3 flex items-center justify-between gap-2">
                  <span className={`grid h-10 w-10 place-items-center rounded-full text-lg font-extrabold ${
                    sameDay(day, today) ? 'bg-primary text-white' : 'bg-sunken text-ink'
                  }`}>
                    {day.getDate()}
                  </span>
                  {dayEvents.length > 0 && <span className="rounded-full bg-warning-soft px-2 py-1 text-xs font-bold text-warning">{dayEvents.length}</span>}
                </div>
                <div className="space-y-2">
                  {dayEvents.slice(0, 2).map(event => eventCard(event, true))}
                  {dayEvents.length > 2 && <p className="text-xs font-bold text-muted">+{dayEvents.length - 2} more</p>}
                </div>
              </section>
            )
          })}
        </div>
      ) : (
        <div className={`grid grid-cols-1 gap-4 ${mode === 'week' ? 'md:grid-cols-2 xl:grid-cols-4' : ''}`}>
          {daysForMode.map(day => {
            const dayEvents = events.filter(event => eventStartsOn(event, day))
            return (
              <section key={day.toISOString()} className={`${panelClass} min-h-[260px]`}>
                <div className="mb-4 flex items-baseline justify-between gap-3">
                  <div>
                    <h2 className="text-xl font-extrabold">
                      {sameDay(day, today) ? 'Today' : day.toLocaleDateString(undefined, { weekday: 'long' })}
                    </h2>
                    <p className="text-sm text-muted">{day.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}</p>
                  </div>
                  <span className="rounded-full bg-sunken px-3 py-1 text-sm font-bold text-muted-strong">
                    {dayEvents.length}
                  </span>
                </div>
                {dayEvents.length === 0 ? (
                  <p className={emptyClass}>Nothing booked</p>
                ) : (
                  <div className="space-y-3">{dayEvents.map(event => eventCard(event))}</div>
                )}
              </section>
            )
          })}
        </div>
      )}
    </section>
  )
}

const WIDGET_COMPONENTS: Record<string, React.ComponentType<{ widget: HubWidget }>> = {
  clock: ClockWidget,
  calendar_upcoming: UpcomingWidget,
  atlas_todos: TodosWidget,
  atlas_reminders: RemindersWidget,
  meridian_my_tasks: MeridianTasksWidget,
  meridian_hot_tasks: MeridianTasksWidget,
  meridian_points: MeridianPointsWidget,
}

export function KioskDashboard({ authUser, onLogout }: Props) {
  const [widgets, setWidgets] = useState<HubWidget[]>([])
  const [loadError, setLoadError] = useState<string | null>(null)
  const [time, setTime] = useState(new Date())
  const [view, setView] = useState<DashboardView>('home')

  // Return to avatar selection after 5 minutes of inactivity.
  useInactivityTimeout(onLogout, 5 * 60 * 1000)

  useEffect(() => {
    const id = setInterval(() => setTime(new Date()), 60_000)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    api.kioskHub()
      .then((data) => setWidgets(data.widgets))
      .catch(() => setLoadError('Could not load hub data.'))
  }, [])

  const pad = (n: number) => String(n).padStart(2, '0')
  const timeStr = `${pad(time.getHours())}:${pad(time.getMinutes())}`
  const avatarIsImage = !!authUser.avatar && isImageAvatar(authUser.avatar)

  const handleLogout = async () => {
    try { await api.logout() } catch { /* ignore */ }
    onLogout()
  }

  return (
    <div className="flex h-full w-full flex-col bg-sunken text-ink">
      {/* Header */}
      <header className="flex items-center justify-between gap-4 border-b-2 border-line-strong bg-raised px-8 py-4 shadow-card">
        <div className="flex items-center gap-3">
          {avatarIsImage ? (
            <img src={authUser.avatar} alt="" className="w-10 h-10 rounded-full object-cover" />
          ) : (
            <div
              className="flex h-11 w-11 items-center justify-center rounded-full text-lg font-bold text-white shadow-soft"
              style={{ backgroundColor: authUser.colour || '#4B5563' }}
            >
              {authUser.avatar || authUser.display_name.slice(0, 2).toUpperCase()}
            </div>
          )}
          <span className="text-lg font-bold">{authUser.display_name}</span>
        </div>
        <span className="text-3xl font-thin tabular-nums text-muted-strong">{timeStr}</span>
        <div className="flex items-center gap-3">
          <div className="flex rounded-xl border border-line-strong bg-sunken p-1">
            {(['home', 'calendar'] as DashboardView[]).map(tab => (
              <button
                key={tab}
                onClick={() => setView(tab)}
                className={`min-h-10 rounded-lg px-4 text-sm font-bold capitalize transition-colors ${
                  view === tab ? 'bg-raised text-primary shadow-soft' : 'text-muted-strong hover:bg-surface'
                }`}
              >
                {tab}
              </button>
            ))}
          </div>
          <KioskThemeToggle />
          <a
            href="/"
            className="flex min-h-11 items-center rounded-lg border border-line-strong bg-raised px-4 py-2 text-sm font-bold text-muted-strong transition-colors hover:bg-primary-soft hover:text-primary"
          >
            Web mode
          </a>
          <button
            onClick={handleLogout}
            className="min-h-11 rounded-lg border border-primary bg-primary-soft px-4 py-2 text-sm font-bold text-primary transition-colors hover:bg-primary hover:text-white"
          >
            Switch user
          </button>
        </div>
      </header>

      {/* Widgets */}
      <main className="flex-1 overflow-auto p-8">
        {view === 'calendar' ? (
          <KioskCalendarView />
        ) : (
          <>
            {loadError && <p className="mb-4 rounded-xl border border-danger bg-danger-soft px-4 py-3 text-danger">{loadError}</p>}
            <div className="flex flex-wrap gap-6">
              {widgets.map((w) => {
                const Component = WIDGET_COMPONENTS[w.key]
                return Component ? <Component key={w.key} widget={w} /> : null
              })}
              {widgets.length === 0 && !loadError && (
                <p className="text-muted">Loading...</p>
              )}
            </div>
            <div className="mt-6 flex flex-col gap-6">
              <KioskRoutines />
              <KioskShop />
              <KioskGoalsWishlist />
              <KioskBadges />
            </div>
          </>
        )}
      </main>
    </div>
  )
}
