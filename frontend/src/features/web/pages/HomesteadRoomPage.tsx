import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'

import { api } from '../../../api/client'
import type {
  Person, RoomAreaType, RoomDetailResponse, RoomItemPriority, RoomItemStatus,
  RoomItemType, RoomPlanItem, RoomPlanMode,
} from '../../../api/types'
import { AssigneeSelect, assigneeLabel } from '../../../components/AssigneeSelect'
import { Badge, type BadgeTone } from '../../../components/Badge'
import { Button } from '../../../components/Button'
import { Card } from '../../../components/Card'
import { EmptyState } from '../../../components/EmptyState'
import { Field, Input, Select, Textarea, fieldClass } from '../../../components/Field'
import { PageHeader } from '../../../components/PageHeader'
import { DeleteAction, EditAction } from '../../../components/RowActions'
import { StatCard } from '../../../components/StatCard'
import { RoomIconSelect } from '../../../components/RoomIconSelect'
import { useAuth } from '../../auth/AuthContext'
import { confirmDialog, promptDialog } from '../../../components/Dialogs'

const ITEM_TYPES: RoomItemType[] = ['purchase', 'maintenance', 'renovation', 'upgrade']
const ITEM_STATUSES: RoomItemStatus[] = ['planned', 'in_progress', 'completed', 'archived']
const PRIORITIES: RoomItemPriority[] = ['low', 'medium', 'high']
const AREA_TYPES: RoomAreaType[] = ['interior', 'outdoor', 'utility', 'storage', 'other']
const cap = (value: string) => value.charAt(0).toUpperCase() + value.slice(1).replace(/_/g, ' ')
const money = (value: string | number) => Number(value || 0).toLocaleString(undefined, { style: 'currency', currency: 'AUD' })
const errMsg = (error: unknown) => error instanceof Error ? error.message : 'Something went wrong.'

const TYPE_ICON: Record<RoomItemType, string> = {
  purchase: '🛒', maintenance: '🔧', renovation: '🧱', upgrade: '✨',
}
const STATUS_TONE: Record<RoomItemStatus, BadgeTone> = {
  planned: 'neutral', in_progress: 'warning', completed: 'success', archived: 'neutral',
}

const EMPTY_PRODUCT = {
  title: '', url: '', image_url: '', source_image_url: '', retailer: '', quantity: '1', unit_cost: '',
  currency: 'AUD', cache_image: true, price_watch_enabled: false,
}

/**
 * The shopping list behind one room job.
 *
 * A job used to hold a single link, which could not represent the two or three options a
 * household is actually comparing. Each option carries what it is, where to buy it, what it
 * costs and a picture — the picture as a URL, so adding one is a copy-paste from a retailer
 * page rather than a download-then-upload round trip.
 */
