import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../../api/client'
import type { NotificationPreference, PushDevice, UserNotificationSettings } from '../../../api/types'
import { Card } from '../../../components/Card'
import { Button } from '../../../components/Button'
import { PageHeader } from '../../../components/PageHeader'
import { confirmDialog } from '../../../components/Dialogs'
import { deviceDetail, lastSeenLabel } from './pushDeviceFormat'

const errMsg = (e: unknown) => (e instanceof Error ? e.message : 'Something went wrong.')

const PUSH_SUPPORTED = typeof window !== 'undefined' && 'serviceWorker' in navigator && 'PushManager' in window

// applicationServerKey must be a Uint8Array, not the base64url string the API returns. Built via
// `new Uint8Array(n)` + indexed writes (not Uint8Array.from) so it's ArrayBuffer- rather than
// the wider ArrayBufferLike-backed, matching what lib.dom's PushSubscriptionOptionsInit expects.
function urlBase64ToUint8Array(base64url: string): Uint8Array<ArrayBuffer> {
  const padding = '='.repeat((4 - (base64url.length % 4)) % 4)
  const base64 = (base64url + padding).replace(/-/g, '+').replace(/_/g, '/')
  const raw = atob(base64)
  const bytes = new Uint8Array(raw.length)
  for (let i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i)
  return bytes
}

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
  const [devices, setDevices] = useState<PushDevice[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [savingSettings, setSavingSettings] = useState(false)
  const [subscribing, setSubscribing] = useState(false)
  const [busyDeviceId, setBusyDeviceId] = useState<number | null>(null)
  const [testedDeviceId, setTestedDeviceId] = useState<number | null>(null)
  const [renamingId, setRenamingId] = useState<number | null>(null)
  const [renameDraft, setRenameDraft] = useState('')

  const loadDevices = () => api.getPushDevices().then(setDevices).catch(e => setError(errMsg(e)))

  useEffect(() => {
    Promise.all([api.getNotificationPreferences(), api.getNotificationSettings(), api.getPushDevices()])
      .then(([prefRows, settingsRow, deviceRows]) => { setRows(prefRows); setSettings(settingsRow); setDevices(deviceRows) })
      .catch(e => setError(errMsg(e)))
      .finally(() => setLoading(false))
  }, [])

  const enablePushOnThisDevice = async () => {
    setSubscribing(true); setError(null)
    try {
      if (!PUSH_SUPPORTED) throw new Error('This browser does not support push notifications.')
      const permission = await Notification.requestPermission()
      if (permission !== 'granted') throw new Error('Notification permission was not granted.')
      const registration = await navigator.serviceWorker.ready
      const { public_key: publicKey } = await api.getVapidPublicKey()
      if (!publicKey) throw new Error('Push is not configured on this server yet.')
      let subscription = await registration.pushManager.getSubscription()
      if (!subscription) {
        subscription = await registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(publicKey),
        })
      }
      const json = subscription.toJSON() as { endpoint: string; keys?: { p256dh: string; auth: string } }
      if (!json.keys) throw new Error('The browser did not return subscription keys.')
      // No label: the server names the device from the User-Agent it already receives, so every
      // client gets the same "Chrome on Android" naming and a renamed device stays renamed.
      await api.registerPushDevice({ endpoint: json.endpoint, keys: json.keys })
      await loadDevices()
    } catch (e) { setError(errMsg(e)) } finally { setSubscribing(false) }
  }

  const revokeDevice = async (device: PushDevice) => {
    if (!(await confirmDialog({ title: `Stop push on "${device.label || 'this device'}"?`, confirmLabel: 'Revoke' }))) return
    setBusyDeviceId(device.id)
    try { await api.unregisterPushDevice(device.id); await loadDevices() }
    catch (e) { setError(errMsg(e)) } finally { setBusyDeviceId(null) }
  }

  const testDevice = async (device: PushDevice) => {
    setBusyDeviceId(device.id); setTestedDeviceId(null)
    try { await api.testPushDevice(device.id); setTestedDeviceId(device.id) }
    catch (e) { setError(errMsg(e)) } finally { setBusyDeviceId(null) }
  }

  const startRename = (device: PushDevice) => {
    setRenamingId(device.id)
    // Seed with the generated name too, so renaming is an edit rather than a blank box.
    setRenameDraft(device.label)
  }

  const saveRename = async (device: PushDevice) => {
    setBusyDeviceId(device.id); setError(null)
    try {
      const saved = await api.renamePushDevice(device.id, renameDraft.trim())
      setDevices(prev => prev.map(row => row.id === saved.id ? saved : row))
      setRenamingId(null)
    } catch (e) { setError(errMsg(e)) } finally { setBusyDeviceId(null) }
  }

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

      <Card title="Devices">
        <p className="text-sm text-muted mb-3">
          Push notifications go to devices you've enabled here — each phone, tablet or computer
          you use HomeStack on needs its own. Requires an explicit permission prompt; nothing is
          enabled automatically. Only you can see your own devices; rename any of them with ✏️.
        </p>
        {!PUSH_SUPPORTED ? (
          <p className="text-sm text-muted-strong">This browser doesn't support push notifications.</p>
        ) : (
          <Button onClick={enablePushOnThisDevice} loading={subscribing} className="mb-4">
            Enable push on this device
          </Button>
        )}
        {devices.length === 0 ? (
          <p className="text-sm text-muted">No devices enabled yet.</p>
        ) : (
          <ul className="space-y-2">
            {devices.map(device => (
              <li key={device.id} className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-line px-3 py-2.5">
                {renamingId === device.id ? (
                  <form
                    className="flex flex-1 flex-wrap items-center gap-2"
                    onSubmit={e => { e.preventDefault(); void saveRename(device) }}
                  >
                    <input
                      autoFocus
                      value={renameDraft}
                      onChange={e => setRenameDraft(e.target.value)}
                      onKeyDown={e => { if (e.key === 'Escape') setRenamingId(null) }}
                      maxLength={120}
                      aria-label="Device name"
                      placeholder={deviceDetail(device) || 'Device name'}
                      className="min-w-[8rem] flex-1 rounded-xl border border-line bg-surface px-3 py-1.5 text-sm text-ink"
                    />
                    <Button size="sm" type="submit" loading={busyDeviceId === device.id}>Save</Button>
                    <Button size="sm" variant="ghost" type="button" onClick={() => setRenamingId(null)}>Cancel</Button>
                  </form>
                ) : (
                  <>
                    <div className="min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="text-sm font-semibold text-ink">{device.label || 'Device'}</span>
                        <button
                          type="button"
                          onClick={() => startRename(device)}
                          aria-label={`Rename ${device.label || 'device'}`}
                          title="Rename"
                          className="rounded px-1 text-xs text-muted hover:text-primary"
                        >
                          ✏️
                        </button>
                      </div>
                      <div className="text-xs text-muted">
                        {[deviceDetail(device), `Last seen ${lastSeenLabel(device.last_seen_at)}`].filter(Boolean).join(' · ')}
                        {testedDeviceId === device.id && <span className="ml-2 font-semibold text-success">Test sent ✓</span>}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button size="sm" variant="secondary" onClick={() => testDevice(device)} loading={busyDeviceId === device.id}>Test</Button>
                      <Button size="sm" variant="ghost" onClick={() => revokeDevice(device)} loading={busyDeviceId === device.id}>Revoke</Button>
                    </div>
                  </>
                )}
              </li>
            ))}
          </ul>
        )}
      </Card>

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
          In-app always shows in the bell. Push goes to every device you've enabled above.
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
