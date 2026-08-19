import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../../../api/client'
import type { AtlasContact, AtlasList, AtlasListItem, AtlasNote, AtlasSearchResults, CalendarEvent, Person } from '../../../api/types'
import { Card } from '../../../components/Card'
import { Button } from '../../../components/Button'
import { Modal } from '../../../components/Modal'
import { Field, Input, SearchField, Textarea, Select } from '../../../components/Field'
import { type TabDef } from '../../../components/Tabs'
import { CustomisableTabs } from '../../../components/CustomisableTabs'
import { useCustomisableTabs } from '../../../hooks/useCustomisableTabs'
import { PageHeader } from '../../../components/PageHeader'
import { EmptyState } from '../../../components/EmptyState'
import { DateTimeField } from '../../../components/DateTimeField'
import { AssigneeSelect, personIdForUser } from '../../../components/AssigneeSelect'
import { DeleteAction } from '../../..//components/RowActions'
import { useAuth } from '../../auth/AuthContext'
import { useUrlQueryState } from '../../../hooks/useUrlTab'
import { confirmDialog } from '../../../components/Dialogs'
import { sourcePath } from '../../../lib/sourceLinks'
import { EventModal } from './CalendarPage'
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

// D19: Atlas's three primary areas are Grocery, To-dos and Lists & Notes (checklist). `general`
// is a legacy fallback for anything that predates that model.
const LIST_TYPE_META: Record<string, { label: string; icon: string }> = {
  todo: { label: 'To-do', icon: '✓' },
  grocery: { label: 'Grocery', icon: '🛒' },
  checklist: { label: 'Checklist', icon: '☑️' },
  general: { label: 'List', icon: '📋' },
}
const listTypeMeta = (t: string) => LIST_TYPE_META[t] ?? { label: t, icon: '•' }

