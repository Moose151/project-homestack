import { useEffect, useState } from 'react'
import { api } from '../../../../api/client'
import type {
  Badge,
  MeridianCategory,
  MeridianPointsResponse,
  MeridianReports,
  MeridianSettings,
  MeridianTaskCompletion,
  PersonBadge,
} from '../../../../api/types'
import { Card } from '../../../../components/Card'
import { Button } from '../../../../components/Button'

// Leaderboard + recent activity + badge catalogue (mirrors legacy leaderboard.html + badges).

export function LeaderboardTab({ pointsLabel }: { pointsLabel: string }) {
  const [reports, setReports] = useState<MeridianReports | null>(null)
  const [points, setPoints] = useState<MeridianPointsResponse | null>(null)
  const [completions, setCompletions] = useState<MeridianTaskCompletion[]>([])
  const [badges, setBadges] = useState<Badge[]>([])
  const [myBadges, setMyBadges] = useState<PersonBadge[]>([])

  useEffect(() => {
    api.getMeridianReports().then(setReports).catch(() => setReports({ leaderboard: [], recent_activity: [] }))
    api.getMeridianPoints().then(setPoints).catch(() => setPoints({ summary: [], entries: [] }))
    api.getMeridianTaskCompletions().then(setCompletions).catch(() => setCompletions([]))
    api.getBadges().then(setBadges).catch(() => {})
    api.getMyBadges().then(setMyBadges).catch(() => {})
  }, [])

  if (!reports) return <div className="h-32 rounded-2xl bg-sunken animate-pulse" />
  const earnedCodes = new Set(myBadges.map(b => b.badge.code))
  const medal = (i: number) => ['🥇', '🥈', '🥉'][i] ?? `${i + 1}.`
  const approved = completions.filter(c => c.status === 'approved').length
  const rejected = completions.filter(c => c.status === 'rejected').length
  const submitted = completions.filter(c => c.status === 'submitted').length

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Metric label="Approved tasks" value={String(approved)} detail={`${submitted} waiting, ${rejected} rejected`} />
        <Metric label={`Total ${pointsLabel} entries`} value={String(points?.entries.length ?? 0)} detail="Latest ledger movements" />
        <Metric label="Badges earned" value={String(myBadges.length)} detail={`${badges.length} in catalogue`} />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_380px] gap-4">
        <Card title="Leaderboard">
          {reports.leaderboard.length === 0 ? (
            <p className="text-sm text-muted text-center py-4">No points yet.</p>
          ) : (
            <ul className="flex flex-col gap-1.5">
              {reports.leaderboard.map((r, i) => (
                <li key={r.person_id} className="flex items-center gap-3 py-1.5">
                  <span className="w-7 text-center font-bold text-muted-strong">{medal(i)}</span>
                  <span className="flex-1 font-semibold text-ink">{r.display_name || `Person ${r.person_id}`}</span>
                  {r.badge_count > 0 && <span className="text-xs text-muted">{r.badge_count} badges</span>}
                  <span className="text-xs text-muted">earned {r.total_earned}</span>
                  <span className="font-bold text-primary whitespace-nowrap">★ {r.balance}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title="Badge catalogue">
          {myBadges.length === 0 && <p className="text-sm text-muted mb-3">No badges earned yet.</p>}
          <div className="grid grid-cols-3 sm:grid-cols-4 xl:grid-cols-3 gap-3">
            {badges.map(b => {
              const earned = earnedCodes.has(b.code)
              return (
                <div key={b.id} title={b.description}
                  className={`rounded-xl border border-line bg-raised p-2 text-center ${earned ? '' : 'opacity-35 grayscale'}`}>
                  <span className="text-2xl">{b.icon}</span>
                  <span className="block text-[11px] text-muted-strong leading-tight mt-1">{b.name}</span>
                </div>
              )
            })}
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <Card title="Task completion history">
          {completions.length === 0 ? (
            <p className="text-sm text-muted py-3">No task completions yet.</p>
          ) : (
            <ul className="divide-y divide-line/70">
              {completions.slice(0, 12).map(c => (
                <li key={c.id} className="py-2 flex items-start gap-3 text-sm">
                  <span className={`mt-1 h-2.5 w-2.5 rounded-full ${statusDot(c.status)}`} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-semibold text-ink">{c.task_title}</p>
                    <p className="text-xs text-muted">
                      {c.person_display_name || `Person ${c.person_id}`} · {c.status} · {formatWhen(c.reviewed_at || c.submitted_at)}
                    </p>
                    {c.rejection_reason && <p className="mt-1 text-xs text-danger">{c.rejection_reason}</p>}
                    {c.review_note && <p className="mt-1 text-xs text-muted-strong">{c.review_note}</p>}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title="Points ledger">
          {points?.entries.length === 0 ? (
            <p className="text-sm text-muted py-3">No ledger entries yet.</p>
          ) : (
            <ul className="divide-y divide-line/70">
              {(points?.entries ?? []).slice(0, 12).map(entry => (
                <li key={entry.id} className="flex items-center justify-between gap-3 py-2 text-sm">
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-muted-strong">{entry.reason || 'Points entry'}</span>
                    <span className="block text-xs text-muted">{formatWhen(entry.created_at)}</span>
                  </span>
                  <span className={entry.points >= 0 ? 'font-semibold text-success' : 'font-semibold text-danger'}>
                    {entry.points >= 0 ? '+' : ''}{entry.points} {pointsLabel}
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

function statusDot(status: MeridianTaskCompletion['status']) {
  if (status === 'approved') return 'bg-success'
  if (status === 'rejected') return 'bg-danger'
  return 'bg-warning'
}

function formatWhen(value: string | null) {
  if (!value) return ''
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleString([], { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })
}

// Household settings (admin) — mirrors legacy household_settings.

export function SettingsTab() {
  const [s, setS] = useState<MeridianSettings | null>(null)
  const [taskCategories, setTaskCategories] = useState<MeridianCategory[]>([])
  const [rewardCategories, setRewardCategories] = useState<MeridianCategory[]>([])
  const [newTaskCategory, setNewTaskCategory] = useState('')
  const [newRewardCategory, setNewRewardCategory] = useState('')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const reloadCategories = async () => {
    const [tasks, rewards] = await Promise.all([
      api.getMeridianCategories('task').catch(() => []),
      api.getMeridianCategories('reward').catch(() => []),
    ])
    setTaskCategories(tasks)
    setRewardCategories(rewards)
  }

  useEffect(() => {
    api.getMeridianSettings().then(setS).catch(() => {})
    reloadCategories()
  }, [])
  if (!s) return <div className="h-32 rounded-2xl bg-sunken animate-pulse" />

  const set = (patch: Partial<MeridianSettings>) => setS({ ...s, ...patch })
  const save = async () => {
    setSaving(true); setSaved(false); setError(null)
    try { setS(await api.updateMeridianSettings(s)); setSaved(true) } catch { setError('Settings did not save.') } finally { setSaving(false) }
  }

  const createCategory = async (kind: 'task' | 'reward') => {
    const name = (kind === 'task' ? newTaskCategory : newRewardCategory).trim()
    if (!name) return
    setError(null)
    try {
      await api.createMeridianCategory({ name, kind })
      if (kind === 'task') setNewTaskCategory('')
      else setNewRewardCategory('')
      await reloadCategories()
    } catch {
      setError('Category could not be created.')
    }
  }

  const deleteCategory = async (id: number) => {
    setError(null)
    try {
      await api.deleteMeridianCategory(id)
      await reloadCategories()
    } catch {
      setError('Category could not be deleted.')
    }
  }

  const toggle = (key: keyof MeridianSettings, label: string, help: string) => (
    <label className="flex items-start gap-3 py-2">
      <input type="checkbox" className="mt-1" checked={Boolean(s[key])}
        onChange={e => set({ [key]: e.target.checked } as Partial<MeridianSettings>)} />
      <span>
        <span className="block text-ink font-medium">{label}</span>
        <span className="block text-xs text-muted">{help}</span>
      </span>
    </label>
  )

  return (
    <div className="flex flex-col gap-4">
      {error && <div className="rounded-xl border border-danger/30 bg-danger-soft px-4 py-3 text-sm text-danger">{error}</div>}

      <Card title="Meridian settings">
        <div className="flex flex-col gap-2 max-w-lg">
          <label className="flex flex-col gap-1 mb-2">
            <span className="text-ink font-medium">Points label</span>
            <span className="text-xs text-muted">What points are called everywhere (e.g. points, stars, tokens).</span>
            <input value={s.points_label} onChange={e => set({ points_label: e.target.value })}
              className="mt-1 px-3 py-2 rounded-xl border border-line bg-raised text-sm text-ink outline-none focus:ring-2 focus:ring-primary w-48" />
          </label>
          {toggle('group_goals_enabled', 'Group goals', 'Let the household pool points toward shared goals.')}
          {toggle('wishlist_requests_enabled', 'Wishlist requests', 'Let children request items for their wishlist.')}
          {toggle('auto_end_streaks', 'Auto-end streaks', 'Break a routine streak after a missed day (off = lenient, for split households).')}
          <div className="flex items-center gap-3 mt-3">
            <Button onClick={save} loading={saving}>Save settings</Button>
            {saved && <span className="text-sm text-success">Saved ✓</span>}
          </div>
        </div>
      </Card>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <CategoryPanel
          title="Task categories"
          categories={taskCategories}
          value={newTaskCategory}
          onChange={setNewTaskCategory}
          onCreate={() => createCategory('task')}
          onDelete={deleteCategory}
        />
        <CategoryPanel
          title="Reward categories"
          categories={rewardCategories}
          value={newRewardCategory}
          onChange={setNewRewardCategory}
          onCreate={() => createCategory('reward')}
          onDelete={deleteCategory}
        />
      </div>
    </div>
  )
}

function CategoryPanel({
  title,
  categories,
  value,
  onChange,
  onCreate,
  onDelete,
}: {
  title: string
  categories: MeridianCategory[]
  value: string
  onChange: (value: string) => void
  onCreate: () => void
  onDelete: (id: number) => void
}) {
  return (
    <Card title={title}>
      <div className="flex gap-2">
        <input
          value={value}
          onChange={e => onChange(e.target.value)}
          className="min-w-0 flex-1 px-3 py-2 rounded-xl border border-line bg-raised text-sm text-ink placeholder-muted outline-none focus:ring-2 focus:ring-primary"
          placeholder="New category"
        />
        <Button size="sm" disabled={!value.trim()} onClick={onCreate}>Add</Button>
      </div>
      {categories.length === 0 ? (
        <p className="mt-4 text-sm text-muted">No categories yet.</p>
      ) : (
        <ul className="mt-4 divide-y divide-line/70">
          {categories.map(c => (
            <li key={c.id} className="flex items-center justify-between gap-3 py-2">
              <span className="font-medium text-ink">{c.name}</span>
              <Button size="sm" variant="ghost" onClick={() => onDelete(c.id)}>Delete</Button>
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}
