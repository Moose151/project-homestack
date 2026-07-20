import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../../api/client'
import type { AtlasList, AtlasListItem, AtlasNote, AtlasReminder, AtlasSearchResults, Person } from '../../../api/types'
import { Card } from '../../../components/Card'
import { Button } from '../../../components/Button'
import { Input, Textarea, Select } from '../../../components/Field'
import { Tabs } from '../../../components/Tabs'
import { PageHeader } from '../../../components/PageHeader'
import { EmptyState } from '../../../components/EmptyState'
import { DateTimeField } from '../../../components/DateTimeField'
import { AssigneeSelect, personIdForUser } from '../../../components/AssigneeSelect'
import { useAuth } from '../../auth/AuthContext'

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

function calendarDayHref(iso: string | null) {
  if (!iso) return '/calendar'
  return `/calendar?date=${new Date(iso).toISOString().slice(0, 10)}`
}

// ---------------------------------------------------------------------------
// List item row
// ---------------------------------------------------------------------------

function ItemRow({
  item, listId, people, onToggle, onDelete, onError,
}: {
  item: AtlasListItem
  listId: number
  people: Person[]
  onToggle: (item: AtlasListItem) => void
  onDelete: (item: AtlasListItem) => void
  onError: (m: string) => void
}) {
  const [busy, setBusy] = useState(false)
  const due = dueLabel(item.due_at)
  const assignee = item.assigned_to_person_id
    ? people.find(p => p.id === item.assigned_to_person_id)
    : null

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
      {assignee && !item.is_complete && (
        <span className="flex items-center gap-1 text-xs text-muted-strong flex-shrink-0" title={`Assigned to ${assignee.display_name}`}>
          <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: assignee.colour || 'var(--hs-muted)' }} />
          <span className="hidden sm:inline">{assignee.preferred_name || assignee.display_name}</span>
        </span>
      )}
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

function ListCard({ list, people, defaultAssignee, onDeleted, onError }: {
  list: AtlasList
  people: Person[]
  defaultAssignee: number | null
  onDeleted: (id: number) => void
  onError: (m: string) => void
}) {
  const [items, setItems] = useState<AtlasListItem[]>(list.items ?? [])
  const [newTitle, setNewTitle] = useState('')
  const [qty, setQty] = useState('')
  const [assignee, setAssignee] = useState<number | null>(defaultAssignee)
  const [adding, setAdding] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const hasQty = list.list_type === 'grocery' || list.list_type === 'shopping'

  const addItem = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newTitle.trim()) return
    setAdding(true)
    try {
      const item = await api.createItem(list.id, {
        title: newTitle.trim(), quantity: qty.trim() || undefined,
        assigned_to_person_id: assignee,
      })
      setItems(prev => [...prev, item])
      setNewTitle(''); setQty(''); setAssignee(defaultAssignee)
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
          <span className="text-xs text-muted capitalize">{list.list_type} · {pending.length} to do</span>
        </div>
        <button onClick={deleteList} className="text-muted hover:text-danger transition-colors text-xl leading-none" aria-label="Delete list">×</button>
      </div>

      {items.length > 0 && (
        <ul className="divide-y divide-line/60">
          {pending.map(item => (
            <ItemRow key={item.id} item={item} listId={list.id} people={people} onToggle={handleToggle} onDelete={handleDelete} onError={onError} />
          ))}
          {done.map(item => (
            <ItemRow key={item.id} item={item} listId={list.id} people={people} onToggle={handleToggle} onDelete={handleDelete} onError={onError} />
          ))}
        </ul>
      )}

      {/* Add row: stacks on mobile (input, then who + add), inline from sm up. */}
      <form onSubmit={addItem} className="mt-3 pt-3 border-t border-line flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
        <div className="flex items-center gap-2 min-w-0 flex-1">
          {hasQty && (
            <input
              value={qty}
              onChange={e => setQty(e.target.value)}
              placeholder="Qty"
              className="w-14 text-sm bg-transparent text-ink placeholder-muted outline-none min-h-[40px] border-b border-line focus:border-primary"
            />
          )}
          <input
            ref={inputRef}
            value={newTitle}
            onChange={e => setNewTitle(e.target.value)}
            placeholder="Add item…"
            className="flex-1 min-w-0 text-sm bg-transparent text-ink placeholder-muted outline-none min-h-[40px]"
          />
        </div>
        <div className="flex items-center gap-2">
          <AssigneeSelect
            people={people}
            value={assignee}
            onChange={setAssignee}
            className="flex-1 sm:flex-none text-sm rounded-lg border border-line bg-surface px-2 py-1.5 text-muted-strong min-h-[40px] max-w-[10rem]"
          />
          <Button type="submit" size="sm" loading={adding} disabled={!newTitle.trim()}>Add</Button>
        </div>
      </form>
    </Card>
  )
}

