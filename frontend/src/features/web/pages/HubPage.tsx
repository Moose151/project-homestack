import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../../api/client'
import type {
  HubResponse,
  HubWidget,
  AtlasListItem,
  AtlasReminder,
  MeridianTask,
  PointsSummaryRow,
  MeridianRewardRequest,
  CalendarEvent,
  EducationAssessment,
  EducationClassSession,
  EducationEvent,
  WikiPage,
  PetTreatment,
  PetAppointment,
  MaintenanceTask,
  Appliance,
  Improvement,
  AppNotification,
} from '../../../api/types'
import { Card } from '../../../components/Card'
import { Input } from '../../../components/Field'
import { Button } from '../../../components/Button'
import { HubConfig } from './HubConfig'
import { useAuth } from '../../auth/AuthContext'
import { STACK_BY_KEY, softColour } from '../../../config/stacks'

const SIZE_SPAN: Record<string, string> = {
  small: 'sm:col-span-1',
  medium: 'sm:col-span-2',
  large: 'sm:col-span-2',
}

// Which stack a hub widget belongs to → its accent colour + icon for the card header.
function widgetAccent(key: string): { colour: string; icon: string } {
  const pick = (k: string) => ({ colour: STACK_BY_KEY[k].colour, icon: STACK_BY_KEY[k].icon })
  if (key.startsWith('atlas')) return pick('atlas')
  if (key.startsWith('meridian')) return pick('meridian')
  if (key.startsWith('education')) return pick('education')
  if (key === 'calendar_upcoming') return pick('calendar')
  return { colour: STACK_BY_KEY.hub.colour, icon: '' } // clock, greeting, other core widgets
}

function formatDue(iso: string | null) {
  if (!iso) return null
  const d = new Date(iso)
  const now = new Date()
  const diff = Math.round((d.getTime() - now.getTime()) / 86400000)
  if (diff === 0) return 'Today'
  if (diff === 1) return 'Tomorrow'
  if (diff === -1) return 'Yesterday'
  if (diff < 0) return `${Math.abs(diff)}d overdue`
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

function calendarDayHref(iso: string | null) {
  if (!iso) return '/calendar'
  return `/calendar?date=${new Date(iso).toISOString().slice(0, 10)}`
}

function TodoWidget({ items }: { items: AtlasListItem[] }) {
  const pending = items.filter(i => !i.is_complete)
  if (pending.length === 0) return <p className="text-sm text-muted">All done ✓</p>
  return (
    <ul className="flex flex-col gap-2">
      {pending.slice(0, 8).map(item => (
        <li key={item.id} className="flex items-center gap-3 text-sm">
          <div className="w-5 h-5 rounded-full border-2 border-line-strong flex-shrink-0" />
          <span className="text-ink">{item.title}</span>
        </li>
      ))}
      {pending.length > 8 && (
        <li className="text-xs text-muted">+{pending.length - 8} more</li>
      )}
    </ul>
  )
}

function RemindersWidget({ items }: { items: AtlasReminder[] }) {
  if (items.length === 0) return <p className="text-sm text-muted">No upcoming reminders</p>
  return (
    <ul className="flex flex-col gap-3">
      {items.slice(0, 6).map(r => {
        const due = formatDue(r.due_at)
        return (
          <li key={r.id} className="flex items-start gap-3">
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-ink truncate">{r.title}</p>
              {r.body && <p className="text-xs text-muted truncate">{r.body}</p>}
              {r.due_at && <Link to={calendarDayHref(r.due_at)} className="text-xs text-primary hover:underline">Open day</Link>}
            </div>
            {due && (
              <span className={`text-xs px-2 py-0.5 rounded-full flex-shrink-0 font-medium ${
                due.includes('overdue')
                  ? 'bg-danger-soft text-danger'
                  : due === 'Today'
                  ? 'bg-primary-soft text-primary'
                  : 'bg-sunken text-muted'
              }`}>
                {due}
              </span>
            )}
          </li>
        )
      })}
    </ul>
  )
}

function TasksWidget({ items }: { items: MeridianTask[] }) {
  if (items.length === 0) return <p className="text-sm text-muted">Nothing here right now</p>
  return (
    <ul className="flex flex-col gap-2">
      {items.slice(0, 8).map(task => (
        <li key={task.id} className="flex items-center gap-3 text-sm">
          <span className="flex-1 min-w-0 truncate text-ink">{task.title}</span>
          {task.is_hot && (
            <span className="text-xs px-2 py-0.5 rounded-full flex-shrink-0 font-medium bg-danger-soft text-danger">
              {task.hot_label || 'Hot'}
            </span>
          )}
          <span className="text-xs px-2 py-0.5 rounded-full flex-shrink-0 font-medium bg-primary-soft text-primary">
            {task.award_value} pts
          </span>
        </li>
      ))}
      {items.length > 8 && (
        <li className="text-xs text-muted">+{items.length - 8} more</li>
      )}
    </ul>
  )
}

function PointsWidget({ items }: { items: PointsSummaryRow[] }) {
  if (items.length === 0) return <p className="text-sm text-muted">No points yet</p>
  return (
    <ul className="flex flex-col gap-2">
      {items.map(row => (
        <li key={row.person_id} className="flex items-center justify-between text-sm">
          <span className="text-ink truncate">{row.display_name}</span>
          <span className="font-semibold text-primary flex-shrink-0">{row.balance} pts</span>
        </li>
      ))}
    </ul>
  )
}

function RewardRequestsWidget({ items }: { items: MeridianRewardRequest[] }) {
  const pending = items.filter(r => r.status === 'pending')
  if (pending.length === 0) return <p className="text-sm text-muted">No requests awaiting approval</p>
  return (
    <ul className="flex flex-col gap-2">
      {pending.slice(0, 8).map(req => (
        <li key={req.id} className="flex items-center justify-between text-sm">
          <span className="text-ink">Reward redemption</span>
          <span className="text-xs px-2 py-0.5 rounded-full flex-shrink-0 font-medium bg-sunken text-muted">
            {req.points_spent} pts · pending
          </span>
        </li>
      ))}
      {pending.length > 8 && (
        <li className="text-xs text-muted">+{pending.length - 8} more</li>
      )}
    </ul>
  )
}

function ClockWidget() {
  const [now, setNow] = useState(new Date())
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(id)
  }, [])
  return (
    <div className="text-center py-2">
      <p className="text-4xl font-thin tabular-nums text-ink">
        {now.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })}
      </p>
      <p className="text-sm text-muted mt-1">
        {now.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' })}
      </p>
    </div>
  )
}

