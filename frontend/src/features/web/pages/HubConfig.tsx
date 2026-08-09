import { useEffect, useState, type DragEvent } from 'react'
import { api } from '../../../api/client'
import type { HubWidgetConfig } from '../../../api/types'
import { Card } from '../../../components/Card'
import { Button } from '../../../components/Button'
import { Field, Input } from '../../../components/Field'

const SIZES = ['small', 'medium', 'large'] as const

export function HubConfig({ isAdmin, onChanged }: { isAdmin: boolean; onChanged: () => void }) {
  const [widgets, setWidgets] = useState<HubWidgetConfig[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [draggedKey, setDraggedKey] = useState<string | null>(null)
  const [dragOverKey, setDragOverKey] = useState<string | null>(null)
  const [countdownTitle, setCountdownTitle] = useState('')
  const [countdownDate, setCountdownDate] = useState('')

  const load = () => api.getHubWidgetConfig().then(r => {
    setWidgets(r.widgets)
    const countdown = r.widgets.find(widget => widget.key === 'countdown')
    setCountdownTitle(countdown?.settings.title ?? '')
    setCountdownDate(countdown?.settings.target_date ?? '')
  })
  useEffect(() => { load() }, [])

  const apply = async (fn: () => Promise<{ widgets: HubWidgetConfig[] }>) => {
    setBusy(true); setError('')
    try {
      const r = await fn()
      setWidgets(r.widgets)
      onChanged()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not save the Hub change.')
    } finally {
      setBusy(false)
    }
  }

  // "Your Hub": household-enabled widgets in their effective (per-user) order.
  const mine = widgets
    .filter(w => w.household_enabled)
    .sort((a, b) => (a.user_order ?? a.household_order) - (b.user_order ?? b.household_order))

  const saveOrder = async (next: HubWidgetConfig[]) => {
    if (busy) return
    const previous = widgets
    const positions = new Map(next.map((widget, index) => [widget.key, index]))
    setWidgets(current => current.map(widget => (
      positions.has(widget.key)
        ? { ...widget, user_order: positions.get(widget.key)! }
        : widget
    )))
    setBusy(true); setError('')
    try {
      const response = await api.setUserWidgetOrder(next.map(widget => widget.key))
      setWidgets(response.widgets)
      onChanged()
    } catch (reason) {
      setWidgets(previous)
      setError(reason instanceof Error ? reason.message : 'Could not save the new widget order.')
    } finally {
      setBusy(false)
    }
  }

  const reorder = (idx: number, dir: -1 | 1) => {
    const next = [...mine]
    const j = idx + dir
    if (j < 0 || j >= next.length) return
    ;[next[idx], next[j]] = [next[j], next[idx]]
    void saveOrder(next)
  }

  const beginDrag = (event: DragEvent, key: string) => {
    if (busy) { event.preventDefault(); return }
    event.dataTransfer.effectAllowed = 'move'
    event.dataTransfer.setData('text/plain', key)
    setDraggedKey(key)
  }

  const dropOn = (event: DragEvent, targetKey: string) => {
    event.preventDefault()
    const sourceKey = draggedKey || event.dataTransfer.getData('text/plain')
    setDraggedKey(null); setDragOverKey(null)
    if (!sourceKey || sourceKey === targetKey || busy) return
    const next = [...mine]
    const from = next.findIndex(widget => widget.key === sourceKey)
    const to = next.findIndex(widget => widget.key === targetKey)
    if (from < 0 || to < 0) return
    const [moved] = next.splice(from, 1)
    next.splice(to, 0, moved)
    void saveOrder(next)
  }

  return (
    <Card title="Customise your Hub">
      <div className="flex flex-col gap-4">
        {error && <div role="alert" className="rounded-xl bg-danger-soft px-3 py-2 text-sm text-danger">{error}</div>}
        <div>
          <p className="text-xs font-semibold text-muted uppercase tracking-wide mb-2">Your Hub</p>
          <p className="mb-2 hidden text-xs text-muted md:block">Drag the grip here—or on the Hub cards below—to rearrange. Arrow buttons still work too.</p>
          <ul className="flex flex-col gap-1.5">
            {mine.map((w, i) => (
              <li
                key={w.key}
                onDragOver={event => { event.preventDefault(); event.dataTransfer.dropEffect = 'move'; setDragOverKey(w.key) }}
                onDragLeave={() => setDragOverKey(current => current === w.key ? null : current)}
                onDrop={event => dropOn(event, w.key)}
                className={`flex min-h-12 items-center gap-2 rounded-xl border px-2 text-sm transition-colors ${
                  dragOverKey === w.key && draggedKey !== w.key
                    ? 'border-primary bg-primary-soft'
                    : 'border-transparent bg-sunken/50'
                } ${draggedKey === w.key ? 'opacity-50' : ''}`}
              >
                <span
                  draggable={!busy}
                  onDragStart={event => beginDrag(event, w.key)}
                  onDragEnd={() => { setDraggedKey(null); setDragOverKey(null) }}
                  className="hidden h-10 w-8 cursor-grab select-none items-center justify-center rounded-lg text-lg text-muted hover:bg-raised hover:text-ink active:cursor-grabbing md:flex"
                  title={`Drag ${w.name}`}
                  aria-label={`Drag ${w.name} to reorder`}
                >
                  ⠿
                </span>
                <div className="flex flex-col">
                  <button disabled={busy || i === 0} onClick={() => reorder(i, -1)}
                    aria-label={`Move ${w.name} up`}
                    className="grid h-5 w-8 place-items-center text-muted hover:text-ink disabled:opacity-30 leading-none">▲</button>
                  <button disabled={busy || i === mine.length - 1} onClick={() => reorder(i, 1)}
                    aria-label={`Move ${w.name} down`}
                    className="grid h-5 w-8 place-items-center text-muted hover:text-ink disabled:opacity-30 leading-none">▼</button>
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
                <li key={w.key} className="rounded-xl text-sm">
                  <div className="flex min-h-10 items-center gap-2">
                    <span className="flex-1 text-ink">{w.name}</span>
                    <select
                      disabled={busy || !w.household_enabled}
                      value={w.size}
                      onChange={e => apply(() => api.setHouseholdWidget(w.key, { size: e.target.value }))}
                      className="rounded-lg border border-line bg-raised px-1.5 py-1 text-xs text-ink disabled:opacity-40"
                    >
                      {SIZES.map(s => <option key={s} value={s}>{s}</option>)}
                    </select>
                    <button
                      disabled={busy}
                      onClick={() => apply(() => api.setHouseholdWidget(w.key, { is_enabled: !w.household_enabled }))}
                      className={`min-h-9 rounded-lg px-2 py-1 text-xs font-medium ${
                        w.household_enabled ? 'bg-primary-soft text-primary' : 'bg-sunken text-muted'
                      }`}
                    >
                      {w.household_enabled ? 'Enabled' : 'Disabled'}
                    </button>
                  </div>
                  {w.key === 'countdown' && (
                    <div className="mt-2 grid gap-2 rounded-xl bg-sunken p-3 sm:grid-cols-[1fr_180px_auto] sm:items-end">
                      <Field label="Countdown name">
                        <Input value={countdownTitle} onChange={event => setCountdownTitle(event.target.value)} placeholder="Our holiday" />
                      </Field>
                      <Field label="Target date">
                        <Input type="date" value={countdownDate} onChange={event => setCountdownDate(event.target.value)} />
                      </Field>
                      <Button
                        size="sm"
                        disabled={busy || !countdownTitle.trim() || !countdownDate}
                        onClick={() => apply(() => api.setHouseholdWidget('countdown', {
                          is_enabled: true,
                          size: w.size,
                          settings: { title: countdownTitle.trim(), target_date: countdownDate },
                        }))}
                      >
                        Save & show
                      </Button>
                    </div>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </Card>
  )
}
