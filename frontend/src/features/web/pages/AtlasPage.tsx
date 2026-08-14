import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../../../api/client'
import type { AtlasContact, AtlasList, AtlasListItem, AtlasNote, AtlasReminder, AtlasSearchResults, CalendarEvent, Person } from '../../../api/types'
import { Card } from '../../../components/Card'
import { Button } from '../../../components/Button'
import { Modal } from '../../../components/Modal'
import { Field, Input, SearchField, Textarea, Select } from '../../../components/Field'
import { Tabs } from '../../../components/Tabs'
import { PageHeader } from '../../../components/PageHeader'
import { EmptyState } from '../../../components/EmptyState'
import { DateTimeField } from '../../../components/DateTimeField'
import { AssigneeSelect, personIdForUser } from '../../../components/AssigneeSelect'
import { DeleteAction } from '../../..//components/RowActions'
import { useAuth } from '../../auth/AuthContext'
import { useUrlQueryState, useUrlTab } from '../../../hooks/useUrlTab'
import { confirmDialog } from '../../../components/Dialogs'
import { sourcePath } from '../../../lib/sourceLinks'
import { EventModal } from './CalendarPage'
import { ShoppingTab } from './atlas/ShoppingTab'
import { MobileListRow, MobileSection } from '../../../components/mobile'

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

// One source of truth for list-type label + glyph (used by cards and the create form).
const LIST_TYPE_META: Record<string, { label: string; icon: string }> = {
  todo: { label: 'To-do', icon: '✓' },
  grocery: { label: 'Grocery', icon: '🛒' },
  shopping: { label: 'Shopping', icon: '🛍️' },
  checklist: { label: 'Checklist', icon: '☑️' },
  general: { label: 'General', icon: '📋' },
}
const listTypeMeta = (t: string) => LIST_TYPE_META[t] ?? { label: t, icon: '•' }

// ---------------------------------------------------------------------------
// List item row
// ---------------------------------------------------------------------------

