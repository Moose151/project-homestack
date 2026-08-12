import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../../api/client'
import type { NotificationPreference, UserNotificationSettings } from '../../../api/types'
import { Card } from '../../../components/Card'
import { Button } from '../../../components/Button'
import { PageHeader } from '../../../components/PageHeader'

const errMsg = (e: unknown) => (e instanceof Error ? e.message : 'Something went wrong.')

function Toggle({ on, onClick, label }: { on: boolean; onClick: () => void; label: string }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={on}
      aria-label={label}
      onClick={onClick}
      className={`relative flex-shrink-0 w-11 h-6 rounded-full transition-colors ${on ? 'bg-success' : 'bg-line-strong'}`}
    >
      <span className={`absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition-all ${on ? 'left-5' : 'left-0.5'}`} />
    </button>
  )
}

export function NotificationSettingsPage() {
  const [rows, setRows] = useState<NotificationPreference[]>([])
  const [settings, setSettings] = useState<UserNotificationSettings | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [savingSettings, setSavingSettings] = useState(false)

  useEffect(() => {
    Promise.all([api.getNotificationPreferences(), api.getNotificationSettings()])
      .then(([prefRows, settingsRow]) => { setRows(prefRows); setSettings(settingsRow) })
      .catch(e => setError(errMsg(e)))
      .finally(() => setLoading(false))
  }, [])

  const setRow = (category: string, patch: Partial<NotificationPreference>) =>
    setRows(prev => prev.map(row => row.category === category ? { ...row, ...patch } : row))

  const save = async () => {
    setSaving(true); setError(null)
    try {
      const saved = await api.updateNotificationPreferences(rows.map(row => ({
        category: row.category, in_app_enabled: row.in_app_enabled,
        push_enabled: row.push_enabled, mine_only: row.mine_only,
      })))
      setRows(saved)
    } catch (e) { setError(errMsg(e)) } finally { setSaving(false) }
  }

  const saveSettings = async () => {
    if (!settings) return
    setSavingSettings(true); setError(null)
    try {
      const saved = await api.updateNotificationSettings(settings)
      setSettings(saved)
    } catch (e) { setError(errMsg(e)) } finally { setSavingSettings(false) }
  }

  if (loading) return <div className="mx-auto max-w-2xl"><div className="h-40 animate-pulse rounded-2xl bg-sunken" /></div>

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-5">
      <PageHeader
        title="Notifications"
        icon="🔔"
        subtitle="Choose what you hear about, and when. Applies to your login only."
      />

      {error && (
        <div className="flex items-center justify-between gap-3 bg-danger-soft text-danger text-sm rounded-xl px-4 py-2.5">
          <span>{error}</span>
          <button onClick={() => setError(null)} aria-label="Dismiss">×</button>
        </div>
      )}

      <Card title="Quiet hours">
        <p className="text-sm text-muted mb-3">
          No phone push notifications during this window; the in-app bell still updates
          immediately whenever you open HomeStack. Leave blank for no quiet hours.
        </p>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <div>
            <div className="text-xs text-muted-strong mb-1">Starts</div>
            <input
              type="time"
              value={settings?.quiet_start?.slice(0, 5) ?? ''}
              onChange={e => setSettings(s => s ? { ...s, quiet_start: e.target.value || null } : s)}
              className="w-full rounded-xl border border-line bg-surface px-3 py-2 text-sm text-ink"
            />
          </div>
          <div>
            <div className="text-xs text-muted-strong mb-1">Ends</div>
            <input
              type="time"
              value={settings?.quiet_end?.slice(0, 5) ?? ''}
              onChange={e => setSettings(s => s ? { ...s, quiet_end: e.target.value || null } : s)}
              className="w-full rounded-xl border border-line bg-surface px-3 py-2 text-sm text-ink"
            />
          </div>
          <div>
            <div className="text-xs text-muted-strong mb-1">Morning digest time</div>
            <input
              type="time"
              value={settings?.morning_time?.slice(0, 5) ?? '08:00'}
              onChange={e => setSettings(s => s ? { ...s, morning_time: e.target.value } : s)}
              className="w-full rounded-xl border border-line bg-surface px-3 py-2 text-sm text-ink"
            />
          </div>
        </div>
        <p className="mt-2 text-xs text-muted">
          "Morning digest time" is when same-day reminders (an appointment due today, a countdown
          update) are sent, once that feature is live.
        </p>
        <Button className="mt-3" onClick={saveSettings} loading={savingSettings}>Save</Button>
      </Card>

      <Card title="Categories">
        <p className="text-sm text-muted mb-4">
          In-app always shows in the bell. Push goes to your phone once notifications are set up
          on it — the toggle is ready now, delivery is coming soon.
        </p>
        <div className="space-y-4">
          {rows.map(row => (
            <div key={row.category} className="flex flex-wrap items-center gap-x-6 gap-y-2 border-b border-line/60 pb-4 last:border-0 last:pb-0">
              <div className="min-w-[10rem] flex-1">
                <div className="text-sm font-semibold text-ink">{row.label}</div>
                {row.supports_mine_only && (
                  <label className="mt-1 flex items-center gap-1.5 text-xs text-muted">
                    <input
                      type="checkbox"
                      checked={row.mine_only}
                      onChange={e => setRow(row.category, { mine_only: e.target.checked })}
                    />
                    Only things assigned to me
                  </label>
                )}
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-muted-strong w-10">In-app</span>
                <Toggle on={row.in_app_enabled} onClick={() => setRow(row.category, { in_app_enabled: !row.in_app_enabled })} label={`${row.label} in-app`} />
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-muted-strong w-10">Push</span>
                <Toggle on={row.push_enabled} onClick={() => setRow(row.category, { push_enabled: !row.push_enabled })} label={`${row.label} push`} />
              </div>
            </div>
          ))}
        </div>
        <Button className="mt-4" onClick={save} loading={saving}>Save preferences</Button>
      </Card>

      <Link to="/settings" className="font-bold text-primary hover:underline">← Manage HomeStack</Link>
    </div>
  )
}
