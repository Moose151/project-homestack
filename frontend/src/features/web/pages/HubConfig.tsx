import { useEffect, useState } from 'react'
import { api } from '../../../api/client'
import type { HubWidgetConfig } from '../../../api/types'
import { Card } from '../../../components/Card'

const SIZES = ['small', 'medium', 'large'] as const

export function HubConfig({ isAdmin, onChanged }: { isAdmin: boolean; onChanged: () => void }) {
  const [widgets, setWidgets] = useState<HubWidgetConfig[]>([])
  const [busy, setBusy] = useState(false)

  const load = () => api.getHubWidgetConfig().then(r => setWidgets(r.widgets))
  useEffect(() => { load() }, [])

  const apply = async (fn: () => Promise<{ widgets: HubWidgetConfig[] }>) => {
    setBusy(true)
    try {
      const r = await fn()
      setWidgets(r.widgets)
      onChanged()
    } finally {
      setBusy(false)
    }
  }

  // "Your Hub": household-enabled widgets in their effective (per-user) order.
  const mine = widgets
    .filter(w => w.household_enabled)
    .sort((a, b) => (a.user_order ?? a.household_order) - (b.user_order ?? b.household_order))

  const reorder = (idx: number, dir: -1 | 1) => {
    const next = [...mine]
    const j = idx + dir
    if (j < 0 || j >= next.length) return
    ;[next[idx], next[j]] = [next[j], next[idx]]
    apply(async () => {
      // Normalise everyone's order to the new sequence (last response wins).
      let last = { widgets } as { widgets: HubWidgetConfig[] }
      for (let i = 0; i < next.length; i++) last = await api.setUserWidget(next[i].key, { display_order: i })
      return last
    })
  }

  return (
    <Card title="Customise your Hub">
      <div className="flex flex-col gap-4">
        <div>
          <p className="text-xs font-semibold text-muted uppercase tracking-wide mb-2">Your Hub</p>
          <ul className="flex flex-col gap-1.5">
            {mine.map((w, i) => (
              <li key={w.key} className="flex items-center gap-2 text-sm">
                <div className="flex flex-col">
                  <button disabled={busy || i === 0} onClick={() => reorder(i, -1)}
                    className="text-muted hover:text-ink disabled:opacity-30 leading-none">▲</button>
                  <button disabled={busy || i === mine.length - 1} onClick={() => reorder(i, 1)}
                    className="text-muted hover:text-ink disabled:opacity-30 leading-none">▼</button>
                </div>
                <span className={`flex-1 ${w.user_hidden ? 'text-muted line-through' : 'text-ink'}`}>{w.name}</span>
                <button
                  disabled={busy}
                  onClick={() => apply(() => api.setUserWidget(w.key, { is_enabled: w.user_hidden }))}
                  className={`text-xs px-2 py-1 rounded-lg font-medium ${
                    w.user_hidden ? 'bg-sunken text-muted' : 'bg-primary-soft text-primary'
                  }`}
                >
                  {w.user_hidden ? 'Hidden' : 'Shown'}
                </button>
              </li>
            ))}
            {mine.length === 0 && <li className="text-sm text-muted">No widgets enabled for the household yet.</li>}
          </ul>
        </div>

        {isAdmin && (
          <div className="pt-3 border-t border-line">
            <p className="text-xs font-semibold text-muted uppercase tracking-wide mb-2">Household defaults (admin)</p>
            <ul className="flex flex-col gap-1.5">
              {widgets.map(w => (
                <li key={w.key} className="flex items-center gap-2 text-sm">
                  <span className="flex-1 text-ink">{w.name}</span>
                  <select
                    disabled={busy || !w.household_enabled}
                    value={w.size}
                    onChange={e => apply(() => api.setHouseholdWidget(w.key, { size: e.target.value }))}
                    className="text-xs rounded-lg border border-line bg-raised px-1.5 py-1 text-ink disabled:opacity-40"
                  >
                    {SIZES.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                  <button
                    disabled={busy}
                    onClick={() => apply(() => api.setHouseholdWidget(w.key, { is_enabled: !w.household_enabled }))}
                    className={`text-xs px-2 py-1 rounded-lg font-medium ${
                      w.household_enabled ? 'bg-primary-soft text-primary' : 'bg-sunken text-muted'
                    }`}
                  >
                    {w.household_enabled ? 'Enabled' : 'Disabled'}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </Card>
  )
}