function ProductList({ roomId, item, canEdit, canDelete, onChanged, onError }: {
  roomId: number
  item: RoomPlanItem
  canEdit: boolean
  canDelete: boolean
  onChanged: () => Promise<void> | void
  onError: (message: string) => void
}) {
  const [open, setOpen] = useState(false)
  const [adding, setAdding] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [form, setForm] = useState(EMPTY_PRODUCT)
  const [busy, setBusy] = useState(false)
  const [previewing, setPreviewing] = useState(false)
  // A remote image can 404 or be blocked; remember which ones failed so the card falls back
  // to a placeholder instead of showing a broken-image glyph.
  const [brokenImages, setBrokenImages] = useState<number[]>([])

  const products = item.products ?? []
  const isProject = item.plan_mode === 'project'
  // A project's rows are parts that are all needed; a single item's are alternatives.
  const noun = isProject ? 'Parts' : 'Options'
  const chosen = products.find(product => product.is_chosen)
  const cheapest = products.reduce<number | null>(
    (low, product) => (low === null || Number(product.total_cost) < low ? Number(product.total_cost) : low),
    null,
  )

  const summaryLine = isProject
    ? `${item.parts_bought_count} of ${item.parts_count} bought · ${money(item.spent_cost)} spent, ${money(item.remaining_cost)} to go`
    : chosen
      ? `Chosen: ${chosen.title} · ${money(chosen.total_cost)}`
      : `from ${money(cheapest ?? 0)}`

  const startAdd = () => { setEditingId(null); setForm(EMPTY_PRODUCT); setAdding(true); setOpen(true) }

  const startEdit = (productId: number) => {
    const product = products.find(row => row.id === productId)
    if (!product) return
    setEditingId(productId)
    setForm({
      title: product.title, url: product.url, image_url: product.image_url,
      source_image_url: product.source_image_url, retailer: product.retailer,
      quantity: product.quantity, unit_cost: product.unit_cost, currency: product.currency,
      cache_image: true, price_watch_enabled: Boolean(product.price_watch?.is_active),
    })
    setAdding(true)
  }

  const fillFromLink = async () => {
    if (!form.url.trim()) return
    setPreviewing(true)
    try {
      const preview = await api.previewProductLink(form.url.trim())
      setForm(current => ({
        ...current, title: current.title.trim() ? current.title : preview.title, url: preview.source_url,
        image_url: current.image_url || preview.image_url,
        source_image_url: current.source_image_url || preview.image_url,
        retailer: current.retailer.trim() ? current.retailer : preview.retailer,
        unit_cost: current.unit_cost || preview.price || '',
        currency: preview.currency || 'AUD', cache_image: true,
      }))
      if (preview.warnings.length) onError(preview.warnings.join(' '))
    } catch (error) {
      onError(`${errMsg(error)} You can still enter the product manually.`)
    } finally { setPreviewing(false) }
  }

  const save = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!form.title.trim()) return
    setBusy(true)
    const payload = {
      ...form,
      title: form.title.trim(),
      quantity: form.quantity || '1',
      unit_cost: form.unit_cost || '0.00',
    }
    try {
      if (editingId) await api.updateRoomProduct(roomId, item.id, editingId, payload)
      else await api.createRoomProduct(roomId, item.id, payload)
      setAdding(false); setEditingId(null); setForm(EMPTY_PRODUCT)
      await onChanged()
    } catch (error) { onError(errMsg(error)) } finally { setBusy(false) }
  }

  const choose = async (productId: number, isChosen: boolean) => {
    setBusy(true)
    try {
      await api.updateRoomProduct(roomId, item.id, productId, { is_chosen: isChosen })
      await onChanged()
    } catch (error) { onError(errMsg(error)) } finally { setBusy(false) }
  }

  /** Tick a part off. Asking the paid price here is the only moment the household knows it. */
  const setPurchased = async (productId: number, purchased: boolean) => {
    const product = products.find(row => row.id === productId)
    let actual_cost: string | null = null
    if (purchased && product) {
      const answer = await promptDialog({
        title: `What did "${product.title}" cost?`,
        message: 'Leave blank to use the estimate.',
        label: 'Actual cost', defaultValue: product.total_cost,
        inputMode: 'decimal', confirmLabel: 'Mark bought',
      })
      if (answer === null) return
      actual_cost = answer.trim() === '' ? null : answer.trim()
    }
    setBusy(true)
    try {
      await api.updateRoomProduct(roomId, item.id, productId, {
        is_purchased: purchased,
        actual_cost: purchased ? actual_cost : null,
      })
      await onChanged()
    } catch (error) { onError(errMsg(error)) } finally { setBusy(false) }
  }

  const remove = async (productId: number, title: string) => {
    if (!(await confirmDialog({ title: `Remove "${title}" from the options?`, confirmLabel: 'Remove' }))) return
    setBusy(true)
    try {
      await api.deleteRoomProduct(roomId, item.id, productId)
      await onChanged()
    } catch (error) { onError(errMsg(error)) } finally { setBusy(false) }
  }

  return (
    <div className="mt-3 border-t border-line pt-3">
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => setOpen(value => !value)}
          className="flex min-h-10 items-center gap-1.5 rounded-lg px-1.5 text-xs font-bold text-muted-strong hover:text-ink"
          aria-expanded={open}
        >
          <span aria-hidden>{open ? '▾' : '▸'}</span>
          {products.length === 0 ? noun : `${noun} (${products.length})`}
        </button>
        {products.length > 0 && <span className="text-xs text-muted">{summaryLine}</span>}
        {canEdit && open && !adding && (
          <Button size="sm" variant="ghost" onClick={startAdd} className="ml-auto">
            {isProject ? '+ Add part' : '+ Add option'}
          </Button>
        )}
      </div>

      {open && (
        <div className="mt-2 flex flex-col gap-2">
          {products.length === 0 && !adding && (
            <p className="text-xs text-muted">
              {isProject
                ? 'No parts yet. Add everything the project needs — each with its link, price and picture.'
                : 'No options yet. Add what you are considering — name, link, price and a picture.'}
            </p>
          )}

          {products.length > 0 && (
            <ul className="grid gap-2 sm:grid-cols-2">
              {products.map(product => {
                const imageBroken = brokenImages.includes(product.id)
                return (
                  <li
                    key={product.id}
                    className={`flex gap-2.5 rounded-xl border p-2 ${
                      (isProject ? product.is_purchased : product.is_chosen)
                        ? 'border-primary bg-primary-soft/40'
                        : 'border-line'
                    }`}
                  >
                    {/* Three distinct states. A picture that fails to load used to fall back to
                        the type icon, which looks exactly like "no picture set" — so a blocked
                        image read as a lost one. A broken link now says so and offers to open
                        the URL, since the usual cause is a shop that refuses hotlinking. */}
                    <div className="grid h-20 w-20 flex-shrink-0 place-items-center overflow-hidden rounded-lg border border-line bg-sunken">
                      {(product.cached_image_url || product.image_url || product.source_image_url) && !imageBroken ? (
                        <a href={product.url || product.source_image_url || product.image_url} target="_blank" rel="noreferrer noopener" className="block h-full w-full">
                          <img
                            src={product.cached_image_url || product.source_image_url || product.image_url}
                            alt={product.title}
                            loading="lazy"
                            referrerPolicy="no-referrer"
                            onError={() => setBrokenImages(current => [...current, product.id])}
                            className="h-full w-full object-cover"
                          />
                        </a>
                      ) : product.image_url || product.source_image_url ? (
                        <a
                          href={product.source_image_url || product.image_url}
                          target="_blank"
                          rel="noreferrer noopener"
                          title="This shop is blocking the picture. Open the image link to check it."
                          className="flex h-full w-full flex-col items-center justify-center gap-0.5 px-1 text-center text-muted hover:text-ink"
                        >
                          <span className="text-base" aria-hidden>🚫</span>
                          <span className="text-[9px] font-semibold leading-tight">Image blocked</span>
                        </a>
                      ) : (
                        <span className="text-xl" aria-hidden>{TYPE_ICON[item.item_type]}</span>
                      )}
                    </div>

                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-1.5">
                        <span className="truncate text-sm font-semibold text-ink">{product.title}</span>
                        {isProject
                          ? product.is_purchased && <Badge tone="success">Bought</Badge>
                          : product.is_chosen && <Badge tone="success">Chosen</Badge>}
                      </div>
                      <p className="text-xs text-muted">
                        {Number(product.quantity) !== 1 && `${Number(product.quantity).toLocaleString()} × `}
                        {money(product.unit_cost)}
                        {Number(product.quantity) !== 1 && ` = ${money(product.total_cost)}`}
                        {product.retailer && ` · ${product.retailer}`}
                        {isProject && product.is_purchased && product.actual_cost !== null
                          && ` · paid ${money(product.actual_cost)}`}
                      </p>
                      {product.price_watch?.is_active && <p className="mt-0.5 text-[10px] font-bold text-success">Watching for a price drop</p>}
                      <div className="mt-1 flex flex-wrap items-center gap-1">
                        {product.url && (
                          <a
                            href={product.url}
                            target="_blank"
                            rel="noreferrer noopener"
                            className="grid min-h-10 place-items-center rounded-lg px-1.5 text-xs font-semibold text-primary hover:underline"
                          >
                            Open ↗
                          </a>
                        )}
                        {canEdit && (
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() => (isProject
                              ? setPurchased(product.id, !product.is_purchased)
                              : choose(product.id, !product.is_chosen))}
                            className="grid min-h-10 place-items-center rounded-lg px-1.5 text-xs font-semibold text-muted hover:bg-sunken hover:text-ink disabled:opacity-40"
                          >
                            {isProject
                              ? (product.is_purchased ? 'Not bought' : 'Mark bought')
                              : (product.is_chosen ? 'Unchoose' : 'Choose')}
                          </button>
                        )}
                        {canEdit && <EditAction onClick={() => startEdit(product.id)} label={product.title} disabled={busy} />}
                        {canDelete && <DeleteAction onClick={() => remove(product.id, product.title)} label={product.title} disabled={busy} />}
                      </div>
                    </div>
                  </li>
                )
              })}
            </ul>
          )}

          {adding && (
            <form onSubmit={save} className="grid gap-2 rounded-xl bg-sunken p-3 sm:grid-cols-2">
              <div className="sm:col-span-2">
                <Field label="What is it?">
                  <Input
                    autoFocus
                    value={form.title}
                    onChange={event => setForm(f => ({ ...f, title: event.target.value }))}
                    placeholder="Corner sofa, oak finish"
                  />
                </Field>
              </div>
              <Field label="Link to the item" hint="Paste a shop link and HomeStack will fill the details it can find.">
                <div className="flex gap-2">
                  <Input type="url" value={form.url} onChange={event => setForm(f => ({ ...f, url: event.target.value }))} placeholder="https://…" />
                  <Button type="button" size="sm" variant="secondary" loading={previewing} disabled={!form.url.trim()} onClick={fillFromLink}>Fill</Button>
                </div>
              </Field>
              <Field label="Image link" hint="Right-click the product photo → Copy image address">
                <Input
                  type="url"
                  value={form.image_url}
                  onChange={event => setForm(f => ({ ...f, image_url: event.target.value, source_image_url: event.target.value }))}
                  placeholder="https://…/photo.jpg"
                />
              </Field>
              <Field label="Shop">
                <Input
                  value={form.retailer}
                  onChange={event => setForm(f => ({ ...f, retailer: event.target.value }))}
                  placeholder="Optional"
                />
              </Field>
              <div className="grid grid-cols-2 gap-2">
                <Field label="Price each">
                  <Input
                    type="number"
                    min="0"
                    step="0.01"
                    value={form.unit_cost}
                    onChange={event => setForm(f => ({ ...f, unit_cost: event.target.value }))}
                    placeholder="0.00"
                  />
                </Field>
                <Field label="Qty">
                  {/* step="any" rather than a fixed step: with min="0.01" the browser only
                      accepts min + n*step, so step="1" rejected 2 and snapped to 2.01, which
                      then priced the part at 2.01×. */}
                  <Input
                    type="number"
                    min="0.01"
                    step="any"
                    value={form.quantity}
                    onChange={event => setForm(f => ({ ...f, quantity: event.target.value }))}
                  />
                </Field>
              </div>
              <div className="flex gap-2 sm:col-span-2">
                <Button type="submit" size="sm" loading={busy} disabled={!form.title.trim()}>
                  {editingId ? 'Save option' : 'Add option'}
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  onClick={() => { setAdding(false); setEditingId(null) }}
                >
                  Cancel
                </Button>
                <label className="ml-auto flex min-h-10 items-center gap-2 text-xs font-semibold text-muted-strong">
                  <input type="checkbox" checked={form.price_watch_enabled} onChange={event => setForm(current => ({ ...current, price_watch_enabled: event.target.checked }))} />
                  Notify me if the price drops
                </label>
              </div>
            </form>
          )}
        </div>
      )}
    </div>
  )
}

