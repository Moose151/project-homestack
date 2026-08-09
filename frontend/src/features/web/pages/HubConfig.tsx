import { useEffect, useMemo, useState, type DragEvent } from 'react'
import { api } from '../../../api/client'
import type { HubWidgetConfig } from '../../../api/types'
import { Card } from '../../../components/Card'
import { Button } from '../../../components/Button'
import { Field, Input } from '../../../components/Field'
import { STACK_BY_KEY } from '../../../config/stacks'

const SIZES = [
  { key: 'small', label: 'Small' },
  { key: 'medium', label: 'Medium' },
  { key: 'large', label: 'Wide' },
] as const

/** Household-facing group name for a widget — its node's nav label, or "Household" for core. */
function groupName(widget: HubWidgetConfig): string {
  if (!widget.source_node) return 'Household'
  return STACK_BY_KEY[widget.source_node]?.navLabel ?? widget.source_node_name ?? 'Other'
}

function groupIcon(widget: HubWidgetConfig): string {
  if (!widget.source_node) return '🏡'
  return STACK_BY_KEY[widget.source_node]?.icon ?? '◇'
}

export function HubConfig({ isAdmin, onChanged }: { isAdmin: boolean; onChanged: () => void }) {
  const [widgets, setWidgets] = useState<HubWidgetConfig[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [draggedKey, setDraggedKey] = useState<string | null>(null)
  const [dragOverKey, setDragOverKey] = useState<string | null>(null)
  const [query, setQuery] = useState('')
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

  // On the board = household-enabled and not personally hidden, in effective order.
  const onBoard = useMemo(() => widgets
    .filter(w => w.household_enabled && !w.user_hidden)
    .sort((a, b) => (a.user_order ?? a.household_order) - (b.user_order ?? b.household_order)),
    [widgets])

  // Everything else is a single "add" catalogue, grouped by where it comes from, so adding a
  // card is one click in one place instead of a hunt across two lists.
  const available = useMemo(() => {
    const term = query.trim().toLowerCase()
    const rows = widgets
      .filter(w => !w.household_enabled || w.user_hidden)
      .filter(w => !term
        || w.name.toLowerCase().includes(term)
        || w.description.toLowerCase().includes(term)
        || groupName(w).toLowerCase().includes(term))
    const groups = new Map<string, HubWidgetConfig[]>()
    for (const widget of rows) {
      const name = groupName(widget)
      groups.set(name, [...(groups.get(name) ?? []), widget])
    }
    return [...groups.entries()].sort((a, b) => a[0].localeCompare(b[0]))
  }, [widgets, query])

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

  const move = (index: number, direction: -1 | 1) => {
    const next = [...onBoard]
    const target = index + direction
    if (target < 0 || target >= next.length) return
    ;[next[index], next[target]] = [next[target], next[index]]
    void saveOrder(next)
  }

  /** Add to the board: enable for the household when allowed, and clear any personal hide. */
  const addWidget = (widget: HubWidgetConfig) => apply(async () => {
    if (!widget.household_enabled && isAdmin) await api.setHouseholdWidget(widget.key, { is_enabled: true })
    return api.setUserWidget(widget.key, { is_enabled: true })
  })

  /** Remove from the board: a personal hide, so one person's choice never edits the household's. */
  const removeWidget = (widget: HubWidgetConfig) =>
    apply(() => api.setUserWidget(widget.key, { is_enabled: false }))

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
    const next = [...onBoard]
    const from = next.findIndex(widget => widget.key === sourceKey)
    const to = next.findIndex(widget => widget.key === targetKey)
    if (from < 0 || to < 0) return
    const [moved] = next.splice(from, 1)
    next.splice(to, 0, moved)
    void saveOrder(next)
  }

  return (
    <Card title="Tune this page">
      <div className="flex flex-col gap-5">
        {error && <div role="alert" className="rounded-xl bg-danger-soft px-3 py-2 text-sm text-danger">{error}</div>}

        <p className="text-sm text-muted">
          Cards only appear on your Home page when they have something to show, so a quiet card is
          not wasted space — it simply waits until it matters.
        </p>

        <section>
          <h3 className="mb-2 text-sm font-bold text-ink">On your Home page</h3>
          {onBoard.length === 0 ? (
            <p className="text-sm text-muted">Nothing chosen yet — add a card below.</p>
          ) : (
            <ul className="flex flex-col gap-1.5">
              {onBoard.map((widget, index) => (
                <li
                  key={widget.key}
                  onDragOver={event => { event.preventDefault(); event.dataTransfer.dropEffect = 'move'; setDragOverKey(widget.key) }}
                  onDragLeave={() => setDragOverKey(current => current === widget.key ? null : current)}
                  onDrop={event => dropOn(event, widget.key)}
                  className={`flex min-h-14 flex-wrap items-center gap-2 rounded-xl border px-2 py-1.5 text-sm transition-colors ${
                    dragOverKey === widget.key && draggedKey !== widget.key
                      ? 'border-primary bg-primary-soft'
                      : 'border-line bg-sunken/50'
                  } ${draggedKey === widget.key ? 'opacity-50' : ''}`}
                >
                  <span
                    draggable={!busy}
                    onDragStart={event => beginDrag(event, widget.key)}
                    onDragEnd={() => { setDraggedKey(null); setDragOverKey(null) }}
                    className="hidden h-10 w-8 cursor-grab select-none items-center justify-center rounded-lg text-lg text-muted hover:bg-raised hover:text-ink active:cursor-grabbing md:flex"
                    title={`Drag ${widget.name}`}
                    aria-label={`Drag ${widget.name} to reorder`}
                  >
                    ⠿
                  </span>
                  <div className="flex flex-col">
                    <button
                      disabled={busy || index === 0}
                      onClick={() => move(index, -1)}
                      aria-label={`Move ${widget.name} up`}
                      className="grid h-6 w-8 place-items-center leading-none text-muted hover:text-ink disabled:opacity-30"
                    >▲</button>
                    <button
                      disabled={busy || index === onBoard.length - 1}
                      onClick={() => move(index, 1)}
                      aria-label={`Move ${widget.name} down`}
                      className="grid h-6 w-8 place-items-center leading-none text-muted hover:text-ink disabled:opacity-30"
                    >▼</button>
                  </div>

                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-medium text-ink">{widget.name}</span>
                    <span className="block truncate text-xs text-muted">
                      {groupIcon(widget)} {groupName(widget)}
                    </span>
                  </span>

                  {isAdmin && (
                    <div className="flex gap-0.5 rounded-lg bg-raised p-0.5" role="group" aria-label={`${widget.name} width`}>
                      {SIZES.map(size => (
                        <button
                          key={size.key}
                          disabled={busy}
                          onClick={() => apply(() => api.setHouseholdWidget(widget.key, { size: size.key }))}
                          aria-pressed={widget.size === size.key}
                          className={`min-h-9 rounded-md px-2 text-xs font-semibold transition-colors ${
                            widget.size === size.key ? 'bg-primary-soft text-primary' : 'text-muted hover:text-ink'
                          }`}
                        >
                          {size.label}
                        </button>
                      ))}
                    </div>
                  )}

                  <Button
                    variant="ghost"
                    size="sm"
                    disabled={busy}
                    onClick={() => removeWidget(widget)}
                    aria-label={`Remove ${widget.name} from your Home page`}
                  >
                    Remove
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="border-t border-line pt-4">
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-sm font-bold text-ink">Add a card</h3>
            <Input
              value={query}
              onChange={event => setQuery(event.target.value)}
              placeholder="Search cards…"
              aria-label="Search available cards"
              className="w-full sm:w-56"
            />
          </div>

          {available.length === 0 ? (
            <p className="text-sm text-muted">
              {query.trim() ? 'No cards match that search.' : 'Every available card is already on your page.'}
            </p>
          ) : (
            <div className="flex flex-col gap-4">
              {available.map(([name, rows]) => (
                <div key={name}>
                  <p className="mb-1.5 text-xs font-bold uppercase tracking-wide text-muted">{name}</p>
                  <ul className="grid gap-1.5 sm:grid-cols-2">
                    {rows.map(widget => (
                      <li
                        key={widget.key}
                        className="flex min-h-14 items-center gap-2 rounded-xl border border-line px-2.5 py-1.5"
                      >
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-sm font-medium text-ink">{widget.name}</span>
                          {widget.description && (
                            <span className="block truncate text-xs text-muted">{widget.description}</span>
                          )}
                        </span>
                        {widget.household_enabled || isAdmin ? (
                          <Button size="sm" disabled={busy} onClick={() => addWidget(widget)}>Add</Button>
                        ) : (
                          <span className="flex-shrink-0 text-xs text-muted">Admin only</span>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          )}
        </section>

        {isAdmin && (
          <section className="border-t border-line pt-4">
            <h3 className="mb-2 text-sm font-bold text-ink">Countdown</h3>
            <div className="grid gap-2 rounded-xl bg-sunken p-3 sm:grid-cols-[1fr_180px_auto] sm:items-end">
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
                  settings: { title: countdownTitle.trim(), target_date: countdownDate },
                }))}
              >
                Save &amp; show
              </Button>
            </div>
          </section>
        )}
      </div>
    </Card>
  )
}
