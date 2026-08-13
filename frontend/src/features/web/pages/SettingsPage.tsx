import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, ApiError } from '../../../api/client'
import type { Backup, MeridianSettings } from '../../../api/types'
import { useStacks } from '../../stacks/StacksContext'
import { useAuth } from '../../auth/AuthContext'
import { STACK_BY_KEY, softColour } from '../../../config/stacks'
import { NODE_GUIDE_BY_KEY, fallbackNodeGuide } from '../../../config/nodeGuides'
import { Card } from '../../../components/Card'
import { Button } from '../../../components/Button'
import { PageHeader } from '../../../components/PageHeader'
import { ColourPicker } from '../../../components/ColourPicker'
import { MobileListRow, MobileSection } from '../../../components/mobile'

const COMMON_TIMEZONES = [
  'UTC', 'Australia/Sydney', 'Australia/Melbourne', 'Australia/Brisbane',
  'Australia/Perth', 'Australia/Adelaide', 'America/New_York', 'America/Chicago',
  'America/Denver', 'America/Los_Angeles', 'Europe/London', 'Europe/Paris',
  'Europe/Berlin', 'Asia/Tokyo', 'Asia/Singapore', 'Asia/Dubai',
]

const errMsg = (e: unknown) => (e instanceof Error ? e.message : 'Something went wrong.')


const BACKUP_STATUS_TONE: Record<Backup['status'], string> = {
  complete: 'text-success',
  failed: 'text-danger',
  running: 'text-warning',
  pending: 'text-muted',
}

const formatBytes = (bytes: number) => {
  if (!bytes) return '—'
  const mb = bytes / 1024 / 1024
  return mb >= 1024 ? `${(mb / 1024).toFixed(1)} GB` : `${mb.toFixed(1)} MB`
}

/**
 * Take a backup of the database and protected media (D17).
 *
 * The backup API has existed since Milestone 1 but nothing in the app ever called it, so the
 * only way to run one was by hand against the API. Creating a backup needs recent password
 * re-authentication, so this asks for the password only when the server says it needs one
 * rather than demanding it up front.
 */