// ---------------------------------------------------------------------------
// Notes tab
// ---------------------------------------------------------------------------

function NoteCard({ note, onSaved, onDeleted, onError }: {
  note: AtlasNote
  onSaved: (n: AtlasNote) => void
  onDeleted: (id: number) => void
  onError: (m: string) => void
}) {
  const [editing, setEditing] = useState(false)
  const [title, setTitle] = useState(note.title)
  const [body, setBody] = useState(note.body)
  const [visibility, setVisibility] = useState(note.visibility)
  const [saving, setSaving] = useState(false)

  const save = async () => {
    if (!title.trim()) return
    setSaving(true)
    try {
      const updated = await api.updateNote(note.id, { title: title.trim(), body, visibility })
      onSaved(updated)
      setEditing(false)
    } catch (e) { onError(errMsg(e)) } finally { setSaving(false) }
  }

  const remove = async () => {
    if (!confirm(`Delete "${note.title}"?`)) return
    try { await api.deleteNote(note.id); onDeleted(note.id) } catch (e) { onError(errMsg(e)) }
  }

  if (editing) {
    return (
      <Card>
        <div className="flex flex-col gap-2">
          <Input value={title} onChange={e => setTitle(e.target.value)} placeholder="Title" autoFocus />
          <Textarea value={body} onChange={e => setBody(e.target.value)} placeholder="Write something…" rows={5} />
          <div className="flex items-center gap-2">
            <Select value={visibility} onChange={e => setVisibility(e.target.value)} className="max-w-[10rem]">
              <option value="household">Household</option>
              <option value="private">Private</option>
            </Select>
            <div className="ml-auto flex gap-2">
              <Button variant="ghost" size="sm" onClick={() => { setEditing(false); setTitle(note.title); setBody(note.body); setVisibility(note.visibility) }}>Cancel</Button>
              <Button size="sm" onClick={save} loading={saving} disabled={!title.trim()}>Save</Button>
            </div>
          </div>
        </div>
      </Card>
    )
  }

  return (
    <Card className="group">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3 className="font-bold text-ink">{note.title}</h3>
            {note.visibility === 'private' && <span className="text-xs text-muted">🔒 Private</span>}
          </div>
          {note.body && <p className="mt-1 whitespace-pre-wrap text-sm text-muted-strong">{note.body}</p>}
        </div>
        <div className="flex flex-shrink-0 items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
          <button onClick={() => setEditing(true)} className="rounded-lg px-2 py-1 text-xs text-muted hover:bg-sunken hover:text-ink">Edit</button>
          <button onClick={remove} className="rounded-lg px-2 py-1 text-xs text-muted hover:text-danger" aria-label="Delete">Delete</button>
        </div>
      </div>
    </Card>
  )
}

