import { useEffect, useState, type DragEvent } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../../api/client'
import type {
  HubResponse,
  HubWidget,
  AtlasList,
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
  SolaceBill,
  SolaceBillOccurrence,
  SolacePurchase,
  UpcomingHorizon,
  FitnessSession,
} from '../../../api/types'
import { sourceColour, sourceLabel, sourcePath } from '../../../lib/sourceLinks'
import { Card } from '../../../components/Card'
import { Input, Select } from '../../../components/Field'
import { Button } from '../../../components/Button'
import { HubConfig } from './HubConfig'
import { useAuth } from '../../auth/AuthContext'
import { STACK_BY_KEY, softColour } from '../../../config/stacks'
import { InlineAlert, PageSkeleton } from '../../../components/PageState'
import { openGlobalSearch } from '../../../lib/shellEvents'
import { isPhoneViewport } from '../../../lib/viewport'

// Spans are chosen so a board of same-size widgets tiles a row exactly and leaves no dead
// column: at xl the grid is 4 columns, so 4 small / 2 medium / 1 large fills a row.
const SIZE_SPAN: Record<string, string> = {
  small: 'md:col-span-1 xl:col-span-1',
  medium: 'md:col-span-1 xl:col-span-2',
  large: 'md:col-span-2 xl:col-span-4',
}

const MOBILE_ATTENTION_WIDGETS = new Set([
  'notifications_summary', 'meridian_hot_tasks', 'meridian_pending_approvals',
  'meridian_reward_requests', 'education_deadlines', 'pets_reminders', 'pets_appointments',
  'homestead_maintenance', 'homestead_warranties', 'solace_bills_due',
])
const MOBILE_UPCOMING_WIDGETS = new Set([
  'upcoming', 'calendar_upcoming', 'atlas_reminders', 'education_classes', 'education_events',
  'countdown',
])
const MOBILE_QUICK_WIDGETS = new Set(['quick_add', 'atlas_todos', 'meridian_my_tasks'])

function mobileFeedSections(widgets: HubWidget[]) {
  const sections = [
    { key: 'attention', title: 'Needs attention', widgets: widgets.filter(widget => MOBILE_ATTENTION_WIDGETS.has(widget.key)) },
    { key: 'upcoming', title: 'Today & upcoming', widgets: widgets.filter(widget => MOBILE_UPCOMING_WIDGETS.has(widget.key)) },
    { key: 'quick', title: 'Quick actions', widgets: widgets.filter(widget => MOBILE_QUICK_WIDGETS.has(widget.key)) },
  ]
  const prioritized = new Set(sections.flatMap(section => section.widgets.map(widget => widget.key)))
  sections.push({ key: 'more', title: 'More from your home', widgets: widgets.filter(widget => !prioritized.has(widget.key)) })
  return sections.filter(section => section.widgets.length > 0)
}

// Which stack a hub widget belongs to → its accent colour + icon for the card header.
function widgetAccent(key: string): { colour: string; icon: string } {
  const pick = (k: string) => ({ colour: STACK_BY_KEY[k].colour, icon: STACK_BY_KEY[k].icon })
  if (key.startsWith('atlas')) return pick('atlas')
  if (key.startsWith('meridian')) return pick('meridian')
  if (key.startsWith('education')) return pick('education')
  if (key.startsWith('wiki')) return pick('home_wiki')
  if (key.startsWith('pets')) return pick('pets')
  if (key.startsWith('homestead')) return pick('homestead')
  if (key.startsWith('solace')) return pick('solace')
  if (key.startsWith('fitness')) return pick('fitness')
  if (key === 'calendar_upcoming' || key === 'upcoming') return pick('calendar')
  return { colour: STACK_BY_KEY.hub.colour, icon: '' } // clock, greeting, other core widgets
}

const DUE_RECORD_TYPES = new Set([
  'AtlasReminder',
  'Bill',
  'BillOccurrence',
  'EducationAssessment',
  'MaintenanceTask',
  'MeridianTask',
  'PetTreatment',
  'PlannedPurchase',
])

function dayDiff(iso: string) {
  const d = new Date(iso)
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime()
  const target = new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime()
  return Math.round((target - today) / 86400000)
}

