import { useEffect, useState } from 'react'
import { api } from '../../../api/client'
import type {
  MeridianPointsResponse, MeridianReward, MeridianRewardRequest, MeridianTask,
} from '../../../api/types'
import { Card } from '../../../components/Card'
import { Button } from '../../../components/Button'
import { useAuth } from '../../auth/AuthContext'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const STATUS_STYLES: Record<string, string> = {
  available: 'bg-primary-soft text-primary',
  pending: 'bg-warning-soft text-warning',
  approved: 'bg-success-soft text-success',
  rejected: 'bg-danger-soft text-danger',
}

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full capitalize ${STATUS_STYLES[status] ?? 'bg-sunken text-muted'}`}>
      {status}
    </span>
  )
}

function PointsPill({ points }: { points: number }) {
  return (
    <span className="inline-flex items-center gap-1 text-sm font-bold text-primary">
      ★ {points}
    </span>
  )
}

// ---------------------------------------------------------------------------
// Tasks tab
// ---------------------------------------------------------------------------

function TasksTab({ canManage }: { canManage: boolean }) {
  const [tasks, setTasks] = useState<MeridianTask[]>([])
  const [loading, setLoading] = useState(true)
  const [title, setTitle] = useState('')
  const [points, setPoints] = useState('5')
  const [saving, setSaving] = useState(false)

  const reload = () => api.getMeridianTasks().then(setTasks).finally(() => setLoading(false))
  useEffect(() => { reload() }, [])

  const create = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim()) return
    setSaving(true)
    try {
      await api.createMeridianTask({ title: title.trim(), points: Number(points) || 0 })
      setTitle('')
      setPoints('5')
      await reload()
    } finally {
      setSaving(false)
    }
  }

  const act = async (fn: Promise<unknown>) => { await fn.catch(() => {}); await reload() }

  if (loading) return <div className="h-32 rounded-2xl bg-sunken animate-pulse" />

  return (
    <div className="flex flex-col gap-4">
      {canManage && (
        <Card title="New task">
          <form onSubmit={create} className="flex flex-col sm:flex-row gap-2">
            <input
              value={title}
              onChange={e => setTitle(e.target.value)}
              placeholder="Task name…"
              className="flex-1 px-3 py-2.5 rounded-xl border border-line bg-raised text-sm text-ink placeholder-muted outline-none focus:ring-2 focus:ring-primary"
            />
            <input
              type="number" min="0" value={points}
              onChange={e => setPoints(e.target.value)}
              className="w-24 px-3 py-2.5 rounded-xl border border-line bg-raised text-sm text-ink outline-none focus:ring-2 focus:ring-primary"
              aria-label="Points"
            />
            <Button type="submit" loading={saving} disabled={!title.trim()}>Add</Button>
          </form>
        </Card>
      )}

      {tasks.length === 0 ? (
        <p className="text-sm text-muted text-center py-8">No tasks yet.</p>
      ) : (
        tasks.map(task => (
          <Card key={task.id}>
            <div className="flex items-start gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  {task.is_hot && <span title="Hot task">🔥</span>}
                  <h3 className="font-bold text-ink">{task.title}</h3>
                  <StatusBadge status={task.status} />
                </div>
                {task.description && <p className="text-sm text-muted mt-0.5">{task.description}</p>}
                {task.rejection_reason && (
                  <p className="text-xs text-danger mt-1">Rejected: {task.rejection_reason}</p>
                )}
                <div className="mt-2"><PointsPill points={task.points} /></div>
              </div>
              <div className="flex flex-col gap-2 items-end flex-shrink-0">
                {task.status === 'available' && (
                  <Button size="sm" variant="secondary" onClick={() => act(api.completeMeridianTask(task.id))}>
                    Complete
                  </Button>
                )}
                {task.status === 'pending' && canManage && (
                  <div className="flex gap-2">
                    <Button size="sm" onClick={() => act(api.approveMeridianTask(task.id))}>Approve</Button>
                    <Button size="sm" variant="ghost" onClick={() => act(api.rejectMeridianTask(task.id))}>Reject</Button>
                  </div>
                )}
                {canManage && (
                  <button
                    onClick={() => { if (confirm(`Delete "${task.title}"?`)) act(api.deleteMeridianTask(task.id)) }}
                    className="text-muted hover:text-danger transition-colors text-lg leading-none"
                    aria-label="Delete task"
                  >×</button>
                )}
              </div>
            </div>
          </Card>
        ))
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Rewards tab
// ---------------------------------------------------------------------------

function RewardsTab({ canManage }: { canManage: boolean }) {
  const [rewards, setRewards] = useState<MeridianReward[]>([])
  const [requests, setRequests] = useState<MeridianRewardRequest[]>([])
  const [loading, setLoading] = useState(true)
  const [name, setName] = useState('')
  const [cost, setCost] = useState('20')
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)

  const reload = async () => {
    const [r, q] = await Promise.all([
      api.getMeridianRewards(),
      canManage ? api.getMeridianRewardRequests('pending') : Promise.resolve([]),
    ])
    setRewards(r)
    setRequests(q)
    setLoading(false)
  }
  useEffect(() => { reload() }, [])

  const create = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return
    setSaving(true)
    try {
      await api.createMeridianReward({ name: name.trim(), cost_points: Number(cost) || 0 })
      setName(''); setCost('20')
      await reload()
    } finally {
      setSaving(false)
    }
  }

  const request = async (reward: MeridianReward) => {
    setMsg(null)
    try {
      await api.requestMeridianReward(reward.id)
      setMsg(`Requested "${reward.name}" — awaiting approval.`)
    } catch (err) {
      setMsg(err instanceof Error ? 'Could not request: not enough points.' : 'Could not request.')
    }
  }

  const act = async (fn: Promise<unknown>) => { await fn.catch(() => {}); await reload() }

  if (loading) return <div className="h-32 rounded-2xl bg-sunken animate-pulse" />

  return (
    <div className="flex flex-col gap-4">
      {canManage && (
        <Card title="New reward">
          <form onSubmit={create} className="flex flex-col sm:flex-row gap-2">
            <input
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="Reward name…"
              className="flex-1 px-3 py-2.5 rounded-xl border border-line bg-raised text-sm text-ink placeholder-muted outline-none focus:ring-2 focus:ring-primary"
            />
            <input
              type="number" min="0" value={cost}
              onChange={e => setCost(e.target.value)}
              className="w-24 px-3 py-2.5 rounded-xl border border-line bg-raised text-sm text-ink outline-none focus:ring-2 focus:ring-primary"
              aria-label="Cost in points"
            />
            <Button type="submit" loading={saving} disabled={!name.trim()}>Add</Button>
          </form>
        </Card>
      )}

      {canManage && requests.length > 0 && (
        <Card title="Pending reward requests">
          <ul className="flex flex-col gap-2">
            {requests.map(req => (
              <li key={req.id} className="flex items-center justify-between gap-3">
                <span className="text-sm text-ink">
                  Reward request #{req.id} · {req.reward_id}
                </span>
                <div className="flex gap-2">
                  <Button size="sm" onClick={() => act(api.approveMeridianRewardRequest(req.id))}>Approve</Button>
                  <Button size="sm" variant="ghost" onClick={() => act(api.rejectMeridianRewardRequest(req.id))}>Reject</Button>
                </div>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {msg && <p className="text-sm text-primary text-center">{msg}</p>}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {rewards.map(reward => (
          <Card key={reward.id}>
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <h3 className="font-bold text-ink">{reward.name}</h3>
                {reward.description && <p className="text-sm text-muted mt-0.5">{reward.description}</p>}
                <div className="mt-2"><PointsPill points={reward.cost_points} /></div>
              </div>
              <div className="flex flex-col gap-2 items-end flex-shrink-0">
                <Button size="sm" variant="secondary" onClick={() => request(reward)}>Request</Button>
                {canManage && (
                  <button
                    onClick={() => { if (confirm(`Delete "${reward.name}"?`)) act(api.deleteMeridianReward(reward.id)) }}
                    className="text-muted hover:text-danger transition-colors text-lg leading-none"
                    aria-label="Delete reward"
                  >×</button>
                )}
              </div>
            </div>
          </Card>
        ))}
        {rewards.length === 0 && (
          <p className="text-sm text-muted text-center py-8 sm:col-span-2">No rewards yet.</p>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Points tab
// ---------------------------------------------------------------------------

function PointsTab() {
  const [data, setData] = useState<MeridianPointsResponse | null>(null)

  useEffect(() => { api.getMeridianPoints().then(setData).catch(() => setData({ summary: [], entries: [] })) }, [])

  if (!data) return <div className="h-32 rounded-2xl bg-sunken animate-pulse" />

  return (
    <div className="flex flex-col gap-4">
      <Card title="Points by person">
        {data.summary.length === 0 ? (
          <p className="text-sm text-muted text-center py-4">No points earned yet.</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {data.summary.map(row => (
              <li key={row.person_id} className="flex items-center justify-between py-1">
                <span className="font-semibold text-ink">{row.display_name || `Person ${row.person_id}`}</span>
                <PointsPill points={row.balance} />
              </li>
            ))}
          </ul>
        )}
      </Card>

      {data.entries.length > 0 && (
        <Card title="Recent activity">
          <ul className="divide-y divide-line/60">
            {data.entries.map(e => (
              <li key={e.id} className="flex items-center justify-between py-2 text-sm">
                <span className="text-muted-strong">{e.reason || 'Adjustment'}</span>
                <span className={e.points >= 0 ? 'text-success font-semibold' : 'text-danger font-semibold'}>
                  {e.points >= 0 ? '+' : ''}{e.points}
                </span>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Meridian page
// ---------------------------------------------------------------------------

type Tab = 'tasks' | 'rewards' | 'points'

export function MeridianPage() {
  const { user } = useAuth()
  const canManage = user?.role === 'admin' || user?.role === 'manager'
  const [tab, setTab] = useState<Tab>('tasks')

  return (
    <div className="flex flex-col gap-5">
      <h1 className="text-2xl font-extrabold tracking-tight text-ink">Meridian</h1>

      <div className="flex gap-1 bg-sunken p-1 rounded-xl w-fit">
        {(['tasks', 'rewards', 'points'] as Tab[]).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-1.5 rounded-lg text-sm font-semibold transition-colors capitalize ${
              tab === t ? 'bg-raised text-ink shadow-soft' : 'text-muted hover:text-ink'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === 'tasks' && <TasksTab canManage={canManage} />}
      {tab === 'rewards' && <RewardsTab canManage={canManage} />}
      {tab === 'points' && <PointsTab />}
    </div>
  )
}