// ---------------------------------------------------------------------------
// Checklist item row (Lists & Notes) — reused for checklist-type lists, which keep the
// optional quantity/assignee fields plain To-dos and Grocery no longer need.
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
// Single checklist card (Lists & Notes)
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
  const [assignee, setAssignee] = useState<number[]>(defaultAssignee)
  const [adding, setAdding] = useState(false)
  const [showDone, setShowDone] = useState(Boolean(focusedItemId && items.some(item => item.id === focusedItemId && item.is_complete)))
  const inputRef = useRef<HTMLInputElement>(null)
  const meta = listTypeMeta(list.list_type)

  const addItem = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newTitle.trim()) return
    setAdding(true)
    try {
      const item = await api.createItem(list.id, {
        title: newTitle.trim(), assigned_to_person_ids: assignee,
      })
      setItems(prev => [...prev, item])
      setNewTitle(''); setAssignee(defaultAssignee)
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
              {pending.length > 0
                ? `${pending.length} to do`
                : total > 0 ? 'All done ✓' : 'Checklist'}
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
        <input
          ref={inputRef}
          value={newTitle}
          onChange={e => setNewTitle(e.target.value)}
          placeholder="Add item…"
          className="flex-1 min-w-0 text-sm bg-transparent text-ink placeholder-muted outline-none min-h-[40px]"
        />
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
// Notes
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

// ---------------------------------------------------------------------------
// Lists & Notes — checklists + notes, "New → Checklist / Note" (D19 §H)
// ---------------------------------------------------------------------------

function ListsAndNotesTab({ checklistLists, people, defaultAssignee, focusedListId, focusedItemId, onOpenList, onListCreated, onListDeleted, onError }: {
  checklistLists: AtlasList[]
  people: Person[]
  defaultAssignee: number[]
  focusedListId: number
  focusedItemId: number
  onOpenList: (id: number) => void
  onListCreated: (list: AtlasList) => void
  onListDeleted: (id: number) => void
  onError: (m: string) => void
}) {
  const [notes, setNotes] = useState<AtlasNote[] | null>(null)
  const [creating, setCreating] = useState<'checklist' | 'note' | null>(null)
  const [title, setTitle] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => { api.getNotes().then(setNotes).catch(e => onError(errMsg(e))) }, [onError])

  const createChecklist = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim()) return
    setBusy(true)
    try {
      const list = await api.createList({ title: title.trim(), list_type: 'checklist' })
      const full = await api.getList(list.id)
      onListCreated(full)
      setTitle(''); setCreating(null)
    } catch (e) { onError(errMsg(e)) } finally { setBusy(false) }
  }

  const createNote = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim()) return
    setBusy(true)
    try {
      const note = await api.createNote({ title: title.trim(), visibility: 'household' })
      setNotes(prev => [note, ...(prev ?? [])])
      setTitle(''); setCreating(null)
    } catch (e) { onError(errMsg(e)) } finally { setBusy(false) }
  }

  return (
    <div className="flex flex-col gap-5">
      {creating === null ? (
        <div className="flex gap-2">
          <Button size="sm" onClick={() => setCreating('checklist')}>+ New checklist</Button>
          <Button size="sm" variant="ghost" onClick={() => setCreating('note')}>+ New note</Button>
        </div>
      ) : (
        <Card title={creating === 'checklist' ? 'New checklist' : 'New note'}>
          <form onSubmit={creating === 'checklist' ? createChecklist : createNote} className="flex flex-col gap-2 sm:flex-row">
            <Input value={title} onChange={e => setTitle(e.target.value)} placeholder={creating === 'checklist' ? 'Checklist name…' : 'Note title…'} className="flex-1" autoFocus />
            <div className="flex gap-2">
              <Button type="button" variant="ghost" onClick={() => { setCreating(null); setTitle('') }}>Cancel</Button>
              <Button type="submit" loading={busy} disabled={!title.trim()}>Create</Button>
            </div>
          </form>
        </Card>
      )}

      <div>
        <p className="mb-2 text-xs font-bold uppercase tracking-wide text-muted-strong">Checklists</p>
        {checklistLists.length === 0 ? (
          <EmptyState icon="☑️" title="No checklists yet" hint="Bunnings run, holiday packing, movies to watch — anything you'd tick off." />
        ) : (
          <>
            <div className="sm:hidden">
              <MobileSection title="Checklists">
                {checklistLists.map(list => {
                  const meta = listTypeMeta(list.list_type)
                  const pendingCount = (list.items ?? []).filter(i => !i.is_complete).length
                  const total = (list.items ?? []).length
                  return (
                    <MobileListRow
                      key={list.id}
                      icon={meta.icon}
                      title={list.title}
                      subtitle={pendingCount > 0 ? `${pendingCount} to do` : total > 0 ? 'All done ✓' : 'Checklist'}
                      onClick={() => onOpenList(list.id)}
                    />
                  )
                })}
              </MobileSection>
            </div>
            <div className="hidden grid-cols-1 gap-4 lg:grid-cols-2 sm:grid">
              {checklistLists.map(list => (
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
          </>
        )}
      </div>

      <div>
        <p className="mb-2 text-xs font-bold uppercase tracking-wide text-muted-strong">Notes</p>
        {notes === null ? (
          <div className="h-24 rounded-2xl bg-sunken animate-pulse" />
        ) : notes.length === 0 ? (
          <EmptyState icon="📝" title="No notes yet" hint="Jot down anything you want to remember — recipes, ideas or household information." />
        ) : (
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
            {notes.map(n => (
              <NoteCard key={n.id} note={n}
                onSaved={u => setNotes(prev => (prev ?? []).map(x => x.id === u.id ? u : x))}
                onDeleted={id => setNotes(prev => (prev ?? []).filter(x => x.id !== id))}
                onError={onError} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Grocery — the single household list (D19 §C)
// ---------------------------------------------------------------------------

// Client-side only — a lightweight heuristic, not a stored field, so it costs nothing to
// change or extend and never conflicts with anyone else's data.
const GROCERY_CATEGORY_KEYWORDS: [string, string[]][] = [
  ['Produce', ['apple', 'banana', 'carrot', 'potato', 'onion', 'tomato', 'lettuce', 'spinach', 'fruit', 'veg', 'vegetable', 'berry', 'avocado', 'capsicum', 'broccoli', 'garlic', 'mushroom', 'lemon', 'lime']],
  ['Dairy', ['milk', 'cheese', 'yoghurt', 'yogurt', 'butter', 'cream', 'egg']],
  ['Bakery', ['bread', 'bun', 'roll', 'bagel', 'muffin', 'croissant']],
  ['Meat & Seafood', ['chicken', 'beef', 'pork', 'lamb', 'mince', 'fish', 'salmon', 'prawn', 'sausage', 'bacon']],
  ['Pantry', ['rice', 'pasta', 'flour', 'sugar', 'oil', 'sauce', 'can', 'tin', 'cereal', 'coffee', 'tea', 'spice', 'salt', 'stock']],
  ['Frozen', ['frozen', 'ice cream']],
  ['Household', ['dishwasher', 'detergent', 'tablet', 'tissue', 'paper towel', 'toilet paper', 'cleaner', 'soap', 'bin bag', 'foil', 'wrap']],
]
function guessGroceryCategory(title: string): string {
  const lower = title.toLowerCase()
  for (const [category, keywords] of GROCERY_CATEGORY_KEYWORDS) {
    if (keywords.some(k => lower.includes(k))) return category
  }
  return 'Other'
}

function GroceryItemRow({ item, onToggle, onDelete, onError }: {
  item: AtlasListItem
  onToggle: (item: AtlasListItem) => void
  onDelete: (item: AtlasListItem) => void
  onError: (m: string) => void
}) {
  const [busy, setBusy] = useState(false)
  const listId = item.atlas_list_id

  const toggle = async () => {
    setBusy(true)
    const optimistic: AtlasListItem = {
      ...item, is_complete: !item.is_complete, completed_at: item.is_complete ? null : new Date().toISOString(),
    }
    onToggle(optimistic)
    try {
      const updated = item.is_complete ? await api.uncompleteItem(listId, item.id) : await api.completeItem(listId, item.id)
      onToggle(updated)
    } catch (e) { onToggle(item); onError(errMsg(e)) } finally { setBusy(false) }
  }

  return (
    <li id={`atlas-item-${item.id}`} className="group flex items-center gap-1 rounded-xl">
      <button
        onClick={toggle} disabled={busy}
        className="flex min-h-[48px] min-w-0 flex-1 items-center gap-3 py-2 text-left disabled:opacity-60"
        aria-label={item.is_complete ? 'Mark not bought' : 'Mark bought'}
      >
        <span className={`grid h-6 w-6 flex-shrink-0 place-items-center rounded-full border-2 ${item.is_complete ? 'bg-success border-success text-white' : 'border-line-strong group-hover:border-success'}`}>
          {item.is_complete && <span className="text-xs">✓</span>}
        </span>
        <span className={`min-w-0 flex-1 truncate text-sm ${item.is_complete ? 'line-through text-muted' : 'text-ink'}`}>
          {item.title}{item.quantity ? <span className="ml-1.5 text-muted-strong">× {item.quantity}</span> : ''}
        </span>
      </button>
      <button
        onClick={() => onDelete(item)}
        className="grid h-10 w-9 flex-shrink-0 place-items-center rounded-xl text-lg leading-none text-muted hover:bg-danger-soft hover:text-danger sm:opacity-0 sm:group-hover:opacity-100"
        aria-label="Delete"
      >
        ×
      </button>
    </li>
  )
}

function GroceryTab({ groceryList, onError }: {
  groceryList: AtlasList | null
  onError: (m: string) => void
}) {
  const [items, setItems] = useState<AtlasListItem[]>(groceryList?.items ?? [])
  const [title, setTitle] = useState('')
  const [qty, setQty] = useState('')
  const [adding, setAdding] = useState(false)
  const [grouped, setGrouped] = useState(true)
  const [showBought, setShowBought] = useState(false)
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [clearing, setClearing] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => { setItems(groceryList?.items ?? []) }, [groceryList])
  useEffect(() => { api.getGrocerySuggestions().then(setSuggestions).catch(() => { /* suggestions are a nicety */ }) }, [])

  const addTitled = async (value: string, quantity?: string) => {
    const trimmed = value.trim()
    if (!trimmed) return
    setAdding(true)
    try {
      const item = await api.addGroceryItem({ title: trimmed, quantity: quantity?.trim() || undefined })
      setItems(prev => prev.some(i => i.id === item.id) ? prev.map(i => i.id === item.id ? item : i) : [...prev, item])
      setTitle(''); setQty('')
      inputRef.current?.focus()
    } catch (e) { onError(errMsg(e)) } finally { setAdding(false) }
  }

  const add = (e: React.FormEvent) => { e.preventDefault(); void addTitled(title, qty) }

  const handleToggle = (updated: AtlasListItem) => setItems(prev => prev.map(i => i.id === updated.id ? updated : i))
  const handleDelete = async (item: AtlasListItem) => {
    try { await api.deleteItem(item.atlas_list_id, item.id); setItems(prev => prev.filter(i => i.id !== item.id)) }
    catch (e) { onError(errMsg(e)) }
  }
  const clearBought = async () => {
    setClearing(true)
    try { await api.clearBoughtGroceryItems(); setItems(prev => prev.filter(i => !i.is_complete)) }
    catch (e) { onError(errMsg(e)) } finally { setClearing(false) }
  }

  if (!groceryList) return <div className="h-32 rounded-2xl bg-sunken animate-pulse" />

  const pending = items.filter(i => !i.is_complete)
  const bought = items.filter(i => i.is_complete)
  const groupEntries: [string, AtlasListItem[]][] = grouped
    ? Object.entries(
      pending.reduce<Record<string, AtlasListItem[]>>((acc, item) => {
        const cat = guessGroceryCategory(item.title)
        acc[cat] = acc[cat] ?? []
        acc[cat].push(item)
        return acc
      }, {}),
    ).sort(([a], [b]) => (a === 'Other' ? 1 : b === 'Other' ? -1 : a.localeCompare(b)))
    : [['Grocery', pending]]
  const offeredSuggestions = suggestions.filter(s => !pending.some(i => i.title.toLowerCase() === s.toLowerCase()))

  return (
    <div className="flex flex-col gap-4">
      <Card contentClassName="p-3">
        <form onSubmit={add} className="flex items-center gap-2">
          <input
            ref={inputRef} value={title} onChange={e => setTitle(e.target.value)}
            placeholder="Add grocery item…"
            className="min-h-[44px] flex-1 min-w-0 bg-transparent text-sm text-ink placeholder-muted outline-none"
          />
          <input
            value={qty} onChange={e => setQty(e.target.value)} placeholder="Qty" aria-label="Quantity"
            className="w-16 min-h-[44px] border-l border-line bg-transparent pl-2 text-sm text-ink placeholder-muted outline-none"
          />
          <Button type="submit" size="sm" loading={adding} disabled={!title.trim()}>+</Button>
        </form>
      </Card>

      {offeredSuggestions.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {offeredSuggestions.map(s => (
            <button
              key={s} type="button" onClick={() => void addTitled(s)}
              className="min-h-9 rounded-full border border-line px-3 text-xs font-semibold text-muted-strong hover:border-primary hover:text-primary"
            >
              + {s}
            </button>
          ))}
        </div>
      )}

      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-muted-strong">{pending.length} item{pending.length === 1 ? '' : 's'} to buy</span>
        <button type="button" onClick={() => setGrouped(v => !v)} className="text-xs font-semibold text-muted hover:text-ink">
          {grouped ? 'Ungroup' : 'Group by category'}
        </button>
      </div>

      {pending.length === 0 ? (
        <EmptyState icon="🛒" title="Grocery list is empty" hint="Add the first item above." />
      ) : (
        <div className="flex flex-col gap-4">
          {groupEntries.map(([category, rows]) => (
            <div key={category}>
              {grouped && <p className="mb-1 text-xs font-bold uppercase tracking-wide text-muted-strong">{category}</p>}
              <ul className="divide-y divide-line/60">
                {rows.map(item => <GroceryItemRow key={item.id} item={item} onToggle={handleToggle} onDelete={handleDelete} onError={onError} />)}
              </ul>
            </div>
          ))}
        </div>
      )}

      {bought.length > 0 && (
        <div>
          <div className="flex items-center justify-between">
            <button onClick={() => setShowBought(v => !v)} className="flex items-center gap-1 py-1.5 text-xs font-semibold text-muted hover:text-ink transition-colors">
              <span className="w-3 inline-block">{showBought ? '▾' : '▸'}</span>{bought.length} bought
            </button>
            <Button size="sm" variant="ghost" onClick={clearBought} loading={clearing}>Clear bought</Button>
          </div>
          {showBought && (
            <ul className="divide-y divide-line/60">
              {bought.map(item => <GroceryItemRow key={item.id} item={item} onToggle={handleToggle} onDelete={handleDelete} onError={onError} />)}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// To-dos — Household + one list per active Person, Today aggregation (D19 §D/§E/§F/§G)
// ---------------------------------------------------------------------------

const NOTIFY_OFFSET_CHOICES: { minutes: number; label: string }[] = [
  { minutes: 0, label: 'At time' },
  { minutes: 15, label: '15 min before' },
  { minutes: 30, label: '30 min before' },
  { minutes: 60, label: '1 hour before' },
  { minutes: 120, label: '2 hours before' },
  { minutes: 1440, label: '1 day before' },
  { minutes: 2880, label: '2 days before' },
  { minutes: 10080, label: '1 week before' },
]

function TodoItemRow({ item, lists, busy, showListLabel, onToggle, onToggleImportant, onSetOffsets, onMove, onDelete }: {
  item: AtlasListItem
  lists: AtlasList[]
  busy: boolean
  showListLabel: boolean
  onToggle: () => void
  onToggleImportant: () => void
  onSetOffsets: (offsets: number[]) => void
  onMove: (destinationListId: number) => void
  onDelete: () => void
}) {
  const [showNotify, setShowNotify] = useState(false)
  const due = dueLabel(item.due_at)
  const listLabel = showListLabel ? lists.find(l => l.id === item.atlas_list_id)?.title : null

  return (
    <li id={`atlas-item-${item.id}`} className="group flex flex-col gap-1 rounded-xl px-1 py-1.5">
      <div className="flex items-start gap-1">
        <button
          onClick={onToggle} disabled={busy}
          className="flex min-h-[48px] min-w-0 flex-1 items-start gap-3 py-1 text-left disabled:opacity-60"
          aria-label={item.is_complete ? 'Mark not done' : 'Mark done'}
        >
          <span className={`mt-0.5 grid h-6 w-6 flex-shrink-0 place-items-center rounded-full border-2 ${item.is_complete ? 'bg-success border-success text-white' : 'border-line-strong group-hover:border-success'}`}>
            {item.is_complete && <span className="text-xs">✓</span>}
          </span>
          <span className="min-w-0 flex-1">
            <span className={`block break-words text-sm leading-5 ${item.is_complete ? 'line-through text-muted' : 'text-ink'}`}>
              {item.is_important && <span className="mr-1 text-warning" aria-label="Important">★</span>}
              {item.title}
            </span>
            {(listLabel || (!item.is_complete && due)) && (
              <span className="mt-1 flex flex-wrap items-center gap-1.5 text-[11px] text-muted">
                {listLabel && <span className="rounded-full bg-sunken px-1.5 py-0.5 font-semibold">{listLabel}</span>}
                {!item.is_complete && due && <span className={`rounded-full px-1.5 py-0.5 font-semibold ${due.tone}`}>{due.text}</span>}
              </span>
            )}
          </span>
        </button>
        <div className="flex flex-shrink-0 items-center gap-0.5 sm:opacity-0 sm:group-hover:opacity-100 sm:group-focus-within:opacity-100">
          <button
            type="button" onClick={onToggleImportant}
            className={`grid h-9 w-9 place-items-center rounded-xl text-base ${item.is_important ? 'text-warning' : 'text-muted hover:text-ink'}`}
            aria-label={item.is_important ? 'Unmark important' : 'Mark important'}
          >★</button>
          {item.due_at && (
            <button
              type="button" onClick={() => setShowNotify(v => !v)}
              className={`grid h-9 w-9 place-items-center rounded-xl text-base ${item.notify_offsets.length ? 'text-primary' : 'text-muted hover:text-ink'}`}
              aria-label="Notification settings" aria-expanded={showNotify}
            >🔔</button>
          )}
          {lists.length > 1 && (
            <select
              value={item.atlas_list_id} onChange={e => onMove(Number(e.target.value))}
              aria-label="Move to list"
              className="h-9 rounded-xl border border-line bg-surface px-1 text-xs text-muted-strong"
            >
              {lists.map(l => <option key={l.id} value={l.id}>{l.title}</option>)}
            </select>
          )}
          <button type="button" onClick={onDelete} className="grid h-9 w-9 place-items-center rounded-xl text-lg leading-none text-muted hover:bg-danger-soft hover:text-danger" aria-label="Delete">×</button>
        </div>
      </div>
      {showNotify && item.due_at && (
        <div className="ml-9 flex flex-wrap gap-1.5 rounded-xl bg-sunken/60 p-2">
          {NOTIFY_OFFSET_CHOICES.map(choice => {
            const active = item.notify_offsets.includes(choice.minutes)
            return (
              <button
                key={choice.minutes} type="button"
                onClick={() => onSetOffsets(active ? item.notify_offsets.filter(m => m !== choice.minutes) : [...item.notify_offsets, choice.minutes])}
                aria-pressed={active}
                className={`min-h-8 rounded-full px-2.5 text-xs font-semibold ${active ? 'bg-primary text-white' : 'border border-line bg-surface text-muted-strong'}`}
              >
                {choice.label}
              </button>
            )
          })}
        </div>
      )}
    </li>
  )
}

function TodoTab({ todoLists, focusedListId, onRefresh, onError }: {
  todoLists: AtlasList[]
  focusedListId: number
  onRefresh: () => Promise<void>
  onError: (m: string) => void
}) {
  const household = todoLists.find(l => l.owner_person_id === null) ?? null
  const [view, setView] = useState<number | 'today'>(focusedListId || household?.id || 'today')
  const [today, setToday] = useState<AtlasListItem[] | null>(null)
  const [title, setTitle] = useState('')
  const [adding, setAdding] = useState(false)
  const [busyIds, setBusyIds] = useState<Set<number>>(new Set())
  const [showDone, setShowDone] = useState(false)

  const loadToday = () => api.getTodayTodos().then(setToday).catch(e => onError(errMsg(e)))
  useEffect(() => { if (view === 'today') void loadToday() }, [view])
  useEffect(() => {
    if (focusedListId && todoLists.some(l => l.id === focusedListId)) setView(focusedListId)
  }, [focusedListId, todoLists])
  useEffect(() => {
    if (view !== 'today' && !todoLists.some(l => l.id === view) && household) setView(household.id)
  }, [todoLists, view, household])

  const activeList = typeof view === 'number' ? todoLists.find(l => l.id === view) ?? null : null
  const items = view === 'today' ? (today ?? []) : (activeList?.items ?? [])

  const refreshAfterMutation = async () => {
    await onRefresh()
    if (view === 'today') await loadToday()
  }

  const add = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim() || activeList === null) return
    setAdding(true)
    try { await api.createItem(activeList.id, { title: title.trim() }); setTitle(''); await refreshAfterMutation() }
    catch (e) { onError(errMsg(e)) } finally { setAdding(false) }
  }

  const withBusy = async (id: number, fn: () => Promise<void>) => {
    setBusyIds(prev => new Set(prev).add(id))
    try { await fn() } catch (e) { onError(errMsg(e)) } finally {
      setBusyIds(prev => { const next = new Set(prev); next.delete(id); return next })
    }
  }

  const toggle = (item: AtlasListItem) => withBusy(item.id, async () => {
    if (item.is_complete) await api.uncompleteItem(item.atlas_list_id, item.id)
    else await api.completeItem(item.atlas_list_id, item.id)
    await refreshAfterMutation()
  })
  const toggleImportant = (item: AtlasListItem) => withBusy(item.id, async () => {
    await api.updateItem(item.atlas_list_id, item.id, { is_important: !item.is_important })
    await refreshAfterMutation()
  })
  const setOffsets = (item: AtlasListItem, offsets: number[]) => withBusy(item.id, async () => {
    await api.updateItem(item.atlas_list_id, item.id, { notify_offsets: offsets })
    await refreshAfterMutation()
  })
  const moveTo = (item: AtlasListItem, destinationId: number) => withBusy(item.id, async () => {
    if (destinationId === item.atlas_list_id) return
    await api.moveListItem(item.atlas_list_id, item.id, destinationId)
    await refreshAfterMutation()
  })
  const remove = (item: AtlasListItem) => withBusy(item.id, async () => {
    await api.deleteItem(item.atlas_list_id, item.id)
    await refreshAfterMutation()
  })

  const pending = items.filter(i => !i.is_complete)
  const done = items.filter(i => i.is_complete)

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap gap-1 rounded-xl bg-sunken p-1">
        <button type="button" onClick={() => setView('today')} className={`min-h-9 rounded-lg px-3 text-xs font-bold ${view === 'today' ? 'bg-raised text-ink shadow-soft' : 'text-muted hover:text-ink'}`}>Today</button>
        {todoLists.map(list => (
          <button key={list.id} type="button" onClick={() => setView(list.id)} className={`min-h-9 rounded-lg px-3 text-xs font-bold ${view === list.id ? 'bg-raised text-ink shadow-soft' : 'text-muted hover:text-ink'}`}>{list.title}</button>
        ))}
      </div>

      {view !== 'today' && (
        <Card contentClassName="p-3">
          <form onSubmit={add} className="flex items-center gap-2">
            <input value={title} onChange={e => setTitle(e.target.value)} placeholder="Add a to-do…" className="min-h-[44px] flex-1 min-w-0 bg-transparent text-sm text-ink placeholder-muted outline-none" />
            <Button type="submit" size="sm" loading={adding} disabled={!title.trim()}>+</Button>
          </form>
        </Card>
      )}

      {view === 'today' && today === null ? (
        <div className="h-32 rounded-2xl bg-sunken animate-pulse" />
      ) : pending.length === 0 && done.length === 0 ? (
        <EmptyState
          icon="✓"
          title={view === 'today' ? 'Nothing due today' : 'Nothing here yet'}
          hint={view === 'today' ? 'Overdue and today’s to-dos across Household and personal lists appear here.' : 'Add the first to-do above.'}
        />
      ) : (
        <>
          {pending.length === 0 ? <p className="text-sm text-muted py-1">All done ✓</p> : (
            <ul className="divide-y divide-line/60">
              {pending.map(item => (
                <TodoItemRow
                  key={item.id} item={item} lists={todoLists} busy={busyIds.has(item.id)} showListLabel={view === 'today'}
                  onToggle={() => void toggle(item)} onToggleImportant={() => void toggleImportant(item)}
                  onSetOffsets={offsets => void setOffsets(item, offsets)} onMove={id => void moveTo(item, id)}
                  onDelete={() => void remove(item)}
                />
              ))}
            </ul>
          )}
          {done.length > 0 && view !== 'today' && (
            <div>
              <button onClick={() => setShowDone(v => !v)} className="flex items-center gap-1 py-1.5 text-xs font-semibold text-muted hover:text-ink transition-colors">
                <span className="w-3 inline-block">{showDone ? '▾' : '▸'}</span>{done.length} completed
              </button>
              {showDone && (
                <ul className="divide-y divide-line/60">
                  {done.map(item => (
                    <TodoItemRow
                      key={item.id} item={item} lists={todoLists} busy={busyIds.has(item.id)} showListLabel={false}
                      onToggle={() => void toggle(item)} onToggleImportant={() => void toggleImportant(item)}
                      onSetOffsets={offsets => void setOffsets(item, offsets)} onMove={id => void moveTo(item, id)}
                      onDelete={() => void remove(item)}
                    />
                  ))}
                </ul>
              )}
            </div>
          )}
        </>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Quick capture — one bar that drops text into a to-do, grocery item or note.
// ---------------------------------------------------------------------------

type CaptureKind = 'todo' | 'grocery' | 'note'

function CaptureBar({ todoLists, onCapture }: {
  todoLists: AtlasList[]
  onCapture: (kind: CaptureKind, text: string, listId: number | null) => Promise<void>
}) {
  const [kind, setKind] = useState<CaptureKind>('todo')
  const [text, setText] = useState('')
  const household = todoLists.find(l => l.owner_person_id === null) ?? null
  const [listId, setListId] = useState<number | null>(household?.id ?? todoLists[0]?.id ?? null)
  const [busy, setBusy] = useState(false)
  const [open, setOpen] = useState(false)

  // Keep a valid target list selected as lists load / change.
  useEffect(() => {
    if (kind !== 'todo') return
    if (listId == null || !todoLists.some(l => l.id === listId)) setListId(household?.id ?? todoLists[0]?.id ?? null)
  }, [todoLists, kind, listId, household])

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
          Quickly add a to-do, grocery item or note
        </button>
      )}
      <form onSubmit={submit} className={`${open ? 'flex' : 'hidden'} flex-col gap-2 sm:flex`}>
        <div className="flex items-center justify-between sm:hidden">
          <span className="text-xs font-bold uppercase tracking-wide text-muted">Quick add</span>
          <button type="button" onClick={() => setOpen(false)} className="grid h-9 w-9 place-items-center rounded-xl text-muted" aria-label="Close quick add">✕</button>
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
            {seg('grocery', 'Grocery')}
            {seg('note', 'Note')}
          </div>
          {kind === 'todo' && (
            todoLists.length > 0 ? (
              <Select value={listId ?? 0} onChange={e => setListId(Number(e.target.value))} className="!w-auto min-w-[9rem] !min-h-[38px] !py-1.5">
                {todoLists.map(l => <option key={l.id} value={l.id}>{l.title}</option>)}
              </Select>
            ) : (
              <span className="text-xs text-muted">Loading your to-do lists…</span>
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

function listTabFor(listType: string): 'lists' | 'grocery' | 'todos' {
  if (listType === 'grocery') return 'grocery'
  if (listType === 'todo') return 'todos'
  return 'lists'
}

function SearchResults({ results, lists }: { results: AtlasSearchResults; lists: AtlasList[] }) {
  const empty = !results.notes.length && !results.lists.length && !results.items.length
  if (empty) return <EmptyState icon="🔍" title="No matches" hint="Try a different word, or check another list." />

  return (
    <div className="flex flex-col gap-4">
      {results.lists.length > 0 && (
        <Section title="Lists">
          {results.lists.map(l => (
            <Link key={`l${l.id}`} to={`/atlas?tab=${listTabFor(l.list_type)}&list=${l.id}`} className="group block">
              <Card className="transition-colors group-hover:border-primary/40">
                <span className="text-sm font-medium text-ink">{l.title}</span>
                <span className="text-xs text-muted"> · {listTypeMeta(l.list_type).label}</span>
              </Card>
            </Link>
          ))}
        </Section>
      )}
      {results.items.length > 0 && (
        <Section title="Items">
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
            <Link key={`n${n.id}`} to="/atlas?tab=lists" className="group block">
              <Card className="transition-colors group-hover:border-primary/40">
                <p className="text-sm font-medium text-ink">{n.title}</p>
                {n.body && <p className="text-xs text-muted truncate">{n.body}</p>}
              </Card>
            </Link>
          ))}
        </Section>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Agenda / Appointments & Events / Birthdays — Calendar-adjacent conveniences,
// secondary to the three primary areas above (D19 §B).
// ---------------------------------------------------------------------------

function AtlasItemAgendaModal({ list, item, people, onClose, onSaved, onError }: {
  list: AtlasList; item: AtlasListItem; people: Person[]; onClose: () => void
  onSaved: () => void; onError: (message: string) => void
}) {
  const [title, setTitle] = useState(item.title)
  const [notes, setNotes] = useState(item.notes)
  const [dueAt, setDueAt] = useState<string | null>(item.due_at)
  const [allDay, setAllDay] = useState(item.is_all_day)
  const [assignees, setAssignees] = useState<number[]>(item.assigned_to_person_ids)
  const [saving, setSaving] = useState(false)
  const isChecklist = list.list_type !== 'grocery'
  const save = async () => {
    if (!title.trim()) return
    setSaving(true)
    try {
      await api.updateItem(list.id, item.id, {
        title: title.trim(), notes, due_at: dueAt, is_all_day: allDay,
        ...(isChecklist ? { assigned_to_person_ids: assignees } : {}),
      })
      onSaved()
    } catch (error) { onError(errMsg(error)) } finally { setSaving(false) }
  }
  return <Modal title="Edit item" onClose={onClose} footer={<><Button variant="ghost" size="sm" onClick={onClose}>Cancel</Button><Button size="sm" onClick={save} loading={saving} disabled={!title.trim()}>Save</Button></>}>
    <div className="space-y-3">
      <Field label="Title"><Input value={title} onChange={event => setTitle(event.target.value)} autoFocus /></Field>
      <Field label="Due"><DateTimeField value={dueAt} allDay={allDay} onChange={({ value, allDay: nextAllDay }) => { setDueAt(value); setAllDay(nextAllDay) }} /></Field>
      {isChecklist && (
        <Field label="Assigned to"><AssigneeSelect people={people} value={assignees} onChange={value => setAssignees(value || [])} /></Field>
      )}
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
    {!rows.length ? <EmptyState icon="🎂" title="No birthdays yet" hint="Add friends and relatives here, or add a household member's birth date in user management. Pet birthdays appear automatically on the Calendar." /> : <div className="grid gap-3 lg:grid-cols-2">{rows.map(row => <Card key={row.id}><div className="flex items-center justify-between gap-3"><div><h3 className="font-bold text-ink">{row.name}</h3><p className="text-sm text-muted">🎂 {new Date(`${row.dob}T00:00:00`).toLocaleDateString(undefined, { day: 'numeric', month: 'long', year: 'numeric' })}{row.relationship ? ` · ${row.relationship}` : ''}</p></div>{row.contact && <DeleteAction onClick={() => remove(row.contact!)} label={row.name} />}</div></Card>)}</div>}
  </div>
}

// ---------------------------------------------------------------------------
// Atlas page
// ---------------------------------------------------------------------------

type Tab = 'grocery' | 'todos' | 'lists' | 'agenda' | 'schedule' | 'people'

export function AtlasPage() {
  const { user } = useAuth()
  const [lists, setLists] = useState<AtlasList[]>([])
  const [groceryList, setGroceryList] = useState<AtlasList | null>(null)
  const [todoLists, setTodoLists] = useState<AtlasList[]>([])
  const atlasTabs: TabDef<Tab>[] = [
    { key: 'grocery', label: 'grocery' },
    { key: 'todos', label: 'to-dos' },
    { key: 'lists', label: 'lists & notes' },
    { key: 'agenda', label: 'agenda' },
    { key: 'schedule', label: 'appointments & events' },
    { key: 'people', label: 'people & birthdays' },
  ]
  const tabsState = useCustomisableTabs<Tab>('atlas', atlasTabs)
  const { tab, setTab } = tabsState
  const [people, setPeople] = useState<Person[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useUrlQueryState()
  const [results, setResults] = useState<AtlasSearchResults | null>(null)
  // docs/36 §6.3: opening a checklist should be a focused screen on phone, not one card in an
  // already-tall stack of every list's full contents — desktop's grid is untouched.
  const [openListId, setOpenListId] = useState<number | null>(null)
  const [searchParams] = useSearchParams()
  const focusedListId = Number(searchParams.get('list') || 0)
  const focusedItemId = Number(searchParams.get('item') || 0)

  const refreshGrocery = () => api.getGrocery().then(setGroceryList).catch(e => setError(errMsg(e)))
  const refreshTodoLists = () => api.getTodoLists().then(setTodoLists).catch(e => setError(errMsg(e)))
  const refreshLists = () => api.getLists().then(setLists).catch(e => setError(errMsg(e)))

  useEffect(() => {
    Promise.all([refreshLists(), refreshGrocery(), refreshTodoLists()]).finally(() => setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  useEffect(() => { api.getPeople().then(setPeople).catch(() => {}) }, [])

  const checklistLists = lists.filter(l => l.list_type === 'checklist' || l.list_type === 'general')

  // A deep link may name only the item (a calendar entry knows the record it came from, not
  // which list holds it). Resolve the owning list from what is already loaded, so `?item=` alone
  // still lands on the right tab instead of the default one.
  const resolvedListId = focusedListId || (focusedItemId
    ? [groceryList, ...todoLists, ...checklistLists].find(
        list => list?.items?.some(item => item.id === focusedItemId),
      )?.id ?? 0
    : 0)

  useEffect(() => {
    if (loading || !resolvedListId) return
    const focusedListId = resolvedListId
    if (groceryList && focusedListId === groceryList.id) { setTab('grocery'); return }
    if (todoLists.some(l => l.id === focusedListId)) { setTab('todos'); return }
    const focusedList = checklistLists.find(list => list.id === focusedListId)
    if (focusedList) {
      setTab('lists')
      setOpenListId(focusedListId)
      window.setTimeout(() => {
        document.getElementById(focusedItemId ? `atlas-item-${focusedItemId}` : `atlas-list-${focusedListId}`)
          ?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      }, 0)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resolvedListId, focusedItemId, loading, groceryList, todoLists, checklistLists, setTab])

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

  const capture = async (kind: CaptureKind, text: string, listId: number | null) => {
    try {
      if (kind === 'note') {
        await api.createNote({ title: text, visibility: 'household' })
        setTab('lists')
      } else if (kind === 'grocery') {
        await api.addGroceryItem({ title: text })
        await refreshGrocery()
        setTab('grocery')
      } else if (kind === 'todo' && listId != null) {
        await api.createItem(listId, { title: text })
        await refreshTodoLists()
        setTab('todos')
      }
    } catch (e) {
      setError(errMsg(e))
    }
  }

  return (
    <div className="flex flex-col gap-4 sm:gap-5">
      <div className="hidden sm:block">
        <PageHeader title="Atlas" icon="🗒" />
      </div>

      <CaptureBar todoLists={todoLists} onCapture={capture} />

      <SearchField
        value={query}
        onChange={e => setQuery(e.target.value)}
        onClear={() => setQuery('')}
        placeholder="Search to-dos, checklists, notes, grocery…"
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
          <CustomisableTabs state={tabsState} label="Atlas" className="w-fit" />

          {tab === 'grocery' ? (
            <GroceryTab groceryList={groceryList} onError={setError} />
          ) : tab === 'todos' ? (
            <TodoTab todoLists={todoLists} focusedListId={resolvedListId} onRefresh={refreshTodoLists} onError={setError} />
          ) : tab === 'lists' ? (
            loading ? (
              <div className="h-32 rounded-2xl bg-sunken animate-pulse" />
            ) : (
              <ListsAndNotesTab
                checklistLists={checklistLists}
                people={people}
                defaultAssignee={defaultAssignee}
                focusedListId={resolvedListId}
                focusedItemId={focusedItemId}
                onOpenList={setOpenListId}
                onListCreated={list => setLists(prev => [list, ...prev])}
                onListDeleted={id => setLists(prev => prev.filter(l => l.id !== id))}
                onError={setError}
              />
            )
          ) : tab === 'agenda' ? (
            <AgendaTab people={people} lists={lists} defaultAssignee={defaultAssignee} onError={setError} onListsChanged={refreshLists} />
          ) : tab === 'schedule' ? (
            <AppointmentsEventsTab people={people} defaultAssignee={defaultAssignee} onError={setError} />
          ) : (
            <PeopleBirthdaysTab people={people} onError={setError} />
          )}
        </>
      )}

      {openListId !== null && (() => {
        const list = checklistLists.find(l => l.id === openListId)
        if (!list) return null
        return (
          <Modal title={list.title} onClose={() => setOpenListId(null)} size="full">
            <ListCard
              list={list}
              people={people}
              defaultAssignee={defaultAssignee}
              focusedItemId={list.id === resolvedListId ? focusedItemId : undefined}
              onDeleted={id => { setLists(prev => prev.filter(l => l.id !== id)); setOpenListId(null) }}
              onError={setError}
            />
          </Modal>
        )
      })()}
    </div>
  )
}
