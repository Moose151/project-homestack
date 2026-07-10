import { useEffect, useMemo, useState } from 'react'
import { api } from '../../../../api/client'
import type {
  MeridianReports,
  MeridianReward,
  MeridianRewardRequest,
  MeridianTaskCompletion,
  Person,
} from '../../../../api/types'
import { Card } from '../../../../components/Card'
import { Button } from '../../../../components/Button'

interface Props {
  canManage: boolean
  pointsLabel: string
  onOpenTasks?: () => void
  onOpenShop?: () => void
}

export function OverviewTab({ canManage, pointsLabel, onOpenTasks, onOpenShop }: Props) {
  const [taskCompletions, setTaskCompletions] = useState<MeridianTaskCompletion[]>([])
  const [rewardRequests, setRewardRequests] = useState<MeridianRewardRequest[]>([])
  const [rewards, setRewards] = useState<MeridianReward[]>([])
  const [people, setPeople] = useState<Person[]>([])
  const [reports, setReports] = useState<MeridianReports | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const reload = async () => {
    setError(null)
    try {
      const [completions, rewardReqs, rewardList, peopleList, reportData] = await Promise.all([
        canManage ? api.getMeridianTaskCompletions({ status: 'submitted' }) : Promise.resolve([]),
        canManage ? api.getMeridianRewardRequests('pending') : Promise.resolve([]),
        api.getMeridianRewards().catch(() => []),
        api.getPeople().catch(() => []),
        api.getMeridianReports().catch(() => ({ leaderboard: [], recent_activity: [] })),
      ])
      setTaskCompletions(completions)
      setRewardRequests(rewardReqs)
      setRewards(rewardList)
      setPeople(peopleList)
      setReports(reportData)
    } catch {
      setError('Meridian could not be refreshed. Try again in a moment.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { reload() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const personName = (id: number | null) =>
    people.find(p => p.id === id)?.display_name || (id ? `Person ${id}` : 'Someone')

  const rewardName = (id: number) =>
    rewards.find(r => r.id === id)?.name || `Reward #${id}`

  const pendingCount = taskCompletions.length + rewardRequests.length
  const topBalances = useMemo(() => reports?.leaderboard.slice(0, 4) ?? [], [reports])

  const approveCompletion = async (id: number) => {
    await api.approveMeridianTaskCompletion(id)
    await reload()
  }

  const rejectCompletion = async (id: number) => {
    const reason = prompt('Reason (optional)') || ''
    await api.rejectMeridianTaskCompletion(id, reason)
    await reload()
  }

  const approveReward = async (id: number) => {
    await api.approveMeridianRewardRequest(id)
    await reload()
  }

  const rejectReward = async (id: number) => {
    const reason = prompt('Reason (optional)') || ''
    await api.rejectMeridianRewardRequest(id, reason)
    await reload()
  }

  if (loading) return <div className="h-48 rounded-2xl bg-sunken animate-pulse" />

  return (
    <div className="flex flex-col gap-4">
      {error && (
        <div className="rounded-xl border border-danger/30 bg-danger-soft px-4 py-3 text-sm text-danger">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Metric label="Pending approvals" value={String(pendingCount)} detail={`${taskCompletions.length} tasks · ${rewardRequests.length} rewards`} />
        <Metric label="Active earners" value={String(topBalances.length)} detail="People with Meridian activity" />
        <Metric label={`Top ${pointsLabel} balance`} value={topBalances[0] ? `★ ${topBalances[0].balance}` : '★ 0'} detail={topBalances[0]?.display_name || 'No activity yet'} />
      </div>

      {canManage && (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          <Card title="Task approvals">
            {taskCompletions.length === 0 ? (
              <EmptyApproval text="No task submissions waiting." action="Manage tasks" onAction={onOpenTasks} />
            ) : (
              <ul className="divide-y divide-line/70">
                {taskCompletions.map(c => (
                  <li key={c.id} className="py-3 flex flex-col sm:flex-row sm:items-center gap-3">
                    <div className="min-w-0 flex-1">
                      <p className="font-semibold text-ink truncate">{c.task_title}</p>
                      <p className="text-sm text-muted">
                        {c.person_display_name || personName(c.person_id)} submitted {formatWhen(c.submitted_at)}
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <Button size="sm" onClick={() => approveCompletion(c.id)}>Approve</Button>
                      <Button size="sm" variant="ghost" onClick={() => rejectCompletion(c.id)}>Reject</Button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <Card title="Reward approvals">
            {rewardRequests.length === 0 ? (
              <EmptyApproval text="No reward requests waiting." action="Manage shop" onAction={onOpenShop} />
            ) : (
              <ul className="divide-y divide-line/70">
                {rewardRequests.map(r => (
                  <li key={r.id} className="py-3 flex flex-col sm:flex-row sm:items-center gap-3">
                    <div className="min-w-0 flex-1">
                      <p className="font-semibold text-ink truncate">{rewardName(r.reward_id)}</p>
                      <p className="text-sm text-muted">
                        {personName(r.requested_by_person_id)} · ★ {r.points_spent} {pointsLabel}
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <Button size="sm" onClick={() => approveReward(r.id)}>Approve</Button>
                      <Button size="sm" variant="ghost" onClick={() => rejectReward(r.id)}>Reject</Button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <Card title="Balances">
          {topBalances.length === 0 ? (
            <p className="text-sm text-muted py-3">No points have been earned yet.</p>
          ) : (
            <ul className="flex flex-col gap-2">
              {topBalances.map((row, idx) => (
                <li key={row.person_id} className="flex items-center gap-3">
                  <span className="w-7 text-center text-sm font-bold text-muted-strong">{idx + 1}</span>
                  <span className="flex-1 font-semibold text-ink">{row.display_name || `Person ${row.person_id}`}</span>
                  <span className="text-xs text-muted">earned {row.total_earned}</span>
                  <span className="font-bold text-primary whitespace-nowrap">★ {row.balance}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title="Recent activity">
          {!reports || reports.recent_activity.length === 0 ? (
            <p className="text-sm text-muted py-3">No recent Meridian activity.</p>
          ) : (
            <ul className="divide-y divide-line/70">
              {reports.recent_activity.slice(0, 6).map(a => (
                <li key={a.id} className="py-2 flex items-center gap-3 text-sm">
                  <span className="min-w-0 flex-1 text-muted-strong truncate">
                    {a.display_name}: {a.reason || a.transaction_type}
                  </span>
                  <span className={a.points >= 0 ? 'font-semibold text-success' : 'font-semibold text-danger'}>
                    {a.points >= 0 ? '+' : ''}{a.points}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </div>
  )
}

function Metric({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div className="rounded-2xl border border-line bg-surface p-4 shadow-soft">
      <p className="text-xs font-semibold uppercase tracking-wide text-muted">{label}</p>
      <p className="mt-1 text-2xl font-extrabold text-ink">{value}</p>
      <p className="mt-1 text-sm text-muted">{detail}</p>
    </div>
  )
}

function EmptyApproval({ text, action, onAction }: { text: string; action: string; onAction?: () => void }) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center gap-3 py-3">
      <p className="flex-1 text-sm text-muted">{text}</p>
      {onAction && <Button size="sm" variant="secondary" onClick={onAction}>{action}</Button>}
    </div>
  )
}

function formatWhen(value: string) {
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleString([], { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })
}
