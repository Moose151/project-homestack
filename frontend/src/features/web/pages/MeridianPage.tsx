import { useEffect, useState } from 'react'
import { api } from '../../../api/client'
import type { MeridianPointsResponse } from '../../../api/types'
import { Card } from '../../../components/Card'
import { useAuth } from '../../auth/AuthContext'
import { TasksTab } from './meridian/TasksTab'
import { ShopTab } from './meridian/ShopTab'

function PointsPill({ points, label = '' }: { points: number; label?: string }) {
  return (
    <span className="inline-flex items-center gap-1 text-sm font-bold text-primary">
      ★ {points}{label ? ` ${label}` : ''}
    </span>
  )
}

// ---------------------------------------------------------------------------
// Points tab
// ---------------------------------------------------------------------------

function PointsTab({ pointsLabel }: { pointsLabel: string }) {
  const [data, setData] = useState<MeridianPointsResponse | null>(null)

  useEffect(() => {
    api.getMeridianPoints().then(setData).catch(() => setData({ summary: [], entries: [] }))
  }, [])

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

type Tab = 'tasks' | 'shop' | 'points'

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
        {(['tasks', 'shop', 'points'] as Tab[]).map(t => (
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
      {tab === 'shop' && <ShopTab canManage={canManage} pointsLabel={pointsLabel} />}
      {tab === 'points' && <PointsTab pointsLabel={pointsLabel} />}
    </div>
  )
}