function UpcomingWidget({ items }: { items: CalendarEvent[] }) {
  if (items.length === 0) return <p className="text-sm text-muted">Nothing upcoming</p>
  return (
    <ul className="flex flex-col gap-2">
      {items.slice(0, 6).map(e => {
        const d = new Date(e.start_at)
        const label = e.is_all_day
          ? d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
          : d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })
        return (
          <li key={e.id} className="flex items-center justify-between gap-3 text-sm">
            <span className="text-ink truncate">{e.title}</span>
            <Link to={calendarDayHref(e.start_at)} className="text-xs text-primary hover:underline flex-shrink-0">{label}</Link>
          </li>
        )
      })}
    </ul>
  )
}

function EducationDeadlinesWidget({ items }: { items: EducationAssessment[] }) {
  if (items.length === 0) return <p className="text-sm text-muted">Nothing due</p>
  return (
    <ul className="flex flex-col gap-2">
      {items.slice(0, 6).map(a => {
        const label = a.due_at
          ? new Date(a.due_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
          : ''
        return (
          <li key={a.id} className="flex items-center justify-between gap-3 text-sm">
            <span className="text-ink truncate">
              {a.course_code && <span className="text-muted mr-1">{a.course_code}</span>}
              {a.title}
            </span>
            {label && <Link to={calendarDayHref(a.due_at)} className="text-xs text-primary hover:underline flex-shrink-0">{label}</Link>}
          </li>
        )
      })}
    </ul>
  )
}

function EducationClassesWidget({ items }: { items: EducationClassSession[] }) {
  if (items.length === 0) return <p className="text-sm text-muted">No classes</p>
  return (
    <ul className="flex flex-col gap-2">
      {items.slice(0, 6).map(s => (
        <li key={s.id} className="flex items-center justify-between gap-3 text-sm">
          <span className="text-ink truncate">{s.display_title}</span>
          <span className="text-xs text-muted flex-shrink-0">
            {new Date(s.start_at).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })}
          </span>
        </li>
      ))}
    </ul>
  )
}

