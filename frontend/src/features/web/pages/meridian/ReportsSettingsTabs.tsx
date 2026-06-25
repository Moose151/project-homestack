import { useEffect, useState } from 'react'
import { api } from '../../../../api/client'
import type { Badge, MeridianReports, MeridianSettings, PersonBadge } from '../../../../api/types'
import { Card } from '../../../../components/Card'
import { Button } from '../../../../components/Button'

// Leaderboard + recent activity + badge catalogue (mirrors legacy leaderboard.html + badges).

export function LeaderboardTab({ pointsLabel }: { pointsLabel: string }) {
  const [reports, setReports] = useState<MeridianReports | null>(null)
  const [badges, setBadges] = useState<Badge[]>([])
  const [myBadges, setMyBadges] = useState<PersonBadge[]>([])

  useEffect(() => {
    api.getMeridianReports().then(setReports).catch(() => setReports({ leaderboard: [], recent_activity: [] }))
    api.getBadges().then(setBadges).catch(() => {})
    api.getMyBadges().then(setMyBadges).catch(() => {})
  }, [])

  if (!reports) return <div className="h-32 rounded-2xl bg-sunken animate-pulse" />
  const earnedCodes = new Set(myBadges.map(b => b.badge.code))
  const medal = (i: number) => ['🥇', '🥈', '🥉'][i] ?? `${i + 1}.`

  return (
    <div className="flex flex-col gap-4">
      <Card title="Leaderboard">
        {reports.leaderboard.length === 0 ? (
          <p className="text-sm text-muted text-center py-4">No points yet.</p>
        ) : (
          <ul className="flex flex-col gap-1.5">
            {reports.leaderboard.map((r, i) => (
              <li key={r.person_id} className="flex items-center gap-3 py-1.5">
                <span className="w-7 text-center font-bold text-muted-strong">{medal(i)}</span>
                <span className="flex-1 font-semibold text-ink">{r.display_name || `Person ${r.person_id}`}</span>
                {r.badge_count > 0 && <span className="text-xs text-muted">🏅 {r.badge_count}</span>}
                <span className="text-xs text-muted">earned {r.total_earned}</span>
                <span className="font-bold text-primary whitespace-nowrap">★ {r.balance}</span>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card title="My badges">
        {myBadges.length === 0 && <p className="text-sm text-muted mb-3">No badges yet — complete tasks and routines to earn them!</p>}
        <div className="flex flex-wrap gap-3">
          {badges.map(b => {
            const earned = earnedCodes.has(b.code)
            return (
              <div key={b.id} title={b.description}
                className={`flex flex-col items-center w-20 text-center ${earned ? '' : 'opacity-30 grayscale'}`}>
                <span className="text-3xl">{b.icon}</span>
                <span className="text-[11px] text-muted-strong leading-tight mt-1">{b.name}</span>
              </div>
            )
          })}
        </div>
      </Card>

      {reports.recent_activity.length > 0 && (
        <Card title="Recent activity">
          <ul className="divide-y divide-line/60">
            {reports.recent_activity.map(a => (
              <li key={a.id} className="flex items-center justify-between py-2 text-sm">
                <span className="text-muted-strong">{a.display_name}: {a.reason || a.transaction_type}</span>
                <span className={a.points >= 0 ? 'text-success font-semibold' : 'text-danger font-semibold'}>
                  {a.points >= 0 ? '+' : ''}{a.points} {pointsLabel}
                </span>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  )
}

// Household settings (admin) — mirrors legacy household_settings.

export function SettingsTab() {
  const [s, setS] = useState<MeridianSettings | null>(null)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => { api.getMeridianSettings().then(setS).catch(() => {}) }, [])
  if (!s) return <div className="h-32 rounded-2xl bg-sunken animate-pulse" />

  const set = (patch: Partial<MeridianSettings>) => setS({ ...s, ...patch })
  const save = async () => {
    setSaving(true); setSaved(false)
    try { setS(await api.updateMeridianSettings(s)); setSaved(true) } finally { setSaving(false) }
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
  )
}
