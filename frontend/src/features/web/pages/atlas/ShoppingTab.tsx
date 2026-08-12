import { useState } from 'react'
import { api } from '../../../../api/client'
import type { AtlasList, AtlasListItem, Person } from '../../../../api/types'
import { AssigneeSelect } from '../../../../components/AssigneeSelect'
import { Badge } from '../../../../components/Badge'
import { Button } from '../../../../components/Button'
import { Card } from '../../../../components/Card'
import { confirmDialog } from '../../../../components/Dialogs'
import { EmptyState } from '../../../../components/EmptyState'
import { Field, Input, Select } from '../../../../components/Field'
import { DeleteAction, EditAction } from '../../../../components/RowActions'

const errMsg = (error: unknown) => (error instanceof Error ? error.message : 'Something went wrong.')

type Priority = '' | 'low' | 'medium' | 'high'
const PRIORITIES: Priority[] = ['', 'low', 'medium', 'high']
const PRIORITY_LABEL: Record<Priority, string> = { '': 'No priority', low: 'Low', medium: 'Medium', high: 'High' }

const EMPTY_FORM = {
  title: '', url: '', image_url: '', retailer: '', unit_price: '', currency: 'AUD',
  quantity: '1', priority: '' as Priority, assignee: [] as number[], price_watch_enabled: false,
}

function money(value: string | null, currency: string) {
  if (!value) return null
  const n = Number(value)
  if (!Number.isFinite(n)) return null
  try {
    return new Intl.NumberFormat(undefined, { style: 'currency', currency: currency || 'AUD' }).format(n)
  } catch {
    return `${currency} ${n.toFixed(2)}`
  }
}

// ---------------------------------------------------------------------------
// One shopping-list item: link-import, price, priority — the same shape as a
// room-project shopping option (RoomPlanProduct), but attached directly to an
// AtlasListItem since a shopping-list entry is a single decision, not a set
// of alternatives to compare.
// ---------------------------------------------------------------------------

function ShoppingItemRow({ item, listId, people, onSaved, onDeleted, onError }: {
  item: AtlasListItem
  listId: number
  people: Person[]
  onSaved: (item: AtlasListItem) => void
  onDeleted: (id: number) => void
  onError: (message: string) => void
}) {
  const [editing, setEditing] = useState(false)
  const [busy, setBusy] = useState(false)

  const toggle = async () => {
    setBusy(true)
    try {
      const updated = item.is_complete ? await api.uncompleteItem(listId, item.id) : await api.completeItem(listId, item.id)
      onSaved(updated)
    } catch (error) { onError(errMsg(error)) } finally { setBusy(false) }
  }

  const remove = async () => {
    if (!(await confirmDialog({ title: `Delete "${item.title}"?`, confirmLabel: 'Delete' }))) return
    try { await api.deleteItem(listId, item.id); onDeleted(item.id) } catch (error) { onError(errMsg(error)) }
  }

  const assignees = item.assigned_to_person_ids.map(id => people.find(p => p.id === id)).filter((p): p is Person => Boolean(p))
  const price = money(item.unit_price, item.currency)

  if (editing) {
    return (
      <Card>
        <ShoppingItemForm
          listId={listId}
          people={people}
          initial={item}
          onSaved={updated => { onSaved(updated); setEditing(false) }}
          onCancel={() => setEditing(false)}
          onError={onError}
        />
      </Card>
    )
  }

  return (
    <Card className="group">
      <div className="flex items-start gap-3">
        <button
          onClick={toggle}
          disabled={busy}
          aria-label={item.is_complete ? 'Mark not bought' : 'Mark bought'}
          className={`mt-0.5 grid h-6 w-6 flex-shrink-0 place-items-center rounded-full border-2 transition-all ${
            item.is_complete ? 'bg-success border-success text-white' : 'border-line-strong hover:border-success'
          }`}
        >
          {item.is_complete && <span className="text-xs">✓</span>}
        </button>

        {item.cached_image_url && (
          <img src={item.cached_image_url} alt="" className="h-12 w-12 flex-shrink-0 rounded-lg object-cover bg-sunken" />
        )}

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className={`font-medium ${item.is_complete ? 'line-through text-muted' : 'text-ink'}`}>
              {item.quantity && <span className="mr-1 text-muted-strong">{item.quantity}×</span>}
              {item.title}
            </span>
            {item.priority === 'high' && <Badge tone="danger">High priority</Badge>}
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted">
            {price && <span className="font-semibold text-muted-strong">{price}</span>}
            {item.retailer && <span>{item.retailer}</span>}
            {item.product_url && (
              <a href={item.product_url} target="_blank" rel="noreferrer" className="text-primary hover:underline">
                Open link ↗
              </a>
            )}
            {item.price_watch?.is_active && <span className="font-semibold text-success">Price watch on</span>}
            {assignees.length > 0 && (
              <span className="flex items-center gap-1">
                <span className="h-2 w-2 rounded-full" style={{ backgroundColor: assignees[0].colour || 'var(--hs-muted)' }} />
                {assignees[0].preferred_name || assignees[0].display_name}
                {assignees.length > 1 && ` +${assignees.length - 1}`}
              </span>
            )}
          </div>
        </div>

        <div className="flex flex-shrink-0 items-center gap-1 opacity-100 transition-opacity sm:opacity-0 sm:group-hover:opacity-100 sm:group-focus-within:opacity-100">
          <EditAction onClick={() => setEditing(true)} label={item.title} />
          <DeleteAction onClick={remove} label={item.title} />
        </div>
      </div>
    </Card>
  )
}