function BackupCard({ onError }: { onError: (message: string) => void }) {
  const [backups, setBackups] = useState<Backup[]>([])
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [password, setPassword] = useState('')
  const [needsPassword, setNeedsPassword] = useState(false)
  const [done, setDone] = useState<string | null>(null)

  const load = () => api.getBackups().then(setBackups).catch(() => {})

  useEffect(() => { load().finally(() => setLoading(false)) }, [])

  const run = async () => {
    setRunning(true); setDone(null)
    try {
      if (needsPassword) {
        await api.reauth(password)
        setPassword(''); setNeedsPassword(false)
      }
      const backup = await api.createBackup()
      await load()
      setDone(backup.status === 'complete'
        ? `Backup complete — ${formatBytes(backup.size_bytes)}.`
        : `Backup ${backup.status}. ${backup.error_message}`.trim())
    } catch (error) {
      // 403 here means the password elevation has expired, not that the user lacks access.
      if (error instanceof ApiError && error.status === 403 && !needsPassword) {
        setNeedsPassword(true)
      } else {
        onError(errMsg(error))
      }
    } finally { setRunning(false) }
  }

  const latest = backups[0]

  return (
    <Card title="Backups">
      <p className="text-sm text-muted mb-3">
        A backup captures the household database and protected uploads. It runs on the server and
        can take a moment. Restoring one is a command-line operation — see the restore guide.
      </p>

      {loading ? (
        <p className="text-sm text-muted">Loading…</p>
      ) : latest ? (
        <p className="text-sm text-muted">
          Last backup{' '}
          <span className="font-semibold text-ink">{new Date(latest.created_at).toLocaleString()}</span>
          {' · '}
          <span className={`font-semibold ${BACKUP_STATUS_TONE[latest.status]}`}>{latest.status}</span>
          {latest.status === 'complete' && ` · ${formatBytes(latest.size_bytes)}`}
        </p>
      ) : (
        <p className="text-sm text-warning">No backup has ever been taken on this server.</p>
      )}

      {needsPassword && (
        <div className="mt-3 rounded-xl border border-line bg-sunken p-3">
          <div className="text-xs text-muted-strong mb-1">Confirm your password to run a backup</div>
          <input
            type="password" autoFocus value={password}
            onChange={event => setPassword(event.target.value)}
            onKeyDown={event => { if (event.key === 'Enter' && password) void run() }}
            className="w-full rounded-xl border border-line bg-surface px-3 py-2 text-sm text-ink"
          />
        </div>
      )}

      <div className="mt-3 flex flex-wrap items-center gap-3">
        <Button onClick={run} loading={running} disabled={needsPassword && !password}>
          {needsPassword ? 'Confirm and back up' : 'Back up now'}
        </Button>
        {done && <span className="text-sm font-semibold text-success">{done}</span>}
      </div>

      {backups.length > 1 && (
        <ul className="mt-4 space-y-1 border-t border-line pt-3 text-xs text-muted">
          {backups.slice(1, 6).map(backup => (
            <li key={backup.id} className="flex justify-between gap-3">
              <span>{new Date(backup.created_at).toLocaleString()}</span>
              <span className={BACKUP_STATUS_TONE[backup.status]}>
                {backup.status}{backup.status === 'complete' ? ` · ${formatBytes(backup.size_bytes)}` : ''}
              </span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}

export function SettingsPage() {
  const { nodes, household, refresh } = useStacks()
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'
  const isManager = isAdmin || user?.role === 'manager'

  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Household general
  const [householdName, setHouseholdName] = useState('')
  const [timezone, setTimezone] = useState('UTC')
  const [savingHousehold, setSavingHousehold] = useState(false)
  useEffect(() => {
    if (household) { setHouseholdName(household.name); setTimezone(household.timezone || 'UTC') }
  }, [household])
  const householdDirty = !!household && (householdName !== household.name || timezone !== (household.timezone || 'UTC'))

  // Family colour
  const [familyColour, setFamilyColour] = useState('#7C6F5A')
  const [savingColour, setSavingColour] = useState(false)
  useEffect(() => { if (household?.family_colour) setFamilyColour(household.family_colour) }, [household])

  // Meridian settings
  const [meridian, setMeridian] = useState<MeridianSettings | null>(null)
  const [savingMeridian, setSavingMeridian] = useState(false)
  const meridianEnabled = nodes.some(n => n.key === 'meridian' && n.is_enabled && !n.is_hidden)
  useEffect(() => {
    if (!meridianEnabled) return
    api.getMeridianSettings().then(setMeridian).catch(() => {})
  }, [meridianEnabled])

  const buildable = nodes

  const toggle = async (key: string, enabled: boolean) => {
    setBusy(key); setError(null)
    try {
      if (enabled) await api.disableNode(key)
      else await api.enableNode(key)
      await refresh()
    } catch (e) { setError(errMsg(e)) } finally { setBusy(null) }
  }

  const saveHousehold = async () => {
    setSavingHousehold(true); setError(null)
    try {
      await api.updateHousehold({ name: householdName.trim() || household?.name, timezone })
      await refresh()
    } catch (e) { setError(errMsg(e)) } finally { setSavingHousehold(false) }
  }

  const saveColour = async () => {
    setSavingColour(true); setError(null)
    try { await api.updateHousehold({ family_colour: familyColour }); await refresh() }
    catch (e) { setError(errMsg(e)) } finally { setSavingColour(false) }
  }

  const saveMeridian = async () => {
    if (!meridian) return
    setSavingMeridian(true); setError(null)
    try { const updated = await api.updateMeridianSettings(meridian); setMeridian(updated) }
    catch (e) { setError(errMsg(e)) } finally { setSavingMeridian(false) }
  }

  const inputCls = 'w-full rounded-xl border border-line bg-surface px-3 py-2 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-primary/40'

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-5">
      <PageHeader title="Manage HomeStack" icon="⚙️" subtitle="Household-wide stacks and settings that apply to everyone." />

      {error && (
        <div className="flex items-center justify-between gap-3 bg-danger-soft text-danger text-sm rounded-xl px-4 py-2.5">
          <span>{error}</span>
          <button onClick={() => setError(null)} aria-label="Dismiss">×</button>
        </div>
      )}

      {isManager && (
        <Card title="Household">
          <p className="text-sm text-muted mb-3">Name and timezone shown across the app.</p>
          <div className="space-y-3">
            <div>
              <div className="text-xs text-muted-strong mb-1">Household name</div>
              <input className={inputCls} value={householdName} onChange={e => setHouseholdName(e.target.value)} placeholder="e.g. The Smith Household" />
            </div>
            <div>
              <div className="text-xs text-muted-strong mb-1">Timezone</div>
              <input className={inputCls} list="tz-options" value={timezone} onChange={e => setTimezone(e.target.value)} placeholder="e.g. Australia/Sydney" />
              <datalist id="tz-options">{COMMON_TIMEZONES.map(tz => <option key={tz} value={tz} />)}</datalist>
            </div>
            <Button onClick={saveHousehold} loading={savingHousehold} disabled={!householdDirty}>Save</Button>
          </div>
        </Card>
      )}

      <Card title="Stacks">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <p className="text-sm text-muted">Turn stacks on or off for the whole household. Guides remain available while a node is disabled.</p>
          <button
            type="button"
            onClick={() => {
              localStorage.removeItem(`hs-hidden-guides-${user?.id ?? 'guest'}`)
              window.dispatchEvent(new CustomEvent('homestack-guide-preferences'))
            }}
            className="text-xs font-bold text-primary hover:underline"
          >
            Show in-node guide links
          </button>
        </div>
        <ul className="flex flex-col gap-2">
          {buildable.map(n => {
            const def = STACK_BY_KEY[n.key]
            const guide = NODE_GUIDE_BY_KEY[n.key] ?? fallbackNodeGuide(n)
            const on = n.is_enabled && !n.is_hidden
            const canToggle = Boolean(def?.isNode)
            return (
              <li key={n.key} className="flex items-center gap-3 py-2">
                <span
                  className="inline-grid place-items-center w-10 h-10 rounded-xl text-lg flex-shrink-0"
                  style={{ background: softColour(guide.colour, '22'), color: guide.colour }}
                >
                  {def?.icon || n.custom_icon || n.icon || guide.icon}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <Link to={`/settings/guides/${n.key}`} className="font-semibold text-ink hover:text-primary hover:underline">
                      {n.custom_name || def?.label || n.name}
                    </Link>
                    <span className="group relative inline-flex">
                      <button type="button" className="grid h-6 w-6 place-items-center rounded-full text-xs font-black text-muted hover:bg-sunken hover:text-primary focus:bg-sunken focus:text-primary" aria-label={`About ${guide.label}`}>i</button>
                      <span role="tooltip" className="pointer-events-none absolute bottom-full left-1/2 z-20 mb-2 hidden w-64 -translate-x-1/2 rounded-xl border border-line bg-surface p-2.5 text-xs font-normal leading-5 text-muted-strong shadow-card group-hover:block group-focus-within:block">
                        {guide.summary} <span className="font-bold text-primary">Open the title for the full guide.</span>
                      </span>
                    </span>
                  </div>
                  <div className="text-xs text-muted truncate">{guide.summary}</div>
                </div>
                {canToggle ? (
                  // 44px hit area around a visually unchanged 48x28 pill (docs/36 §3.3).
                  <button
                    onClick={() => toggle(n.key, on)}
                    disabled={busy === n.key || !isManager}
                    role="switch"
                    aria-checked={on}
                    className="grid h-11 w-11 flex-shrink-0 place-items-center disabled:opacity-50"
                  >
                    <span className={`relative h-7 w-12 rounded-full transition-colors ${on ? 'bg-success' : 'bg-line-strong'}`}>
                      <span className={`absolute top-1 w-5 h-5 rounded-full bg-white shadow transition-all ${on ? 'left-6' : 'left-1'}`} />
                    </span>
                  </button>
                ) : <span className="flex-shrink-0 rounded-full bg-sunken px-2.5 py-1 text-[11px] font-bold text-muted">Future</span>}
              </li>
            )
          })}
        </ul>
      </Card>

      {/* docs/36 §6.15: a settings directory, not another dense card — the same destination
          list regardless of screen size, since these are always one-tap-deeper navigation
          rather than inline controls. */}
      <MobileSection title="More">
        {isAdmin && <MobileListRow icon="👥" to="/users" title="People & access" subtitle="Profiles, roles and sign-in" />}
        <MobileListRow icon="🔔" to="/settings/notifications" title="Your notifications" subtitle="What you get notified about, and quiet hours — applies to your login only" />
        {isAdmin && <MobileListRow icon="📱" to="/settings/push-devices" title="Push devices" subtitle="Household-wide — who's registered for push notifications" />}
        <MobileListRow icon="🕘" to="/settings/version-history" title="Version history" subtitle="The installed version and what's changed over time" />
      </MobileSection>

      {isAdmin && <BackupCard onError={setError} />}

      <Card title="Family colour">
        <p className="text-sm text-muted mb-3">
          The accent used on the calendar for "Whole family" events and tasks (anything not
          assigned to a specific person).
        </p>
        <div className="flex items-center gap-3">
          <div className="min-w-0 flex-1"><ColourPicker value={familyColour} onChange={value => isManager && setFamilyColour(value)} ariaLabel="Whole-family calendar colour" /></div>
          <span
            className="text-sm px-3 py-1.5 rounded-full font-medium"
            style={{ background: softColour(familyColour, '22'), color: familyColour }}
          >
            Whole family
          </span>
          <Button onClick={saveColour} loading={savingColour} disabled={!isManager || familyColour === household?.family_colour}>Save</Button>
        </div>
      </Card>

      {meridianEnabled && meridian && (
        <Card title="Meridian">
          <p className="text-sm text-muted mb-4">Configure Meridian behaviour for the whole household.</p>
          <div className="space-y-4">
            <div>
              <div className="text-xs text-muted-strong mb-1">Points label (e.g. "Stars", "Coins")</div>
              <input
                className={inputCls}
                value={meridian.points_label}
                onChange={e => setMeridian(m => m ? { ...m, points_label: e.target.value } : m)}
                placeholder="Points"
                disabled={!isManager}
              />
            </div>
            {([
              ['group_goals_enabled', 'Group goals', 'Allow the household to pool points toward shared goals'],
              ['wishlist_requests_enabled', 'Wishlist requests', 'Allow children to request wishlist items for manager approval'],
              ['auto_end_streaks', 'Auto-end streaks', 'Automatically break a streak if a routine is missed (strict mode)'],
            ] as [keyof MeridianSettings, string, string][]).map(([key, label, desc]) => (
              <div key={key} className="flex items-start gap-3">
                <div className="flex-1">
                  <div className="text-sm font-semibold text-ink">{label}</div>
                  <div className="text-xs text-muted">{desc}</div>
                </div>
                <button
                  role="switch"
                  aria-checked={!!meridian[key]}
                  onClick={() => isManager && setMeridian(m => m ? { ...m, [key]: !m[key] } : m)}
                  disabled={!isManager}
                  className={`relative flex-shrink-0 w-11 h-6 rounded-full transition-colors disabled:opacity-50 ${meridian[key] ? 'bg-success' : 'bg-line-strong'}`}
                >
                  <span className={`absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition-all ${meridian[key] ? 'left-5' : 'left-0.5'}`} />
                </button>
              </div>
            ))}
            {isManager && (
              <Button onClick={saveMeridian} loading={savingMeridian}>Save Meridian settings</Button>
            )}
          </div>
        </Card>
      )}
    </div>
  )
}
