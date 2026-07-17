import { useEffect, useState } from 'react'
import { api } from '../../../api/client'
import type { MeridianSettings } from '../../../api/types'
import { useStacks } from '../../stacks/StacksContext'
import { useAuth } from '../../auth/AuthContext'
import { STACK_BY_KEY, softColour } from '../../../config/stacks'
import { Card } from '../../../components/Card'
import { Button } from '../../../components/Button'

const COMMON_TIMEZONES = [
  'UTC', 'Australia/Sydney', 'Australia/Melbourne', 'Australia/Brisbane',
  'Australia/Perth', 'Australia/Adelaide', 'America/New_York', 'America/Chicago',
  'America/Denver', 'America/Los_Angeles', 'Europe/London', 'Europe/Paris',
  'Europe/Berlin', 'Asia/Tokyo', 'Asia/Singapore', 'Asia/Dubai',
]

const errMsg = (e: unknown) => (e instanceof Error ? e.message : 'Something went wrong.')

export function SettingsPage() {
  const { nodes, household, refresh } = useStacks()
  const { user } = useAuth()
  const isManager = user?.role === 'admin' || user?.role === 'manager'

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

  const buildable = nodes.filter(n => STACK_BY_KEY[n.key]?.isNode)

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
    <div className="space-y-5 max-w-2xl mx-auto">
      <div>
        <h1 className="text-2xl font-extrabold tracking-tight text-ink">Settings</h1>
        <p className="text-sm text-muted">Household-wide configuration. Applies to everyone.</p>
      </div>

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
        <p className="text-sm text-muted mb-3">Turn stacks on or off for the whole household.</p>
        <ul className="flex flex-col gap-2">
          {buildable.map(n => {
            const def = STACK_BY_KEY[n.key]
            const on = n.is_enabled && !n.is_hidden
            return (
              <li key={n.key} className="flex items-center gap-3 py-2">
                <span
                  className="inline-grid place-items-center w-10 h-10 rounded-xl text-lg flex-shrink-0"
                  style={{ background: softColour(def.colour, '22'), color: def.colour }}
                >
                  {def.icon}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-ink">{def.label}</div>
                  <div className="text-xs text-muted truncate">{n.description}</div>
                </div>
                <button
                  onClick={() => toggle(n.key, on)}
                  disabled={busy === n.key || !isManager}
                  role="switch"
                  aria-checked={on}
                  className={`relative w-12 h-7 rounded-full transition-colors flex-shrink-0 disabled:opacity-50 ${on ? 'bg-success' : 'bg-line-strong'}`}
                >
                  <span className={`absolute top-1 w-5 h-5 rounded-full bg-white shadow transition-all ${on ? 'left-6' : 'left-1'}`} />
                </button>
              </li>
            )
          })}
        </ul>
      </Card>

      <Card title="Family colour">
        <p className="text-sm text-muted mb-3">
          The accent used on the calendar for "Whole family" events and tasks (anything not
          assigned to a specific person).
        </p>
        <div className="flex items-center gap-3">
          <input
            type="color"
            value={familyColour}
            onChange={e => setFamilyColour(e.target.value)}
            className="w-12 h-12 rounded-lg border border-line cursor-pointer"
            aria-label="Family colour"
            disabled={!isManager}
          />
          <span
            className="text-sm px-3 py-1.5 rounded-full font-medium"
            style={{ background: softColour(familyColour, '22'), color: familyColour }}
          >
            Whole family
          </span>
          <div className="flex-1" />
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