function formatDue(iso: string | null) {
  if (!iso) return null
  const diff = dayDiff(iso)
  if (diff === 0) return 'Due today'
  if (diff === 1) return 'Due tomorrow'
  if (diff < 0) return `${Math.abs(diff)}d overdue`
  if (diff <= 7) return `Due in ${diff} days`
  return `Due ${new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}`
}

function formatEventWhen(iso: string | null, isAllDay = false) {
  if (!iso) return null
  const d = new Date(iso)
  const now = new Date()
  const diff = dayDiff(iso)
  if (diff === 0 && !isAllDay) {
    const hours = Math.ceil((d.getTime() - now.getTime()) / 3_600_000)
    if (hours > 0 && hours <= 12) return `Starts in ${hours} hour${hours === 1 ? '' : 's'}`
    return `At ${d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })}`
  }
  if (diff === 0) return 'Today'
  if (diff === 1) return 'Tomorrow'
  if (diff > 1 && diff <= 7) return `In ${diff} days`
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
                  : due === 'Due today'
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

function CountdownWidget({ title, targetDate, targetTime, targetAt }: { title?: string; targetDate?: string; targetTime?: string; targetAt?: string }) {
  const [now, setNow] = useState(new Date())
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 60_000)
    return () => clearInterval(id)
  }, [])

  if (!title || !targetDate) return <p className="text-sm text-muted">Set a name and date in Tune my Hub.</p>
  const target = targetAt ? new Date(targetAt) : new Date(`${targetDate}T${targetTime || '12:00'}:00`)
  const difference = target.getTime() - now.getTime()
  const future = difference > 0
  const absoluteHours = Math.ceil(Math.abs(difference) / 3_600_000)
  const showHours = future && difference <= 48 * 3_600_000
  const amount = showHours ? absoluteHours : Math.ceil(Math.abs(difference) / 86_400_000)
  // Match the page header's date format: the year only earns its place when it isn't this one.
  const targetLabel = target.toLocaleString(undefined, {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    hour: 'numeric', minute: '2-digit',
    ...(target.getFullYear() === now.getFullYear() ? {} : { year: 'numeric' }),
  })

  return (
    <div className="py-2 text-center">
      <p className="text-sm font-bold text-ink">{title}</p>
      {Math.abs(difference) < 60_000 ? (
        <p className="mt-2 text-4xl font-extrabold text-primary">It’s today! 🎉</p>
      ) : (
        <>
          <p className="mt-2 text-5xl font-extrabold tabular-nums text-primary">{amount}</p>
          <p className="text-sm font-semibold text-muted-strong">
            {showHours
              ? `hour${amount === 1 ? '' : 's'} to go`
              : `${amount === 1 ? 'day' : 'days'} ${future ? 'to go' : 'since'}`}
          </p>
        </>
      )}
      <p className="mt-2 text-xs text-muted">{targetLabel}</p>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Upcoming — one card for everything dated, replacing a permanent card per node.
// The backend sends a wide window plus the horizon boundaries, so switching range
// is instant and costs no round trip.
// ---------------------------------------------------------------------------

const HORIZON_STORAGE_KEY = 'hs-upcoming-horizon'

function localDateKey(iso: string) {
  const d = new Date(iso)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

/** "Overdue" / "Today" / "Tomorrow" / "Thu 14 Aug" for a day group. */
function dayHeading(dateKey: string, todayKey: string) {
  if (dateKey < todayKey) return 'Overdue'
  const [y, m, d] = dateKey.split('-').map(Number)
  const date = new Date(y, m - 1, d)
  const today = new Date()
  const diff = Math.round((date.getTime() - new Date(today.getFullYear(), today.getMonth(), today.getDate()).getTime()) / 86400000)
  if (diff === 0) return 'Today'
  if (diff === 1) return 'Tomorrow'
  return date.toLocaleDateString(undefined, { weekday: 'short', day: 'numeric', month: 'short' })
}

function upcomingRowLabel(item: CalendarEvent) {
  if (DUE_RECORD_TYPES.has(item.source_record_type)) return formatDue(item.start_at)
  return formatEventWhen(item.start_at, item.is_all_day)
}

function UpcomingWidget({ items, horizons }: { items: CalendarEvent[]; horizons?: UpcomingHorizon[] }) {
  const ranges = horizons?.length ? horizons : [{ key: 'week', label: 'Next 7 days', until: '9999-12-31' }]
  const [horizonKey, setHorizonKey] = useState(
    () => localStorage.getItem(HORIZON_STORAGE_KEY) || ranges[0].key,
  )
  const active = ranges.find(r => r.key === horizonKey) ?? ranges[0]

  const chooseHorizon = (key: string) => {
    setHorizonKey(key)
    localStorage.setItem(HORIZON_STORAGE_KEY, key)
  }

  const todayKey = localDateKey(new Date().toISOString())
  const visible = items.filter(item => localDateKey(item.start_at) <= active.until)

  // Group by day so a busy week reads as a short agenda rather than a flat list.
  const groups: { key: string; heading: string; items: CalendarEvent[] }[] = []
  for (const item of visible) {
    const dateKey = localDateKey(item.start_at)
    const heading = dayHeading(dateKey, todayKey)
    const bucket = heading === 'Overdue' ? 'overdue' : dateKey
    const existing = groups.find(g => g.key === bucket)
    if (existing) existing.items.push(item)
    else groups.push({ key: bucket, heading, items: [item] })
  }
  groups.sort((a, b) => (a.key === 'overdue' ? -1 : b.key === 'overdue' ? 1 : a.key.localeCompare(b.key)))

  return (
    <div className="flex flex-col gap-3">
      {ranges.length > 1 && (
        <div className="flex gap-1 rounded-xl bg-sunken p-1" role="group" aria-label="Time range">
          {ranges.map(range => (
            <button
              key={range.key}
              type="button"
              onClick={() => chooseHorizon(range.key)}
              aria-pressed={range.key === active.key}
              className={`min-h-9 flex-1 rounded-lg px-2 py-1.5 text-xs font-semibold transition-colors ${
                range.key === active.key ? 'bg-raised text-ink shadow-soft' : 'text-muted hover:text-ink'
              }`}
            >
              {range.label}
            </button>
          ))}
        </div>
      )}

      {groups.length === 0 ? (
        <p className="text-sm text-muted">Nothing in this range — try a longer one.</p>
      ) : (
        <div className="flex flex-col gap-3">
          {groups.map(group => (
            <div key={group.key} className="flex flex-col gap-1.5">
              <p className={`text-xs font-bold uppercase tracking-wide ${group.key === 'overdue' ? 'text-danger' : 'text-muted'}`}>
                {group.heading}
              </p>
              <ul className="flex flex-col gap-1.5">
                {group.items.map(item => {
                  const href = sourcePath(item) ?? calendarDayHref(item.start_at)
                  const when = upcomingRowLabel(item)
                  return (
                    <li key={item.id}>
                      <Link
                        to={href}
                        className="flex min-h-11 items-center gap-2.5 rounded-xl px-2 py-1.5 transition-colors hover:bg-sunken"
                      >
                        <span
                          className="h-2.5 w-2.5 flex-shrink-0 rounded-full"
                          style={{ background: sourceColour(item.source_node) }}
                          aria-hidden
                        />
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-sm font-medium text-ink">{item.title}</span>
                          <span className="block truncate text-xs text-muted">{sourceLabel(item.source_node)}</span>
                        </span>
                        {when && <span className="flex-shrink-0 text-xs tabular-nums text-muted">{when}</span>}
                      </Link>
                    </li>
                  )
                })}
              </ul>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function CalendarUpcomingWidget({ items }: { items: CalendarEvent[] }) {
  if (items.length === 0) return <p className="text-sm text-muted">Nothing upcoming</p>
  return (
    <ul className="flex flex-col gap-2">
      {items.slice(0, 6).map(e => {
        const label = formatEventWhen(e.start_at, e.is_all_day)
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
          <Link to={`/wiki?q=${encodeURIComponent(p.title)}`} className="text-ink truncate hover:text-primary">{p.title}</Link>
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
          <Link to={`/pets?tab=reminders&q=${encodeURIComponent(t.display_name)}`} className="text-ink truncate hover:text-primary">
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
          <Link to={`/pets?tab=appointments&q=${encodeURIComponent(a.display_title)}`} className="text-ink truncate hover:text-primary">
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
          <Link to={`/homestead?tab=maintenance&q=${encodeURIComponent(t.title)}`} className="text-ink truncate hover:text-primary">{t.title}</Link>
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
          <Link to={`/homestead?tab=appliances&q=${encodeURIComponent(a.name)}`} className="text-ink truncate hover:text-primary">{a.name}</Link>
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
          <Link to={`/homestead?tab=improvements&q=${encodeURIComponent(i.title)}`} className="text-ink truncate hover:text-primary">{i.title}</Link>
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

function SolaceBillsWidget({ items, meta }: { items: SolaceBillOccurrence[]; meta?: HubWidget['meta'] }) {
  if (meta?.locked) {
    return (
      <div className="space-y-3">
        <p className="text-sm text-muted">Unlock Money to view your payday and bill summary.</p>
        <Link to="/solace" className="inline-flex min-h-11 items-center text-sm font-bold text-primary hover:underline">Open Money →</Link>
      </div>
    )
  }
  if (meta?.configured === false) {
    return (
      <div className="space-y-3">
        <p className="text-sm text-muted">Add an active income date so HomeStack can determine the next payday.</p>
        <Link to="/solace?tab=plan&section=paydays" className="inline-flex min-h-11 items-center text-sm font-bold text-primary hover:underline">Configure income →</Link>
      </div>
    )
  }
  const payday = meta?.next_payday
    ? new Date(`${meta.next_payday}T00:00:00`).toLocaleDateString(undefined, { weekday: 'short', day: 'numeric', month: 'short' })
    : 'Not available'
  return (
    <div className="space-y-3">
      <div className="rounded-xl bg-sunken px-3 py-2.5">
        <p className="text-xs font-semibold text-muted">Next payday: <span className="text-ink">{payday}</span></p>
        <div className="mt-1 flex items-end justify-between gap-3">
          <p className="text-sm font-bold text-ink">{meta?.bill_count ?? items.length} bill{(meta?.bill_count ?? items.length) === 1 ? '' : 's'}</p>
          <p className="text-lg font-extrabold text-ink">{moneyLabel(meta?.total ?? 0)}</p>
        </div>
        {!!meta?.overdue_count && <p className="mt-1 text-xs font-bold text-danger">{meta.overdue_count} overdue</p>}
      </div>
      {items.length === 0 ? (
        <p className="text-sm text-muted">Nothing unpaid is due before payday.</p>
      ) : (
        <ul className="space-y-1.5">
          {items.slice(0, 4).map(occurrence => {
            const params = new URLSearchParams({
              tab: 'bills', section: 'upcoming', bill: String(occurrence.bill_id),
              occurrence: String(occurrence.id),
            })
            return (
              <li key={occurrence.id}>
                <Link to={`/solace?${params.toString()}`} className="flex min-h-11 items-center justify-between gap-3 rounded-xl px-2 hover:bg-sunken">
                  <span className="min-w-0">
                    <span className="block truncate text-sm font-medium text-ink">{occurrence.bill_name}</span>
                    <span className={`block text-xs ${occurrence.is_overdue ? 'font-bold text-danger' : 'text-muted'}`}>{formatDue(occurrence.due_at)}</span>
                  </span>
                  <span className="shrink-0 text-sm font-semibold text-ink">{moneyLabel(occurrence.amount)}</span>
                </Link>
              </li>
            )
          })}
        </ul>
      )}
      <Link to="/solace?tab=bills&section=upcoming" className="inline-flex min-h-11 w-full items-center justify-center rounded-xl text-sm font-bold text-primary hover:bg-primary-soft">View all upcoming bills →</Link>
    </div>
  )
}

function SolaceSubscriptionsWidget({ items }: { items: SolaceBill[] }) {
  if (!items.length) return <p className="text-sm text-muted">No active subscriptions</p>
  return (
    <ul className="space-y-2.5">
      {items.slice(0, 6).map(item => (
        <li key={item.id} className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-ink">{item.name}</p>
            <p className="text-xs text-muted">{moneyLabel(item.amount)}</p>
          </div>
          <Link to="/solace?tab=subscriptions" className="shrink-0 text-xs text-primary hover:underline">
            {formatDue(item.next_due_at || item.due_at)}
          </Link>
        </li>
      ))}
    </ul>
  )
}

function SolacePurchasesWidget({ items }: { items: SolacePurchase[] }) {
  if (!items.length) return <p className="text-sm text-muted">No planned purchases</p>
  return (
    <ul className="space-y-2.5">
      {items.slice(0, 6).map(item => (
        <li key={item.id} className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-ink">{item.name}</p>
            <p className="text-xs text-muted">{moneyLabel(item.saved_amount)} of {moneyLabel(item.target_amount)}</p>
          </div>
          <Link to="/solace?tab=purchases" className="shrink-0 text-xs text-primary hover:underline">
            {item.progress_percent}%
          </Link>
        </li>
      ))}
    </ul>
  )
}

function FitnessRecentWidget({ items }: { items: FitnessSession[] }) {
  return (
    <ul className="space-y-2.5">
      {items.slice(0, 6).map(session => (
        <li key={session.id} className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-ink">{session.person_name} · {session.name}</p>
            <p className="text-xs text-muted">{Math.round((session.duration_seconds || 0) / 60)} min · {session.total_reps} reps</p>
          </div>
          <Link to="/fitness?tab=history" className="shrink-0 text-xs font-semibold text-primary hover:underline">
            {session.personal_records.length ? `🏆 ${session.personal_records.length}` : 'View'}
          </Link>
        </li>
      ))}
    </ul>
  )
}

function moneyLabel(value: string | number) {
  return Number(value || 0).toLocaleString(undefined, { style: 'currency', currency: 'AUD' })
}

// Same three kinds, in the same order, as the Lists page's capture box — it was the odd one
// out offering only two, so the same job had two different answers depending on where you
// started it. A to-do needs a list to live in, which is why one is chosen here too.
const QUICK_KINDS = [
  { key: 'todo', label: 'To-do' },
  { key: 'note', label: 'Note' },
  { key: 'reminder', label: 'Reminder' },
] as const
type QuickKind = (typeof QUICK_KINDS)[number]['key']

function QuickAddWidget({ onAdded }: { onAdded: () => void }) {
  const [kind, setKind] = useState<QuickKind>('todo')
  const [text, setText] = useState('')
  const [lists, setLists] = useState<AtlasList[]>([])
  const [listId, setListId] = useState<number | null>(null)
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    api.getLists()
      .then(rows => { setLists(rows); setListId(current => current ?? rows[0]?.id ?? null) })
      .catch(() => { /* a missing list only disables to-do capture, not the widget */ })
  }, [])

  const needsList = kind === 'todo'
  const canSubmit = Boolean(text.trim()) && (!needsList || listId !== null)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    const title = text.trim()
    if (!canSubmit) return
    setBusy(true); setErr(null); setDone(null)
    try {
      if (kind === 'reminder') await api.createReminder({ title })
      else if (kind === 'note') await api.createNote({ title })
      else await api.createItem(listId!, { title })
      setText('')
      setDone(kind === 'reminder' ? 'Reminder added ✓' : kind === 'note' ? 'Note saved ✓' : 'To-do added ✓')
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
            aria-pressed={kind === k.key}
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
          placeholder={kind === 'reminder' ? 'Remind me to…' : kind === 'note' ? 'Jot something down…' : 'Add a to-do…'}
          className="flex-1"
        />
        <Button type="submit" size="sm" loading={busy} disabled={!canSubmit}>Add</Button>
      </div>
      {needsList && (
        lists.length > 0 ? (
          <Select
            value={listId ?? 0}
            onChange={e => setListId(Number(e.target.value))}
            aria-label="List for this to-do"
          >
            {lists.map(list => <option key={list.id} value={list.id}>{list.title}</option>)}
          </Select>
        ) : (
          <p className="text-xs text-muted">Create a list first to capture to-dos.</p>
        )
      )}
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
    case 'countdown':
      return <CountdownWidget title={w.meta?.title} targetDate={w.meta?.target_date} targetTime={w.meta?.target_time} targetAt={w.meta?.target_at} />
    case 'notifications_summary':
      return <NotificationsSummaryWidget items={w.items as AppNotification[]} unread={w.meta?.unread_count} />
    case 'quick_add':
      return <QuickAddWidget onAdded={onChanged} />
    case 'daily_quote':
      return <DailyQuoteWidget />
    case 'upcoming':
      return <UpcomingWidget items={w.items as CalendarEvent[]} horizons={w.meta?.horizons} />
    case 'calendar_upcoming':
      return <CalendarUpcomingWidget items={w.items as CalendarEvent[]} />
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
    case 'solace_bills_due':
      return <SolaceBillsWidget items={w.items as SolaceBillOccurrence[]} meta={w.meta} />
    case 'solace_subscriptions':
      return <SolaceSubscriptionsWidget items={w.items as SolaceBill[]} />
    case 'solace_planned_purchases':
      return <SolacePurchasesWidget items={w.items as SolacePurchase[]} />
    case 'fitness_recent':
      return <FitnessRecentWidget items={w.items as FitnessSession[]} />
    default:
      return <p className="text-sm text-muted">Nothing to show</p>
  }
}

export function HubPage() {
  const { user } = useAuth()
  const [phone] = useState(isPhoneViewport)
  const [data, setData] = useState<HubResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [configuring, setConfiguring] = useState(false)
  const [draggedWidget, setDraggedWidget] = useState<string | null>(null)
  const [dragOverWidget, setDragOverWidget] = useState<string | null>(null)
  const [savingOrder, setSavingOrder] = useState(false)
  const [configVersion, setConfigVersion] = useState(0)

  const loadHub = () => api.hub().then(setData).catch(e => setError(e.message))
  useEffect(() => { loadHub() }, [])

  const beginWidgetDrag = (event: DragEvent, key: string) => {
    if (!configuring || savingOrder) { event.preventDefault(); return }
    event.dataTransfer.effectAllowed = 'move'
    event.dataTransfer.setData('text/plain', key)
    setDraggedWidget(key)
  }

  const dropWidget = async (event: DragEvent, targetKey: string) => {
    event.preventDefault()
    const sourceKey = draggedWidget || event.dataTransfer.getData('text/plain')
    setDraggedWidget(null); setDragOverWidget(null)
    if (!data || !sourceKey || sourceKey === targetKey || savingOrder) return
    const previous = data
    const next = [...data.widgets]
    const from = next.findIndex(widget => widget.key === sourceKey)
    const to = next.findIndex(widget => widget.key === targetKey)
    if (from < 0 || to < 0) return
    const [moved] = next.splice(from, 1)
    next.splice(to, 0, moved)
    setData({ widgets: next })
    setSavingOrder(true); setError(null)
    try {
      await api.setUserWidgetOrder(next.map(widget => widget.key))
      const refreshed = await api.hub()
      setData(refreshed)
      setConfigVersion(value => value + 1)
    } catch (reason) {
      setData(previous)
      setError(reason instanceof Error ? reason.message : 'Could not save the new widget order.')
    } finally {
      setSavingOrder(false)
    }
  }

  const widgetCard = (widget: HubWidget, desktopBoard = false) => {
    const accent = widgetAccent(widget.key)
    return (
      <div
        key={widget.key}
        onDragOver={desktopBoard ? event => {
          if (!configuring) return
          event.preventDefault()
          event.dataTransfer.dropEffect = 'move'
          setDragOverWidget(widget.key)
        } : undefined}
        onDragLeave={desktopBoard ? () => setDragOverWidget(current => current === widget.key ? null : current) : undefined}
        onDrop={desktopBoard ? event => void dropWidget(event, widget.key) : undefined}
        className={`${desktopBoard ? SIZE_SPAN[widget.size] ?? SIZE_SPAN.medium : ''} overflow-hidden rounded-2xl border bg-surface shadow-soft transition-all ${
          dragOverWidget === widget.key && draggedWidget !== widget.key
            ? 'border-primary ring-2 ring-primary/20'
            : 'border-line'
        } ${draggedWidget === widget.key ? 'opacity-50' : ''}`}
      >
        <div
          className="flex items-center gap-2 border-b border-line px-4 py-2.5"
          style={{ background: softColour(accent.colour, '18') }}
        >
          {accent.icon
            ? <span className="grid h-8 w-8 flex-shrink-0 place-items-center rounded-xl bg-surface/75 text-base shadow-sm">{accent.icon}</span>
            : <span className="h-2.5 w-2.5 flex-shrink-0 rounded-full" style={{ background: accent.colour }} />}
          <h3 className="truncate text-sm font-bold text-ink">{widget.name}</h3>
          {desktopBoard && configuring && (
            <span
              draggable={!savingOrder}
              onDragStart={event => beginWidgetDrag(event, widget.key)}
              onDragEnd={() => { setDraggedWidget(null); setDragOverWidget(null) }}
              className="ml-auto hidden h-8 w-9 cursor-grab select-none items-center justify-center rounded-lg bg-surface/70 text-lg text-muted hover:text-ink active:cursor-grabbing md:flex"
              title={`Drag ${widget.name}`}
              aria-label={`Drag ${widget.name} to reorder`}
            >
              ⠿
            </span>
          )}
        </div>
        <div className="p-4">{renderWidget(widget, loadHub)}</div>
      </div>
    )
  }

  const now = new Date()
  const greeting =
    now.getHours() < 12 ? 'Good morning' : now.getHours() < 18 ? 'Good afternoon' : 'Good evening'
  return (
    <div className="flex flex-col gap-5 sm:gap-6">
      {/* The top bar already says "Home", so this is a greeting line rather than a second
          page header repeating the destination name. */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-semibold text-muted-strong">
          {greeting}{user ? `, ${user.display_name}` : ''} · {now.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' })}
        </p>
        {!phone && (
          <Button variant="secondary" size="sm" onClick={() => setConfiguring(c => !c)}>
            {configuring ? 'Done tuning' : 'Tune this page'}
          </Button>
        )}
      </div>

      {phone && (
        <button
          type="button"
          onClick={openGlobalSearch}
          className="flex min-h-14 w-full items-center gap-3 rounded-2xl border border-line bg-surface px-4 text-left shadow-soft transition-colors hover:border-primary/40 hover:bg-primary-soft/40"
          aria-label="Search HomeStack"
        >
          <span className="grid h-10 w-10 flex-none place-items-center rounded-xl bg-primary-soft text-xl text-primary">⌕</span>
          <span className="min-w-0 flex-1">
            <span className="block text-base font-bold text-ink">Search HomeStack</span>
            <span className="block text-sm text-muted">Find a list, event, room, person or record</span>
          </span>
          <span className="text-xl text-muted">›</span>
        </button>
      )}

      {error && <InlineAlert message={error} onRetry={loadHub} onDismiss={() => setError(null)} />}

      {configuring && (
        <HubConfig key={configVersion} isAdmin={user?.role === 'admin'} onChanged={loadHub} />
      )}

      {!data ? <PageSkeleton /> : (
        phone ? (
          <div className="flex flex-col gap-5" aria-label="Your daily feed">
            {data.widgets.length === 0 ? (
              <Card>
                <p className="py-4 text-center text-sm text-muted">Nothing needs your attention right now.</p>
              </Card>
            ) : mobileFeedSections(data.widgets).map(section => (
              <section key={section.key} className="flex flex-col gap-2">
                <h2 className="px-1 text-xs font-bold uppercase tracking-wide text-muted">{section.title}</h2>
                <div className="flex flex-col gap-3">{section.widgets.map(widget => widgetCard(widget))}</div>
              </section>
            ))}
            <Button variant="ghost" className="w-full" onClick={() => setConfiguring(c => !c)}>
              {configuring ? 'Done tuning Home' : 'Tune Home'}
            </Button>
          </div>
        ) : (
          data.widgets.length === 0 ? (
            <div>
              <Card>
                <p className="py-4 text-center text-sm text-muted">
                  Nothing needs your attention right now. Cards appear here as things come up — use{' '}
                  <span className="font-medium text-ink">Tune this page</span> to choose which ones.
                </p>
              </Card>
            </div>
          ) : (
            <div className="grid grid-cols-1 items-start gap-4 md:grid-cols-2 xl:grid-cols-4">
              {data.widgets.map(widget => widgetCard(widget, true))}
            </div>
          )
        )
      )}
    </div>
  )
}
