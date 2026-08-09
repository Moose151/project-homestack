import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { api } from '../../../api/client'
import type {
  Person, RoomAreaType, RoomDetailResponse, RoomItemPriority, RoomItemStatus,
  RoomItemType, RoomPlanItem,
} from '../../../api/types'
import { AssigneeSelect } from '../../../components/AssigneeSelect'
import { Badge, type BadgeTone } from '../../../components/Badge'
import { Button } from '../../../components/Button'
import { Card } from '../../../components/Card'
import { EmptyState } from '../../../components/EmptyState'
import { Field, Input, Select, Textarea, fieldClass } from '../../../components/Field'
import { PageHeader } from '../../../components/PageHeader'
import { useAuth } from '../../auth/AuthContext'

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
  title: '', item_type: 'purchase' as RoomItemType, status: 'planned' as RoomItemStatus,
  priority: 'medium' as RoomItemPriority, description: '', quantity: '1',
  estimated_unit_cost: '', actual_cost: '', link_url: '', notes: '',
  assigned_to_person_id: null as number | null,
}

export function HomesteadRoomPage() {
  const { roomId } = useParams()
  const id = Number(roomId)
  const navigate = useNavigate()
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
    if (!confirm(`Delete "${data.room.name}" and all of its plan items?`)) return
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
      title: item.title, item_type: item.item_type, status: item.status,
      priority: item.priority, description: item.description, quantity: item.quantity,
      estimated_unit_cost: item.estimated_unit_cost, actual_cost: item.actual_cost ?? '',
      link_url: item.link_url, notes: item.notes,
      assigned_to_person_id: item.assigned_to_person_id,
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
    if (!confirm(`Delete "${item.title}"?`)) return
    try { await api.deleteRoomItem(id, item.id); await load() } catch (e) { setError(errMsg(e)) }
  }

  if (loading) return <div className="h-64 rounded-2xl bg-sunken animate-pulse" />
  if (error && !data.room.id) return (
    <Card><p className="text-danger">{error}</p><Link to="/homestead?tab=rooms" className="mt-3 inline-block text-primary">← Back to rooms</Link></Card>
  )

  const canEdit = Boolean(user && user.role !== 'guest' && !user.is_child_account)
  const canDelete = user?.role === 'admin' || user?.role === 'manager'

  const itemCard = (item: RoomPlanItem) => {
    const person = people.find(row => row.id === item.assigned_to_person_id)
    return (
      <div key={item.id} className="group rounded-xl border border-line bg-surface p-3">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="font-semibold text-ink">{item.title}</h3>
              <Badge tone={STATUS_TONE[item.status]}>{cap(item.status)}</Badge>
              {item.priority === 'high' && <Badge tone="danger">High</Badge>}
            </div>
            {item.description && <p className="mt-1 whitespace-pre-wrap text-sm text-muted-strong">{item.description}</p>}
            <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
              <span>{Number(item.quantity).toLocaleString()} × {money(item.estimated_unit_cost)} = <strong className="text-ink">{money(item.estimated_total)}</strong></span>
              {item.actual_cost !== null && <span>Actual <strong className="text-ink">{money(item.actual_cost)}</strong></span>}
              {person && <span>👤 {person.preferred_name || person.display_name}</span>}
              {item.link_url && <a href={item.link_url} target="_blank" rel="noreferrer" className="text-primary hover:underline">Open link ↗</a>}
            </div>
            {item.notes && <p className="mt-2 whitespace-pre-wrap text-xs text-muted">{item.notes}</p>}
          </div>
          <div className="flex flex-wrap items-center gap-1">
            {canEdit && item.status !== 'completed' && item.status !== 'archived' && <Button size="sm" variant="secondary" onClick={() => setStatus(item, 'completed')}>Complete</Button>}
            {canEdit && item.status === 'completed' && <Button size="sm" variant="ghost" onClick={() => setStatus(item, 'planned')}>Reopen</Button>}
            {canEdit && item.status !== 'archived' && <Button size="sm" variant="ghost" onClick={() => setStatus(item, 'archived')}>Archive</Button>}
            {canEdit && item.status === 'archived' && <Button size="sm" variant="ghost" onClick={() => setStatus(item, 'planned')}>Restore</Button>}
            {canEdit && <Button size="sm" variant="ghost" onClick={() => startEdit(item)}>Edit</Button>}
            {canDelete && <button onClick={() => removeItem(item)} className="rounded-lg px-2 py-1 text-xs text-muted hover:text-danger" aria-label="Delete item">✕</button>}
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
        <Card><p className="text-2xl font-extrabold text-ink">{money(data.summary.remaining_estimated_cost)}</p><p className="text-sm text-muted">Remaining estimate</p><p className="mt-1 text-xs text-muted">{data.summary.active_count} active</p></Card>
        <Card><p className="text-2xl font-extrabold text-ink">{money(data.summary.completed_cost)}</p><p className="text-sm text-muted">Completed cost</p><p className="mt-1 text-xs text-muted">{data.summary.completed_count} completed</p></Card>
        <Card><p className="text-2xl font-extrabold text-ink">{money(data.summary.overall_cost)}</p><p className="text-sm text-muted">Overall room cost</p><p className="mt-1 text-xs text-muted">Archived excluded</p></Card>
      </div>

      {roomEditing ? (
        <Card title="Edit room or area">
          <form onSubmit={saveRoom} className="flex flex-col gap-3">
            <div className="grid gap-3 sm:grid-cols-[90px_1fr_180px]">
              <Field label="Icon"><Input value={roomForm.icon} onChange={e => setRoomForm(f => ({ ...f, icon: e.target.value }))} /></Field>
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
              <Field label="Type"><Select value={itemForm.item_type} onChange={e => setItemForm(f => ({ ...f, item_type: e.target.value as RoomItemType }))}>{ITEM_TYPES.map(type => <option key={type} value={type}>{cap(type)}</option>)}</Select></Field>
              <Field label="Status"><Select value={itemForm.status} onChange={e => setItemForm(f => ({ ...f, status: e.target.value as RoomItemStatus }))}>{ITEM_STATUSES.map(status => <option key={status} value={status}>{cap(status)}</option>)}</Select></Field>
              <Field label="Priority"><Select value={itemForm.priority} onChange={e => setItemForm(f => ({ ...f, priority: e.target.value as RoomItemPriority }))}>{PRIORITIES.map(priority => <option key={priority} value={priority}>{cap(priority)}</option>)}</Select></Field>
            </div>
            <Field label="Description"><Textarea rows={2} value={itemForm.description} onChange={e => setItemForm(f => ({ ...f, description: e.target.value }))} /></Field>
            <div className="grid gap-3 sm:grid-cols-3">
              <Field label="Quantity"><Input type="number" min="0.01" step="0.01" value={itemForm.quantity} onChange={e => setItemForm(f => ({ ...f, quantity: e.target.value }))} /></Field>
              <Field label="Estimated unit cost"><Input type="number" min="0" step="0.01" value={itemForm.estimated_unit_cost} onChange={e => setItemForm(f => ({ ...f, estimated_unit_cost: e.target.value }))} placeholder="0.00" /></Field>
              <Field label="Actual total cost"><Input type="number" min="0" step="0.01" value={itemForm.actual_cost} onChange={e => setItemForm(f => ({ ...f, actual_cost: e.target.value }))} placeholder="Optional" /></Field>
            </div>
            <Field label="Assigned to"><AssigneeSelect people={people} value={itemForm.assigned_to_person_id} onChange={value => setItemForm(f => ({ ...f, assigned_to_person_id: value }))} className={fieldClass} /></Field>
            <Field label="Product or reference link"><Input type="url" value={itemForm.link_url} onChange={e => setItemForm(f => ({ ...f, link_url: e.target.value }))} placeholder="https://…" /></Field>
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