function EducationEventsWidget({ items }: { items: EducationEvent[] }) {
  if (items.length === 0) return <p className="text-sm text-muted">No upcoming events</p>
  return (
    <ul className="flex flex-col gap-2">
      {items.slice(0, 6).map(ev => (
        <li key={ev.id} className="flex items-center justify-between gap-3 text-sm">
          <span className="text-ink truncate">{ev.title}</span>
          <Link to={calendarDayHref(ev.start_at)} className="text-xs text-primary hover:underline flex-shrink-0">
            {new Date(ev.start_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
          </Link>
        </li>
      ))}
    </ul>
  )
}

function WikiPagesWidget({ items, emptyLabel }: { items: WikiPage[]; emptyLabel: string }) {
  if (items.length === 0) return <p className="text-sm text-muted">{emptyLabel}</p>
  return (
    <ul className="flex flex-col gap-2">
      {items.slice(0, 6).map(p => (
        <li key={p.id} className="flex items-center justify-between gap-3 text-sm">
          <Link to="/wiki" className="text-ink truncate hover:text-primary">{p.title}</Link>
          {p.category_name && <span className="text-xs text-muted flex-shrink-0">{p.category_name}</span>}
        </li>
      ))}
    </ul>
  )
}

function PetRemindersWidget({ items }: { items: PetTreatment[] }) {
  if (items.length === 0) return <p className="text-sm text-muted">Nothing due</p>
  return (
    <ul className="flex flex-col gap-2">
      {items.slice(0, 6).map(t => (
        <li key={t.id} className="flex items-center justify-between gap-3 text-sm">
          <Link to="/pets" className="text-ink truncate hover:text-primary">
            <span className="text-muted mr-1">{t.pet_name}</span>{t.display_name}
          </Link>
          {t.next_due_at && (
            <span className={`text-xs flex-shrink-0 ${t.is_overdue ? 'text-danger' : 'text-muted'}`}>
              {new Date(t.next_due_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
            </span>
          )}
        </li>
      ))}
    </ul>
  )
}

function PetAppointmentsWidget({ items }: { items: PetAppointment[] }) {
  if (items.length === 0) return <p className="text-sm text-muted">No appointments</p>
  return (
    <ul className="flex flex-col gap-2">
      {items.slice(0, 6).map(a => (
        <li key={a.id} className="flex items-center justify-between gap-3 text-sm">
          <Link to="/pets" className="text-ink truncate hover:text-primary">
            <span className="text-muted mr-1">{a.pet_name}</span>{a.display_title}
          </Link>
          <span className="text-xs text-muted flex-shrink-0">{new Date(a.start_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}</span>
        </li>
      ))}
    </ul>
  )
}

function HomesteadMaintenanceWidget({ items }: { items: MaintenanceTask[] }) {
  if (items.length === 0) return <p className="text-sm text-muted">Nothing due</p>
  return (
    <ul className="flex flex-col gap-2">
      {items.slice(0, 6).map(t => (
        <li key={t.id} className="flex items-center justify-between gap-3 text-sm">
          <Link to="/homestead" className="text-ink truncate hover:text-primary">{t.title}</Link>
          {t.next_due_at && (
            <span className={`text-xs flex-shrink-0 ${t.is_overdue ? 'text-danger' : 'text-muted'}`}>
              {new Date(t.next_due_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
            </span>
          )}
        </li>
      ))}
    </ul>
  )
}

function HomesteadWarrantiesWidget({ items }: { items: Appliance[] }) {
  if (items.length === 0) return <p className="text-sm text-muted">No warranties expiring soon</p>
  return (
    <ul className="flex flex-col gap-2">
      {items.slice(0, 6).map(a => (
        <li key={a.id} className="flex items-center justify-between gap-3 text-sm">
          <Link to="/homestead" className="text-ink truncate hover:text-primary">{a.name}</Link>
          {a.warranty_expires_at && (
            <span className="text-xs text-muted flex-shrink-0">
              {new Date(a.warranty_expires_at).toLocaleDateString(undefined, { month: 'short', year: 'numeric' })}
            </span>
          )}
        </li>
      ))}
    </ul>
  )
}

function HomesteadImprovementsWidget({ items }: { items: Improvement[] }) {
  if (items.length === 0) return <p className="text-sm text-muted">No active improvements</p>
  return (
    <ul className="flex flex-col gap-2">
      {items.slice(0, 6).map(i => (
        <li key={i.id} className="flex items-center justify-between gap-3 text-sm">
          <Link to="/homestead" className="text-ink truncate hover:text-primary">{i.title}</Link>
          <span className="text-xs text-muted flex-shrink-0 capitalize">{i.status.replace('_', ' ')}</span>
        </li>
      ))}
    </ul>
  )
}

const LEVEL_TONE: Record<string, string> = {
  info: 'bg-primary-soft text-primary',
  success: 'bg-success-soft text-success',
  warning: 'bg-warning-soft text-warning',
  danger: 'bg-danger-soft text-danger',
}

function NotificationsSummaryWidget({ items, unread }: { items: AppNotification[]; unread?: number }) {
  if (!items.length) {
    return <p className="text-sm text-muted">{unread ? `${unread} unread` : 'You’re all caught up ✓'}</p>
  }
  return (
    <ul className="flex flex-col gap-2.5">
      {items.slice(0, 5).map(n => {
        const dot = LEVEL_TONE[n.level] ?? LEVEL_TONE.info
        return (
          <li key={n.id} className="flex items-start gap-2.5">
            <span className={`mt-0.5 h-2 w-2 flex-shrink-0 rounded-full ${dot}`} />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-ink">{n.title}</p>
              {n.message && <p className="truncate text-xs text-muted">{n.message}</p>}
            </div>
          </li>
        )
      })}
      {unread !== undefined && unread > items.length && (
        <li className="text-xs text-muted">+{unread - items.length} more unread</li>
      )}
    </ul>
  )
}

const QUICK_KINDS = [
  { key: 'reminder', label: 'Reminder' },
  { key: 'note', label: 'Note' },
] as const
type QuickKind = (typeof QUICK_KINDS)[number]['key']

function QuickAddWidget({ onAdded }: { onAdded: () => void }) {
  const [kind, setKind] = useState<QuickKind>('reminder')
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    const title = text.trim()
    if (!title) return
    setBusy(true); setErr(null); setDone(null)
    try {
      if (kind === 'reminder') await api.createReminder({ title })
      else await api.createNote({ title })
      setText('')
      setDone(kind === 'reminder' ? 'Reminder added ✓' : 'Note saved ✓')
      onAdded()
      setTimeout(() => setDone(null), 2500)
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Could not save')
    } finally { setBusy(false) }
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-2.5">
      <div className="flex gap-1 rounded-xl bg-sunken p-1">
        {QUICK_KINDS.map(k => (
          <button
            key={k.key}
            type="button"
            onClick={() => setKind(k.key)}
            className={`flex-1 rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
              kind === k.key ? 'bg-raised text-ink shadow-soft' : 'text-muted hover:text-ink'
            }`}
          >
            {k.label}
          </button>
        ))}
      </div>
      <div className="flex gap-2">
        <Input
          value={text}
          onChange={e => setText(e.target.value)}
          placeholder={kind === 'reminder' ? 'Remind me to…' : 'Jot something down…'}
          className="flex-1"
        />
        <Button type="submit" size="sm" loading={busy} disabled={!text.trim()}>Add</Button>
      </div>
      {done && <p className="text-xs text-success">{done}</p>}
      {err && <p className="text-xs text-danger">{err}</p>}
    </form>
  )
}

// Small, local, offline set — no external data (Hub spec §6 ambient widget).
const QUOTES = [
  'Small steps every day add up to big journeys.',
  'The best time to start was yesterday. The next best time is now.',
  'A calm home is built one tidy corner at a time.',
  'Done is better than perfect.',
  'Be kind — everyone is fighting a battle you know nothing about.',
  'Today is a good day to do a small good thing.',
  'Progress, not perfection.',
  'The little things? The little moments? They aren’t little.',
]

function DailyQuoteWidget() {
  const dayOfYear = Math.floor((Date.now() - new Date(new Date().getFullYear(), 0, 0).getTime()) / 86400000)
  const quote = QUOTES[dayOfYear % QUOTES.length]
  return <p className="py-1 text-sm italic leading-relaxed text-muted-strong">“{quote}”</p>
}

function renderWidget(w: HubWidget, onChanged: () => void) {
  switch (w.key) {
    case 'clock':
      return <ClockWidget />
    case 'notifications_summary':
      return <NotificationsSummaryWidget items={w.items as AppNotification[]} unread={w.meta?.unread_count} />
    case 'quick_add':
      return <QuickAddWidget onAdded={onChanged} />
    case 'daily_quote':
      return <DailyQuoteWidget />
    case 'calendar_upcoming':
      return <UpcomingWidget items={w.items as CalendarEvent[]} />
    case 'atlas_todos':
      return <TodoWidget items={w.items as AtlasListItem[]} />
    case 'atlas_reminders':
      return <RemindersWidget items={w.items as AtlasReminder[]} />
    case 'meridian_my_tasks':
    case 'meridian_hot_tasks':
    case 'meridian_pending_approvals':
      return <TasksWidget items={w.items as MeridianTask[]} />
    case 'meridian_points':
      return <PointsWidget items={w.items as PointsSummaryRow[]} />
    case 'meridian_reward_requests':
      return <RewardRequestsWidget items={w.items as MeridianRewardRequest[]} />
    case 'education_deadlines':
      return <EducationDeadlinesWidget items={w.items as EducationAssessment[]} />
    case 'education_classes':
      return <EducationClassesWidget items={w.items as EducationClassSession[]} />
    case 'education_events':
      return <EducationEventsWidget items={w.items as EducationEvent[]} />
    case 'wiki_favourites':
      return <WikiPagesWidget items={w.items as WikiPage[]} emptyLabel="No favourite pages" />
    case 'wiki_emergency':
      return <WikiPagesWidget items={w.items as WikiPage[]} emptyLabel="No emergency info" />
    case 'wiki_recent':
      return <WikiPagesWidget items={w.items as WikiPage[]} emptyLabel="Nothing recent" />
    case 'pets_reminders':
      return <PetRemindersWidget items={w.items as PetTreatment[]} />
    case 'pets_appointments':
      return <PetAppointmentsWidget items={w.items as PetAppointment[]} />
    case 'homestead_maintenance':
      return <HomesteadMaintenanceWidget items={w.items as MaintenanceTask[]} />
    case 'homestead_warranties':
      return <HomesteadWarrantiesWidget items={w.items as Appliance[]} />
    case 'homestead_improvements':
      return <HomesteadImprovementsWidget items={w.items as Improvement[]} />
    default:
      return <p className="text-sm text-muted">Nothing to show</p>
  }
}

export function HubPage() {
  const { user } = useAuth()
  const [data, setData] = useState<HubResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [configuring, setConfiguring] = useState(false)

  const loadHub = () => api.hub().then(setData).catch(e => setError(e.message))
  useEffect(() => { loadHub() }, [])

  const now = new Date()
  const greeting =
    now.getHours() < 12 ? 'Good morning' : now.getHours() < 18 ? 'Good afternoon' : 'Good evening'

  if (error) return <div className="text-danger text-sm">{error}</div>

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-ink">
            {greeting}{user ? `, ${user.display_name}` : ''}
          </h1>
          <p className="text-muted text-sm mt-0.5">
            {now.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' })}
          </p>
        </div>
        <button
          onClick={() => setConfiguring(c => !c)}
          className="text-sm text-muted hover:text-ink transition-colors px-3 py-1.5 rounded-xl hover:bg-sunken whitespace-nowrap"
        >
          {configuring ? 'Done' : '⚙ Customise'}
        </button>
      </div>

      {configuring && (
        <HubConfig isAdmin={user?.role === 'admin'} onChanged={loadHub} />
      )}

      {!data ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {[1, 2, 3].map(i => (
            <div key={i} className={`h-36 rounded-2xl bg-sunken animate-pulse ${i === 1 ? 'sm:col-span-2' : ''}`} />
          ))}
        </div>
      ) : data.widgets.length === 0 ? (
        <Card>
          <p className="text-muted text-sm text-center py-4">
            No widgets on your Hub yet. Use <span className="font-medium text-ink">Customise</span> to add some.
          </p>
        </Card>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 items-start">
          {data.widgets.map(w => {
            const accent = widgetAccent(w.key)
            return (
              <div
                key={w.key}
                className={`${SIZE_SPAN[w.size] ?? 'sm:col-span-2'} bg-surface rounded-2xl shadow-soft border border-line overflow-hidden`}
              >
                <div
                  className="flex items-center gap-2 px-4 py-2.5 border-b border-line"
                  style={{ background: softColour(accent.colour, '18') }}
                >
                  <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: accent.colour }} />
                  <h3 className="text-sm font-bold text-ink truncate">{w.name}</h3>
                </div>
                <div className="p-4">{renderWidget(w, loadHub)}</div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
