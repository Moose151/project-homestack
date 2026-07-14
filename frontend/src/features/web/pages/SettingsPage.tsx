import { useEffect, useState } from 'react'
import { api } from '../../../api/client'
import { useStacks } from '../../stacks/StacksContext'
import { STACK_BY_KEY, softColour } from '../../../config/stacks'
import { Card } from '../../../components/Card'
import { Button } from '../../../components/Button'

const errMsg = (e: unknown) => (e instanceof Error ? e.message : 'Something went wrong.')

export function SettingsPage() {
  const { nodes, household, refresh } = useStacks()
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const [familyColour, setFamilyColour] = useState('#7C6F5A')
  const [savingColour, setSavingColour] = useState(false)
  useEffect(() => { if (household?.family_colour) setFamilyColour(household.family_colour) }, [household])

  // Only stacks we have actually built (in the config, node-backed) are toggleable — the rest
  // of the node catalogue isn't routable yet.
  const buildable = nodes.filter(n => STACK_BY_KEY[n.key]?.isNode)

  const toggle = async (key: string, enabled: boolean) => {
    setBusy(key); setError(null)
    try {
      if (enabled) await api.disableNode(key)
      else await api.enableNode(key)
      await refresh()
    } catch (e) { setError(errMsg(e)) } finally { setBusy(null) }
  }

  const saveColour = async () => {
    setSavingColour(true); setError(null)
    try { await api.updateHousehold({ family_colour: familyColour }); await refresh() }
    catch (e) { setError(errMsg(e)) } finally { setSavingColour(false) }
  }

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
                  disabled={busy === n.key}
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
          />
          <span
            className="text-sm px-3 py-1.5 rounded-full font-medium"
            style={{ background: softColour(familyColour, '22'), color: familyColour }}
          >
            Whole family
          </span>
          <div className="flex-1" />
          <Button onClick={saveColour} loading={savingColour}
            disabled={familyColour === household?.family_colour}>Save</Button>
        </div>
      </Card>
    </div>
  )
}