const EMPTY_DETAIL: RoomDetailResponse = {
  room: {
    id: 0, name: '', area_type: 'interior', description: '', icon: '', colour: '#B0563C',
    display_order: 0, floorplan_data: {}, visibility: 'household',
    summary: { active_count: 0, completed_count: 0, archived_count: 0, remaining_estimated_cost: '0.00', completed_cost: '0.00', overall_cost: '0.00' },
    created_at: '', updated_at: '',
  },
  items: [],
  summary: { active_count: 0, completed_count: 0, archived_count: 0, remaining_estimated_cost: '0.00', completed_cost: '0.00', overall_cost: '0.00' },
}

const EMPTY_ITEM = {
  title: '', plan_mode: 'single' as RoomPlanMode,
  item_type: 'purchase' as RoomItemType, status: 'planned' as RoomItemStatus,
  priority: 'medium' as RoomItemPriority, description: '', quantity: '1',
  estimated_unit_cost: '', actual_cost: '', notes: '',
  assigned_to_person_ids: [] as number[],
}

export function HomesteadRoomPage() {
  const { roomId } = useParams()
  const id = Number(roomId)
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const focusedItemId = Number(searchParams.get('plan_item') || 0)
  const { user } = useAuth()
  const [data, setData] = useState<RoomDetailResponse>(EMPTY_DETAIL)
  const [people, setPeople] = useState<Person[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [roomEditing, setRoomEditing] = useState(false)
  const [roomSaving, setRoomSaving] = useState(false)
  const [itemOpen, setItemOpen] = useState(false)
  const [itemSaving, setItemSaving] = useState(false)
  const [editItemId, setEditItemId] = useState<number | null>(null)
  const [itemForm, setItemForm] = useState(EMPTY_ITEM)
  const [roomForm, setRoomForm] = useState({
    name: '', area_type: 'interior' as RoomAreaType, description: '', icon: '', colour: '#B0563C', display_order: 0,
  })

  const load = async () => {
    if (!Number.isInteger(id) || id <= 0) { setError('Room not found.'); setLoading(false); return }
    try {
      const result = await api.getRoom(id)
      setData(result)
      setRoomForm({
        name: result.room.name, area_type: result.room.area_type,
        description: result.room.description, icon: result.room.icon,
        colour: result.room.colour, display_order: result.room.display_order,
      })
    } catch (e) { setError(errMsg(e)) } finally { setLoading(false) }
  }

  useEffect(() => {
    void load()
    api.getPeople().then(setPeople).catch(() => {})
  }, [id])
  useEffect(() => {
    if (!loading && focusedItemId) window.setTimeout(() => document.getElementById(`homestead-plan-item-${focusedItemId}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' }), 0)
  }, [loading, focusedItemId])

  const grouped = useMemo(() => {
    const active = data.items.filter(item => item.status === 'planned' || item.status === 'in_progress')
    return {
      active,
      completed: data.items.filter(item => item.status === 'completed'),
      archived: data.items.filter(item => item.status === 'archived'),
    }
  }, [data.items])

  const saveRoom = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!roomForm.name.trim()) return
    setRoomSaving(true)
    try {
      await api.updateRoom(id, { ...roomForm, name: roomForm.name.trim() })
      setRoomEditing(false)
      await load()
    } catch (e) { setError(errMsg(e)) } finally { setRoomSaving(false) }
  }

  const removeRoom = async () => {
    if (!(await confirmDialog({ title: `Delete "${data.room.name}" and all of its plan items?`, confirmLabel: 'Delete' }))) return
    try { await api.deleteRoom(id); navigate('/homestead?tab=rooms') } catch (e) { setError(errMsg(e)) }
  }

  const startAdd = (type: RoomItemType = 'purchase') => {
    setEditItemId(null)
    setItemForm({ ...EMPTY_ITEM, item_type: type })
    setItemOpen(true)
  }

  const startEdit = (item: RoomPlanItem) => {
    setEditItemId(item.id)
    setItemForm({
      title: item.title, plan_mode: item.plan_mode, item_type: item.item_type, status: item.status,
      priority: item.priority, description: item.description, quantity: item.quantity,
      estimated_unit_cost: item.estimated_unit_cost, actual_cost: item.actual_cost ?? '',
      notes: item.notes,
      assigned_to_person_ids: item.assigned_to_person_ids,
    })
    setItemOpen(true)
  }

  const saveItem = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!itemForm.title.trim()) return
    setItemSaving(true)
    const payload = {
      ...itemForm,
      title: itemForm.title.trim(),
      quantity: itemForm.quantity || '1',
      estimated_unit_cost: itemForm.estimated_unit_cost || '0.00',
      actual_cost: itemForm.actual_cost || null,
    }
    try {
      if (editItemId) await api.updateRoomItem(id, editItemId, payload)
      else await api.createRoomItem(id, payload)
      setItemOpen(false)
      await load()
    } catch (e) { setError(errMsg(e)) } finally { setItemSaving(false) }
  }

  const setStatus = async (item: RoomPlanItem, status: RoomItemStatus) => {
    try { await api.updateRoomItem(id, item.id, { status }); await load() } catch (e) { setError(errMsg(e)) }
  }

  const removeItem = async (item: RoomPlanItem) => {
    if (!(await confirmDialog({ title: `Delete "${item.title}"?`, confirmLabel: 'Delete' }))) return
    try { await api.deleteRoomItem(id, item.id); await load() } catch (e) { setError(errMsg(e)) }
  }

  if (loading) return <div className="h-64 rounded-2xl bg-sunken animate-pulse" />
  if (error && !data.room.id) return (
    <Card><p className="text-danger">{error}</p><Link to="/homestead?tab=rooms" className="mt-3 inline-block text-primary">← Back to rooms</Link></Card>
  )

  const canEdit = Boolean(user && user.role !== 'guest' && !user.is_child_account)
  const canDelete = user?.role === 'admin' || user?.role === 'manager'

  const itemCard = (item: RoomPlanItem) => {
    const assigneeName = assigneeLabel(people, item.assigned_to_person_ids)
    return (
      <div key={item.id} id={`homestead-plan-item-${item.id}`} className={`group rounded-xl border bg-surface p-3 ${focusedItemId === item.id ? 'border-primary ring-2 ring-primary ring-offset-2 ring-offset-paper' : 'border-line'}`}>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="font-semibold text-ink">{item.title}</h3>
              <Badge tone={STATUS_TONE[item.status]}>{cap(item.status)}</Badge>
              {item.priority === 'high' && <Badge tone="danger">High</Badge>}
            </div>
            {item.description && <p className="mt-1 whitespace-pre-wrap text-sm text-muted-strong">{item.description}</p>}
            <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
              {item.plan_mode === 'project' ? (
                <span>
                  {item.parts_count} part{item.parts_count === 1 ? '' : 's'} ={' '}
                  <strong className="text-ink">{money(item.estimated_total)}</strong>
                </span>
              ) : (
                <span>{Number(item.quantity).toLocaleString()} × {money(item.estimated_unit_cost)} = <strong className="text-ink">{money(item.estimated_total)}</strong></span>
              )}
              {item.actual_cost !== null && <span>Actual <strong className="text-ink">{money(item.actual_cost)}</strong></span>}
              {item.assigned_to_person_ids.length > 0 && <span>👤 {assigneeName}</span>}
            </div>
            {item.notes && <p className="mt-2 whitespace-pre-wrap text-xs text-muted">{item.notes}</p>}
            <ProductList
              roomId={id}
              item={item}
              canEdit={canEdit}
              canDelete={canDelete}
              onChanged={load}
              onError={setError}
            />
          </div>
          <div className="flex flex-wrap items-center gap-1">
            {canEdit && item.status !== 'completed' && item.status !== 'archived' && <Button size="sm" variant="secondary" onClick={() => setStatus(item, 'completed')}>Complete</Button>}
            {canEdit && item.status === 'completed' && <Button size="sm" variant="ghost" onClick={() => setStatus(item, 'planned')}>Reopen</Button>}
            {canEdit && item.status !== 'archived' && <Button size="sm" variant="ghost" onClick={() => setStatus(item, 'archived')}>Archive</Button>}
            {canEdit && item.status === 'archived' && <Button size="sm" variant="ghost" onClick={() => setStatus(item, 'planned')}>Restore</Button>}
            {canEdit && <Button size="sm" variant="ghost" onClick={() => startEdit(item)}>Edit</Button>}
            {canDelete && <DeleteAction onClick={() => removeItem(item)} label={item.title} />}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-5">
      <Link to="/homestead?tab=rooms" className="text-sm text-muted hover:text-primary">← All rooms &amp; areas</Link>
      <PageHeader
        title={data.room.name}
        icon={data.room.icon || (data.room.area_type === 'outdoor' ? '🌿' : '🚪')}
        subtitle={data.room.description || `${cap(data.room.area_type)} room plan`}
        mobile="show"
      />

      {error && <div className="rounded-xl bg-danger-soft px-4 py-2.5 text-sm text-danger">{error}</div>}

      <div className="grid gap-3 sm:grid-cols-3">
        <StatCard label="Remaining estimate" value={money(data.summary.remaining_estimated_cost)} hint={`${data.summary.active_count} active`} />
        <StatCard label="Completed cost" value={money(data.summary.completed_cost)} hint={`${data.summary.completed_count} completed`} />
        <StatCard label="Overall room cost" value={money(data.summary.overall_cost)} hint="Archived excluded" />
      </div>

      {roomEditing ? (
        <Card title="Edit room or area">
          <form onSubmit={saveRoom} className="flex flex-col gap-3">
            <div className="grid gap-3 sm:grid-cols-[90px_1fr_180px]">
              <Field label="Icon"><RoomIconSelect value={roomForm.icon} onChange={icon => setRoomForm(f => ({ ...f, icon }))} className={fieldClass} /></Field>
              <Field label="Name"><Input value={roomForm.name} onChange={e => setRoomForm(f => ({ ...f, name: e.target.value }))} /></Field>
              <Field label="Type"><Select value={roomForm.area_type} onChange={e => setRoomForm(f => ({ ...f, area_type: e.target.value as RoomAreaType }))}>{AREA_TYPES.map(type => <option key={type} value={type}>{cap(type)}</option>)}</Select></Field>
            </div>
            <Field label="Description"><Textarea rows={2} value={roomForm.description} onChange={e => setRoomForm(f => ({ ...f, description: e.target.value }))} /></Field>
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Colour"><Input type="color" value={roomForm.colour} onChange={e => setRoomForm(f => ({ ...f, colour: e.target.value }))} /></Field>
              <Field label="Display order"><Input type="number" min="0" value={roomForm.display_order} onChange={e => setRoomForm(f => ({ ...f, display_order: Number(e.target.value) }))} /></Field>
            </div>
            <div className="flex justify-between gap-2">
              {canDelete ? <Button type="button" variant="danger" size="sm" onClick={removeRoom}>Delete room</Button> : <span />}
              <div className="flex gap-2"><Button type="button" variant="ghost" size="sm" onClick={() => setRoomEditing(false)}>Cancel</Button><Button type="submit" size="sm" loading={roomSaving}>Save room</Button></div>
            </div>
          </form>
        </Card>
      ) : canEdit ? (
        <div className="flex justify-between gap-3">
          <Button size="sm" onClick={() => startAdd()}>+ Add plan item</Button>
          <Button size="sm" variant="ghost" onClick={() => setRoomEditing(true)}>Edit room</Button>
        </div>
      ) : null}

      {itemOpen && (
        <Card title={editItemId ? 'Edit plan item' : 'Add plan item'}>
          <form onSubmit={saveItem} className="flex flex-col gap-3">
            <Input value={itemForm.title} onChange={e => setItemForm(f => ({ ...f, title: e.target.value }))} placeholder="What do you want to buy or do?" autoFocus />
            <div className="grid gap-3 sm:grid-cols-3">
              <Field label="What is this?" hint="A project's parts all add up; a single item's options are alternatives.">
                <div className="flex gap-1 rounded-xl bg-sunken p-1">
                  {([['single', 'Single item'], ['project', 'Project']] as const).map(([mode, label]) => (
                    <button
                      key={mode}
                      type="button"
                      onClick={() => setItemForm(f => ({ ...f, plan_mode: mode }))}
                      aria-pressed={itemForm.plan_mode === mode}
                      className={`min-h-10 flex-1 rounded-lg px-2 text-xs font-semibold transition-colors ${
                        itemForm.plan_mode === mode ? 'bg-raised text-ink shadow-soft' : 'text-muted hover:text-ink'
                      }`}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </Field>
              <Field label="Type"><Select value={itemForm.item_type} onChange={e => setItemForm(f => ({ ...f, item_type: e.target.value as RoomItemType }))}>{ITEM_TYPES.map(type => <option key={type} value={type}>{cap(type)}</option>)}</Select></Field>
              <Field label="Status"><Select value={itemForm.status} onChange={e => setItemForm(f => ({ ...f, status: e.target.value as RoomItemStatus }))}>{ITEM_STATUSES.map(status => <option key={status} value={status}>{cap(status)}</option>)}</Select></Field>
              <Field label="Priority"><Select value={itemForm.priority} onChange={e => setItemForm(f => ({ ...f, priority: e.target.value as RoomItemPriority }))}>{PRIORITIES.map(priority => <option key={priority} value={priority}>{cap(priority)}</option>)}</Select></Field>
            </div>
            <Field label="Description"><Textarea rows={2} value={itemForm.description} onChange={e => setItemForm(f => ({ ...f, description: e.target.value }))} /></Field>
            <div className="grid gap-3 sm:grid-cols-3">
              {itemForm.plan_mode === 'project' ? (
                <p className="text-xs text-muted sm:col-span-3">
                  A project costs the total of its parts, so there is nothing to type here —
                  add the parts below and the estimate follows them.
                </p>
              ) : (
                <>
                  <Field label="Quantity"><Input type="number" min="0.01" step="0.01" value={itemForm.quantity} onChange={e => setItemForm(f => ({ ...f, quantity: e.target.value }))} /></Field>
                  <Field label="Estimated unit cost"><Input type="number" min="0" step="0.01" value={itemForm.estimated_unit_cost} onChange={e => setItemForm(f => ({ ...f, estimated_unit_cost: e.target.value }))} placeholder="0.00" /></Field>
                  <Field label="Actual total cost"><Input type="number" min="0" step="0.01" value={itemForm.actual_cost} onChange={e => setItemForm(f => ({ ...f, actual_cost: e.target.value }))} placeholder="Optional" /></Field>
                </>
              )}
            </div>
            <Field label="Assigned to"><AssigneeSelect people={people} value={itemForm.assigned_to_person_ids} onChange={value => setItemForm(f => ({ ...f, assigned_to_person_ids: value }))} className={fieldClass} /></Field>
            <Field label="Notes"><Textarea rows={2} value={itemForm.notes} onChange={e => setItemForm(f => ({ ...f, notes: e.target.value }))} /></Field>
            <div className="flex justify-end gap-2"><Button type="button" variant="ghost" size="sm" onClick={() => setItemOpen(false)}>Cancel</Button><Button type="submit" size="sm" loading={itemSaving} disabled={!itemForm.title.trim()}>Save item</Button></div>
          </form>
        </Card>
      )}

      {grouped.active.length === 0 && grouped.completed.length === 0 && grouped.archived.length === 0 ? (
        <EmptyState icon="📝" title="Nothing planned for this room yet" hint="Add purchases, maintenance, renovations or upgrades and the room and household totals will update automatically." />
      ) : (
        <div className="flex flex-col gap-4">
          {ITEM_TYPES.map(type => {
            const items = grouped.active.filter(item => item.item_type === type)
            if (!items.length) return null
            const typeTotal = items.reduce((sum, item) => sum + Number(item.estimated_total), 0)
            return (
              <details key={type} open className="rounded-2xl border border-line bg-surface/40 p-3">
                <summary className="cursor-pointer list-none font-bold text-ink">
                  <span className="flex items-center justify-between gap-3"><span>{TYPE_ICON[type]} {cap(type)}s <span className="text-sm font-normal text-muted">({items.length})</span></span><span className="text-sm text-muted">{money(typeTotal)}</span></span>
                </summary>
                <div className="mt-3 flex flex-col gap-2">{items.map(itemCard)}</div>
              </details>
            )
          })}

          {grouped.completed.length > 0 && <details className="rounded-2xl border border-line p-3"><summary className="cursor-pointer font-bold text-ink">✓ Completed ({grouped.completed.length}) · {money(data.summary.completed_cost)}</summary><div className="mt-3 flex flex-col gap-2">{grouped.completed.map(itemCard)}</div></details>}
          {grouped.archived.length > 0 && <details className="rounded-2xl border border-line p-3"><summary className="cursor-pointer font-bold text-muted">Archived ({grouped.archived.length})</summary><div className="mt-3 flex flex-col gap-2">{grouped.archived.map(itemCard)}</div></details>}
        </div>
      )}
    </div>
  )
}
