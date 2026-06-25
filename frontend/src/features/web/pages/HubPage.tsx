import { useEffect, useState } from 'react'
import { api } from '../../../api/client'
import type {
  HubResponse,
  HubWidget,
  AtlasListItem,
  AtlasReminder,
  MeridianTask,
  PointsSummaryRow,
  MeridianRewardRequest,
} from '../../../api/types'
import { Card } from '../../../components/Card'

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

function renderWidget(w: HubWidget) {
  switch (w.key) {
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
    default:
      return <p className="text-sm text-muted">Nothing to show</p>
  }
}

export function HubPage() {
  const [data, setData] = useState<HubResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.hub()
      .then(setData)
      .catch(e => setError(e.message))
  }, [])

  const now = new Date()
  const greeting =
    now.getHours() < 12 ? 'Good morning' : now.getHours() < 18 ? 'Good afternoon' : 'Good evening'

  if (error) return <div className="text-danger text-sm">{error}</div>

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-extrabold tracking-tight text-ink">{greeting}</h1>
        <p className="text-muted text-sm mt-0.5">
          {now.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' })}
        </p>
      </div>

      {!data ? (
        <div className="flex flex-col gap-4">
          {[1, 2].map(i => (
            <div key={i} className="h-32 rounded-2xl bg-sunken animate-pulse" />
          ))}
        </div>
      ) : data.widgets.length === 0 ? (
        <Card>
          <p className="text-muted text-sm text-center py-4">No widgets configured yet.</p>
        </Card>
      ) : (
        <div className="flex flex-col gap-4">
          {data.widgets.map(w => (
            <Card key={w.key} title={w.name}>
              {renderWidget(w)}
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
