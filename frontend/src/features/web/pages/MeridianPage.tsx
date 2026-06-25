import { useEffect, useState } from 'react'
import { api } from '../../../api/client'
import type {
  MeridianPointsResponse, MeridianReward, MeridianRewardRequest,
} from '../../../api/types'
import { Card } from '../../../components/Card'
import { Button } from '../../../components/Button'
import { useAuth } from '../../auth/AuthContext'
import { TasksTab } from './meridian/TasksTab'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function PointsPill({ points, label = '' }: { points: number; label?: string }) {
  return (
    <span className="inline-flex items-center gap-1 text-sm font-bold text-primary">
      ★ {points}{label ? ` ${label}` : ''}
    </span>
  )
}

// ---------------------------------------------------------------------------
// Rewards tab
// ---------------------------------------------------------------------------

function RewardsTab({ canManage, pointsLabel }: { canManage: boolean; pointsLabel: string }) {
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
      await reload()
    } catch {
      setMsg('Could not request — not enough points or out of stock.')
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
                <span className="text-sm text-ink">Reward request #{req.id}</span>
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
                <div className="mt-2 flex items-center gap-2">
                  <PointsPill points={reward.cost_points} label={pointsLabel} />
                  {reward.remaining_stock !== null && (
                    <span className="text-xs text-muted">{reward.remaining_stock} left</span>
                  )}
                </div>
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

function PointsTab({ pointsLabel }: { pointsLabel: string }) {
  const [data, setData] = useState<MeridianPointsResponse | null>(null)

  useEffect(() => { api.getMeridianPoints().then(setData).catch(() => setData({ summary: [], entries: [] })) }, [])

  if (!data) return <div className="h-32 rounded-2xl bg-sunken animate-pulse" />

  return (
    <div className="flex flex-col gap-4">
      <Card title={`${pointsLabel} by person`}>
        {data.summary.length === 0 ? (
          <p className="text-sm text-muted text-center py-4">No points earned yet.</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {data.summary.map(row => (
              <li key={row.person_id} className="flex items-center justify-between py-1">
                <span className="font-semibold text-ink">{row.display_name || `Person ${row.person_id}`}</span>
                <PointsPill points={row.balance} label={pointsLabel} />
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
  const [pointsLabel, setPointsLabel] = useState('points')

  useEffect(() => {
    api.getMeridianSettings().then(s => setPointsLabel(s.points_label || 'points')).catch(() => {})
  }, [])

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

      {tab === 'tasks' && <TasksTab canManage={canManage} pointsLabel={pointsLabel} />}
      {tab === 'rewards' && <RewardsTab canManage={canManage} pointsLabel={pointsLabel} />}
      {tab === 'points' && <PointsTab pointsLabel={pointsLabel} />}
    </div>
  )
}