function ShoppingItemForm({ listId, people, initial, onSaved, onCancel, onError }: {
  listId: number
  people: Person[]
  initial?: AtlasListItem
  onSaved: (item: AtlasListItem) => void
  onCancel: () => void
  onError: (message: string) => void
}) {
  const [form, setForm] = useState(() => initial ? {
    title: initial.title, url: initial.product_url, image_url: initial.source_image_url,
    retailer: initial.retailer, unit_price: initial.unit_price ?? '', currency: initial.currency || 'AUD',
    quantity: initial.quantity || '1', priority: initial.priority, assignee: initial.assigned_to_person_ids,
    price_watch_enabled: Boolean(initial.price_watch?.is_active),
  } : EMPTY_FORM)
  const [previewing, setPreviewing] = useState(false)
  const [saving, setSaving] = useState(false)

  const fillFromLink = async () => {
    if (!form.url.trim()) return
    setPreviewing(true)
    try {
      const preview = await api.previewProductLink(form.url.trim())
      setForm(current => ({
        ...current,
        title: current.title.trim() ? current.title : preview.title,
        url: preview.source_url,
        image_url: current.image_url || preview.image_url,
        retailer: current.retailer.trim() ? current.retailer : preview.retailer,
        unit_price: current.unit_price || preview.price || '',
        currency: preview.currency || current.currency,
      }))
      if (preview.warnings.length) onError(preview.warnings.join(' '))
    } catch (error) {
      onError(`${errMsg(error)} You can still enter the item manually.`)
    } finally { setPreviewing(false) }
  }

  const save = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!form.title.trim()) return
    setSaving(true)
    const payload = {
      title: form.title.trim(), quantity: form.quantity.trim(), priority: form.priority,
      product_url: form.url.trim(), source_image_url: form.image_url.trim(), retailer: form.retailer.trim(),
      unit_price: form.unit_price.trim() || null, currency: form.currency,
      assigned_to_person_ids: form.assignee, cache_image: Boolean(form.image_url.trim()),
      price_watch_enabled: form.price_watch_enabled,
    }
    try {
      const saved = initial ? await api.updateItem(listId, initial.id, payload) : await api.createItem(listId, payload)
      onSaved(saved)
      if (!initial) setForm(EMPTY_FORM)
    } catch (error) { onError(errMsg(error)) } finally { setSaving(false) }
  }

  return (
    <form onSubmit={save} className="grid gap-2 sm:grid-cols-2">
      <div className="sm:col-span-2">
        <Field label="What is it?">
          <Input autoFocus value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} placeholder="Vacuum cleaner" />
        </Field>
      </div>
      <div className="sm:col-span-2">
        <Field label="Link to the item" hint="Paste a shop link and HomeStack will fill the details it can find.">
          <div className="flex gap-2">
            <Input type="url" value={form.url} onChange={e => setForm(f => ({ ...f, url: e.target.value }))} placeholder="https://…" />
            <Button type="button" size="sm" variant="secondary" loading={previewing} disabled={!form.url.trim()} onClick={fillFromLink}>Fill</Button>
          </div>
        </Field>
      </div>
      <Field label="Image link" hint="Right-click the product photo → Copy image address">
        <Input type="url" value={form.image_url} onChange={e => setForm(f => ({ ...f, image_url: e.target.value }))} placeholder="https://…/photo.jpg" />
      </Field>
      <Field label="Shop">
        <Input value={form.retailer} onChange={e => setForm(f => ({ ...f, retailer: e.target.value }))} placeholder="Optional" />
      </Field>
      <Field label="Price">
        <Input type="number" min="0" step="0.01" value={form.unit_price} onChange={e => setForm(f => ({ ...f, unit_price: e.target.value }))} placeholder="0.00" />
      </Field>
      <Field label="Qty">
        <Input value={form.quantity} onChange={e => setForm(f => ({ ...f, quantity: e.target.value }))} placeholder="1" />
      </Field>
      <Field label="Priority">
        <Select value={form.priority} onChange={e => setForm(f => ({ ...f, priority: e.target.value as Priority }))}>
          {PRIORITIES.map(p => <option key={p} value={p}>{PRIORITY_LABEL[p]}</option>)}
        </Select>
      </Field>
      <Field label="Assigned to">
        <AssigneeSelect people={people} value={form.assignee} onChange={value => setForm(f => ({ ...f, assignee: value || [] }))} />
      </Field>
      <div className="flex flex-wrap items-center gap-2 sm:col-span-2">
        <Button type="submit" size="sm" loading={saving} disabled={!form.title.trim()}>{initial ? 'Save item' : 'Add item'}</Button>
        <Button type="button" size="sm" variant="ghost" onClick={onCancel}>Cancel</Button>
        <label className="ml-auto flex min-h-10 items-center gap-2 text-xs font-semibold text-muted-strong">
          <input type="checkbox" checked={form.price_watch_enabled} onChange={e => setForm(f => ({ ...f, price_watch_enabled: e.target.checked }))} />
          Notify me if the price drops
        </label>
      </div>
    </form>
  )
}