function NotesTab({ onError }: { onError: (m: string) => void }) {
  const [notes, setNotes] = useState<AtlasNote[]>([])
  const [loading, setLoading] = useState(true)
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const [visibility, setVisibility] = useState('household')
  const [open, setOpen] = useState(false)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    api.getNotes().then(setNotes).catch(e => onError(errMsg(e))).finally(() => setLoading(false))
  }, [onError])

  const create = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim()) return
    setSaving(true)
    try {
      const n = await api.createNote({ title: title.trim(), body, visibility })
      setNotes(prev => [n, ...prev])
      setTitle(''); setBody(''); setVisibility('household'); setOpen(false)
    } catch (e) { onError(errMsg(e)) } finally { setSaving(false) }
  }

  if (loading) return <div className="h-32 rounded-2xl bg-sunken animate-pulse" />

  return (
    <div className="flex flex-col gap-4">
      {open ? (
        <Card title="New note">
          <form onSubmit={create} className="flex flex-col gap-2">
            <Input value={title} onChange={e => setTitle(e.target.value)} placeholder="Title" autoFocus />
            <Textarea value={body} onChange={e => setBody(e.target.value)} placeholder="Write something…" rows={5} />
            <div className="flex items-center gap-2">
              <Select value={visibility} onChange={e => setVisibility(e.target.value)} className="max-w-[10rem]">
                <option value="household">Household</option>
                <option value="private">Private</option>
              </Select>
              <div className="ml-auto flex gap-2">
                <Button variant="ghost" size="sm" onClick={() => setOpen(false)}>Cancel</Button>
                <Button size="sm" type="submit" loading={saving} disabled={!title.trim()}>Save note</Button>
              </div>
            </div>
          </form>
        </Card>
      ) : (
        <Button size="sm" onClick={() => setOpen(true)} className="self-start">+ New note</Button>
      )}

      {notes.length === 0 ? (
        <EmptyState icon="📝" title="No notes yet" hint="Jot down anything you want to remember — recipes, ideas, passwords hints." />
      ) : (
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
          {notes.map(n => (
            <NoteCard key={n.id} note={n}
              onSaved={u => setNotes(prev => prev.map(x => x.id === u.id ? u : x))}
              onDeleted={id => setNotes(prev => prev.filter(x => x.id !== id))}
              onError={onError} />
          ))}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Reminders tab
// ---------------------------------------------------------------------------

function RemindersTab({ onError }: { onError: (m: string) => void }) {
  const [reminders, setReminders] = useState<AtlasReminder[]>([])
  const [loading, setLoading] = useState(true)
  const [title, setTitle] = useState('')
  const [dueAt, setDueAt] = useState<string | null>(null)
  const [dueAllDay, setDueAllDay] = useState(true)
  const [open, setOpen] = useState(false)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    api.getReminders().then(setReminders).catch(e => onError(errMsg(e))).finally(() => setLoading(false))
  }, [onError])

  const create = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim()) return
    setSaving(true)
    try {
      const r = await api.createReminder({ title: title.trim(), due_at: dueAt, is_all_day: dueAllDay })
      setReminders(prev => [...prev, r])
      setTitle(''); setDueAt(null); setDueAllDay(true); setOpen(false)
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
      {open ? (
        <Card title="New reminder">
          <form onSubmit={create} className="flex flex-col gap-3">
            <Input
              value={title}
              onChange={e => setTitle(e.target.value)}
              placeholder="Reminder title"
              autoFocus
            />
            <DateTimeField value={dueAt} allDay={dueAllDay}
              onChange={({ value, allDay }) => { setDueAt(value); setDueAllDay(allDay) }} />
            <div className="flex justify-end gap-2">
              <Button variant="ghost" size="sm" onClick={() => setOpen(false)}>Cancel</Button>
              <Button type="submit" size="sm" loading={saving} disabled={!title.trim()}>Save</Button>
            </div>
          </form>
        </Card>
      ) : (
        <Button size="sm" onClick={() => setOpen(true)} className="self-start">+ New reminder</Button>
      )}

      {reminders.length === 0 ? (
        <EmptyState icon="⏰" title="No reminders yet" hint="Dated reminders also show on your Hub and Calendar." />
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
                      {new Date(r.due_at).toLocaleString(undefined,
                        r.is_all_day ? { dateStyle: 'medium' } : { dateStyle: 'medium', timeStyle: 'short' })}
                      <Link to={calendarDayHref(r.due_at)} className="ml-2 hover:underline">Open day</Link>
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
// Quick capture — one bar that drops text into a list, note or reminder.
// ---------------------------------------------------------------------------

type CaptureKind = 'todo' | 'note' | 'reminder'

function CaptureBar({ lists, onCapture }: {
  lists: AtlasList[]
  onCapture: (kind: CaptureKind, text: string, listId: number | null) => Promise<void>
}) {
  const [kind, setKind] = useState<CaptureKind>('todo')
  const [text, setText] = useState('')
  const [listId, setListId] = useState<number | null>(lists[0]?.id ?? null)
  const [busy, setBusy] = useState(false)

  // Keep a valid target list selected as lists load / change.
  useEffect(() => {
    if (kind !== 'todo') return
    if (listId == null || !lists.some(l => l.id === listId)) setListId(lists[0]?.id ?? null)
  }, [lists, kind, listId])

  const noTarget = kind === 'todo' && listId == null
  const canSubmit = !!text.trim() && !noTarget

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!canSubmit) return
    setBusy(true)
    try { await onCapture(kind, text.trim(), listId); setText('') } finally { setBusy(false) }
  }

  const seg = (k: CaptureKind, label: string) => (
    <button
      type="button"
      onClick={() => setKind(k)}
      className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
        kind === k ? 'bg-raised text-ink shadow-soft' : 'text-muted hover:text-ink'
      }`}
    >
      {label}
    </button>
  )

  return (
    <Card>
      <form onSubmit={submit} className="flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <span className="pl-1 text-muted-strong" aria-hidden>✎</span>
          <input
            value={text}
            onChange={e => setText(e.target.value)}
            placeholder="Capture a quick to-do, note or reminder…"
            className="min-h-[40px] flex-1 bg-transparent text-sm text-ink outline-none placeholder:text-muted"
          />
          <Button type="submit" size="sm" loading={busy} disabled={!canSubmit}>Add</Button>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex gap-1 bg-sunken p-1 rounded-xl">
            {seg('todo', 'To-do')}
            {seg('note', 'Note')}
            {seg('reminder', 'Reminder')}
          </div>
          {kind === 'todo' && (
            lists.length > 0 ? (
              <Select value={listId ?? 0} onChange={e => setListId(Number(e.target.value))} className="!w-auto min-w-[9rem] !min-h-[38px] !py-1.5">
                {lists.map(l => <option key={l.id} value={l.id}>{l.title}</option>)}
              </Select>
            ) : (
              <span className="text-xs text-muted">Create a list first to capture to-dos.</span>
            )
          )}
        </div>
      </form>
    </Card>
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

type Tab = 'lists' | 'notes' | 'reminders'

const LIST_TYPES = [
  { key: 'todo', label: 'To-do' },
  { key: 'grocery', label: 'Grocery' },
  { key: 'shopping', label: 'Shopping' },
  { key: 'checklist', label: 'Checklist' },
  { key: 'general', label: 'General' },
]

export function AtlasPage() {
  const { user } = useAuth()
  const [tab, setTab] = useState<Tab>('lists')
  const [lists, setLists] = useState<AtlasList[]>([])
  const [people, setPeople] = useState<Person[]>([])
  const [loading, setLoading] = useState(true)
  const [newTitle, setNewTitle] = useState('')
  const [newType, setNewType] = useState('todo')
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<AtlasSearchResults | null>(null)
  // Remount only the affected list card / self-fetching tab after a quick capture.
  const [cardRefresh, setCardRefresh] = useState<Record<number, number>>({})
  const [captureTick, setCaptureTick] = useState(0)

  useEffect(() => {
    api.getLists().then(setLists).catch(e => setError(errMsg(e))).finally(() => setLoading(false))
  }, [])
  useEffect(() => { api.getPeople().then(setPeople).catch(() => {}) }, [])

  const defaultAssignee = personIdForUser(people, user?.id)

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
      const list = await api.createList({ title: newTitle.trim(), list_type: newType })
      const full = await api.getList(list.id)
      setLists(prev => [full, ...prev])
      setNewTitle(''); setNewType('todo')
    } catch (e) {
      setError(errMsg(e))
    } finally {
      setCreating(false)
    }
  }

  const capture = async (kind: CaptureKind, text: string, listId: number | null) => {
    try {
      if (kind === 'note') {
        await api.createNote({ title: text, visibility: 'household' })
        setCaptureTick(t => t + 1)
        setTab('notes')
      } else if (kind === 'reminder') {
        await api.createReminder({ title: text, due_at: null, is_all_day: true })
        setCaptureTick(t => t + 1)
        setTab('reminders')
      } else if (kind === 'todo' && listId != null) {
        await api.createItem(listId, { title: text, assigned_to_person_id: defaultAssignee })
        const full = await api.getList(listId)
        setLists(prev => prev.map(l => l.id === listId ? full : l))
        setCardRefresh(prev => ({ ...prev, [listId]: (prev[listId] ?? 0) + 1 }))
        setTab('lists')
      }
    } catch (e) {
      setError(errMsg(e))
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <PageHeader title="Atlas" icon="🗒" subtitle="Notes, lists, checklists and reminders." />

      <CaptureBar lists={lists} onCapture={capture} />

      <Input
        value={query}
        onChange={e => setQuery(e.target.value)}
        placeholder="Search lists, items, notes, reminders…"
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
          <Tabs
            tabs={[
              { key: 'lists', label: 'lists', badge: lists.length || undefined },
              { key: 'notes', label: 'notes' },
              { key: 'reminders', label: 'reminders' },
            ]}
            active={tab}
            onChange={setTab}
            className="w-fit"
          />

          {tab === 'lists' ? (
            <div className="flex flex-col gap-4">
              <form onSubmit={createList} className="flex flex-wrap gap-2">
                <Input
                  value={newTitle}
                  onChange={e => setNewTitle(e.target.value)}
                  placeholder="New list name…"
                  className="flex-1 min-w-[10rem]"
                />
                <Select value={newType} onChange={e => setNewType(e.target.value)} className="w-32">
                  {LIST_TYPES.map(t => <option key={t.key} value={t.key}>{t.label}</option>)}
                </Select>
                <Button type="submit" loading={creating} disabled={!newTitle.trim()}>Create</Button>
              </form>

              {loading ? (
                <div className="h-32 rounded-2xl bg-sunken animate-pulse" />
              ) : lists.length === 0 ? (
                <EmptyState icon="🗒" title="No lists yet" hint="Create your first list above to get started." />
              ) : (
                <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                  {lists.map(list => (
                    <ListCard
                      key={`${list.id}:${cardRefresh[list.id] ?? 0}`}
                      list={list}
                      people={people}
                      defaultAssignee={defaultAssignee}
                      onDeleted={id => setLists(prev => prev.filter(l => l.id !== id))}
                      onError={setError}
                    />
                  ))}
                </div>
              )}
            </div>
          ) : tab === 'notes' ? (
            <NotesTab key={`notes-${captureTick}`} onError={setError} />
          ) : (
            <RemindersTab key={`reminders-${captureTick}`} onError={setError} />
          )}
        </>
      )}
    </div>
  )
}
