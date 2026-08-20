import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, ApiError } from '../../../api/client'
import type { Backup, MeridianSettings } from '../../../api/types'
import { useStacks } from '../../stacks/StacksContext'
import { useAuth } from '../../auth/AuthContext'
import { STACK_BY_KEY, softColour } from '../../../config/stacks'
import { NODE_GUIDE_BY_KEY, fallbackNodeGuide } from '../../../config/nodeGuides'
import { Button } from '../../../components/Button'
import { PageHeader } from '../../../components/PageHeader'
import { ColourPicker } from '../../../components/ColourPicker'
import { AccordionItem } from '../../../components/Accordion'
import { MobileListRow } from '../../../components/mobile'

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

// The canonical set of Settings accordion sections, and the only valid `#hash` deep-link
// targets into this page — e.g. a future "Manage nodes" link can point at `/settings#stacks`
// and have that section open automatically (see the hash-sync effect in SettingsPage below).
const SECTION_KEYS = [
  'household', 'people', 'stacks', 'backups', 'quick-launch',
  'notifications', 'push-devices', 'appearance', 'tasks', 'system',
] as const
type SectionKey = (typeof SECTION_KEYS)[number]

function sectionFromHash(hash: string): SectionKey | null {
  const key = hash.replace(/^#/, '')
  return (SECTION_KEYS as readonly string[]).includes(key) ? (key as SectionKey) : null
}

/**
 * Take a backup of the database and protected media (D17).
 *
 * The backup API has existed since Milestone 1 but nothing in the app ever called it, so the
 * only way to run one was by hand against the API. Creating a backup needs recent password
 * re-authentication, so this asks for the password only when the server says it needs one
 * rather than demanding it up front.
 */
function BackupSection({ onError }: { onError: (message: string) => void }) {
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
    <div>
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
    </div>
  )
}

/** A brief description plus a single clear action into a genuinely separate management page —
 * used for sections that are intentionally not inline configuration (docs/31 §5). */
function LinkOutSection({ description, icon, to, cta }: {
  description: string
  icon: string
  to: string
  cta: string
}) {
  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-muted">{description}</p>
      <MobileListRow icon={icon} to={to} title={cta} compact />
    </div>
  )
}