// ---------------------------------------------------------------------------
// One shopping list
// ---------------------------------------------------------------------------

function ShoppingListCard({ list, people, onDeleted, onError }: {
  list: AtlasList
  people: Person[]
  onDeleted: (id: number) => void
  onError: (message: string) => void
}) {
  const [items, setItems] = useState<AtlasListItem[]>(list.items ?? [])
  const [adding, setAdding] = useState(false)
  const [showBought, setShowBought] = useState(false)

  const pending = items.filter(i => !i.is_complete)
  const bought = items.filter(i => i.is_complete)

  const deleteList = async () => {
    if (!(await confirmDialog({ title: `Delete "${list.title}"?`, confirmLabel: 'Delete' }))) return
    try { await api.deleteList(list.id); onDeleted(list.id) } catch (error) { onError(errMsg(error)) }
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <div>
          <h3 className="font-bold text-ink">{list.title}</h3>
          <span className="text-xs text-muted">{pending.length > 0 ? `${pending.length} to buy` : bought.length > 0 ? 'all bought ✓' : 'Nothing here yet'}</span>
        </div>
        <div className="flex items-center gap-2">
          <Button size="sm" onClick={() => setAdding(v => !v)}>{adding ? 'Close' : '+ Add item'}</Button>
          <DeleteAction onClick={deleteList} label={list.title} />
        </div>
      </div>

      {adding && (
        <Card>
          <ShoppingItemForm
            listId={list.id}
            people={people}
            onSaved={item => { setItems(prev => [...prev, item]) }}
            onCancel={() => setAdding(false)}
            onError={onError}
          />
        </Card>
      )}

      {items.length === 0 && !adding ? (
        <EmptyState icon="🛍️" title="Nothing on this list yet" hint="Add something with a link, price and priority — or just a name." />
      ) : (
        <div className="flex flex-col gap-2">
          {pending.map(item => (
            <ShoppingItemRow
              key={item.id} item={item} listId={list.id} people={people}
              onSaved={updated => setItems(prev => prev.map(i => i.id === updated.id ? updated : i))}
              onDeleted={id => setItems(prev => prev.filter(i => i.id !== id))}
              onError={onError}
            />
          ))}
          {bought.length > 0 && (
            <div>
              <button onClick={() => setShowBought(v => !v)} className="flex items-center gap-1 py-1.5 text-xs font-semibold text-muted hover:text-ink transition-colors">
                <span className="w-3 inline-block">{showBought ? '▾' : '▸'}</span>
                {bought.length} bought
              </button>
              {showBought && (
                <div className="flex flex-col gap-2 mt-1">
                  {bought.map(item => (
                    <ShoppingItemRow
                      key={item.id} item={item} listId={list.id} people={people}
                      onSaved={updated => setItems(prev => prev.map(i => i.id === updated.id ? updated : i))}
                      onDeleted={id => setItems(prev => prev.filter(i => i.id !== id))}
                      onError={onError}
                    />
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Shopping tab
// ---------------------------------------------------------------------------

export function ShoppingTab({ lists, people, onError, onListCreated, onListDeleted }: {
  lists: AtlasList[]
  people: Person[]
  onError: (message: string) => void
  onListCreated: (list: AtlasList) => void
  onListDeleted: (id: number) => void
}) {
  const shoppingLists = lists.filter(l => l.list_type === 'shopping')
  const [creating, setCreating] = useState(false)
  const [title, setTitle] = useState('')
  const [busy, setBusy] = useState(false)

  const create = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!title.trim()) return
    setBusy(true)
    try {
      const list = await api.createList({ title: title.trim(), list_type: 'shopping' })
      const full = await api.getList(list.id)
      onListCreated(full)
      setTitle(''); setCreating(false)
    } catch (error) { onError(errMsg(error)) } finally { setBusy(false) }
  }

  return (
    <div className="flex flex-col gap-5">
      {creating ? (
        <form onSubmit={create} className="flex flex-col gap-2 rounded-2xl border border-line bg-surface p-3 sm:flex-row">
          <Input value={title} onChange={e => setTitle(e.target.value)} placeholder="Shopping list name…" className="flex-1" autoFocus />
          <div className="flex gap-2">
            <Button type="button" variant="ghost" onClick={() => { setCreating(false); setTitle('') }} className="flex-1 sm:flex-none">Cancel</Button>
            <Button type="submit" loading={busy} disabled={!title.trim()} className="flex-1 sm:flex-none">Create</Button>
          </div>
        </form>
      ) : (
        <Button size="sm" onClick={() => setCreating(true)} className="self-start">+ New shopping list</Button>
      )}

      {shoppingLists.length === 0 ? (
        <EmptyState
          icon="🛍️"
          title="No shopping lists yet"
          hint="Somewhere for ordinary household items — a vacuum cleaner, a new lamp — that aren't tied to a room project or a personal wish."
        />
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {shoppingLists.map(list => (
            <ShoppingListCard key={list.id} list={list} people={people} onDeleted={onListDeleted} onError={onError} />
          ))}
        </div>
      )}
    </div>
  )
}