function ItemRow({
  item, listId, people, focused, onToggle, onDelete, onError,
}: {
  item: AtlasListItem
  listId: number
  people: Person[]
  focused?: boolean
  onToggle: (item: AtlasListItem) => void
  onDelete: (item: AtlasListItem) => void
  onError: (m: string) => void
}) {
  const [busy, setBusy] = useState(false)
  const due = dueLabel(item.due_at)
  // Several people can share an item; show the first as a colour dot and name the rest.
  const assignees = item.assigned_to_person_ids
    .map(id => people.find(p => p.id === id))
    .filter((p): p is Person => Boolean(p))
  const assignee = assignees[0] ?? null

  const toggle = async () => {
    setBusy(true)
    const optimistic: AtlasListItem = {
      ...item,
      is_complete: !item.is_complete,
      completed_at: item.is_complete ? null : new Date().toISOString(),
    }
    onToggle(optimistic)
    try {
      const updated = item.is_complete
        ? await api.uncompleteItem(listId, item.id)
        : await api.completeItem(listId, item.id)
      onToggle(updated)
    } catch (e) {
      onToggle(item)
      onError(errMsg(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <li id={`atlas-item-${item.id}`} className={`group flex items-start gap-1 rounded-xl ${focused ? 'bg-primary-soft ring-2 ring-primary' : ''}`}>
      {/* Whole checkbox+title is one tap target (comfortable on mobile). */}
      <button
        onClick={toggle}
        disabled={busy}
        className="flex min-h-[52px] min-w-0 flex-1 items-start gap-3 py-2.5 text-left disabled:opacity-60"
        aria-label={item.is_complete ? 'Mark not done' : 'Mark done'}
      >
        <span
          className={`mt-0.5 grid h-6 w-6 flex-shrink-0 place-items-center rounded-full border-2 transition-all ${
            item.is_complete ? 'bg-success border-success text-white' : 'border-line-strong group-hover:border-success'
          }`}
        >
          {item.is_complete && <span className="text-xs">✓</span>}
        </span>
        <span className="min-w-0 flex-1">
          <span className={`block break-words text-sm leading-5 ${item.is_complete ? 'line-through text-muted' : 'text-ink'}`}>
            {item.quantity && <span className="mr-1.5 font-medium text-muted-strong">{item.quantity}×</span>}
            {item.title}
          </span>
          {!item.is_complete && (assignee || due) && (
            <span className="mt-1 flex flex-wrap items-center gap-1.5 text-[11px] text-muted">
              {assignee && (
                <span className="flex min-w-0 items-center gap-1">
                  <span className="h-2 w-2 flex-shrink-0 rounded-full" style={{ backgroundColor: assignee.colour || 'var(--hs-muted)' }} />
                  <span className="truncate">
                    {assignee.preferred_name || assignee.display_name}
                    {assignees.length > 1 && ` +${assignees.length - 1}`}
                  </span>
                </span>
              )}
              {due && <span className={`rounded-full px-1.5 py-0.5 font-semibold ${due.tone}`}>{due.text}</span>}
            </span>
          )}
        </span>
      </button>
      <button
        onClick={() => onDelete(item)}
        className="grid h-11 w-9 flex-shrink-0 place-items-center rounded-xl text-lg leading-none text-muted transition-all hover:bg-danger-soft hover:text-danger sm:opacity-0 sm:group-hover:opacity-100 sm:group-focus-within:opacity-100"
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

function ListCard({ list, people, defaultAssignee, focusedItemId, onDeleted, onError }: {
  list: AtlasList
  people: Person[]
  defaultAssignee: number[]
  focusedItemId?: number
  onDeleted: (id: number) => void
  onError: (m: string) => void
}) {
  const [items, setItems] = useState<AtlasListItem[]>(list.items ?? [])
  const [newTitle, setNewTitle] = useState('')
  const [qty, setQty] = useState('')
  const [assignee, setAssignee] = useState<number[]>(defaultAssignee)
  const [adding, setAdding] = useState(false)
  const [showDone, setShowDone] = useState(Boolean(focusedItemId && items.some(item => item.id === focusedItemId && item.is_complete)))
  const inputRef = useRef<HTMLInputElement>(null)
  const hasQty = list.list_type === 'grocery' || list.list_type === 'shopping'
  const meta = listTypeMeta(list.list_type)

  const addItem = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newTitle.trim()) return
    setAdding(true)
    try {
      const item = await api.createItem(list.id, {
        title: newTitle.trim(), quantity: qty.trim() || undefined,
        assigned_to_person_ids: assignee,
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
    if (!(await confirmDialog({ title: `Delete "${list.title}"?`, confirmLabel: 'Delete' }))) return
    try {
      await api.deleteList(list.id)
      onDeleted(list.id)
    } catch (e) {
      onError(errMsg(e))
    }
  }

  const pending = items.filter(i => !i.is_complete)
  const done = items.filter(i => i.is_complete)
  const total = items.length
  const pct = total ? Math.round((done.length / total) * 100) : 0

  return (
    <div id={`atlas-list-${list.id}`}><Card>
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-lg leading-none flex-shrink-0" aria-hidden>{meta.icon}</span>
          <div className="min-w-0">
            <h3 className="font-bold text-ink truncate">{list.title}</h3>
            <span className="text-xs text-muted">
              {meta.label}
              {pending.length > 0
                ? ` · ${pending.length} to do`
                : total > 0 ? ' · all done ✓' : ''}
            </span>
          </div>
        </div>
        <DeleteAction onClick={deleteList} label={list.title} />
      </div>

      {done.length > 0 && (
        <div className="h-1 rounded-full bg-sunken mb-3 overflow-hidden" title={`${done.length} of ${total} done`}>
          <div className="h-full bg-success rounded-full transition-all" style={{ width: `${pct}%` }} />
        </div>
      )}

      {pending.length > 0 && (
        <ul className="divide-y divide-line/60">
          {pending.map(item => (
            <ItemRow key={item.id} item={item} listId={list.id} people={people} focused={focusedItemId === item.id} onToggle={handleToggle} onDelete={handleDelete} onError={onError} />
          ))}
        </ul>
      )}

      {done.length > 0 && (
        <div className="mt-1">
          <button
            onClick={() => setShowDone(v => !v)}
            className="flex items-center gap-1 py-1.5 text-xs font-semibold text-muted hover:text-ink transition-colors"
          >
            <span className="w-3 inline-block">{showDone ? '▾' : '▸'}</span>
            {done.length} completed
          </button>
          {showDone && (
            <ul className="divide-y divide-line/60">
              {done.map(item => (
                <ItemRow key={item.id} item={item} listId={list.id} people={people} focused={focusedItemId === item.id} onToggle={handleToggle} onDelete={handleDelete} onError={onError} />
              ))}
            </ul>
          )}
        </div>
      )}

      {total === 0 && (
        <p className="text-sm text-muted py-1">Nothing here yet — add the first item below.</p>
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
    </Card></div>
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
    if (!(await confirmDialog({ title: `Delete "${note.title}"?`, confirmLabel: 'Delete' }))) return
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
        <div className="flex flex-shrink-0 items-center gap-1 opacity-100 transition-opacity sm:opacity-0 sm:group-hover:opacity-100 sm:group-focus-within:opacity-100">
          <button onClick={() => setEditing(true)} className="rounded-lg px-2 py-1 text-xs text-muted hover:bg-sunken hover:text-ink">Edit</button>
          <DeleteAction onClick={remove} label={note.title} />
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
        <EmptyState icon="📝" title="No notes yet" hint="Jot down anything you want to remember — recipes, ideas or household information." />
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

  // Soonest due first; undated reminders sink to the bottom.
  const sortedReminders = [...reminders].sort((a, b) => {
    if (!a.due_at && !b.due_at) return 0
    if (!a.due_at) return 1
    if (!b.due_at) return -1
    return new Date(a.due_at).getTime() - new Date(b.due_at).getTime()
  })

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
          {sortedReminders.map(r => {
            const due = dueLabel(r.due_at)
            return (
              <Card key={r.id}>
                <div className="flex items-start gap-3">
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-ink">{r.title}</p>
                    {r.body && <p className="text-sm text-muted mt-0.5">{r.body}</p>}
                    {r.due_at && (
                      <p className="text-xs text-muted mt-1">
                        {new Date(r.due_at).toLocaleString(undefined,
                          r.is_all_day ? { dateStyle: 'medium' } : { dateStyle: 'medium', timeStyle: 'short' })}
                        <Link to={calendarDayHref(r.due_at)} className="ml-2 text-primary hover:underline">Open day</Link>
                      </p>
                    )}
                  </div>
                  {due && (
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium flex-shrink-0 ${due.tone}`}>{due.text}</span>
                  )}
                  <DeleteAction onClick={() => remove(r.id)} label={r.title} />
                </div>
              </Card>
            )
          })}
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
  const [open, setOpen] = useState(false)

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
    <Card contentClassName="p-2.5 sm:p-4 sm:pt-3">
      {!open && (
        <button type="button" onClick={() => setOpen(true)} className="flex min-h-11 w-full items-center gap-3 rounded-xl px-2 text-left text-sm font-semibold text-muted-strong sm:hidden">
          <span className="grid h-8 w-8 place-items-center rounded-xl bg-primary-soft text-primary">＋</span>
          Quickly capture a to-do, note or reminder
        </button>
      )}
      <form onSubmit={submit} className={`${open ? 'flex' : 'hidden'} flex-col gap-2 sm:flex`}>
        <div className="flex items-center justify-between sm:hidden">
          <span className="text-xs font-bold uppercase tracking-wide text-muted">Quick capture</span>
          <button type="button" onClick={() => setOpen(false)} className="grid h-9 w-9 place-items-center rounded-xl text-muted" aria-label="Close quick capture">✕</button>
        </div>
        <div className="flex items-center gap-2">
          <span className="pl-1 text-muted-strong" aria-hidden>✎</span>
          <input
            value={text}
            onChange={e => setText(e.target.value)}
            placeholder="What do you need to remember?"
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

// Grocery and Shopping are their own tabs now; everything else still lives under Lists.
function listTabFor(listType: string): 'lists' | 'grocery' | 'shopping' {
  if (listType === 'grocery') return 'grocery'
  if (listType === 'shopping') return 'shopping'
  return 'lists'
}

function SearchResults({ results, lists }: { results: AtlasSearchResults; lists: AtlasList[] }) {
  const empty = !results.notes.length && !results.lists.length && !results.items.length && !results.reminders.length
  if (empty) return <EmptyState icon="🔍" title="No matches" hint="Try a different word, or check another list." />

  return (
    <div className="flex flex-col gap-4">
      {results.lists.length > 0 && (
        <Section title="Lists">
          {results.lists.map(l => (
            <Link key={`l${l.id}`} to={`/atlas?tab=${listTabFor(l.list_type)}&list=${l.id}`} className="group block">
              <Card className="transition-colors group-hover:border-primary/40">
                <span className="text-sm font-medium text-ink">{l.title}</span>
                <span className="text-xs text-muted capitalize"> · {l.list_type}</span>
              </Card>
            </Link>
          ))}
        </Section>
      )}
      {results.items.length > 0 && (
        <Section title="List items">
          {results.items.map(i => {
            const parentType = lists.find(l => l.id === i.atlas_list_id)?.list_type ?? 'general'
            return (
              <Link key={`i${i.id}`} to={`/atlas?tab=${listTabFor(parentType)}&list=${i.atlas_list_id}&item=${i.id}`} className="block min-h-11 rounded-xl bg-sunken px-3 py-2.5 text-sm text-ink transition-colors hover:bg-primary-soft">
                {i.quantity && <span className="text-muted-strong mr-1.5">{i.quantity}×</span>}{i.title}
              </Link>
            )
          })}
        </Section>
      )}
      {results.notes.length > 0 && (
        <Section title="Notes">
          {results.notes.map(n => (
            <Link key={`n${n.id}`} to="/atlas?tab=notes" className="group block">
              <Card className="transition-colors group-hover:border-primary/40">
                <p className="text-sm font-medium text-ink">{n.title}</p>
                {n.body && <p className="text-xs text-muted truncate">{n.body}</p>}
              </Card>
            </Link>
          ))}
        </Section>
      )}
      {results.reminders.length > 0 && (
        <Section title="Reminders">
          {results.reminders.map(r => (
            <Link key={`r${r.id}`} to="/atlas?tab=reminders" className="block min-h-11 rounded-xl bg-sunken px-3 py-2.5 text-sm text-ink transition-colors hover:bg-primary-soft">
              {r.title}
            </Link>
          ))}
        </Section>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Atlas page
// ---------------------------------------------------------------------------

function AtlasItemAgendaModal({ list, item, people, onClose, onSaved, onError }: {
  list: AtlasList; item: AtlasListItem; people: Person[]; onClose: () => void
  onSaved: () => void; onError: (message: string) => void
}) {
  const [title, setTitle] = useState(item.title)
  const [notes, setNotes] = useState(item.notes)
  const [dueAt, setDueAt] = useState<string | null>(item.due_at)
  const [allDay, setAllDay] = useState(false)
  const [assignees, setAssignees] = useState<number[]>(item.assigned_to_person_ids)
  const [saving, setSaving] = useState(false)
  const save = async () => {
    if (!title.trim()) return
    setSaving(true)
    try {
      await api.updateItem(list.id, item.id, {
        title: title.trim(), notes, due_at: dueAt, assigned_to_person_ids: assignees,
      })
      onSaved()
    } catch (error) { onError(errMsg(error)) } finally { setSaving(false) }
  }
  return <Modal title="Edit to-do" onClose={onClose} footer={<><Button variant="ghost" size="sm" onClick={onClose}>Cancel</Button><Button size="sm" onClick={save} loading={saving} disabled={!title.trim()}>Save</Button></>}>
    <div className="space-y-3">
      <Field label="To-do"><Input value={title} onChange={event => setTitle(event.target.value)} autoFocus /></Field>
      <Field label="Due"><DateTimeField value={dueAt} allDay={allDay} onChange={({ value, allDay: nextAllDay }) => { setDueAt(value); setAllDay(nextAllDay) }} /></Field>
      <Field label="Assigned to"><AssigneeSelect people={people} value={assignees} onChange={value => setAssignees(value || [])} /></Field>
      <Field label="Notes"><Textarea value={notes} onChange={event => setNotes(event.target.value)} rows={3} /></Field>
    </div>
  </Modal>
}

function AgendaTab({ people, lists, defaultAssignee, onError, onListsChanged }: {
  people: Person[]; lists: AtlasList[]; defaultAssignee: number[]
  onError: (message: string) => void; onListsChanged: () => void
}) {
  const [events, setEvents] = useState<CalendarEvent[]>([])
  const [editingEvent, setEditingEvent] = useState<CalendarEvent | null>(null)
  const [editingItem, setEditingItem] = useState<{ list: AtlasList; item: AtlasListItem } | null>(null)
  const load = () => api.getEvents({ upcoming: true, agenda: true }).then(setEvents).catch(e => onError(errMsg(e)))
  useEffect(() => { void load() }, [onError])
  const open = (event: CalendarEvent) => {
    if (!event.is_synced) { setEditingEvent(event); return }
    if (event.source_node === 'atlas' && event.source_record_type === 'AtlasListItem') {
      for (const list of lists) {
        const item = list.items.find(row => row.id === event.source_record_id)
        if (item) { setEditingItem({ list, item }); return }
      }
    }
    const href = sourcePath(event)
    if (href) window.location.assign(href)
  }
  if (!events.length) return <EmptyState icon="📅" title="Nothing upcoming" hint="Appointments and anything with a due date will appear here automatically." />
  return <><div className="grid gap-3 lg:grid-cols-2">{events.slice(0, 50).map(event => <Card key={event.id}>
    <button type="button" onClick={() => open(event)} className="block w-full text-left">
      <div className="flex items-start gap-3"><span className="text-xl">{event.event_kind === 'appointment' ? '🩺' : event.event_kind === 'task' ? '✓' : '📅'}</span>
        <div className="min-w-0 flex-1"><h3 className="font-bold text-ink">{event.title}</h3><p className="text-sm text-muted">{new Date(event.start_at).toLocaleString()} · {event.source_node || event.event_kind}</p><p className="mt-1 text-xs font-bold text-primary">{!event.is_synced || event.source_node === 'atlas' ? 'Edit here →' : 'Open source →'}</p></div>
      </div>
    </button>
  </Card>)}</div>
    {editingEvent && <EventModal event={editingEvent} defaultDate={null} people={people} defaultAssignee={defaultAssignee} onClose={() => setEditingEvent(null)} onSaved={() => { setEditingEvent(null); void load() }} onError={onError} />}
    {editingItem && <AtlasItemAgendaModal {...editingItem} people={people} onClose={() => setEditingItem(null)} onSaved={() => { setEditingItem(null); onListsChanged(); void load() }} onError={onError} />}
  </>
}

function AppointmentsEventsTab({ people, defaultAssignee, onError }: { people: Person[]; defaultAssignee: number[]; onError: (message: string) => void }) {
  const [events, setEvents] = useState<CalendarEvent[]>([])
  const [filter, setFilter] = useState<'all' | 'appointment' | 'event'>('all')
  const [editing, setEditing] = useState<CalendarEvent | null>(null)
  const [creating, setCreating] = useState(false)
  const load = () => api.getEvents({ upcoming: true }).then(rows => setEvents(rows.filter(row => row.event_kind === 'event' || row.event_kind === 'appointment'))).catch(error => onError(errMsg(error)))
  useEffect(() => { void load() }, [onError])
  const shown = filter === 'all' ? events : events.filter(event => event.event_kind === filter)
  return <div className="space-y-4">
    <div className="flex flex-wrap items-center justify-between gap-2"><div className="flex gap-2">{(['all', 'appointment', 'event'] as const).map(value => <button key={value} onClick={() => setFilter(value)} className={`min-h-10 rounded-full border px-3 text-sm font-bold ${filter === value ? 'border-primary bg-primary-soft text-primary' : 'border-line text-muted'}`}>{value === 'all' ? 'All' : value === 'appointment' ? 'Appointments' : 'Events'}</button>)}</div><Button size="sm" onClick={() => setCreating(true)}>+ Add</Button></div>
    {!shown.length ? <EmptyState icon="📅" title={`No upcoming ${filter === 'all' ? 'appointments or events' : `${filter}s`}`} /> : <div className="grid gap-3 lg:grid-cols-2">{shown.map(event => <Card key={event.id}><button type="button" onClick={() => event.is_synced ? window.location.assign(sourcePath(event) || calendarDayHref(event.start_at)) : setEditing(event)} className="w-full text-left"><p className="text-xs font-bold uppercase text-primary">{event.event_kind}</p><h3 className="font-bold text-ink">{event.title}</h3><p className="text-sm text-muted">{new Date(event.start_at).toLocaleString()}{event.location ? ` · ${event.location}` : ''}</p><p className="mt-1 text-xs font-bold text-primary">{event.is_synced ? 'Open source →' : 'Edit here →'}</p></button></Card>)}</div>}
    {(editing || creating) && <EventModal event={editing} defaultDate={creating ? new Date() : null} people={people} defaultAssignee={defaultAssignee} onClose={() => { setEditing(null); setCreating(false) }} onSaved={() => { setEditing(null); setCreating(false); void load() }} onError={onError} />}
  </div>
}

function PeopleBirthdaysTab({ people, onError }: { people: Person[]; onError: (message: string) => void }) {
  const [contacts, setContacts] = useState<AtlasContact[]>([])
  const [open, setOpen] = useState(false)
  const [name, setName] = useState(''); const [dob, setDob] = useState(''); const [relationship, setRelationship] = useState('')
  const load = () => api.getAtlasContacts().then(setContacts).catch(e => onError(errMsg(e)))
  useEffect(() => { void load() }, [onError])
  const save = async (event: React.FormEvent) => { event.preventDefault(); if (!name.trim() || !dob) return
    try { await api.createAtlasContact({ name: name.trim(), date_of_birth: dob, relationship, visibility: 'household' }); setName(''); setDob(''); setRelationship(''); setOpen(false); load() }
    catch (e) { onError(errMsg(e)) }
  }
  const remove = async (contact: AtlasContact) => { if (!(await confirmDialog({ title: `Delete ${contact.name}?`, confirmLabel: 'Delete' }))) return; try { await api.deleteAtlasContact(contact.id); load() } catch (e) { onError(errMsg(e)) } }
  const rows = [...people.filter(p => p.date_of_birth).map(p => ({ id: `p-${p.id}`, name: p.display_name, dob: p.date_of_birth!, relationship: 'Household member', contact: null as AtlasContact | null })),
    ...contacts.filter(c => !c.linked_person_id).map(c => ({ id: `c-${c.id}`, name: c.name, dob: c.date_of_birth, relationship: c.relationship, contact: c }))]
  return <div className="flex flex-col gap-4">
    {open ? <Card title="Add a person"><form onSubmit={save} className="grid gap-3 sm:grid-cols-3"><Field label="Name"><Input value={name} onChange={e => setName(e.target.value)} autoFocus /></Field><Field label="Date of birth"><Input type="date" value={dob} onChange={e => setDob(e.target.value)} /></Field><Field label="Relationship"><Input value={relationship} onChange={e => setRelationship(e.target.value)} placeholder="Friend, aunt…" /></Field><div className="flex gap-2 sm:col-span-3 sm:justify-end"><Button variant="ghost" onClick={() => setOpen(false)}>Cancel</Button><Button type="submit" disabled={!name.trim() || !dob}>Save person</Button></div></form></Card>
      : <Button size="sm" className="self-start" onClick={() => setOpen(true)}>+ Add person</Button>}
    {!rows.length ? <EmptyState icon="🎂" title="No birthdays yet" hint="Add friends and relatives here, or add a household member's birth date in user management." /> : <div className="grid gap-3 lg:grid-cols-2">{rows.map(row => <Card key={row.id}><div className="flex items-center justify-between gap-3"><div><h3 className="font-bold text-ink">{row.name}</h3><p className="text-sm text-muted">🎂 {new Date(`${row.dob}T00:00:00`).toLocaleDateString(undefined, { day: 'numeric', month: 'long', year: 'numeric' })}{row.relationship ? ` · ${row.relationship}` : ''}</p></div>{row.contact && <DeleteAction onClick={() => remove(row.contact!)} label={row.name} />}</div></Card>)}</div>}
  </div>
}

// ---------------------------------------------------------------------------
// Grocery tab — the plain-quantity list type, kept simple (no link/price/
// priority) so a future Hearth/meal-planning pass can populate it from a
// meal plan's ingredient list without fighting shopping-list-only fields.
// ---------------------------------------------------------------------------

function GroceryTab({ lists, people, defaultAssignee, focusedListId, focusedItemId, onListCreated, onListDeleted, onError }: {
  lists: AtlasList[]
  people: Person[]
  defaultAssignee: number[]
  focusedListId: number
  focusedItemId: number
  onListCreated: (list: AtlasList) => void
  onListDeleted: (id: number) => void
  onError: (message: string) => void
}) {
  const groceryLists = lists.filter(l => l.list_type === 'grocery')
  const [creating, setCreating] = useState(false)
  const [title, setTitle] = useState('')
  const [busy, setBusy] = useState(false)

  const create = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim()) return
    setBusy(true)
    try {
      const list = await api.createList({ title: title.trim(), list_type: 'grocery' })
      const full = await api.getList(list.id)
      onListCreated(full)
      setTitle(''); setCreating(false)
    } catch (err) { onError(errMsg(err)) } finally { setBusy(false) }
  }

  return (
    <div className="flex flex-col gap-4">
      {creating ? (
        <form onSubmit={create} className="flex flex-col gap-2 rounded-2xl border border-line bg-surface p-3 sm:flex-row">
          <Input value={title} onChange={e => setTitle(e.target.value)} placeholder="Grocery list name…" className="flex-1" autoFocus />
          <div className="flex gap-2">
            <Button type="button" variant="ghost" onClick={() => { setCreating(false); setTitle('') }} className="flex-1 sm:flex-none">Cancel</Button>
            <Button type="submit" loading={busy} disabled={!title.trim()} className="flex-1 sm:flex-none">Create</Button>
          </div>
        </form>
      ) : (
        <Button size="sm" onClick={() => setCreating(true)} className="self-start">+ New grocery list</Button>
      )}

      {groceryLists.length === 0 ? (
        <EmptyState
          icon="🛒"
          title="No grocery lists yet"
          hint="A grocery list can later be filled automatically from a meal plan once Hearth ships."
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {groceryLists.map(list => (
            <ListCard
              key={list.id}
              list={list}
              people={people}
              defaultAssignee={defaultAssignee}
              focusedItemId={list.id === focusedListId ? focusedItemId : undefined}
              onDeleted={onListDeleted}
              onError={onError}
            />
          ))}
        </div>
      )}
    </div>
  )
}

type Tab = 'agenda' | 'schedule' | 'lists' | 'grocery' | 'shopping' | 'notes' | 'reminders' | 'people'
const TAB_KEYS: Tab[] = ['agenda', 'schedule', 'lists', 'grocery', 'shopping', 'notes', 'reminders', 'people']

const LIST_TYPES = Object.entries(LIST_TYPE_META)
  .filter(([key]) => key !== 'grocery' && key !== 'shopping')
  .map(([key, m]) => ({ key, label: m.label, icon: m.icon }))

export function AtlasPage() {
  const { user } = useAuth()
  const [tab, setTab] = useUrlTab<Tab>('agenda', TAB_KEYS)
  const [lists, setLists] = useState<AtlasList[]>([])
  const [people, setPeople] = useState<Person[]>([])
  const [loading, setLoading] = useState(true)
  const [newTitle, setNewTitle] = useState('')
  const [newType, setNewType] = useState('todo')
  const [creating, setCreating] = useState(false)
  const [creatingList, setCreatingList] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useUrlQueryState()
  const [results, setResults] = useState<AtlasSearchResults | null>(null)
  // Remount only the affected list card / self-fetching tab after a quick capture.
  const [cardRefresh, setCardRefresh] = useState<Record<number, number>>({})
  const [captureTick, setCaptureTick] = useState(0)
  // docs/36 §6.3: opening a list should be a focused screen on phone, not one card in an
  // already-tall stack of every list's full contents — desktop's grid is untouched.
  const [openListId, setOpenListId] = useState<number | null>(null)
  const [searchParams] = useSearchParams()
  const focusedListId = Number(searchParams.get('list') || 0)
  const focusedItemId = Number(searchParams.get('item') || 0)
  const effectiveFocusedListId = focusedListId || lists.find(list => list.items?.some(item => item.id === focusedItemId))?.id || 0

  useEffect(() => {
    api.getLists().then(setLists).catch(e => setError(errMsg(e))).finally(() => setLoading(false))
  }, [])
  useEffect(() => { api.getPeople().then(setPeople).catch(() => {}) }, [])
  useEffect(() => {
    if (loading || (!focusedListId && !focusedItemId)) return
    if (!effectiveFocusedListId) return
    const focusedList = lists.find(list => list.id === effectiveFocusedListId)
    if (focusedList && focusedList.list_type !== 'grocery' && focusedList.list_type !== 'shopping') {
      setTab('lists')
      setOpenListId(effectiveFocusedListId)
    }
    window.setTimeout(() => {
      document.getElementById(focusedItemId ? `atlas-item-${focusedItemId}` : `atlas-list-${effectiveFocusedListId}`)
        ?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }, 0)
  }, [effectiveFocusedListId, focusedItemId, loading, lists, setTab])

  const defaultAssignee = personIdForUser(people, user?.id)
  // Grocery and Shopping now have their own dedicated tabs; the generic Lists tab keeps
  // everything else (to-do, checklist, general, wishlist).
  const otherLists = lists.filter(l => l.list_type !== 'grocery' && l.list_type !== 'shopping')
  const groceryCount = lists.filter(l => l.list_type === 'grocery').length
  const shoppingCount = lists.filter(l => l.list_type === 'shopping').length

  // Debounced Atlas-wide search.
  useEffect(() => {
    const q = query.trim()
    if (q.length < 2) { setResults(null); return }
    const id = setTimeout(() => {
      api.searchAtlas(q).then(setResults).catch(e => setError(errMsg(e)))
    }, 300)
    return () => clearTimeout(id)
  }, [query])

  const createList = async () => {
    if (!newTitle.trim()) return
    setCreating(true)
    try {
      const list = await api.createList({ title: newTitle.trim(), list_type: newType })
      const full = await api.getList(list.id)
      setLists(prev => [full, ...prev])
      setNewTitle(''); setNewType('todo')
      setCreatingList(false)
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
        await api.createItem(listId, { title: text, assigned_to_person_ids: defaultAssignee })
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
    <div className="flex flex-col gap-4 sm:gap-5">
      <div className="hidden sm:block">
        <PageHeader
          title="Lists & Notes"
          icon="🗒"
          actions={tab === 'lists' && lists.length > 0 && !creatingList
            ? <Button size="sm" onClick={() => setCreatingList(true)}>+ New list</Button>
            : undefined}
        />
      </div>

      <CaptureBar lists={otherLists} onCapture={capture} />

      <SearchField
        value={query}
        onChange={e => setQuery(e.target.value)}
        onClear={() => setQuery('')}
        placeholder="Search lists, items, notes, reminders…"
      />

      {error && (
        <div className="flex items-center justify-between gap-3 px-4 py-2.5 rounded-xl bg-danger-soft text-danger text-sm">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-danger/70 hover:text-danger" aria-label="Dismiss">×</button>
        </div>
      )}

      {results !== null ? (
        <SearchResults results={results} lists={lists} />
      ) : (
        <>
          {/* Tabs */}
          <Tabs
            tabs={[
              { key: 'agenda', label: 'agenda' },
              { key: 'schedule', label: 'appointments & events' },
              { key: 'lists', label: 'lists', badge: otherLists.length || undefined },
              { key: 'grocery', label: 'grocery', badge: groceryCount || undefined },
              { key: 'shopping', label: 'shopping', badge: shoppingCount || undefined },
              { key: 'notes', label: 'notes' },
              { key: 'reminders', label: 'reminders' },
              { key: 'people', label: 'people & birthdays' },
            ]}
            active={tab}
            onChange={setTab}
            className="w-fit"
          />

          {tab === 'agenda' ? <AgendaTab people={people} lists={lists} defaultAssignee={defaultAssignee} onError={setError} onListsChanged={() => api.getLists().then(setLists).catch(error => setError(errMsg(error)))} /> : tab === 'schedule' ? <AppointmentsEventsTab people={people} defaultAssignee={defaultAssignee} onError={setError} /> : tab === 'lists' ? (
            <div className="flex flex-col gap-4">
              {loading ? (
                <div className="h-32 rounded-2xl bg-sunken animate-pulse" />
              ) : otherLists.length === 0 ? (
                <EmptyState
                  icon="🗒"
                  title="No lists yet"
                  hint="Make a shared list for errands, chores or anything else. Groceries and shopping have their own tabs."
                  action={<Button onClick={() => setCreatingList(true)}>Create your first list</Button>}
                />
              ) : (
                <>
                  {/* Phone: a summary row per list, opening the full list as a focused sheet —
                      not every list's full contents stacked one after another. */}
                  <div className="sm:hidden">
                    <MobileSection title="Lists" action={<button type="button" onClick={() => setCreatingList(true)}>+ New</button>}>
                      {otherLists.map(list => {
                        const meta = listTypeMeta(list.list_type)
                        const pendingCount = (list.items ?? []).filter(i => !i.is_complete).length
                        const total = (list.items ?? []).length
                        return (
                          <MobileListRow
                            key={list.id}
                            icon={meta.icon}
                            title={list.title}
                            subtitle={pendingCount > 0 ? `${pendingCount} to do` : total > 0 ? 'All done ✓' : meta.label}
                            onClick={() => setOpenListId(list.id)}
                          />
                        )
                      })}
                    </MobileSection>
                  </div>
                  <div className="hidden grid-cols-1 gap-4 lg:grid-cols-2 sm:grid">
                    {otherLists.map(list => (
                      <ListCard
                        key={`${list.id}:${cardRefresh[list.id] ?? 0}`}
                        list={list}
                        people={people}
                        defaultAssignee={defaultAssignee}
                        focusedItemId={list.id === effectiveFocusedListId ? focusedItemId : undefined}
                        onDeleted={id => setLists(prev => prev.filter(l => l.id !== id))}
                        onError={setError}
                      />
                    ))}
                  </div>
                </>
              )}
            </div>
          ) : tab === 'grocery' ? (
            <GroceryTab
              lists={lists}
              people={people}
              defaultAssignee={defaultAssignee}
              focusedListId={effectiveFocusedListId}
              focusedItemId={focusedItemId}
              onListCreated={list => setLists(prev => [list, ...prev])}
              onListDeleted={id => setLists(prev => prev.filter(l => l.id !== id))}
              onError={setError}
            />
          ) : tab === 'shopping' ? (
            <ShoppingTab
              lists={lists}
              people={people}
              onListCreated={list => setLists(prev => [list, ...prev])}
              onListDeleted={id => setLists(prev => prev.filter(l => l.id !== id))}
              onError={setError}
            />
          ) : tab === 'notes' ? (
            <NotesTab key={`notes-${captureTick}`} onError={setError} />
          ) : tab === 'reminders' ? (
            <RemindersTab key={`reminders-${captureTick}`} onError={setError} />
          ) : (
            <PeopleBirthdaysTab people={people} onError={setError} />
          )}
        </>
      )}

      {creatingList && (
        <Modal
          title="New list"
          onClose={() => { setCreatingList(false); setNewTitle('') }}
          size="full"
          footer={
            <>
              <Button variant="ghost" onClick={() => { setCreatingList(false); setNewTitle('') }}>Cancel</Button>
              <Button onClick={createList} loading={creating} disabled={!newTitle.trim()}>Create</Button>
            </>
          }
        >
          <div className="flex flex-col gap-3">
            <Field label="List name">
              <Input value={newTitle} onChange={e => setNewTitle(e.target.value)} placeholder="New list name…" data-autofocus />
            </Field>
            <Field label="Type">
              <Select value={newType} onChange={e => setNewType(e.target.value)}>
                {LIST_TYPES.map(t => <option key={t.key} value={t.key}>{t.icon} {t.label}</option>)}
              </Select>
            </Field>
          </div>
        </Modal>
      )}

      {openListId !== null && (() => {
        const list = otherLists.find(l => l.id === openListId)
        if (!list) return null
        return (
          <Modal title={list.title} onClose={() => setOpenListId(null)} size="full">
            <ListCard
              key={`${list.id}:${cardRefresh[list.id] ?? 0}`}
              list={list}
              people={people}
              defaultAssignee={defaultAssignee}
              focusedItemId={list.id === effectiveFocusedListId ? focusedItemId : undefined}
              onDeleted={id => { setLists(prev => prev.filter(l => l.id !== id)); setOpenListId(null) }}
              onError={setError}
            />
          </Modal>
        )
      })()}
    </div>
  )
}
