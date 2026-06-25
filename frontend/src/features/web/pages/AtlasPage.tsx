import { useEffect, useRef, useState } from 'react'
import { api } from '../../../api/client'
import type { AtlasList, AtlasListItem, AtlasReminder, AtlasSearchResults } from '../../../api/types'
import { Card } from '../../../components/Card'
import { Button } from '../../../components/Button'

const errMsg = (e: unknown) => (e instanceof Error ? e.message : 'Something went wrong.')

function dueLabel(iso: string | null) {
  if (!iso) return null
  const d = new Date(iso)
  const diff = Math.round((d.getTime() - Date.now()) / 86400000)
  if (diff < 0) return { text: `${Math.abs(diff)}d overdue`, tone: 'bg-danger-soft text-danger' }
  if (diff === 0) return { text: 'Today', tone: 'bg-primary-soft text-primary' }
  if (diff === 1) return { text: 'Tomorrow', tone: 'bg-sunken text-muted-strong' }
  return { text: d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }), tone: 'bg-sunken text-muted-strong' }
}

// ---------------------------------------------------------------------------
// List item row
// ---------------------------------------------------------------------------

function ItemRow({
  item, listId, onToggle, onDelete, onError,
}: {
  item: AtlasListItem
  listId: number
  onToggle: (item: AtlasListItem) => void
  onDelete: (item: AtlasListItem) => void
  onError: (m: string) => void
}) {
  const [busy, setBusy] = useState(false)
  const due = dueLabel(item.due_at)

  const toggle = async () => {
    setBusy(true)
    try {
      const updated = item.is_complete
        ? await api.uncompleteItem(listId, item.id)
        : await api.completeItem(listId, item.id)
      onToggle(updated)
    } catch (e) {
      onError(errMsg(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <li className="flex items-center gap-3 py-2 group">
      <button
        onClick={toggle}
        disabled={busy}
        className={`w-6 h-6 rounded-full border-2 flex items-center justify-center flex-shrink-0 transition-all ${
          item.is_complete ? 'bg-success border-success text-white' : 'border-line-strong hover:border-success'
        }`}
        aria-label={item.is_complete ? 'Uncheck' : 'Check'}
      >
        {item.is_complete && <span className="text-xs">✓</span>}
      </button>
      <span className={`flex-1 text-sm ${item.is_complete ? 'line-through text-muted' : 'text-ink'}`}>
        {item.quantity && <span className="text-muted-strong font-medium mr-1.5">{item.quantity}×</span>}
        {item.title}
      </span>
      {due && !item.is_complete && (
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium flex-shrink-0 ${due.tone}`}>{due.text}</span>
      )}
      <button
        onClick={() => onDelete(item)}
        className="opacity-0 group-hover:opacity-100 text-muted hover:text-danger transition-all text-lg leading-none"
        aria-label="Delete"
      >
        ×
      </button>
    </li>
  )
}

// ---------------------------------------------------------------------------
// Single list card
// ---------------------------------------------------------------------------

function ListCard({ list, onDeleted, onError }: { list: AtlasList; onDeleted: (id: number) => void; onError: (m: string) => void }) {
  const [items, setItems] = useState<AtlasListItem[]>(list.items ?? [])
  const [newTitle, setNewTitle] = useState('')
  const [qty, setQty] = useState('')
  const [adding, setAdding] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const hasQty = list.list_type === 'grocery' || list.list_type === 'shopping'

  const addItem = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newTitle.trim()) return
    setAdding(true)
    try {
      const item = await api.createItem(list.id, { title: newTitle.trim(), quantity: qty.trim() || undefined })
      setItems(prev => [...prev, item])
      setNewTitle(''); setQty('')
      inputRef.current?.focus()
    } catch (e) {
      onError(errMsg(e))
    } finally {
      setAdding(false)
    }
  }

  const handleToggle = (updated: AtlasListItem) => setItems(prev => prev.map(i => i.id === updated.id ? updated : i))

  const handleDelete = async (item: AtlasListItem) => {
    try {
      await api.deleteItem(list.id, item.id)
      setItems(prev => prev.filter(i => i.id !== item.id))
    } catch (e) {
      onError(errMsg(e))
    }
  }

  const deleteList = async () => {
    if (!confirm(`Delete "${list.title}"?`)) return
    try {
      await api.deleteList(list.id)
      onDeleted(list.id)
    } catch (e) {
      onError(errMsg(e))
    }
  }

  const pending = items.filter(i => !i.is_complete)
  const done = items.filter(i => i.is_complete)

  return (
    <Card>
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="font-bold text-ink">{list.title}</h3>
          <span className="text-xs text-muted capitalize">{list.list_type}</span>
        </div>
        <button onClick={deleteList} className="text-muted hover:text-danger transition-colors text-xl leading-none" aria-label="Delete list">×</button>
      </div>

      <ul className="divide-y divide-line/60">
        {pending.map(item => (
          <ItemRow key={item.id} item={item} listId={list.id} onToggle={handleToggle} onDelete={handleDelete} onError={onError} />
        ))}
        {done.map(item => (
          <ItemRow key={item.id} item={item} listId={list.id} onToggle={handleToggle} onDelete={handleDelete} onError={onError} />
        ))}
      </ul>

      <form onSubmit={addItem} className="flex gap-2 mt-3 pt-3 border-t border-line">
        {hasQty && (
          <input
            value={qty}
            onChange={e => setQty(e.target.value)}
            placeholder="Qty"
            className="w-16 text-sm bg-transparent text-ink placeholder-muted outline-none min-h-[36px] border-b border-line focus:border-primary"
          />
        )}
        <input
          ref={inputRef}
          value={newTitle}
          onChange={e => setNewTitle(e.target.value)}
          placeholder="Add item…"
          className="flex-1 text-sm bg-transparent text-ink placeholder-muted outline-none min-h-[36px]"
        />
        <Button type="submit" size="sm" loading={adding} disabled={!newTitle.trim()}>Add</Button>
      </form>
    </Card>
  )
}

// ---------------------------------------------------------------------------
// Reminders tab
// ---------------------------------------------------------------------------

function RemindersTab({ onError }: { onError: (m: string) => void }) {
  const [reminders, setReminders] = useState<AtlasReminder[]>([])
  const [loading, setLoading] = useState(true)
  const [title, setTitle] = useState('')
  const [dueAt, setDueAt] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    api.getReminders().then(setReminders).catch(e => onError(errMsg(e))).finally(() => setLoading(false))
  }, [onError])

  const create = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim()) return
    setSaving(true)
    try {
      const r = await api.createReminder({ title: title.trim(), due_at: dueAt || undefined })
      setReminders(prev => [...prev, r])
      setTitle(''); setDueAt('')
    } catch (e) {
      onError(errMsg(e))
    } finally {
      setSaving(false)
    }
  }

  const remove = async (id: number) => {
    try {
      await api.deleteReminder(id)
      setReminders(prev => prev.filter(r => r.id !== id))
    } catch (e) {
      onError(errMsg(e))
    }
  }

  if (loading) return <div className="h-32 rounded-2xl bg-sunken animate-pulse" />

  return (
    <div className="flex flex-col gap-4">
      <Card title="New reminder">
        <form onSubmit={create} className="flex flex-col gap-3">
          <input
            value={title}
            onChange={e => setTitle(e.target.value)}
            placeholder="Reminder title"
            className="w-full px-3 py-2.5 rounded-xl border border-line bg-raised text-sm text-ink placeholder-muted outline-none focus:ring-2 focus:ring-primary"
          />
          <div className="flex gap-2">
            <input
              type="datetime-local"
              value={dueAt}
              onChange={e => setDueAt(e.target.value)}
              className="flex-1 px-3 py-2 rounded-xl border border-line bg-raised text-sm text-muted-strong outline-none focus:ring-2 focus:ring-primary"
            />
            <Button type="submit" loading={saving} disabled={!title.trim()}>Save</Button>
          </div>
        </form>
      </Card>

      {reminders.length === 0 ? (
        <p className="text-sm text-muted text-center py-6">No reminders yet.</p>
      ) : (
        <div className="flex flex-col gap-3">
          {reminders.map(r => (
            <Card key={r.id}>
              <div className="flex items-start gap-3">
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-ink">{r.title}</p>
                  {r.body && <p className="text-sm text-muted mt-0.5">{r.body}</p>}
                  {r.due_at && (
                    <p className="text-xs text-primary mt-1">
                      {new Date(r.due_at).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })}
                    </p>
                  )}
                </div>
                <button onClick={() => remove(r.id)} className="text-muted hover:text-danger transition-colors text-xl leading-none flex-shrink-0" aria-label="Delete">×</button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Search results
// ---------------------------------------------------------------------------

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <p className="text-xs font-semibold text-muted uppercase tracking-wide">{title}</p>
      {children}
    </div>
  )
}

function SearchResults({ results }: { results: AtlasSearchResults }) {
  const empty = !results.notes.length && !results.lists.length && !results.items.length && !results.reminders.length
  if (empty) return <p className="text-sm text-muted text-center py-8">No matches.</p>

  return (
    <div className="flex flex-col gap-4">
      {results.lists.length > 0 && (
        <Section title="Lists">
          {results.lists.map(l => (
            <Card key={`l${l.id}`}>
              <span className="text-sm text-ink">{l.title}</span>
              <span className="text-xs text-muted capitalize"> · {l.list_type}</span>
            </Card>
          ))}
        </Section>
      )}
      {results.items.length > 0 && (
        <Section title="List items">
          {results.items.map(i => (
            <div key={`i${i.id}`} className="text-sm text-ink px-3 py-1.5 rounded-lg bg-sunken">
              {i.quantity && <span className="text-muted-strong mr-1.5">{i.quantity}×</span>}{i.title}
            </div>
          ))}
        </Section>
      )}
      {results.notes.length > 0 && (
        <Section title="Notes">
          {results.notes.map(n => (
            <Card key={`n${n.id}`}>
              <p className="text-sm font-medium text-ink">{n.title}</p>
              {n.body && <p className="text-xs text-muted truncate">{n.body}</p>}
            </Card>
          ))}
        </Section>
      )}
      {results.reminders.length > 0 && (
        <Section title="Reminders">
          {results.reminders.map(r => (
            <div key={`r${r.id}`} className="text-sm text-ink px-3 py-1.5 rounded-lg bg-sunken">{r.title}</div>
          ))}
        </Section>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Atlas page
// ---------------------------------------------------------------------------

type Tab = 'lists' | 'reminders'

export function AtlasPage() {
  const [tab, setTab] = useState<Tab>('lists')
  const [lists, setLists] = useState<AtlasList[]>([])
  const [loading, setLoading] = useState(true)
  const [newTitle, setNewTitle] = useState('')
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<AtlasSearchResults | null>(null)

  useEffect(() => {
    api.getLists().then(setLists).catch(e => setError(errMsg(e))).finally(() => setLoading(false))
  }, [])

  // Debounced Atlas-wide search.
  useEffect(() => {
    const q = query.trim()
    if (q.length < 2) { setResults(null); return }
    const id = setTimeout(() => {
      api.searchAtlas(q).then(setResults).catch(e => setError(errMsg(e)))
    }, 300)
    return () => clearTimeout(id)
  }, [query])

  const createList = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newTitle.trim()) return
    setCreating(true)
    try {
      const list = await api.createList({ title: newTitle.trim(), list_type: 'todo' })
      const full = await api.getList(list.id)
      setLists(prev => [full, ...prev])
      setNewTitle('')
    } catch (e) {
      setError(errMsg(e))
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <h1 className="text-2xl font-extrabold tracking-tight text-ink">Atlas</h1>

      <input
        value={query}
        onChange={e => setQuery(e.target.value)}
        placeholder="Search lists, items, notes, reminders…"
        className="w-full px-4 py-2.5 rounded-xl border border-line bg-surface text-sm text-ink placeholder-muted outline-none focus:ring-2 focus:ring-primary"
      />

      {error && (
        <div className="flex items-center justify-between gap-3 px-4 py-2.5 rounded-xl bg-danger-soft text-danger text-sm">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-danger/70 hover:text-danger" aria-label="Dismiss">×</button>
        </div>
      )}

      {results !== null ? (
        <SearchResults results={results} />
      ) : (
        <>
          {/* Tabs */}
          <div className="flex gap-1 bg-sunken p-1 rounded-xl w-fit">
            {(['lists', 'reminders'] as Tab[]).map(t => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`px-4 py-1.5 rounded-lg text-sm font-semibold transition-colors capitalize ${
                  tab === t ? 'bg-raised text-ink shadow-soft' : 'text-muted hover:text-ink'
                }`}
              >
                {t}
              </button>
            ))}
          </div>

          {tab === 'lists' ? (
            <div className="flex flex-col gap-4">
              <form onSubmit={createList} className="flex gap-2">
                <input
                  value={newTitle}
                  onChange={e => setNewTitle(e.target.value)}
                  placeholder="New list name…"
                  className="flex-1 px-4 py-2.5 rounded-xl border border-line bg-surface text-sm text-ink placeholder-muted outline-none focus:ring-2 focus:ring-primary"
                />
                <Button type="submit" loading={creating} disabled={!newTitle.trim()}>Create</Button>
              </form>

              {loading ? (
                <div className="h-32 rounded-2xl bg-sunken animate-pulse" />
              ) : lists.length === 0 ? (
                <p className="text-sm text-muted text-center py-8">No lists yet. Create one above.</p>
              ) : (
                lists.map(list => (
                  <ListCard
                    key={list.id}
                    list={list}
                    onDeleted={id => setLists(prev => prev.filter(l => l.id !== id))}
                    onError={setError}
                  />
                ))
              )}
            </div>
          ) : (
            <RemindersTab onError={setError} />
          )}
        </>
      )}
    </div>
  )
}
