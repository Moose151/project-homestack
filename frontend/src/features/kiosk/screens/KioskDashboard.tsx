import { useEffect, useState } from 'react'
import { api } from '../../../api/client'
import type {
  AuthUser, HubWidget, AtlasListItem as ListItem, AtlasReminder as Reminder,
  MeridianTask, PointsSummaryRow, MeridianReward, MeridianRoutine,
  MeridianGoal, MeridianWishlistItem, PersonBadge, CalendarEvent,
} from '../../../api/types'
import { useInactivityTimeout } from '../hooks/useInactivityTimeout'

interface Props {
  authUser: AuthUser
  onLogout: () => void
}

function TodosWidget({ widget }: { widget: HubWidget }) {
  const items = widget.items as ListItem[]
  return (
    <div className="bg-gray-800 rounded-2xl p-6 flex-1 min-w-[280px]">
      <h2 className="text-lg font-semibold text-gray-200 mb-4">{widget.name}</h2>
      {items.length === 0 ? (
        <p className="text-gray-500 text-sm">Nothing to do 🎉</p>
      ) : (
        <ul className="space-y-3">
          {items.map((item) => (
            <li key={item.id} className="flex items-start gap-3">
              <span className="mt-1 w-4 h-4 rounded border border-gray-500 flex-shrink-0" />
              <span className="text-gray-200">{item.title}</span>
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
    <div className="bg-gray-800 rounded-2xl p-6 flex-1 min-w-[280px]">
      <h2 className="text-lg font-semibold text-gray-200 mb-4">{widget.name}</h2>
      {items.length === 0 ? (
        <p className="text-gray-500 text-sm">No upcoming reminders</p>
      ) : (
        <ul className="space-y-3">
          {items.map((item) => (
            <li key={item.id} className="flex flex-col gap-0.5">
              <span className="text-gray-200">{item.title}</span>
              {item.due_at && <span className="text-xs text-gray-500">{fmt(item.due_at)}</span>}
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
      <p className="mt-1 text-amber-300 text-lg">Great job!</p>
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
    <div className="bg-gray-800 rounded-2xl p-6 flex-1 min-w-[280px]">
      <h2 className="text-lg font-semibold text-gray-200 mb-4">{widget.name}</h2>
      {celebrate && <Celebration label={celebrate} onDone={() => setCelebrate(null)} />}
      {tasks.length === 0 ? (
        <p className="text-gray-500 text-sm">All done — nice! 🎉</p>
      ) : (
        <ul className="space-y-3">
          {tasks.map(task => (
            <li key={task.id}>
              <button
                onClick={() => complete(task)}
                disabled={busy === task.id || task.status === 'pending'}
                className="w-full flex items-center justify-between gap-3 rounded-xl bg-gray-700 hover:bg-gray-600 disabled:opacity-60 px-4 py-4 text-left transition-colors min-h-[64px]"
              >
                <span className="flex items-center gap-2 text-gray-100 text-lg">
                  {task.is_hot && <span>🔥</span>}
                  {task.title}
                </span>
                <span className="flex items-center gap-2 flex-shrink-0">
                  <span className="text-amber-300 font-bold">★ {task.award_value ?? task.points}</span>
                  {task.status === 'pending'
                    ? <span className="text-xs text-gray-400">Waiting…</span>
                    : <span className="text-2xl text-gray-400">○</span>}
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
    <div className="bg-gray-800 rounded-2xl p-6 flex-1 min-w-[280px]">
      <h2 className="text-lg font-semibold text-gray-200 mb-4">{widget.name}</h2>
      {rows.length === 0 ? (
        <p className="text-gray-500 text-sm">No points yet — complete a task!</p>
      ) : (
        <ul className="space-y-3">
          {rows.map(row => (
            <li key={row.person_id} className="flex items-center justify-between">
              <span className="text-gray-200">{row.display_name || `Person ${row.person_id}`}</span>
              <span className="text-2xl font-bold text-amber-300">★ {row.balance}</span>
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
    <div className="bg-gray-800 rounded-2xl p-6 w-full">
      <h2 className="text-lg font-semibold text-gray-200 mb-4">My badges</h2>
      <div className="flex flex-wrap gap-4">
        {badges.map(b => (
          <div key={b.id} title={b.badge.description} className="flex flex-col items-center w-20 text-center">
            <span className="text-4xl">{b.badge.icon}</span>
            <span className="text-xs text-gray-300 mt-1 leading-tight">{b.badge.name}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// Kiosk goals + wishlist — progress bars with quick-contribute buttons.
function KioskBar({ pct }: { pct: number }) {
  return (
    <div className="h-2 rounded-full bg-gray-600 overflow-hidden mt-2">
      <div className="h-full bg-amber-400" style={{ width: `${Math.min(100, pct)}%` }} />
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
    <div key={key} className="bg-gray-700 rounded-xl p-4">
      <p className="text-gray-100 font-medium">{title}</p>
      <KioskBar pct={pct} />
      <p className="text-xs text-gray-400 mt-1">★ {saved} / {target}</p>
      <div className="flex gap-2 mt-2">
        {amounts.map(n => (
          <button key={n} disabled={busy === key || balance < n}
            onClick={() => give(key, () => contribute(n))}
            className="px-3 py-1 rounded-lg bg-amber-500/80 hover:bg-amber-500 disabled:opacity-40 text-sm font-semibold text-gray-900">
            +{n}
          </button>
        ))}
      </div>
    </div>
  )

  return (
    <div className="bg-gray-800 rounded-2xl p-6 w-full">
      <h2 className="text-lg font-semibold text-gray-200 mb-4">Goals &amp; Wishlist · ★ {balance}</h2>
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
    <div className="bg-gray-800 rounded-2xl p-6 w-full">
      {celebrate && <Celebration label={celebrate} onDone={() => setCelebrate(null)} />}
      <h2 className="text-lg font-semibold text-gray-200 mb-4">Routines</h2>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {routines.map(r => (
          <button
            key={r.id}
            onClick={() => complete(r)}
            disabled={busy === r.id || !!r.done_today}
            className={`flex flex-col rounded-xl px-4 py-4 text-left transition-colors min-h-[96px] disabled:opacity-60
              ${r.done_today ? 'bg-green-900/40' : 'bg-gray-700 hover:bg-gray-600'}`}
          >
            <span className="text-gray-100 text-lg font-medium">{r.done_today && '✅ '}{r.title}</span>
            <span className="mt-auto pt-2 flex items-center gap-2">
              <span className="text-amber-300 font-bold">+{r.points}</span>
              {(r.streak ?? 0) > 0 && <span className="text-orange-300 text-sm">🔥 {r.streak}</span>}
              {r.done_today && <span className="text-green-300 text-sm ml-auto">Done</span>}
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
    <div className="bg-gray-800 rounded-2xl p-6 w-full">
      {celebrate && <Celebration label={celebrate} onDone={() => setCelebrate(null)} />}
      <h2 className="text-lg font-semibold text-gray-200 mb-4">Reward shop · ★ {balance}</h2>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {rewards.map(r => {
          const cant = balance < r.cost_points || (r.remaining_stock !== null && r.remaining_stock <= 0)
          return (
            <button
              key={r.id}
              onClick={() => request(r)}
              disabled={busy === r.id || cant}
              className="flex flex-col rounded-xl bg-gray-700 hover:bg-gray-600 disabled:opacity-50 overflow-hidden text-left transition-colors"
            >
              {r.image_url && <img src={r.image_url} alt="" className="h-24 w-full object-cover" />}
              <div className="p-3">
                <p className="text-gray-100 font-medium leading-tight">{r.name}</p>
                <p className="text-amber-300 font-bold mt-1">★ {r.cost_points}</p>
                {cant && <p className="text-xs text-gray-400 mt-1">{balance < r.cost_points ? 'Not enough' : 'Out of stock'}</p>}
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
    <div className="bg-gray-800 rounded-2xl p-6 flex-1 min-w-[280px] text-center">
      <h2 className="text-lg font-semibold text-gray-200 mb-2">{widget.name}</h2>
      <p className="text-5xl font-thin tabular-nums text-white">
        {now.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })}
      </p>
      <p className="text-gray-400 mt-2">
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
    <div className="bg-gray-800 rounded-2xl p-6 flex-1 min-w-[280px]">
      <h2 className="text-lg font-semibold text-gray-200 mb-4">{widget.name}</h2>
      {items.length === 0 ? (
        <p className="text-gray-500 text-sm">Nothing upcoming</p>
      ) : (
        <ul className="space-y-3">
          {items.map((e) => (
            <li key={e.id} className="flex flex-col gap-0.5">
              <span className="text-gray-200">{e.title}</span>
              <span className="text-xs text-gray-500">{fmt(e.start_at, e.is_all_day)}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
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

  const handleLogout = async () => {
    try { await api.logout() } catch { /* ignore */ }
    onLogout()
  }

  return (
    <div className="flex flex-col w-full h-full bg-gray-900 text-white">
      {/* Header */}
      <header className="flex items-center justify-between px-8 py-5 border-b border-gray-800">
        <div className="flex items-center gap-3">
          {authUser.avatar ? (
            <img src={authUser.avatar} alt="" className="w-10 h-10 rounded-full object-cover" />
          ) : (
            <div
              className="w-10 h-10 rounded-full flex items-center justify-center font-semibold text-sm"
              style={{ backgroundColor: authUser.colour || '#4B5563' }}
            >
              {authUser.display_name.slice(0, 2).toUpperCase()}
            </div>
          )}
          <span className="text-lg font-medium">{authUser.display_name}</span>
        </div>
        <span className="text-3xl font-thin tabular-nums text-gray-300">{timeStr}</span>
        <button
          onClick={handleLogout}
          className="px-4 py-2 rounded-lg bg-gray-700 hover:bg-gray-600 text-sm text-gray-300 transition-colors"
        >
          Sign out
        </button>
      </header>

      {/* Widgets */}
      <main className="flex-1 overflow-auto p-8">
        {loadError && <p className="text-red-400 mb-4">{loadError}</p>}
        <div className="flex flex-wrap gap-6">
          {widgets.map((w) => {
            const Component = WIDGET_COMPONENTS[w.key]
            return Component ? <Component key={w.key} widget={w} /> : null
          })}
          {widgets.length === 0 && !loadError && (
            <p className="text-gray-500">Loading…</p>
          )}
        </div>
        <div className="mt-6 flex flex-col gap-6">
          <KioskRoutines />
          <KioskShop />
          <KioskGoalsWishlist />
          <KioskBadges />
        </div>
      </main>
    </div>
  )
}