export function SettingsPage() {
  const { nodes, household, refresh } = useStacks()
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'
  const isManager = isAdmin || user?.role === 'manager'

  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Settings is a single accordion: only one section open at a time, on every viewport. A
  // `#hash` deep link (e.g. `/settings#stacks`) opens the matching section automatically, and
  // stays in sync as the reader opens/closes sections so refreshing keeps the same one open.
  const [openSection, setOpenSection] = useState<SectionKey | null>(
    () => sectionFromHash(window.location.hash),
  )
  useEffect(() => {
    const onHashChange = () => setOpenSection(sectionFromHash(window.location.hash))
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])
  const toggleSection = (key: SectionKey) => {
    setOpenSection(current => {
      const next = current === key ? null : key
      const base = window.location.pathname + window.location.search
      window.history.replaceState(null, '', next ? `${base}#${next}` : base)
      return next
    })
  }

  // Household general
  const [householdName, setHouseholdName] = useState('')
  const [timezone, setTimezone] = useState('UTC')
  // Household location drives which public holidays a Calendar Source produces. Configuration
  // only — nothing here affects permissions.
  const [country, setCountry] = useState('')
  const [region, setRegion] = useState('')
  const [locality, setLocality] = useState('')
  const [savingHousehold, setSavingHousehold] = useState(false)
  useEffect(() => {
    if (household) {
      setHouseholdName(household.name)
      setTimezone(household.timezone || 'UTC')
      setCountry(household.country || '')
      setRegion(household.region || '')
      setLocality(household.locality || '')
    }
  }, [household])
  const householdDirty = !!household && (
    householdName !== household.name
    || timezone !== (household.timezone || 'UTC')
    || country !== (household.country || '')
    || region !== (household.region || '')
    || locality !== (household.locality || '')
  )

  // Family colour
  const [familyColour, setFamilyColour] = useState('#7C6F5A')
  const [savingColour, setSavingColour] = useState(false)
  useEffect(() => { if (household?.family_colour) setFamilyColour(household.family_colour) }, [household])

  // Meridian (Tasks) settings
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
      await api.updateHousehold({
        name: householdName.trim() || household?.name, timezone, country, region, locality,
      })
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

      <div className="flex flex-col gap-2.5">
        {isManager && (
          <AccordionItem
            icon="🏠" title="Household" subtitle="Name, timezone and location"
            isOpen={openSection === 'household'} onToggle={() => toggleSection('household')}
          >
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
              <div className="border-t border-line pt-3">
                <div className="text-xs font-semibold text-muted-strong">Location</div>
                <p className="mt-0.5 text-xs text-muted">
                  Decides which public holidays your calendar shows. Automatic holidays are currently
                  available for Queensland only. Nothing here affects who can see what.
                </p>
                <div className="mt-2 grid gap-2 sm:grid-cols-3">
                  <label>
                    <span className="mb-1 block text-xs text-muted-strong">Country</span>
                    <select className={inputCls} value={country} onChange={e => setCountry(e.target.value)}>
                      <option value="">Not set</option>
                      <option value="AU">Australia</option>
                    </select>
                  </label>
                  <label>
                    <span className="mb-1 block text-xs text-muted-strong">State / territory</span>
                    <select className={inputCls} value={region} onChange={e => setRegion(e.target.value)} disabled={country !== 'AU'}>
                      <option value="">Not set</option>
                      {['ACT', 'NSW', 'NT', 'QLD', 'SA', 'TAS', 'VIC', 'WA'].map(code => (
                        <option key={code} value={code}>
                          {code}{code === 'QLD' ? '' : ' — holidays not available yet'}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    <span className="mb-1 block text-xs text-muted-strong">Local area</span>
                    <select className={inputCls} value={locality} onChange={e => setLocality(e.target.value)} disabled={region !== 'QLD'}>
                      <option value="">Not set</option>
                      <option value="brisbane">Brisbane</option>
                      <option value="gold_coast">Gold Coast</option>
                      <option value="toowoomba">Toowoomba</option>
                      <option value="cairns">Cairns</option>
                      <option value="townsville">Townsville</option>
                    </select>
                  </label>
                </div>
              </div>
              <Button onClick={saveHousehold} loading={savingHousehold} disabled={!householdDirty}>Save</Button>
            </div>
          </AccordionItem>
        )}

        {isAdmin && (
          <AccordionItem
            icon="👥" title="People & access" subtitle="Profiles, roles and sign-in"
            isOpen={openSection === 'people'} onToggle={() => toggleSection('people')}
          >
            <LinkOutSection
              icon="👥" to="/users" cta="Open People & access"
              description="Add and edit household members, manage roles, and control how each person signs in — this is a full management page rather than a couple of quick fields."
            />
          </AccordionItem>
        )}

        <AccordionItem
          icon="🧩" title="Stacks" subtitle="Enabled HomeStack areas"
          isOpen={openSection === 'stacks'} onToggle={() => toggleSection('stacks')}
        >
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm text-muted">Turn stacks on or off for the whole household. Guides remain available while a node is disabled.</p>
            <button
              type="button"
              onClick={() => {
                api.resetGuideDismissals()
                  .then(() => window.dispatchEvent(new CustomEvent('homestack-guide-preferences')))
                  .catch(error => setError(errMsg(error)))
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
        </AccordionItem>

        {isAdmin && (
          <AccordionItem
            icon="💾" title="Backups" subtitle="Run and review backups"
            isOpen={openSection === 'backups'} onToggle={() => toggleSection('backups')}
          >
            <BackupSection onError={setError} />
          </AccordionItem>
        )}

        <AccordionItem
          icon="🚀" title="Quick Launch" subtitle="Your own shortcuts to the places you go most"
          isOpen={openSection === 'quick-launch'} onToggle={() => toggleSection('quick-launch')}
        >
          <LinkOutSection
            icon="🚀" to="/settings/quick-launch" cta="Open Quick Launch"
            description="Choose the shortcuts that show up on your own dock/launcher — these are personal to you, not shared with the household."
          />
        </AccordionItem>

        <AccordionItem
          icon="🔔" title="Notifications" subtitle="Your notification preferences"
          isOpen={openSection === 'notifications'} onToggle={() => toggleSection('notifications')}
        >
          <LinkOutSection
            icon="🔔" to="/settings/notifications" cta="Open Notifications"
            description="Choose what you get notified about, in-app and push, plus quiet hours and your morning digest time."
          />
        </AccordionItem>

        {isAdmin && (
          <AccordionItem
            icon="📱" title="Push devices" subtitle="Registered notification devices"
            isOpen={openSection === 'push-devices'} onToggle={() => toggleSection('push-devices')}
          >
            <LinkOutSection
              icon="📱" to="/settings/push-devices" cta="Open push devices"
              description="Review and manage every device registered to receive push notifications for this household."
            />
          </AccordionItem>
        )}

        <AccordionItem
          icon="🎨" title="Appearance" subtitle="Family colour"
          isOpen={openSection === 'appearance'} onToggle={() => toggleSection('appearance')}
        >
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
        </AccordionItem>

        {meridianEnabled && meridian && (
          <AccordionItem
            icon="⭐" title="Tasks" subtitle="Tasks and rewards settings"
            isOpen={openSection === 'tasks'} onToggle={() => toggleSection('tasks')}
          >
            <p className="text-sm text-muted mb-4">Configure Tasks behaviour for the whole household.</p>
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
                    className="grid h-11 w-11 flex-shrink-0 place-items-center disabled:opacity-50"
                  >
                    <span className={`relative h-6 w-11 rounded-full transition-colors ${meridian[key] ? 'bg-success' : 'bg-line-strong'}`}>
                      <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-all ${meridian[key] ? 'left-5' : 'left-0.5'}`} />
                    </span>
                  </button>
                </div>
              ))}
              {isManager && (
                <Button onClick={saveMeridian} loading={savingMeridian}>Save Tasks settings</Button>
              )}
            </div>
          </AccordionItem>
        )}

        <AccordionItem
          icon="🕘" title="Version & system" subtitle="Version history and guides"
          isOpen={openSection === 'system'} onToggle={() => toggleSection('system')}
        >
          <div className="flex flex-col gap-2">
            <MobileListRow icon="🕘" to="/settings/version-history" title="Version history" subtitle="Installed version and changes" compact />
            <MobileListRow icon="📚" to="/settings/guides/hub" title="Guides" subtitle="Open a stack guide" compact />
          </div>
        </AccordionItem>
      </div>
    </div>
  )
}
