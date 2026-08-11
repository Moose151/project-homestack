import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../../api/client'
import type {
  Appliance, Improvement, ImprovementStatus, MaintenanceTask, Person, Property,
  ServiceProvider, HomesteadSearchResults, InsurancePolicy, HouseholdCost,
  RoomAreaType, RoomListResponse, Pool, PoolReadingKey, PoolSanitiser, PoolStatus,
  PoolSurface, UtilityBill, UtilityPeriodPoint, UtilitySeries, UtilityType, UtilityUnit,
  WaterTest, WaterTestWrite,
} from '../../../api/types'
import { Card } from '../../../components/Card'
import { Button } from '../../../components/Button'
import { Field, Input, SearchField, Textarea, Select, fieldClass } from '../../../components/Field'
import { Tabs } from '../../../components/Tabs'
import { Badge, type BadgeTone } from '../../../components/Badge'
import { BarChart, type BarChartPoint } from '../../../components/BarChart'
import { PageHeader } from '../../../components/PageHeader'
import { EmptyState } from '../../../components/EmptyState'
import { Modal } from '../../../components/Modal'
import { DateTimeField } from '../../../components/DateTimeField'
import { AssigneeSelect, personIdForUser } from '../../../components/AssigneeSelect'
import { DeleteAction, EditAction } from '../../../components/RowActions'
import { StatCard } from '../../../components/StatCard'
import { RoomIconSelect } from '../../../components/RoomIconSelect'
import { SensitiveGate } from '../../../components/SensitiveGate'
import { useAuth } from '../../auth/AuthContext'
import { useStacks } from '../../stacks/StacksContext'
import { useUrlAction, useUrlQueryState, useUrlTab } from '../../../hooks/useUrlTab'
import { confirmDialog } from '../../../components/Dialogs'
import { HomeFloorPlan } from '../components/HomeFloorPlan'

const errMsg = (e: unknown) => (e instanceof Error ? e.message : 'Something went wrong.')
const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1).replace(/_/g, ' ')

// ---------------------------------------------------------------------------
// Shared option lists
// ---------------------------------------------------------------------------

const RECURRENCE = [
  { label: 'One-off', value: '' },
  { label: 'Weekly', value: 'FREQ=WEEKLY' },
  { label: 'Fortnightly', value: 'FREQ=WEEKLY;INTERVAL=2' },
  { label: 'Monthly', value: 'FREQ=MONTHLY' },
  { label: 'Every 3 months', value: 'FREQ=MONTHLY;INTERVAL=3' },
  { label: 'Every 6 months', value: 'FREQ=MONTHLY;INTERVAL=6' },
  { label: 'Yearly', value: 'FREQ=YEARLY' },
]
const recurrenceLabel = (rule: string) =>
  RECURRENCE.find(r => r.value === rule)?.label ?? 'Repeats'

const MAINT_CATS = ['heating', 'plumbing', 'electrical', 'safety', 'garden', 'exterior', 'cleaning', 'appliance', 'renewal', 'general']
const APPLIANCE_CATS = ['appliance', 'heating', 'kitchen', 'laundry', 'electrical', 'plumbing', 'security', 'outdoor', 'other']
const TRADES = ['plumber', 'electrician', 'gas_engineer', 'builder', 'gardener', 'cleaner', 'roofer', 'pest_control', 'handyman', 'other']
const IMPROVEMENT_STATUSES: ImprovementStatus[] = ['idea', 'planned', 'in_progress', 'on_hold', 'done', 'cancelled']

function dueLabel(iso: string | null): { text: string; tone: BadgeTone } | null {
  if (!iso) return null
  const d = new Date(iso)
  const diff = Math.round((d.getTime() - Date.now()) / 86400000)
  if (diff < 0) return { text: `${Math.abs(diff)}d overdue`, tone: 'danger' }
  if (diff === 0) return { text: 'Due today', tone: 'primary' }
  if (diff === 1) return { text: 'Tomorrow', tone: 'warning' }
  if (diff <= 30) return { text: `in ${diff}d`, tone: 'neutral' }
  return { text: d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }), tone: 'neutral' }
}

function warrantyLabel(iso: string | null): { text: string; tone: BadgeTone } | null {
  if (!iso) return null
  const d = new Date(iso)
  const diff = Math.round((d.getTime() - Date.now()) / 86400000)
  const on = d.toLocaleDateString(undefined, { month: 'short', year: 'numeric' })
  if (diff < 0) return { text: `expired ${on}`, tone: 'danger' }
  if (diff <= 60) return { text: `expires ${on}`, tone: 'warning' }
  return { text: `warranty to ${on}`, tone: 'success' }
}

const STATUS_TONE: Record<ImprovementStatus, BadgeTone> = {
  idea: 'neutral', planned: 'primary', in_progress: 'warning',
  on_hold: 'neutral', done: 'success', cancelled: 'neutral',
}
const money = (v: string | number) =>
  Number(v || 0).toLocaleString(undefined, { style: 'currency', currency: 'AUD' })
const POLICY_TYPES = ['building', 'contents', 'building_contents', 'landlord', 'mortgage_protection', 'other']
const COST_TYPES = ['rates', 'water', 'gas', 'electricity', 'mortgage', 'body_corporate', 'waste', 'internet', 'other']

// ---------------------------------------------------------------------------
// Overview tab — the property record + emergency info + at-a-glance
// ---------------------------------------------------------------------------

const EMPTY_PROPERTY = {
  name: 'Home', address: '', property_type: 'house', tenure: 'unknown',
  purchase_date: '', move_in_date: '', year_built: '',
  water_shutoff: '', gas_shutoff: '', electricity_consumer_unit: '', boiler_location: '',
  notes: '',
}

function PropertyForm({ initial, onSave, onCancel, saving }: {
  initial: typeof EMPTY_PROPERTY
  onSave: (data: typeof EMPTY_PROPERTY) => void
  onCancel: () => void
  saving: boolean
}) {
  const [f, setF] = useState(initial)
  const set = (k: string, v: string) => setF(prev => ({ ...prev, [k]: v }))
  return (
    <div className="flex flex-col gap-3">
      <Field label="Name"><Input value={f.name} onChange={e => set('name', e.target.value)} placeholder="Home" /></Field>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Type">
          <Select value={f.property_type} onChange={e => set('property_type', e.target.value)}>
            {['house', 'flat', 'bungalow', 'maisonette', 'other'].map(t => <option key={t} value={t}>{cap(t)}</option>)}
          </Select>
        </Field>
        <Field label="Tenure">
          <Select value={f.tenure} onChange={e => set('tenure', e.target.value)}>
            {['freehold', 'leasehold', 'share_of_freehold', 'rented', 'other', 'unknown'].map(t => <option key={t} value={t}>{cap(t)}</option>)}
          </Select>
        </Field>
      </div>
      <Field label="Address"><Textarea rows={2} value={f.address} onChange={e => set('address', e.target.value)} /></Field>
      <div className="grid gap-3 sm:grid-cols-3">
        <Field label="Purchased"><input type="date" className={fieldClass} value={f.purchase_date ?? ''} onChange={e => set('purchase_date', e.target.value)} /></Field>
        <Field label="Moved in"><input type="date" className={fieldClass} value={f.move_in_date ?? ''} onChange={e => set('move_in_date', e.target.value)} /></Field>
        <Field label="Year built"><Input value={f.year_built} onChange={e => set('year_built', e.target.value)} placeholder="e.g. 1998" /></Field>
      </div>
      <p className="text-xs font-semibold uppercase tracking-wide text-muted-strong">Where is it? (emergency info)</p>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Water stopcock"><Input value={f.water_shutoff} onChange={e => set('water_shutoff', e.target.value)} /></Field>
        <Field label="Gas shut-off"><Input value={f.gas_shutoff} onChange={e => set('gas_shutoff', e.target.value)} /></Field>
        <Field label="Consumer unit / fuse box"><Input value={f.electricity_consumer_unit} onChange={e => set('electricity_consumer_unit', e.target.value)} /></Field>
        <Field label="Boiler"><Input value={f.boiler_location} onChange={e => set('boiler_location', e.target.value)} /></Field>
      </div>
      <Field label="Notes"><Textarea rows={2} value={f.notes} onChange={e => set('notes', e.target.value)} /></Field>
      <div className="flex justify-end gap-2">
        <Button variant="ghost" size="sm" onClick={onCancel}>Cancel</Button>
        <Button size="sm" onClick={() => onSave(f)} loading={saving} disabled={!f.name.trim()}>Save</Button>
      </div>
    </div>
  )
}

function InfoRow({ label, value }: { label: string; value: string }) {
  if (!value) return null
  return (
    <div className="flex justify-between gap-3 py-1 text-sm">
      <span className="text-muted flex-shrink-0">{label}</span>
      <span className="text-ink text-right">{value}</span>
    </div>
  )
}

function OverviewTab({ onError, onGoTab, canUseMoney }: {
  onError: (m: string) => void
  onGoTab: (t: Tab) => void
  canUseMoney: boolean
}) {
  const [property, setProperty] = useState<Property | null>(null)
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [counts, setCounts] = useState({ due: 0, warranties: 0, improvements: 0 })

  const load = () => {
    api.getProperties().then(ps => setProperty(ps[0] ?? null)).catch(e => onError(errMsg(e))).finally(() => setLoading(false))
    Promise.all([api.getMaintenance(true), api.getAppliances(true), api.getImprovements(true)])
      .then(([m, a, i]) => setCounts({ due: m.length, warranties: a.length, improvements: i.length }))
      .catch(() => {})
  }
  useEffect(load, [onError])

  const save = async (data: typeof EMPTY_PROPERTY) => {
    setSaving(true)
    const payload = { ...data, purchase_date: data.purchase_date || null, move_in_date: data.move_in_date || null }
    try {
      const saved = property ? await api.updateProperty(property.id, payload) : await api.createProperty(payload)
      setProperty(saved); setEditing(false)
    } catch (e) { onError(errMsg(e)) } finally { setSaving(false) }
  }

  if (loading) return <div className="h-40 rounded-2xl bg-sunken animate-pulse" />

  const glance = (label: string, n: number, tab: Tab, tone: BadgeTone) => (
    <StatCard
      label={label}
      value={n}
      badge={<Badge tone={n > 0 ? tone : 'neutral'}>{n > 0 ? 'Needs attention' : 'All clear'}</Badge>}
      onClick={() => onGoTab(tab)}
    />
  )

  const initial = property ? {
    name: property.name, address: property.address, property_type: property.property_type,
    tenure: property.tenure, purchase_date: property.purchase_date ?? '', move_in_date: property.move_in_date ?? '',
    year_built: property.year_built, water_shutoff: property.water_shutoff, gas_shutoff: property.gas_shutoff,
    electricity_consumer_unit: property.electricity_consumer_unit, boiler_location: property.boiler_location,
    notes: property.notes,
  } : EMPTY_PROPERTY

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-3 sm:flex-row">
        {glance('Maintenance due', counts.due, 'maintenance', 'danger')}
        {glance('Warranties expiring', counts.warranties, 'appliances', 'warning')}
        {glance('Open improvements', counts.improvements, 'improvements', 'primary')}
      </div>

      {editing || !property ? (
        <Card title={property ? 'Edit home' : 'Set up your home'}>
          <PropertyForm initial={initial} onSave={save} onCancel={() => setEditing(false)} saving={saving} />
        </Card>
      ) : (
        <Card>
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <h3 className="text-lg font-bold text-ink">{property.name}</h3>
              <p className="text-sm text-muted">{cap(property.property_type)} · {cap(property.tenure)}</p>
              {property.address && <p className="mt-1 whitespace-pre-wrap text-sm text-muted-strong">{property.address}</p>}
            </div>
            <Button variant="ghost" size="sm" onClick={() => setEditing(true)}>Edit</Button>
          </div>
          <div className="mt-3 grid gap-x-6 gap-y-0 sm:grid-cols-2">
            <InfoRow label="Purchased" value={property.purchase_date ? new Date(property.purchase_date).toLocaleDateString() : ''} />
            <InfoRow label="Moved in" value={property.move_in_date ? new Date(property.move_in_date).toLocaleDateString() : ''} />
            <InfoRow label="Year built" value={property.year_built} />
          </div>
          {(property.water_shutoff || property.gas_shutoff || property.electricity_consumer_unit || property.boiler_location) && (
            <div className="mt-3 rounded-xl bg-sunken/60 p-3">
              <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-strong">Emergency info</p>
              <InfoRow label="💧 Water stopcock" value={property.water_shutoff} />
              <InfoRow label="🔥 Gas shut-off" value={property.gas_shutoff} />
              <InfoRow label="⚡ Consumer unit" value={property.electricity_consumer_unit} />
              <InfoRow label="🔧 Boiler" value={property.boiler_location} />
            </div>
          )}
          {property.notes && <p className="mt-3 whitespace-pre-wrap text-sm text-muted-strong">{property.notes}</p>}
        </Card>
      )}

      <Card>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="font-semibold text-ink">Costs &amp; cover</p>
            <p className="text-sm text-muted">
              {canUseMoney
                ? 'Insurance, rates and utilities are protected and synced into Solace.'
                : 'Home finance access is not enabled for this account.'}
            </p>
          </div>
          {canUseMoney && <Button variant="secondary" size="sm" onClick={() => onGoTab('finances')}>Open finances</Button>}
        </div>
      </Card>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Rooms & areas — linked overview into dedicated room planning pages
// ---------------------------------------------------------------------------

const EMPTY_ROOMS: RoomListResponse = {
  rooms: [],
  household_summary: {
    active_count: 0, completed_count: 0, archived_count: 0,
    remaining_estimated_cost: '0.00', completed_cost: '0.00', overall_cost: '0.00',
  },
}

function RoomsTab({ onError, canEdit }: { onError: (m: string) => void; canEdit: boolean }) {
  const [data, setData] = useState<RoomListResponse>(EMPTY_ROOMS)
  const [loading, setLoading] = useState(true)
  const [adding, setAdding] = useState(false)
  const [saving, setSaving] = useState(false)
  const [roomView, setRoomView] = useState<'plan' | 'list'>('plan')
  const [form, setForm] = useState({
    name: '', area_type: 'interior' as RoomAreaType, description: '', icon: '',
  })

  const load = () => api.getRooms().then(setData).catch(e => onError(errMsg(e))).finally(() => setLoading(false))
  useEffect(() => { void load() }, [])

  const save = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.name.trim()) return
    setSaving(true)
    try {
      await api.createRoom({ ...form, name: form.name.trim() })
      setForm({ name: '', area_type: 'interior', description: '', icon: '' })
      setAdding(false)
      await load()
    } catch (e) { onError(errMsg(e)) } finally { setSaving(false) }
  }

  if (loading) return <div className="h-40 rounded-2xl bg-sunken animate-pulse" />
  const summary = data.household_summary

  return (
    <div className="flex flex-col gap-5">
      <div className="grid gap-3 sm:grid-cols-3">
        <Card>
          <p className="text-2xl font-extrabold text-ink">{money(summary.remaining_estimated_cost)}</p>
          <p className="text-sm text-muted">Still planned across the house</p>
          <p className="mt-1 text-xs text-muted">{summary.active_count} active item{summary.active_count === 1 ? '' : 's'}</p>
        </Card>
        <Card>
          <p className="text-2xl font-extrabold text-ink">{money(summary.completed_cost)}</p>
          <p className="text-sm text-muted">Completed cost</p>
          <p className="mt-1 text-xs text-muted">Actual cost where recorded</p>
        </Card>
        <Card>
          <p className="text-2xl font-extrabold text-ink">{money(summary.overall_cost)}</p>
          <p className="text-sm text-muted">Overall household plan</p>
          <p className="mt-1 text-xs text-muted">Archived ideas excluded</p>
        </Card>
      </div>

      {adding ? (
        <Card title="Add a room or area">
          <form onSubmit={save} className="flex flex-col gap-3">
            <div className="grid gap-3 sm:grid-cols-[90px_1fr_180px]">
              <Field label="Icon"><RoomIconSelect value={form.icon} onChange={icon => setForm(f => ({ ...f, icon }))} /></Field>
              <Field label="Name"><Input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} placeholder="Living room" autoFocus /></Field>
              <Field label="Type">
                <Select value={form.area_type} onChange={e => setForm(f => ({ ...f, area_type: e.target.value as RoomAreaType }))}>
                  {['interior', 'outdoor', 'utility', 'storage', 'other'].map(type => <option key={type} value={type}>{cap(type)}</option>)}
                </Select>
              </Field>
            </div>
            <Field label="Description"><Textarea rows={2} value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} placeholder="What this space is used for, or the overall goal for it…" /></Field>
            <div className="flex justify-end gap-2">
              <Button type="button" variant="ghost" size="sm" onClick={() => setAdding(false)}>Cancel</Button>
              <Button type="submit" size="sm" loading={saving} disabled={!form.name.trim()}>Create room</Button>
            </div>
          </form>
        </Card>
      ) : (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="font-bold text-ink">Rooms &amp; areas</h2>
            <p className="text-sm text-muted">Each room opens its own purchases, maintenance, renovations and upgrades plan.</p>
          </div>
          {canEdit && <Button size="sm" onClick={() => setAdding(true)}>+ Add room or area</Button>}
        </div>
      )}

      <Tabs
        tabs={[{ key: 'plan' as const, label: 'Floor plan' }, { key: 'list' as const, label: 'Room list', badge: data.rooms.length }]}
        active={roomView}
        onChange={setRoomView}
        variant="secondary"
      />

      {roomView === 'plan' && (
        <HomeFloorPlan
          rooms={data.rooms}
          canEdit={canEdit}
          onRoomsChanged={load}
          onError={onError}
        />
      )}

      {roomView === 'list' && (
        data.rooms.length === 0 ? (
          <EmptyState icon="🚪" title="No rooms or areas yet" hint="Add rooms using the names shown on the floor plan to make each space clickable." />
        ) : (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {data.rooms.map(room => (
              <Link key={room.id} to={`/homestead/rooms/${room.id}`} className="group rounded-2xl border border-line bg-surface p-4 transition hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-sm">
                <div className="flex items-start gap-3">
                  <div className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-xl text-2xl" style={{ backgroundColor: `${room.colour}20` }}>
                    {room.icon || (room.area_type === 'outdoor' ? '🌿' : '🚪')}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-2">
                      <h3 className="truncate font-bold text-ink group-hover:text-primary">{room.name}</h3>
                      <span className="text-muted transition group-hover:translate-x-0.5">→</span>
                    </div>
                    <p className="text-xs text-muted">{cap(room.area_type)} · {room.summary.active_count} active</p>
                    {room.description && <p className="mt-2 line-clamp-2 text-sm text-muted-strong">{room.description}</p>}
                    <div className="mt-3 flex items-end justify-between gap-3 border-t border-line pt-2">
                      <div><p className="text-xs text-muted">Remaining</p><p className="font-bold text-ink">{money(room.summary.remaining_estimated_cost)}</p></div>
                      <p className="text-xs text-muted">{room.summary.completed_count} completed · {room.summary.archived_count} archived</p>
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Maintenance tab
// ---------------------------------------------------------------------------

function MaintenanceTab({ people, defaultAssignee, onError, canUseMoney }: {
  people: Person[]
  defaultAssignee: number[]
  onError: (m: string) => void
  canUseMoney: boolean
}) {
  const [tasks, setTasks] = useState<MaintenanceTask[]>([])
  const [appliances, setAppliances] = useState<Appliance[]>([])
  const [providers, setProviders] = useState<ServiceProvider[]>([])
  const [loading, setLoading] = useState(true)
  const [open, setOpen] = useState(false)
  useUrlAction('maintenance', () => setOpen(true))
  const [editId, setEditId] = useState<number | null>(null)
  const blank = {
    title: '', category: 'general', next_due_at: null as string | null, is_all_day: true,
    recurrence_rule: '', appliance_id: 0, provider_id: 0, assigned_to_person_ids: defaultAssignee, notes: '',
  }
  const [f, setF] = useState(blank)
  const [saving, setSaving] = useState(false)
  const [costTask, setCostTask] = useState<MaintenanceTask | null>(null)
  const [costAmount, setCostAmount] = useState('')
  const [costCategory, setCostCategory] = useState('other')
  const [costPassword, setCostPassword] = useState('')
  const [costError, setCostError] = useState('')
  const [trackingCost, setTrackingCost] = useState(false)
  const set = (k: string, v: unknown) => setF(prev => ({ ...prev, [k]: v }))

  const load = () => api.getMaintenance().then(setTasks).catch(e => onError(errMsg(e))).finally(() => setLoading(false))
  useEffect(() => {
    load()
    api.getAppliances().then(setAppliances).catch(() => {})
    api.getProviders().then(setProviders).catch(() => {})
  }, [])

  const startAdd = () => { setEditId(null); setF({ ...blank, assigned_to_person_ids: defaultAssignee }); setOpen(true) }
  const startEdit = (t: MaintenanceTask) => {
    setEditId(t.id)
    setF({
      title: t.title, category: t.category, next_due_at: t.next_due_at, is_all_day: t.is_all_day,
      recurrence_rule: t.recurrence_rule, appliance_id: t.appliance_id ?? 0, provider_id: t.provider_id ?? 0,
      assigned_to_person_ids: t.assigned_to_person_ids, notes: t.notes,
    })
    setOpen(true)
  }

  const save = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!f.title.trim()) return
    setSaving(true)
    const payload = {
      title: f.title.trim(), category: f.category, next_due_at: f.next_due_at, is_all_day: f.is_all_day,
      recurrence_rule: f.recurrence_rule, notes: f.notes,
      appliance_id: f.appliance_id || null, provider_id: f.provider_id || null,
      assigned_to_person_ids: f.assigned_to_person_ids,
    }
    try {
      if (editId) await api.updateMaintenance(editId, payload)
      else await api.createMaintenance(payload)
      setOpen(false); load()
    } catch (e) { onError(errMsg(e)) } finally { setSaving(false) }
  }

  const complete = async (t: MaintenanceTask) => {
    try { await api.completeMaintenance(t.id); load() } catch (e) { onError(errMsg(e)) }
  }
  const remove = async (t: MaintenanceTask) => {
    if (!(await confirmDialog({ title: `Delete "${t.title}"?`, confirmLabel: 'Delete' }))) return
    try { await api.deleteMaintenance(t.id); load() } catch (e) { onError(errMsg(e)) }
  }
  const startCost = (task: MaintenanceTask) => {
    setCostTask(task)
    setCostAmount('')
    setCostCategory('other')
    setCostPassword('')
    setCostError('')
  }
  const closeCost = () => {
    if (trackingCost) return
    setCostTask(null)
    setCostPassword('')
    setCostError('')
  }
  const trackCost = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!costTask || !costPassword || Number(costAmount) <= 0) return
    setTrackingCost(true)
    setCostError('')
    try {
      await api.reauth(costPassword)
      await api.trackMaintenanceCost(costTask.id, {
        amount: costAmount,
        category: costCategory,
      })
      setCostTask(null)
      setCostPassword('')
      await load()
    } catch (e) {
      setCostError(errMsg(e))
    } finally {
      setTrackingCost(false)
    }
  }

  if (loading) return <div className="h-32 rounded-2xl bg-sunken animate-pulse" />

  return (
    <div className="flex flex-col gap-4">
      {open ? (
        <Card title={editId ? 'Edit task' : 'New maintenance task'}>
          <form onSubmit={save} className="flex flex-col gap-3">
            <Input placeholder="e.g. Service the boiler" value={f.title} onChange={e => set('title', e.target.value)} autoFocus />
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Category">
                <Select value={f.category} onChange={e => set('category', e.target.value)}>
                  {MAINT_CATS.map(c => <option key={c} value={c}>{cap(c)}</option>)}
                </Select>
              </Field>
              <Field label="Repeats">
                <Select value={f.recurrence_rule} onChange={e => set('recurrence_rule', e.target.value)}>
                  {RECURRENCE.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
                </Select>
              </Field>
            </div>
            <Field label="Next due">
              <DateTimeField value={f.next_due_at} allDay={f.is_all_day}
                onChange={({ value, allDay }) => setF(prev => ({ ...prev, next_due_at: value, is_all_day: allDay }))} />
            </Field>
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Appliance (optional)">
                <Select value={f.appliance_id} onChange={e => set('appliance_id', Number(e.target.value))}>
                  <option value={0}>—</option>
                  {appliances.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
                </Select>
              </Field>
              <Field label="Provider (optional)">
                <Select value={f.provider_id} onChange={e => set('provider_id', Number(e.target.value))}>
                  <option value={0}>—</option>
                  {providers.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                </Select>
              </Field>
            </div>
            <Field label="Assigned to">
              <AssigneeSelect people={people} value={f.assigned_to_person_ids}
                onChange={v => set('assigned_to_person_ids', v)} className={fieldClass} />
            </Field>
            <Field label="Notes"><Textarea rows={2} value={f.notes} onChange={e => set('notes', e.target.value)} /></Field>
            <div className="flex justify-end gap-2">
              <Button type="button" variant="ghost" size="sm" onClick={() => setOpen(false)}>Cancel</Button>
              <Button type="submit" size="sm" loading={saving} disabled={!f.title.trim()}>Save</Button>
            </div>
          </form>
        </Card>
      ) : (
        <Button size="sm" onClick={startAdd} className="self-start">+ New task</Button>
      )}

      {tasks.length === 0 ? (
        <EmptyState icon="🔧" title="No maintenance yet" hint="Add recurring upkeep — gutters, boiler service, smoke alarms — and mark it done to roll to the next date." />
      ) : (
        <div className="flex flex-col gap-2">
          {tasks.map(t => {
            const due = dueLabel(t.next_due_at)
            const assignee = people.find(p => t.assigned_to_person_ids.includes(p.id)) ?? null
            return (
              <div key={t.id} className="group flex flex-col gap-3 rounded-xl border border-line p-3 sm:flex-row sm:items-center">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium text-ink">{t.title}</span>
                    <Badge>{cap(t.category)}</Badge>
                    {t.solace_bill_ref && canUseMoney && (
                      <Link to={`/solace?tab=bills&q=${encodeURIComponent(t.title)}`} aria-label={`Open ${t.title} in Solace`}>
                        <Badge tone="success">Cost tracked in Solace →</Badge>
                      </Link>
                    )}
                    {t.recurrence_rule && <Badge tone="primary">↻ {recurrenceLabel(t.recurrence_rule)}</Badge>}
                    {due && <Badge tone={due.tone}>{due.text}</Badge>}
                  </div>
                  {(assignee || t.last_done_at) && (
                    <p className="mt-0.5 text-xs text-muted">
                      {assignee && <>👤 {assignee.preferred_name || assignee.display_name} </>}
                      {t.last_done_at && <>· last done {new Date(t.last_done_at).toLocaleDateString()}</>}
                    </p>
                  )}
                </div>
                <div className="flex w-full flex-wrap items-center justify-end gap-1 sm:w-auto">
                  {t.next_due_at && <Button size="sm" variant="secondary" onClick={() => complete(t)} className="mr-auto sm:mr-1">Done</Button>}
                  {!t.solace_bill_ref && canUseMoney && <Button size="sm" variant="ghost" onClick={() => startCost(t)}>Track cost</Button>}
                  <div className="flex items-center gap-1 sm:opacity-0 sm:transition-opacity sm:group-hover:opacity-100 sm:group-focus-within:opacity-100">
                    <EditAction onClick={() => startEdit(t)} label={t.title} />
                    <DeleteAction onClick={() => remove(t)} label={t.title} />
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
      {costTask && (
        <Modal
          title="Track maintenance cost in Solace"
          onClose={closeCost}
          size="sm"
          footer={(
            <>
              <Button type="button" variant="ghost" size="sm" onClick={closeCost} disabled={trackingCost}>Cancel</Button>
              <Button type="submit" form="maintenance-cost-form" size="sm" loading={trackingCost} disabled={!costPassword || Number(costAmount) <= 0}>Track cost</Button>
            </>
          )}
        >
          <form id="maintenance-cost-form" onSubmit={trackCost} className="flex flex-col gap-4">
            <div className="rounded-xl bg-primary-soft px-3 py-2.5 text-sm text-ink">
              <strong>{costTask.title}</strong> stays owned by Homestead. Solace will hold the
              amount and payment history, using the same due date and recurrence.
            </div>
            {costError && <div className="rounded-xl bg-danger-soft px-3 py-2 text-sm text-danger">{costError}</div>}
            <Field label="Expected cost">
              <Input type="number" min="0.01" step="0.01" inputMode="decimal" value={costAmount} onChange={e => setCostAmount(e.target.value)} placeholder="0.00" autoFocus />
            </Field>
            <Field label="Solace category">
              <Select value={costCategory} onChange={e => setCostCategory(e.target.value)}>
                {['other', 'utilities', 'insurance', 'council', 'mortgage'].map(category => <option key={category} value={category}>{cap(category)}</option>)}
              </Select>
            </Field>
            <Field label="Password" hint="Financial actions require password confirmation.">
              <Input type="password" value={costPassword} onChange={e => setCostPassword(e.target.value)} autoComplete="current-password" />
            </Field>
          </form>
        </Modal>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Appliances tab
// ---------------------------------------------------------------------------

function AppliancesTab({ onError }: { onError: (m: string) => void }) {
  const [appliances, setAppliances] = useState<Appliance[]>([])
  const [loading, setLoading] = useState(true)
  const [open, setOpen] = useState(false)
  const [editId, setEditId] = useState<number | null>(null)
  const blank = {
    name: '', category: 'appliance', brand: '', model_number: '', serial_number: '', room: '',
    purchase_date: '', warranty_expires_at: '', warranty_provider: '', manual_url: '', notes: '',
  }
  const [f, setF] = useState(blank)
  const [saving, setSaving] = useState(false)
  const set = (k: string, v: string) => setF(prev => ({ ...prev, [k]: v }))

  const load = () => { api.getAppliances().then(setAppliances).catch(e => onError(errMsg(e))).finally(() => setLoading(false)) }
  useEffect(load, [])

  const startAdd = () => { setEditId(null); setF(blank); setOpen(true) }
  const startEdit = (a: Appliance) => {
    setEditId(a.id)
    setF({
      name: a.name, category: a.category, brand: a.brand, model_number: a.model_number,
      serial_number: a.serial_number, room: a.room, purchase_date: a.purchase_date ?? '',
      warranty_expires_at: a.warranty_expires_at ?? '', warranty_provider: a.warranty_provider,
      manual_url: a.manual_url, notes: a.notes,
    })
    setOpen(true)
  }

  const save = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!f.name.trim()) return
    setSaving(true)
    const payload = { ...f, purchase_date: f.purchase_date || null, warranty_expires_at: f.warranty_expires_at || null }
    try {
      if (editId) await api.updateAppliance(editId, payload)
      else await api.createAppliance(payload)
      setOpen(false); load()
    } catch (e) { onError(errMsg(e)) } finally { setSaving(false) }
  }
  const remove = async (a: Appliance) => {
    if (!(await confirmDialog({ title: `Delete "${a.name}"?`, confirmLabel: 'Delete' }))) return
    try { await api.deleteAppliance(a.id); load() } catch (e) { onError(errMsg(e)) }
  }

  if (loading) return <div className="h-32 rounded-2xl bg-sunken animate-pulse" />

  return (
    <div className="flex flex-col gap-4">
      {open ? (
        <Card title={editId ? 'Edit appliance' : 'New appliance'}>
          <form onSubmit={save} className="flex flex-col gap-3">
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Name"><Input value={f.name} onChange={e => set('name', e.target.value)} placeholder="e.g. Boiler" autoFocus /></Field>
              <Field label="Category">
                <Select value={f.category} onChange={e => set('category', e.target.value)}>
                  {APPLIANCE_CATS.map(c => <option key={c} value={c}>{cap(c)}</option>)}
                </Select>
              </Field>
              <Field label="Brand"><Input value={f.brand} onChange={e => set('brand', e.target.value)} /></Field>
              <Field label="Model"><Input value={f.model_number} onChange={e => set('model_number', e.target.value)} /></Field>
              <Field label="Serial number"><Input value={f.serial_number} onChange={e => set('serial_number', e.target.value)} /></Field>
              <Field label="Room"><Input value={f.room} onChange={e => set('room', e.target.value)} /></Field>
              <Field label="Purchased"><input type="date" className={fieldClass} value={f.purchase_date} onChange={e => set('purchase_date', e.target.value)} /></Field>
              <Field label="Warranty expires"><input type="date" className={fieldClass} value={f.warranty_expires_at} onChange={e => set('warranty_expires_at', e.target.value)} /></Field>
              <Field label="Warranty provider"><Input value={f.warranty_provider} onChange={e => set('warranty_provider', e.target.value)} /></Field>
              <Field label="Manual link"><Input value={f.manual_url} onChange={e => set('manual_url', e.target.value)} placeholder="https://…" /></Field>
            </div>
            <Field label="Notes"><Textarea rows={2} value={f.notes} onChange={e => set('notes', e.target.value)} /></Field>
            <div className="flex justify-end gap-2">
              <Button type="button" variant="ghost" size="sm" onClick={() => setOpen(false)}>Cancel</Button>
              <Button type="submit" size="sm" loading={saving} disabled={!f.name.trim()}>Save</Button>
            </div>
          </form>
        </Card>
      ) : (
        <Button size="sm" onClick={startAdd} className="self-start">+ New appliance</Button>
      )}

      {appliances.length === 0 ? (
        <EmptyState icon="🧺" title="No appliances yet" hint="Record appliances and home systems with their model, serial and warranty for when something breaks." />
      ) : (
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
          {appliances.map(a => {
            const w = warrantyLabel(a.warranty_expires_at)
            return (
              <Card key={a.id} className="group">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="font-bold text-ink">{a.name}</h3>
                      <Badge>{cap(a.category)}</Badge>
                      {w && <Badge tone={w.tone}>{w.text}</Badge>}
                    </div>
                    <p className="mt-0.5 text-sm text-muted">
                      {[a.brand, a.model_number].filter(Boolean).join(' ') || '—'}
                      {a.room && <> · {a.room}</>}
                    </p>
                    {a.serial_number && <p className="text-xs text-muted">S/N {a.serial_number}</p>}
                    {a.manual_url && <a href={a.manual_url} target="_blank" rel="noreferrer" className="text-xs text-primary hover:underline">📄 Manual</a>}
                    {a.notes && <p className="mt-1 whitespace-pre-wrap text-sm text-muted-strong">{a.notes}</p>}
                  </div>
                  <div className="flex flex-shrink-0 items-center gap-1 sm:opacity-0 transition-opacity sm:group-hover:opacity-100">
                    <EditAction onClick={() => startEdit(a)} label={a.name} />
                    <DeleteAction onClick={() => remove(a)} label={a.name} />
                  </div>
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
// Improvements tab
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Pool & spa
// ---------------------------------------------------------------------------

const POOL_SANITISERS: { value: PoolSanitiser; label: string }[] = [
  { value: 'saltwater', label: 'Saltwater (chlorinator)' },
  { value: 'chlorine', label: 'Manually chlorinated' },
  { value: 'mineral', label: 'Mineral / magnesium' },
  { value: 'bromine', label: 'Bromine' },
  { value: 'other', label: 'Other' },
]
const POOL_SURFACES: { value: PoolSurface; label: string }[] = [
  { value: 'concrete', label: 'Concrete / rendered' },
  { value: 'fibreglass', label: 'Fibreglass' },
  { value: 'vinyl_liner', label: 'Vinyl liner' },
  { value: 'tiled', label: 'Fully tiled' },
  { value: 'other', label: 'Other' },
]
const POOL_KINDS = [
  { value: 'pool', label: 'Swimming pool' },
  { value: 'spa', label: 'Spa / hot tub' },
  { value: 'swim_spa', label: 'Swim spa' },
  { value: 'plunge', label: 'Plunge pool' },
]
const POOL_FILTERS = [
  { value: 'sand', label: 'Sand' },
  { value: 'cartridge', label: 'Cartridge' },
  { value: 'glass', label: 'Glass media' },
  { value: 'de', label: 'Diatomaceous earth' },
  { value: 'other', label: 'Not sure yet' },
]
/** The order readings are shown in: the weekly two first, then the monthly ones. */
const READING_ORDER: PoolReadingKey[] = [
  'free_chlorine', 'ph', 'total_alkalinity', 'cyanuric_acid', 'salt',
  'calcium_hardness', 'water_temp_c',
]
const READING_TONE: Record<string, BadgeTone> = {
  ok: 'success', low: 'warning', high: 'warning', info: 'neutral',
}
const READING_WORD: Record<string, string> = {
  ok: 'In range', low: 'Low', high: 'High', info: 'Noted',
}

function targetText(min: string | null, max: string | null, unit: string) {
  if (min === null || max === null) return 'No target — recorded for context'
  return `Aim for ${Number(min)}–${Number(max)}${unit ? ` ${unit}` : ''}`
}

/** One reading with its verdict and, when it is out of band, what to do about it. */
function ReadingRow({ reading }: { reading: PoolStatus['readings'][PoolReadingKey] }) {
  if (!reading) return null
  return (
    <div className="rounded-xl border border-line bg-sunken/50 p-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="font-semibold text-ink">{reading.label}</p>
        <div className="flex items-center gap-2">
          <span className="text-lg font-black text-ink">
            {Number(reading.value)}<span className="ml-0.5 text-xs font-semibold text-muted">{reading.unit}</span>
          </span>
          <Badge tone={READING_TONE[reading.status]}>{READING_WORD[reading.status]}</Badge>
        </div>
      </div>
      <p className="mt-1 text-xs text-muted">{targetText(reading.min, reading.max, reading.unit)}</p>
      {reading.advice && <p className="mt-2 text-sm leading-relaxed text-ink">{reading.advice}</p>}
    </div>
  )
}

function WaterTestForm({ pool, status, onSaved, onCancel, onError }: {
  pool: Pool
  status: PoolStatus | null
  onSaved: () => Promise<void>
  onCancel: () => void
  onError: (message: string) => void
}) {
  const [values, setValues] = useState<Record<string, string>>({})
  const [notes, setNotes] = useState('')
  const [busy, setBusy] = useState(false)
  // Only ask for the readings this pool actually has: a chlorine pool has no salt to measure.
  const keys = READING_ORDER.filter(key => status?.targets[key])

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    const payload: WaterTestWrite = { tested_at: new Date().toISOString(), notes }
    let entered = false
    for (const key of keys) {
      const raw = values[key]
      if (raw !== undefined && raw !== '') { (payload as Record<string, unknown>)[key] = raw; entered = true }
    }
    if (!entered) { onError('Enter at least one reading.'); return }
    setBusy(true)
    try {
      await api.logWaterTest(pool.id, payload)
      await onSaved()
      onCancel()
    } catch (error) { onError(errMsg(error)) } finally { setBusy(false) }
  }

  return (
    <form onSubmit={submit} className="space-y-3">
      <p className="text-sm text-muted">
        Fill in whatever you measured — a weekly strip usually gives chlorine and pH, and the rest
        come from a full test or a pool-shop sample.
      </p>
      <div className="grid gap-3 sm:grid-cols-2">
        {keys.map(key => {
          const target = status?.targets[key]
          if (!target) return null
          return (
            <Field key={key} label={`${target.label}${target.unit ? ` (${target.unit})` : ''}`} hint={targetText(target.min, target.max, target.unit)}>
              <Input
                type="number" step="any" inputMode="decimal"
                value={values[key] ?? ''}
                onChange={event => setValues(current => ({ ...current, [key]: event.target.value }))}
              />
            </Field>
          )
        })}
      </div>
      <Field label="Notes"><Textarea value={notes} onChange={event => setNotes(event.target.value)} placeholder="Anything you noticed — water clarity, recent rain, how long the pump ran." /></Field>
      <div className="flex flex-col gap-2 sm:flex-row">
        <Button type="submit" loading={busy} className="w-full sm:w-auto">Save reading</Button>
        <Button type="button" variant="ghost" onClick={onCancel} className="w-full sm:w-auto">Cancel</Button>
      </div>
    </form>
  )
}

function PoolSetupForm({ existing, onSaved, onCancel, onError }: {
  existing: Pool | null
  onSaved: () => Promise<void>
  onCancel: () => void
  onError: (message: string) => void
}) {
  const [form, setForm] = useState({
    name: existing?.name ?? 'Pool',
    kind: existing?.kind ?? 'pool',
    sanitiser: existing?.sanitiser ?? 'saltwater',
    surface: existing?.surface ?? 'concrete',
    filter_type: existing?.filter_type ?? 'other',
    volume_litres: existing?.volume_litres?.toString() ?? '',
    equipment_notes: existing?.equipment_notes ?? '',
  })
  const [busy, setBusy] = useState(false)
  const set = (key: keyof typeof form) => (event: { target: { value: string } }) =>
    setForm(current => ({ ...current, [key]: event.target.value }))

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setBusy(true)
    const payload = {
      ...form,
      kind: form.kind as Pool['kind'],
      sanitiser: form.sanitiser as PoolSanitiser,
      surface: form.surface as PoolSurface,
      filter_type: form.filter_type as Pool['filter_type'],
      volume_litres: form.volume_litres ? Number(form.volume_litres) : null,
    }
    try {
      if (existing) await api.updatePool(existing.id, payload)
      else await api.createPool(payload)
      await onSaved()
      onCancel()
    } catch (error) { onError(errMsg(error)) } finally { setBusy(false) }
  }

  return (
    <form onSubmit={submit} className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Name"><Input value={form.name} onChange={set('name')} /></Field>
        <Field label="Type">
          <Select value={form.kind} onChange={set('kind')}>
            {POOL_KINDS.map(row => <option key={row.value} value={row.value}>{row.label}</option>)}
          </Select>
        </Field>
        <Field label="How it is sanitised" hint="This sets the target water levels and which jobs you get.">
          <Select value={form.sanitiser} onChange={set('sanitiser')}>
            {POOL_SANITISERS.map(row => <option key={row.value} value={row.value}>{row.label}</option>)}
          </Select>
        </Field>
        <Field label="Surface" hint="Fibreglass and vinyl need less calcium in the water than concrete.">
          <Select value={form.surface} onChange={set('surface')}>
            {POOL_SURFACES.map(row => <option key={row.value} value={row.value}>{row.label}</option>)}
          </Select>
        </Field>
        <Field label="Filter">
          <Select value={form.filter_type} onChange={set('filter_type')}>
            {POOL_FILTERS.map(row => <option key={row.value} value={row.value}>{row.label}</option>)}
          </Select>
        </Field>
        <Field label="Volume (litres)" hint="Optional — it is what dosing instructions are based on.">
          <Input type="number" min="0" inputMode="numeric" value={form.volume_litres} onChange={set('volume_litres')} />
        </Field>
      </div>
      <Field label="Equipment notes" hint="Pump and chlorinator models, filter pressure when clean, timer settings.">
        <Textarea value={form.equipment_notes} onChange={set('equipment_notes')} />
      </Field>
      {!existing && (
        <p className="rounded-xl bg-primary-soft px-3 py-2.5 text-sm text-ink">
          Saving also sets up the usual care jobs for this kind of pool — skimming, testing,
          brushing, filter cleaning — each with its own reminder. You can edit or delete any of them.
        </p>
      )}
      <div className="flex flex-col gap-2 sm:flex-row">
        <Button type="submit" loading={busy} disabled={!form.name.trim()} className="w-full sm:w-auto">
          {existing ? 'Save pool' : 'Add pool and its care schedule'}
        </Button>
        <Button type="button" variant="ghost" onClick={onCancel} className="w-full sm:w-auto">Cancel</Button>
      </div>
    </form>
  )
}

function PoolTab({ onError, canEdit }: { onError: (message: string) => void; canEdit: boolean }) {
  const [pools, setPools] = useState<Pool[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [status, setStatus] = useState<PoolStatus | null>(null)
  const [history, setHistory] = useState<WaterTest[]>([])
  const [loading, setLoading] = useState(true)
  const [adding, setAdding] = useState(false)
  const [editing, setEditing] = useState(false)
  const [testing, setTesting] = useState(false)
  const [busy, setBusy] = useState(false)
  const [editingCare, setEditingCare] = useState<MaintenanceTask | null>(null)
  const [careDate, setCareDate] = useState<string | null>(null)
  const [careRule, setCareRule] = useState('')

  const pool = pools.find(row => row.id === selectedId) ?? null

  const loadPools = async () => {
    try {
      const rows = await api.getPools()
      setPools(rows)
      setSelectedId(current => (current && rows.some(row => row.id === current) ? current : rows[0]?.id ?? null))
    } catch (error) { onError(errMsg(error)) } finally { setLoading(false) }
  }
  useEffect(() => { loadPools() }, [])

  const loadDetail = async () => {
    if (!selectedId) { setStatus(null); setHistory([]); return }
    try {
      const [statusData, tests] = await Promise.all([
        api.getPoolStatus(selectedId), api.getWaterTests(selectedId),
      ])
      setStatus(statusData); setHistory(tests)
    } catch (error) { onError(errMsg(error)) }
  }
  useEffect(() => { loadDetail() }, [selectedId])

  const act = async (action: () => Promise<unknown>) => {
    setBusy(true)
    try { await action(); await loadDetail() } catch (error) { onError(errMsg(error)) } finally { setBusy(false) }
  }

  if (loading) return <div className="h-40 animate-pulse rounded-2xl bg-sunken" />

  if (adding || (pools.length === 0 && canEdit && editing)) {
    return (
      <Card title="Add a pool or spa">
        <PoolSetupForm existing={null} onError={onError} onCancel={() => { setAdding(false); setEditing(false) }} onSaved={loadPools} />
      </Card>
    )
  }

  if (!pool) {
    return (
      <EmptyState
        icon="🏊"
        title="No pool or spa yet"
        hint="Add yours and HomeStack sets up the usual care schedule, then tells you what each water reading means."
        action={canEdit ? <Button onClick={() => setAdding(true)}>Add a pool</Button> : undefined}
      />
    )
  }

  const overdue = status?.overdue_task_count ?? 0

  return (
    <div className="space-y-4">
      {pools.length > 1 && (
        <Select value={String(selectedId)} onChange={event => setSelectedId(Number(event.target.value))}>
          {pools.map(row => <option key={row.id} value={row.id}>{row.name}</option>)}
        </Select>
      )}

      {/* Two questions the household actually has: is the water OK, and what is due. */}
      <div className="grid grid-cols-2 gap-3">
        <StatCard
          label="Water"
          value={status?.latest_test_id ? (status.water_is_balanced ? 'Balanced' : 'Needs attention') : 'Not tested'}
          hint={status?.latest_tested_at
            ? `Last tested ${new Date(status.latest_tested_at).toLocaleDateString()}`
            : 'Log a reading to see how it is tracking'}
        />
        <StatCard
          label="Care"
          value={overdue > 0 ? `${overdue} overdue` : 'Up to date'}
          hint={status?.next_due_at ? `Next due ${new Date(status.next_due_at).toLocaleDateString()}` : `${status?.care_task_count ?? 0} jobs`}
        />
      </div>

      <div className="flex flex-col gap-2 sm:flex-row">
        {canEdit && <Button className="w-full sm:w-auto" onClick={() => setTesting(value => !value)}>{testing ? 'Close' : '+ Log a water test'}</Button>}
        {canEdit && <Button variant="secondary" className="w-full sm:w-auto" onClick={() => setEditing(value => !value)}>{editing ? 'Close' : 'Pool details'}</Button>}
      </div>

      {editing && (
        <Card title={`${pool.name} details`}>
          <PoolSetupForm existing={pool} onError={onError} onCancel={() => setEditing(false)} onSaved={async () => { await loadPools(); await loadDetail() }} />
          <div className="mt-4 flex flex-col gap-2 border-t border-line pt-4 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-xs text-muted">Changed how it is sanitised? Add any care jobs that change brings.</p>
            <div className="flex flex-col gap-2 sm:flex-row">
              <Button size="sm" variant="secondary" disabled={busy} onClick={() => act(() => api.applyPoolCareSchedule(pool.id))}>
                Add missing care jobs
              </Button>
              <Button
                size="sm" variant="danger" disabled={busy}
                onClick={async () => {
                  if (!(await confirmDialog({
                    title: `Delete "${pool.name}"?`,
                    message: 'Its care jobs, reminders and water-test history go too.',
                    confirmLabel: 'Delete',
                  }))) return
                  await act(() => api.deletePool(pool.id))
                  await loadPools()
                  setEditing(false)
                }}
              >Delete pool</Button>
            </div>
          </div>
        </Card>
      )}

      {testing && (
        <Card title="New water test">
          <WaterTestForm pool={pool} status={status} onError={onError} onCancel={() => setTesting(false)} onSaved={loadDetail} />
        </Card>
      )}

      <Card title={status?.latest_tested_at ? `Water on ${new Date(status.latest_tested_at).toLocaleDateString()}` : 'Water'}>
        {!status?.latest_test_id ? (
          <p className="text-sm text-muted">
            No readings yet. A test strip takes a minute and tells you whether the water is safe to
            swim in — chlorine and pH are the two that matter weekly.
          </p>
        ) : (
          <div className="space-y-2">
            {READING_ORDER.filter(key => status.readings[key]).map(key => (
              <ReadingRow key={key} reading={status.readings[key]} />
            ))}
            {status.water_is_balanced && (
              <p className="rounded-xl bg-success-soft px-3 py-2.5 text-sm text-success">
                Everything measured is in range. Keep skimming and testing on schedule.
              </p>
            )}
          </div>
        )}
      </Card>

      <Card title="What each reading is for">
        <dl className="space-y-3">
          {READING_ORDER.filter(key => status?.targets[key]).map(key => {
            const target = status?.targets[key]
            if (!target) return null
            return (
              <div key={key}>
                <dt className="text-sm font-semibold text-ink">
                  {target.label}
                  <span className="ml-2 text-xs font-medium text-muted">{targetText(target.min, target.max, target.unit)}</span>
                </dt>
                <dd className="mt-0.5 text-sm leading-relaxed text-muted">{target.why}</dd>
              </div>
            )
          })}
        </dl>
        <p className="mt-4 border-t border-line pt-3 text-xs text-muted">
          General guidance for a domestic pool, not a substitute for a pool shop's water analysis —
          worth getting one at the start of the season and whenever something looks off.
        </p>
      </Card>

      <Card title="Care schedule">
        {!status?.care_tasks.length ? (
          <div className="space-y-3">
            <p className="text-sm text-muted">No care jobs set up yet.</p>
            {canEdit && (
              <Button size="sm" disabled={busy} onClick={() => act(() => api.applyPoolCareSchedule(pool.id))}>
                Set up the usual jobs
              </Button>
            )}
          </div>
        ) : (
          <ul className="space-y-2">
            {status.care_tasks.map(task => (
              <li key={task.id} className="rounded-xl border border-line bg-sunken/50 p-3">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="font-semibold text-ink">{task.title}</p>
                    <p className="mt-0.5 text-xs text-muted">
                      {task.next_due_at ? `Due ${new Date(task.next_due_at).toLocaleDateString()}` : 'No date set'}
                      {task.is_overdue ? ' · overdue' : ''}
                    </p>
                  </div>
                  {canEdit && (
                    <div className="flex gap-2"><Button size="sm" variant="ghost" disabled={busy} onClick={() => { setEditingCare(task); setCareDate(task.next_due_at); setCareRule(task.recurrence_rule) }}>Edit schedule</Button><Button size="sm" variant="secondary" disabled={busy} onClick={() => act(() => api.completeMaintenance(task.id))}>Done</Button></div>
                  )}
                </div>
                {editingCare?.id === task.id && <div className="mt-3 grid gap-3 border-t border-line pt-3 sm:grid-cols-2">
                  <Field label="Next occurrence"><DateTimeField value={careDate} allDay onChange={({ value }) => setCareDate(value)} /></Field>
                  <Field label="Repeats"><Select value={careRule} onChange={event => setCareRule(event.target.value)}><option value="">Does not repeat</option><option value="FREQ=WEEKLY">Weekly</option><option value="FREQ=WEEKLY;INTERVAL=2">Fortnightly</option><option value="FREQ=MONTHLY">Monthly</option></Select></Field>
                  <div className="flex gap-2 sm:col-span-2 sm:justify-end"><Button size="sm" variant="ghost" onClick={() => setEditingCare(null)}>Cancel</Button><Button size="sm" variant="secondary" onClick={() => { setCareDate(null); setCareRule('') }}>Pause</Button><Button size="sm" disabled={busy} onClick={() => act(async () => { await api.updateMaintenance(task.id, { next_due_at: careDate, recurrence_rule: careRule }); setEditingCare(null) })}>Save schedule</Button></div>
                </div>}
                {task.notes && <p className="mt-2 text-sm leading-relaxed text-muted">{task.notes}</p>}
              </li>
            ))}
          </ul>
        )}
        <p className="mt-4 border-t border-line pt-3 text-xs text-muted">
          These are ordinary home maintenance jobs, so they also show on the Calendar and in
          Maintenance. Marking one done moves it to its next date.
        </p>
      </Card>

      {history.length > 1 && (
        <Card title="Test history">
          <ul className="divide-y divide-line/70">
            {history.map(test => (
              <li key={test.id} className="flex flex-wrap items-center justify-between gap-2 py-2.5">
                <span className="text-sm font-medium text-ink">{new Date(test.tested_at).toLocaleDateString()}</span>
                <span className="text-xs text-muted">
                  {[
                    test.free_chlorine !== null ? `Cl ${Number(test.free_chlorine)}` : '',
                    test.ph !== null ? `pH ${Number(test.ph)}` : '',
                    test.salt !== null ? `Salt ${Number(test.salt)}` : '',
                  ].filter(Boolean).join(' · ') || 'No headline readings'}
                </span>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  )
}

function ImprovementsTab({ people, defaultAssignee, onError }: {
  people: Person[]; defaultAssignee: number[]; onError: (m: string) => void
}) {
  const [items, setItems] = useState<Improvement[]>([])
  const [loading, setLoading] = useState(true)
  const [open, setOpen] = useState(false)
  const [editId, setEditId] = useState<number | null>(null)
  const blank = {
    title: '', description: '', status: 'idea', priority: 'medium', room: '',
    target_date: null as string | null, is_all_day: true, assigned_to_person_ids: defaultAssignee,
  }
  const [f, setF] = useState(blank)
  const [saving, setSaving] = useState(false)
  const set = (k: string, v: unknown) => setF(prev => ({ ...prev, [k]: v }))

  const load = () => { api.getImprovements().then(setItems).catch(e => onError(errMsg(e))).finally(() => setLoading(false)) }
  useEffect(load, [])

  const startAdd = () => { setEditId(null); setF({ ...blank, assigned_to_person_ids: defaultAssignee }); setOpen(true) }
  const startEdit = (i: Improvement) => {
    setEditId(i.id)
    setF({
      title: i.title, description: i.description, status: i.status, priority: i.priority, room: i.room,
      target_date: i.target_date, is_all_day: i.is_all_day, assigned_to_person_ids: i.assigned_to_person_ids,
    })
    setOpen(true)
  }

  const save = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!f.title.trim()) return
    setSaving(true)
    const payload = {
      title: f.title.trim(), description: f.description, status: f.status, priority: f.priority,
      room: f.room, target_date: f.target_date, is_all_day: f.is_all_day,
      assigned_to_person_ids: f.assigned_to_person_ids,
    }
    try {
      if (editId) await api.updateImprovement(editId, payload)
      else await api.createImprovement(payload)
      setOpen(false); load()
    } catch (e) { onError(errMsg(e)) } finally { setSaving(false) }
  }
  const setStatus = async (i: Improvement, status: string) => {
    try { await api.updateImprovement(i.id, { status }); load() } catch (e) { onError(errMsg(e)) }
  }
  const remove = async (i: Improvement) => {
    if (!(await confirmDialog({ title: `Delete "${i.title}"?`, confirmLabel: 'Delete' }))) return
    try { await api.deleteImprovement(i.id); load() } catch (e) { onError(errMsg(e)) }
  }

  if (loading) return <div className="h-32 rounded-2xl bg-sunken animate-pulse" />

  const openItems = items.filter(i => i.is_open)
  const doneItems = items.filter(i => !i.is_open)

  const card = (i: Improvement) => (
    <Card key={i.id} className="group">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-bold text-ink">{i.title}</h3>
            <Badge tone={STATUS_TONE[i.status]}>{cap(i.status)}</Badge>
            {i.priority === 'high' && <Badge tone="danger">High</Badge>}
            {i.room && <span className="text-xs text-muted">{i.room}</span>}
          </div>
          {i.target_date && <p className="mt-0.5 text-xs text-muted">🎯 {new Date(i.target_date).toLocaleDateString()}</p>}
          {i.description && <p className="mt-1 whitespace-pre-wrap text-sm text-muted-strong">{i.description}</p>}
        </div>
        <div className="flex flex-shrink-0 items-center gap-1">
          <Select value={i.status} onChange={e => setStatus(i, e.target.value)} className="!min-h-[34px] !w-auto !py-1 text-xs">
            {IMPROVEMENT_STATUSES.map(s => <option key={s} value={s}>{cap(s)}</option>)}
          </Select>
          <div className="flex items-center gap-1 sm:opacity-0 transition-opacity sm:group-hover:opacity-100">
            <EditAction onClick={() => startEdit(i)} label={i.title} />
            <DeleteAction onClick={() => remove(i)} label={i.title} />
          </div>
        </div>
      </div>
    </Card>
  )

  return (
    <div className="flex flex-col gap-4">
      {open ? (
        <Card title={editId ? 'Edit improvement' : 'New improvement'}>
          <form onSubmit={save} className="flex flex-col gap-3">
            <Input placeholder="e.g. Repaint the living room" value={f.title} onChange={e => set('title', e.target.value)} autoFocus />
            <div className="grid gap-3 sm:grid-cols-3">
              <Field label="Status">
                <Select value={f.status} onChange={e => set('status', e.target.value)}>
                  {IMPROVEMENT_STATUSES.map(s => <option key={s} value={s}>{cap(s)}</option>)}
                </Select>
              </Field>
              <Field label="Priority">
                <Select value={f.priority} onChange={e => set('priority', e.target.value)}>
                  {['low', 'medium', 'high'].map(p => <option key={p} value={p}>{cap(p)}</option>)}
                </Select>
              </Field>
              <Field label="Room"><Input value={f.room} onChange={e => set('room', e.target.value)} /></Field>
            </div>
            <Field label="Target date (optional)">
              <DateTimeField value={f.target_date} allDay={f.is_all_day}
                onChange={({ value, allDay }) => setF(prev => ({ ...prev, target_date: value, is_all_day: allDay }))} />
            </Field>
            <Field label="Assigned to">
              <AssigneeSelect people={people} value={f.assigned_to_person_ids}
                onChange={v => set('assigned_to_person_ids', v)} className={fieldClass} />
            </Field>
            <Field label="Details"><Textarea rows={3} value={f.description} onChange={e => set('description', e.target.value)} /></Field>
            <div className="flex justify-end gap-2">
              <Button type="button" variant="ghost" size="sm" onClick={() => setOpen(false)}>Cancel</Button>
              <Button type="submit" size="sm" loading={saving} disabled={!f.title.trim()}>Save</Button>
            </div>
          </form>
        </Card>
      ) : (
        <Button size="sm" onClick={startAdd} className="self-start">+ New improvement</Button>
      )}

      {items.length === 0 ? (
        <EmptyState icon="🛠" title="No improvements yet" hint="Track renovations, room makeovers and to-do improvements — big or small." />
      ) : (
        <div className="flex flex-col gap-4">
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">{openItems.map(card)}</div>
          {doneItems.length > 0 && (
            <details>
              <summary className="cursor-pointer text-sm font-semibold text-muted">Done &amp; cancelled ({doneItems.length})</summary>
              <div className="mt-3 grid grid-cols-1 gap-3 lg:grid-cols-2">{doneItems.map(card)}</div>
            </details>
          )}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Contacts (service providers) tab
// ---------------------------------------------------------------------------

function ContactsTab({ onError }: { onError: (m: string) => void }) {
  const [providers, setProviders] = useState<ServiceProvider[]>([])
  const [loading, setLoading] = useState(true)
  const [open, setOpen] = useState(false)
  const [editId, setEditId] = useState<number | null>(null)
  const blank = { name: '', trade: 'other', company: '', phone: '', email: '', website: '', last_used_at: '', notes: '' }
  const [f, setF] = useState(blank)
  const [saving, setSaving] = useState(false)
  const set = (k: string, v: string) => setF(prev => ({ ...prev, [k]: v }))

  const load = () => { api.getProviders().then(setProviders).catch(e => onError(errMsg(e))).finally(() => setLoading(false)) }
  useEffect(load, [])

  const startAdd = () => { setEditId(null); setF(blank); setOpen(true) }
  const startEdit = (p: ServiceProvider) => {
    setEditId(p.id)
    setF({ name: p.name, trade: p.trade, company: p.company, phone: p.phone, email: p.email, website: p.website, last_used_at: p.last_used_at ?? '', notes: p.notes })
    setOpen(true)
  }

  const save = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!f.name.trim()) return
    setSaving(true)
    const payload = { ...f, last_used_at: f.last_used_at || null }
    try {
      if (editId) await api.updateProvider(editId, payload)
      else await api.createProvider(payload)
      setOpen(false); load()
    } catch (e) { onError(errMsg(e)) } finally { setSaving(false) }
  }
  const remove = async (p: ServiceProvider) => {
    if (!(await confirmDialog({ title: `Delete "${p.name}"?`, confirmLabel: 'Delete' }))) return
    try { await api.deleteProvider(p.id); load() } catch (e) { onError(errMsg(e)) }
  }

  if (loading) return <div className="h-32 rounded-2xl bg-sunken animate-pulse" />

  return (
    <div className="flex flex-col gap-4">
      {open ? (
        <Card title={editId ? 'Edit contact' : 'New contact'}>
          <form onSubmit={save} className="flex flex-col gap-3">
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Name"><Input value={f.name} onChange={e => set('name', e.target.value)} placeholder="e.g. Bob's Plumbing" autoFocus /></Field>
              <Field label="Trade">
                <Select value={f.trade} onChange={e => set('trade', e.target.value)}>
                  {TRADES.map(t => <option key={t} value={t}>{cap(t)}</option>)}
                </Select>
              </Field>
              <Field label="Company"><Input value={f.company} onChange={e => set('company', e.target.value)} /></Field>
              <Field label="Phone"><Input value={f.phone} onChange={e => set('phone', e.target.value)} /></Field>
              <Field label="Email"><Input value={f.email} onChange={e => set('email', e.target.value)} /></Field>
              <Field label="Website"><Input value={f.website} onChange={e => set('website', e.target.value)} placeholder="https://…" /></Field>
              <Field label="Last used"><input type="date" className={fieldClass} value={f.last_used_at} onChange={e => set('last_used_at', e.target.value)} /></Field>
            </div>
            <Field label="Notes"><Textarea rows={2} value={f.notes} onChange={e => set('notes', e.target.value)} /></Field>
            <div className="flex justify-end gap-2">
              <Button type="button" variant="ghost" size="sm" onClick={() => setOpen(false)}>Cancel</Button>
              <Button type="submit" size="sm" loading={saving} disabled={!f.name.trim()}>Save</Button>
            </div>
          </form>
        </Card>
      ) : (
        <Button size="sm" onClick={startAdd} className="self-start">+ New contact</Button>
      )}

      {providers.length === 0 ? (
        <EmptyState icon="📇" title="No contacts yet" hint="Keep your plumber, electrician, gas engineer and other trades in one place." />
      ) : (
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
          {providers.map(p => (
            <Card key={p.id} className="group">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="font-bold text-ink">{p.name}</h3>
                    <Badge>{cap(p.trade)}</Badge>
                  </div>
                  {p.company && <p className="text-sm text-muted">{p.company}</p>}
                  <div className="mt-1 flex flex-wrap gap-x-3 text-sm">
                    {p.phone && <a href={`tel:${p.phone}`} className="text-primary hover:underline">📞 {p.phone}</a>}
                    {p.email && <a href={`mailto:${p.email}`} className="text-primary hover:underline">✉ {p.email}</a>}
                    {p.website && <a href={p.website} target="_blank" rel="noreferrer" className="text-primary hover:underline">🌐 Site</a>}
                  </div>
                  {p.last_used_at && <p className="mt-0.5 text-xs text-muted">Last used {new Date(p.last_used_at).toLocaleDateString()}</p>}
                  {p.notes && <p className="mt-1 whitespace-pre-wrap text-sm text-muted-strong">{p.notes}</p>}
                </div>
                <div className="flex flex-shrink-0 items-center gap-1 sm:opacity-0 transition-opacity sm:group-hover:opacity-100">
                  <EditAction onClick={() => startEdit(p)} label={p.name} />
                  <DeleteAction onClick={() => remove(p)} label={p.name} />
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Usage — metered water/electricity/gas bills and what they plot
// ---------------------------------------------------------------------------

const UTILITY_TYPES: { value: UtilityType; label: string; icon: string }[] = [
  { value: 'electricity', label: 'Electricity', icon: '⚡' },
  { value: 'water', label: 'Water', icon: '💧' },
  { value: 'gas', label: 'Gas', icon: '🔥' },
  { value: 'other', label: 'Other', icon: '📊' },
]
const UTILITY_UNITS: { value: UtilityUnit; label: string }[] = [
  { value: 'kwh', label: 'kWh' }, { value: 'kl', label: 'kL' }, { value: 'litres', label: 'L' },
  { value: 'm3', label: 'm³' }, { value: 'mj', label: 'MJ' }, { value: 'therms', label: 'therms' },
  { value: 'other', label: 'units' },
]
// What a bill of each kind is normally measured in. Changing the type re-picks the unit unless
// the household has already chosen one for this bill.
const DEFAULT_UNIT: Record<UtilityType, UtilityUnit> = {
  electricity: 'kwh', water: 'kl', gas: 'mj', other: 'other',
}
const utilityIcon = (type: UtilityType) =>
  UTILITY_TYPES.find(row => row.value === type)?.icon ?? '📊'

const EMPTY_UTILITY_BILL = {
  utility_type: 'electricity' as UtilityType,
  usage_unit: 'kwh' as UtilityUnit,
  provider: '',
  period_start: '',
  period_end: '',
  usage_amount: '',
  amount: '',
  is_estimated: false,
  notes: '',
}

const num = (value: string | number, digits = 1) =>
  Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: digits })
const rate = (value: string) =>
  Number(value).toLocaleString(undefined, {
    style: 'currency', currency: 'AUD', minimumFractionDigits: 2, maximumFractionDigits: 4,
  })
const periodRange = (start: string, end: string) =>
  `${new Date(`${start}T00:00:00`).toLocaleDateString()} – ${new Date(`${end}T00:00:00`).toLocaleDateString()}`

/** Using more is the bad direction here, which is the opposite of most deltas in the app. */
function ChangeChip({ label, percent, measure }: { label: string; percent: string | null; measure: string }) {
  if (percent === null) return null
  const value = Number(percent)
  const flat = Math.abs(value) < 0.5
  const tone: BadgeTone = flat ? 'neutral' : value > 0 ? 'warning' : 'success'
  const arrow = flat ? '→' : value > 0 ? '↑' : '↓'
  return (
    <Badge tone={tone}>
      {measure} {arrow} {flat ? 'about the same' : `${Math.abs(value).toFixed(1)}%`} {label}
    </Badge>
  )
}

function UtilitySeriesCard({ series, onEdit, onDelete, canEdit }: {
  series: UtilitySeries
  onEdit: (id: number) => void
  onDelete: (point: UtilityPeriodPoint) => void
  canEdit: boolean
}) {
  const unit = series.unit_label
  const latest = series.latest
  const usagePoints: BarChartPoint[] = series.periods.map(point => ({
    key: point.id,
    label: point.label,
    value: Number(point.daily_usage),
    display: `${num(point.daily_usage, 2)} ${unit}`,
    detail: [
      periodRange(point.period_start, point.period_end),
      `${num(point.usage_amount)} ${unit} over ${point.days} days`,
    ],
    hatched: point.is_estimated,
  }))
  const costPoints: BarChartPoint[] = series.periods.map(point => ({
    key: point.id,
    label: point.label,
    value: Number(point.daily_cost),
    display: money(point.daily_cost),
    detail: [
      periodRange(point.period_start, point.period_end),
      `${money(point.amount)} over ${point.days} days`,
      ...(point.unit_cost ? [`${rate(point.unit_cost)} per ${unit}`] : []),
    ],
    hatched: point.is_estimated,
  }))

  return (
    <Card>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-bold text-ink">
          {utilityIcon(series.utility_type)} {series.label}
        </h2>
        <span className="text-xs text-muted">
          {series.bill_count} {series.bill_count === 1 ? 'bill' : 'bills'} logged
        </span>
      </div>

      {latest && (
        <div className="mt-3 grid gap-3 sm:grid-cols-3">
          <StatCard
            label="Latest bill"
            value={money(latest.amount)}
            hint={`${latest.label} · ${latest.days} days`}
          />
          <StatCard
            label="Used per day"
            value={`${num(latest.daily_usage, 2)} ${unit}`}
            hint={`${num(series.average_daily_usage, 2)} ${unit} average across every bill`}
          />
          <StatCard
            label="Effective rate"
            value={latest.unit_cost ? `${rate(latest.unit_cost)} / ${unit}` : '—'}
            hint="Total charged divided by what was used, supply charges included"
          />
        </div>
      )}

      {series.changes.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {series.changes.map(change => (
            <div key={change.label} className="flex flex-wrap gap-2">
              <ChangeChip label={change.label} percent={change.usage_percent} measure="Usage" />
              <ChangeChip label={change.label} percent={change.cost_percent} measure="Cost" />
            </div>
          ))}
        </div>
      )}
      {series.bill_count > 1 && (
        <p className="mt-2 text-xs text-muted">
          Every figure is per day, so a long bill is not mistaken for a heavy one.
        </p>
      )}

      <div className="mt-4 grid gap-5 lg:grid-cols-2">
        <div>
          <p className="text-sm font-semibold text-ink">Used per day ({unit})</p>
          <BarChart
            className="mt-3"
            points={usagePoints}
            ariaLabel={`${series.label} used per day, by billing period`}
            hatchLabel="Estimated meter read"
          />
        </div>
        <div>
          <p className="text-sm font-semibold text-ink">Cost per day</p>
          <BarChart
            className="mt-3"
            points={costPoints}
            ariaLabel={`${series.label} cost per day, by billing period`}
            hatchLabel="Estimated meter read"
          />
        </div>
      </div>

      <details className="mt-4 border-t border-line pt-3">
        <summary className="cursor-pointer text-sm font-semibold text-muted">
          Every bill ({series.bill_count})
        </summary>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[34rem] text-left text-sm tabular-nums">
            <thead className="text-xs uppercase tracking-wide text-muted">
              <tr>
                <th scope="col" className="py-1.5 pr-3 font-bold">Period</th>
                <th scope="col" className="py-1.5 pr-3 font-bold">Days</th>
                <th scope="col" className="py-1.5 pr-3 font-bold">Used ({unit})</th>
                <th scope="col" className="py-1.5 pr-3 font-bold">Cost</th>
                <th scope="col" className="py-1.5 pr-3 font-bold">Rate</th>
                {canEdit && <th scope="col" className="py-1.5 text-right font-bold">Actions</th>}
              </tr>
            </thead>
            <tbody>
              {[...series.periods].reverse().map(point => (
                <tr key={point.id} className="border-t border-line">
                  <td className="py-2 pr-3 text-ink">
                    {periodRange(point.period_start, point.period_end)}
                    {point.is_estimated && <span className="ml-2 text-xs text-muted">estimated</span>}
                  </td>
                  <td className="py-2 pr-3 text-muted">{point.days}</td>
                  <td className="py-2 pr-3 text-muted-strong">{num(point.usage_amount)}</td>
                  <td className="py-2 pr-3 text-muted-strong">{money(point.amount)}</td>
                  <td className="py-2 pr-3 text-muted">{point.unit_cost ? rate(point.unit_cost) : '—'}</td>
                  {canEdit && (
                    <td className="py-2">
                      <div className="flex justify-end gap-1">
                        <EditAction onClick={() => onEdit(point.id)} label={point.label} />
                        <DeleteAction onClick={() => onDelete(point)} label={point.label} />
                      </div>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </Card>
  )
}

function UtilitiesTab({ onError, canEdit }: { onError: (m: string) => void; canEdit: boolean }) {
  const [series, setSeries] = useState<UtilitySeries[]>([])
  const [bills, setBills] = useState<UtilityBill[]>([])
  const [loading, setLoading] = useState(true)
  const [open, setOpen] = useState(false)
  const [editId, setEditId] = useState<number | null>(null)
  const [f, setF] = useState(EMPTY_UTILITY_BILL)
  const [saving, setSaving] = useState(false)
  const set = (key: string, value: unknown) => setF(prev => ({ ...prev, [key]: value }))

  const load = async () => {
    try {
      const [usage, rows] = await Promise.all([api.getUtilityUsage(), api.getUtilityBills()])
      setSeries(usage.series)
      setBills(rows)
    } catch (e) { onError(errMsg(e)) } finally { setLoading(false) }
  }
  useEffect(() => { void load() }, [])

  const startAdd = () => {
    setEditId(null)
    // Most households log the same utility repeatedly, so start where they left off.
    const previous = bills[0]
    setF(previous
      ? { ...EMPTY_UTILITY_BILL, utility_type: previous.utility_type, usage_unit: previous.usage_unit, provider: previous.provider }
      : EMPTY_UTILITY_BILL)
    setOpen(true)
  }

  const startEdit = (id: number) => {
    const bill = bills.find(row => row.id === id)
    if (!bill) return
    setEditId(bill.id)
    setF({
      utility_type: bill.utility_type, usage_unit: bill.usage_unit, provider: bill.provider,
      period_start: bill.period_start, period_end: bill.period_end,
      usage_amount: bill.usage_amount, amount: bill.amount,
      is_estimated: bill.is_estimated, notes: bill.notes,
    })
    setOpen(true)
  }

  const changeType = (value: UtilityType) =>
    setF(prev => ({
      ...prev,
      utility_type: value,
      // Only re-pick the unit while it is still the previous type's default.
      usage_unit: prev.usage_unit === DEFAULT_UNIT[prev.utility_type] ? DEFAULT_UNIT[value] : prev.usage_unit,
    }))

  const save = async (e: FormEvent) => {
    e.preventDefault()
    if (!f.period_start || !f.period_end || f.usage_amount === '') return
    setSaving(true)
    const payload = { ...f, amount: f.amount || '0.00' }
    try {
      if (editId) await api.updateUtilityBill(editId, payload)
      else await api.createUtilityBill(payload)
      setOpen(false)
      await load()
    } catch (e) { onError(errMsg(e)) } finally { setSaving(false) }
  }

  const remove = async (point: UtilityPeriodPoint) => {
    if (!(await confirmDialog({
      title: `Delete the bill for ${point.label}?`,
      message: 'It disappears from the graphs and the comparisons.',
      confirmLabel: 'Delete',
    }))) return
    try { await api.deleteUtilityBill(point.id); await load() } catch (e) { onError(errMsg(e)) }
  }

  if (loading) return <div className="h-40 animate-pulse rounded-2xl bg-sunken" />

  const unitLabel = UTILITY_UNITS.find(row => row.value === f.usage_unit)?.label ?? 'units'

  return (
    <div className="flex flex-col gap-4">
      {open ? (
        <Card title={editId ? 'Edit bill' : 'New bill'}>
          <form onSubmit={save} className="flex flex-col gap-3">
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              <Field label="Utility">
                <Select value={f.utility_type} onChange={e => changeType(e.target.value as UtilityType)}>
                  {UTILITY_TYPES.map(row => <option key={row.value} value={row.value}>{row.label}</option>)}
                </Select>
              </Field>
              <Field label="Period from">
                <input type="date" className={fieldClass} value={f.period_start}
                  onChange={e => set('period_start', e.target.value)} />
              </Field>
              <Field label="Period to">
                <input type="date" className={fieldClass} value={f.period_end}
                  onChange={e => set('period_end', e.target.value)} />
              </Field>
              <Field label={`Amount used (${unitLabel})`}>
                <Input type="number" min="0" step="0.001" inputMode="decimal" value={f.usage_amount}
                  onChange={e => set('usage_amount', e.target.value)} placeholder="e.g. 912" />
              </Field>
              <Field label="Measured in">
                <Select value={f.usage_unit} onChange={e => set('usage_unit', e.target.value as UtilityUnit)}>
                  {UTILITY_UNITS.map(row => <option key={row.value} value={row.value}>{row.label}</option>)}
                </Select>
              </Field>
              <Field label="Total cost" hint="Everything charged, supply charges included.">
                <Input type="number" min="0" step="0.01" inputMode="decimal" value={f.amount}
                  onChange={e => set('amount', e.target.value)} placeholder="e.g. 420.50" />
              </Field>
              <Field label="Provider" className="sm:col-span-2">
                <Input value={f.provider} onChange={e => set('provider', e.target.value)} />
              </Field>
            </div>
            <label className="flex min-h-[44px] items-center gap-2 text-sm text-ink">
              <input type="checkbox" checked={f.is_estimated}
                onChange={e => set('is_estimated', e.target.checked)} />
              The meter was estimated, not read
            </label>
            <Field label="Notes"><Textarea rows={2} value={f.notes} onChange={e => set('notes', e.target.value)} /></Field>
            <div className="flex justify-end gap-2">
              <Button type="button" variant="ghost" size="sm" onClick={() => setOpen(false)}>Cancel</Button>
              <Button type="submit" size="sm" loading={saving}
                disabled={!f.period_start || !f.period_end || f.usage_amount === ''}>Save</Button>
            </div>
          </form>
        </Card>
      ) : (
        canEdit && <Button size="sm" onClick={startAdd} className="self-start">+ Add a bill</Button>
      )}

      {series.length === 0 ? (
        <EmptyState
          icon="⚡"
          title="No usage logged yet"
          hint="Add a water or electricity bill — the period, how much was used and what it cost — and the graphs build themselves from there."
          action={canEdit && !open ? <Button onClick={startAdd}>Add a bill</Button> : undefined}
        />
      ) : (
        series.map(row => (
          <UtilitySeriesCard
            key={row.utility_type}
            series={row}
            canEdit={canEdit}
            onEdit={startEdit}
            onDelete={remove}
          />
        ))
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Costs & cover — password protected Homestead details for Solace-owned bills
// ---------------------------------------------------------------------------

const EMPTY_POLICY = {
  policy_type: 'building_contents', policy_number: '',
  standard_excess: '', additional_excesses: '', coverage_summary: '',
  contact_phone: '', portal_url: '',
}

const EMPTY_COST = {
  cost_type: 'rates', account_number: '',
}

function FinanceTab({ onError }: { onError: (m: string) => void }) {
  const [unlocked, setUnlocked] = useState(false)
  const [checking, setChecking] = useState(true)
  const [policies, setPolicies] = useState<InsurancePolicy[]>([])
  const [costs, setCosts] = useState<HouseholdCost[]>([])
  const [policyForm, setPolicyForm] = useState(EMPTY_POLICY)
  const [costForm, setCostForm] = useState(EMPTY_COST)
  const [policyEdit, setPolicyEdit] = useState<number | null>(null)
  const [costEdit, setCostEdit] = useState<number | null>(null)
  const [showPolicyForm, setShowPolicyForm] = useState(false)
  const [showCostForm, setShowCostForm] = useState(false)
  const [saving, setSaving] = useState(false)
  const [financeQuery, setFinanceQuery] = useState('')

  const load = async () => {
    const [p, c] = await Promise.all([api.getInsurancePolicies(), api.getHouseholdCosts()])
    setPolicies(p)
    setCosts(c)
    setUnlocked(true)
  }

  useEffect(() => {
    load().catch(() => {}).finally(() => setChecking(false))
  }, [])

  if (checking) return <div className="h-40 rounded-2xl bg-sunken animate-pulse" />
  if (!unlocked) {
    return (
      <SensitiveGate
        nodeName="costs & cover"
        hint="Policy numbers and household costs are financial data, so your password is required."
        onUnlock={() => { void load() }}
      />
    )
  }

  const startPolicy = (policy: InsurancePolicy) => {
    setPolicyEdit(policy.id)
    setPolicyForm({
      policy_type: policy.policy_type, policy_number: policy.policy_number,
      standard_excess: policy.standard_excess, additional_excesses: policy.additional_excesses,
      coverage_summary: policy.coverage_summary, contact_phone: policy.contact_phone,
      portal_url: policy.portal_url,
    })
    setShowPolicyForm(true)
  }

  const savePolicy = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!policyEdit) return
    setSaving(true)
    const payload = {
      ...policyForm,
      standard_excess: policyForm.standard_excess || '0.00',
    }
    try {
      await api.updateInsurancePolicy(policyEdit, payload)
      setShowPolicyForm(false)
      await load()
    } catch (e) {
      onError(errMsg(e))
    } finally {
      setSaving(false)
    }
  }

  const startCost = (cost: HouseholdCost) => {
    setCostEdit(cost.id)
    setCostForm({ cost_type: cost.cost_type, account_number: cost.account_number })
    setShowCostForm(true)
  }

  const saveCost = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!costEdit) return
    setSaving(true)
    try {
      await api.updateHouseholdCost(costEdit, costForm)
      setShowCostForm(false)
      await load()
    } catch (e) {
      onError(errMsg(e))
    } finally {
      setSaving(false)
    }
  }

  const setPolicy = (key: string, value: unknown) =>
    setPolicyForm(prev => ({ ...prev, [key]: value }))
  const setCost = (key: string, value: unknown) =>
    setCostForm(prev => ({ ...prev, [key]: value }))

  const annualised = (amount: string, cycle: string) => {
    const factor: Record<string, number> = {
      weekly: 52, fortnightly: 26, monthly: 12, quarterly: 4, half_yearly: 2, yearly: 1,
    }
    return Number(amount || 0) * (factor[cycle] ?? 0)
  }
  const knownAnnual = [
    ...policies.filter(p => p.is_active).map(p => annualised(p.premium_amount, p.billing_cycle)),
    ...costs.filter(c => c.is_active).map(c => annualised(c.amount, c.billing_cycle)),
  ].reduce((sum, value) => sum + value, 0)
  const q = financeQuery.trim().toLowerCase()
  const shownPolicies = q
    ? policies.filter(p => [p.name, p.provider, p.policy_number, p.policy_type].some(v => v.toLowerCase().includes(q)))
    : policies
  const shownCosts = q
    ? costs.filter(c => [c.name, c.provider, c.account_number, c.cost_type].some(v => v.toLowerCase().includes(q)))
    : costs

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-3 rounded-xl bg-primary-soft px-4 py-3 text-sm sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="font-semibold text-ink">Bills are managed in Solace</p>
          <p className="mt-0.5 text-muted-strong">This page shows home-related bills. Change amounts, dates, recurrence, payment status and autopay in Solace; Homestead keeps only policy and account details.</p>
        </div>
        <Link to="/solace?tab=bills" className="flex min-h-11 flex-shrink-0 items-center font-semibold text-primary">Open Solace bills →</Link>
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        <Card><p className="text-2xl font-extrabold text-ink">{policies.filter(p => p.is_active).length}</p><p className="text-sm text-muted">Active policies</p></Card>
        <Card><p className="text-2xl font-extrabold text-ink">{costs.filter(c => c.is_active).length}</p><p className="text-sm text-muted">Active home costs</p></Card>
        <Card>
          <p className="text-2xl font-extrabold text-ink">{money(knownAnnual)}</p>
          <p className="text-sm text-muted">Known annualised cost</p>
          <p className="mt-1 text-xs text-muted">Excludes variable and custom cycles</p>
        </Card>
      </div>

      <Input
        value={financeQuery}
        onChange={e => setFinanceQuery(e.target.value)}
        placeholder="Search policies, providers, account or policy numbers…"
      />

      <section className="flex flex-col gap-3">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-bold text-ink">Insurance</h2>
            <p className="text-sm text-muted">Solace supplies premiums and renewals; policy details stay here.</p>
          </div>
        </div>

        {showPolicyForm && (
          <Card title="Edit policy details">
            <form onSubmit={savePolicy} className="flex flex-col gap-3">
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                <Field label="Policy type"><Select autoFocus value={policyForm.policy_type} onChange={e => setPolicy('policy_type', e.target.value)}>{POLICY_TYPES.map(v => <option key={v} value={v}>{cap(v)}</option>)}</Select></Field>
                <Field label="Policy number"><Input value={policyForm.policy_number} onChange={e => setPolicy('policy_number', e.target.value)} autoComplete="off" /></Field>
                <Field label="Standard excess"><Input type="number" min="0" step="0.01" value={policyForm.standard_excess} onChange={e => setPolicy('standard_excess', e.target.value)} /></Field>
                <Field label="Claims phone"><Input type="tel" value={policyForm.contact_phone} onChange={e => setPolicy('contact_phone', e.target.value)} /></Field>
              </div>
              <Field label="Other excesses" hint="For example: flood $1,500; accidental damage $500."><Textarea rows={2} value={policyForm.additional_excesses} onChange={e => setPolicy('additional_excesses', e.target.value)} /></Field>
              <Field label="Coverage summary"><Textarea rows={2} value={policyForm.coverage_summary} onChange={e => setPolicy('coverage_summary', e.target.value)} /></Field>
              <Field label="Policy portal"><Input type="url" value={policyForm.portal_url} onChange={e => setPolicy('portal_url', e.target.value)} placeholder="https://…" /></Field>
              <div className="flex justify-end gap-2">
                <Button type="button" variant="ghost" size="sm" onClick={() => setShowPolicyForm(false)}>Cancel</Button>
                <Button type="submit" size="sm" loading={saving}>Save details</Button>
              </div>
            </form>
          </Card>
        )}

        {shownPolicies.length === 0 ? (
          <EmptyState icon="🛡️" title={q ? 'No matching policies' : 'No home insurance bills yet'} hint={q ? 'Try a different search.' : 'Create an insurance bill in Solace and choose “Home insurance / cover”.'} />
        ) : (
          <div className="grid gap-3 lg:grid-cols-2">
            {shownPolicies.map(policy => {
              const due = dueLabel(policy.next_renewal_at)
              return (
                <Card key={policy.id} className={!policy.is_active ? 'opacity-65' : ''}>
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="font-bold text-ink">{policy.name}</h3>
                        <Badge>{cap(policy.policy_type)}</Badge>
                        {!policy.is_active && <Badge tone="neutral">Inactive</Badge>}
                        {policy.solace_bill_ref && (
                          <Link to={`/solace?tab=bills&q=${encodeURIComponent(policy.name)}`} aria-label={`Open ${policy.name} in Solace`}>
                            <Badge tone="success">Managed in Solace →</Badge>
                          </Link>
                        )}
                      </div>
                      <p className="mt-1 text-sm text-muted">{policy.provider || 'No insurer'} · {money(policy.premium_amount)} / {cap(policy.billing_cycle).toLowerCase()}</p>
                      {policy.policy_number && <p className="text-sm text-muted-strong">Policy {policy.policy_number}</p>}
                      <div className="mt-2 flex flex-wrap gap-2">
                        {due && <Badge tone={due.tone}>Renews {due.text.toLowerCase()}</Badge>}
                        <Badge tone="neutral">Excess {money(policy.standard_excess)}</Badge>
                      </div>
                      {policy.additional_excesses && <p className="mt-2 whitespace-pre-wrap text-sm text-muted-strong">{policy.additional_excesses}</p>}
                      {policy.coverage_summary && <p className="mt-2 whitespace-pre-wrap text-sm text-muted">{policy.coverage_summary}</p>}
                      <div className="mt-2 flex flex-wrap gap-3 text-sm">
                        {policy.contact_phone && <a href={`tel:${policy.contact_phone}`} className="text-primary hover:underline">📞 Claims</a>}
                        {policy.portal_url && <a href={policy.portal_url} target="_blank" rel="noreferrer" className="text-primary hover:underline">Open portal ↗</a>}
                      </div>
                    </div>
                    <div className="flex flex-shrink-0 justify-end gap-1 border-t border-line pt-2 sm:border-0 sm:pt-0">
                      <EditAction onClick={() => startPolicy(policy)} label={policy.name} />
                    </div>
                  </div>
                </Card>
              )
            })}
          </div>
        )}
      </section>

      <section className="flex flex-col gap-3">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-bold text-ink">Rates &amp; household services</h2>
            <p className="text-sm text-muted">A read-through of home-related Solace bills, with optional account details.</p>
          </div>
        </div>

        {showCostForm && (
          <Card title="Edit home account details">
            <form onSubmit={saveCost} className="flex flex-col gap-3">
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Home cost type"><Select autoFocus value={costForm.cost_type} onChange={e => setCost('cost_type', e.target.value)}>{COST_TYPES.map(v => <option key={v} value={v}>{cap(v)}</option>)}</Select></Field>
                <Field label="Account number"><Input value={costForm.account_number} onChange={e => setCost('account_number', e.target.value)} autoComplete="off" /></Field>
              </div>
              <div className="flex justify-end gap-2">
                <Button type="button" variant="ghost" size="sm" onClick={() => setShowCostForm(false)}>Cancel</Button>
                <Button type="submit" size="sm" loading={saving}>Save details</Button>
              </div>
            </form>
          </Card>
        )}

        {shownCosts.length === 0 ? (
          <EmptyState icon="🧾" title={q ? 'No matching household costs' : 'No home-related bills yet'} hint={q ? 'Try a different search.' : 'Create the bill in Solace and organise it as a home cost.'} />
        ) : (
          <div className="grid gap-3 lg:grid-cols-2">
            {shownCosts.map(cost => {
              const due = dueLabel(cost.next_due_at)
              return (
                <Card key={cost.id} className={!cost.is_active ? 'opacity-65' : ''}>
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="font-bold text-ink">{cost.name}</h3>
                        <Badge>{cap(cost.cost_type)}</Badge>
                        {!cost.is_active && <Badge tone="neutral">Inactive</Badge>}
                        {cost.solace_bill_ref && (
                          <Link to={`/solace?tab=bills&q=${encodeURIComponent(cost.name)}`} aria-label={`Open ${cost.name} in Solace`}>
                            <Badge tone="success">Managed in Solace →</Badge>
                          </Link>
                        )}
                      </div>
                      <p className="mt-1 text-sm text-muted">{cost.provider || cap(cost.cost_type)} · {money(cost.amount)} / {cap(cost.billing_cycle).toLowerCase()}</p>
                      {cost.account_number && <p className="text-sm text-muted-strong">Account {cost.account_number}</p>}
                      {due && <div className="mt-2"><Badge tone={due.tone}>Due {due.text.toLowerCase()}</Badge></div>}
                      {cost.notes && <p className="mt-2 whitespace-pre-wrap text-sm text-muted">{cost.notes}</p>}
                    </div>
                    <div className="flex flex-shrink-0 justify-end gap-1 border-t border-line pt-2 sm:border-0 sm:pt-0">
                      <EditAction onClick={() => startCost(cost)} label={cost.name} />
                    </div>
                  </div>
                </Card>
              )
            })}
          </div>
        )}
      </section>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Search results
// ---------------------------------------------------------------------------

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <p className="text-xs font-semibold uppercase tracking-wide text-muted">{title}</p>
      {children}
    </div>
  )
}

function SearchResults({ results }: { results: HomesteadSearchResults }) {
  const empty = !results.appliances.length && !results.maintenance.length && !results.providers.length && !results.improvements.length && !results.rooms.length && !results.room_items.length
  if (empty) return <p className="py-8 text-center text-sm text-muted">No matches.</p>
  const row = (key: string, href: string, main: string, sub?: string) => (
    <Link key={key} to={href} className="flex min-h-11 items-center justify-between gap-3 rounded-xl bg-sunken px-3 py-2.5 text-sm transition-colors hover:bg-primary-soft hover:text-primary">
      <span className="text-ink">{main}</span>{sub && <span className="text-xs text-muted">{sub}</span>}
    </Link>
  )
  return (
    <div className="flex flex-col gap-4">
      {results.maintenance.length > 0 && <Section title="Maintenance">{results.maintenance.map(t => row(`m${t.id}`, '/homestead?tab=maintenance', t.title, cap(t.category)))}</Section>}
      {results.appliances.length > 0 && <Section title="Appliances">{results.appliances.map(a => row(`a${a.id}`, '/homestead?tab=appliances', a.name, [a.brand, a.model_number].filter(Boolean).join(' ')))}</Section>}
      {results.improvements.length > 0 && <Section title="Improvements">{results.improvements.map(i => row(`i${i.id}`, '/homestead?tab=improvements', i.title, cap(i.status)))}</Section>}
      {results.providers.length > 0 && <Section title="Contacts">{results.providers.map(p => row(`p${p.id}`, '/homestead?tab=contacts', p.name, cap(p.trade)))}</Section>}
      {results.rooms.length > 0 && <Section title="Rooms & areas">{results.rooms.map(room => (
        <Link key={room.id} to={`/homestead/rooms/${room.id}`} className="flex min-h-11 items-center justify-between gap-3 rounded-xl bg-sunken px-3 py-2.5 text-sm transition-colors hover:bg-primary-soft hover:text-primary">
          <span>{room.icon || '🚪'} {room.name}</span><span className="text-xs text-muted">Open room →</span>
        </Link>
      ))}</Section>}
      {results.room_items.length > 0 && <Section title="Room plans">{results.room_items.map(item => (
        <Link key={item.id} to={`/homestead/rooms/${item.room_id}`} className="flex min-h-11 items-center justify-between gap-3 rounded-xl bg-sunken px-3 py-2.5 text-sm transition-colors hover:bg-primary-soft hover:text-primary">
          <span>{item.title}</span><span className="text-xs text-muted">{cap(item.item_type)} →</span>
        </Link>
      ))}</Section>}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Homestead page
// ---------------------------------------------------------------------------

type Tab = 'overview' | 'rooms' | 'maintenance' | 'appliances' | 'pool' | 'usage' | 'improvements' | 'contacts' | 'finances'
// Every tab belongs here — a key left out is silently rewritten to overview when it is linked to.
const TAB_KEYS: Tab[] = [
  'overview', 'rooms', 'maintenance', 'appliances', 'pool', 'usage', 'improvements',
  'contacts', 'finances',
]

export function HomesteadPage() {
  const { user } = useAuth()
  const { enabledKeys, loading: stacksLoading } = useStacks()
  const [tab, setTab] = useUrlTab<Tab>('overview', TAB_KEYS)
  const [people, setPeople] = useState<Person[]>([])
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useUrlQueryState()
  const [results, setResults] = useState<HomesteadSearchResults | null>(null)

  useEffect(() => { api.getPeople().then(setPeople).catch(() => {}) }, [])

  useEffect(() => {
    const q = query.trim()
    if (q.length < 2) { setResults(null); return }
    const id = setTimeout(() => {
      api.searchHomestead(q).then(setResults).catch(e => setError(errMsg(e)))
    }, 300)
    return () => clearTimeout(id)
  }, [query])

  const defaultAssignee = personIdForUser(people, user?.id)
  const canUseMoney = enabledKeys.has('solace')

  useEffect(() => {
    if (!stacksLoading && tab === 'finances' && !canUseMoney) setTab('overview')
  }, [canUseMoney, setTab, stacksLoading, tab])

  return (
    <div className="flex flex-col gap-5">
      <PageHeader title="Our home" icon="🏠" />

      <SearchField
        value={query}
        onChange={e => setQuery(e.target.value)}
        onClear={() => setQuery('')}
        placeholder="Search rooms, plans, maintenance, appliances, contacts…"
      />

      {error && (
        <div className="flex items-center justify-between gap-3 rounded-xl bg-danger-soft px-4 py-2.5 text-sm text-danger">
          <span>{error}</span>
          <button onClick={() => setError(null)} aria-label="Dismiss">×</button>
        </div>
      )}

      {results !== null ? (
        <SearchResults results={results} />
      ) : (
        <>
          <Tabs
            tabs={[
              { key: 'overview', label: 'overview' },
              { key: 'rooms', label: 'rooms' },
              { key: 'maintenance', label: 'maintenance' },
              { key: 'appliances', label: 'appliances' },
              { key: 'pool', label: 'pool & spa' },
              { key: 'usage', label: 'power & water' },
              { key: 'improvements', label: 'improvements' },
              { key: 'contacts', label: 'contacts' },
              ...(canUseMoney ? [{ key: 'finances' as const, label: 'costs & cover' }] : []),
            ]}
            active={tab}
            onChange={setTab}
            className="w-full sm:w-fit"
            mobileSelectLabel="Homestead section"
          />

          {tab === 'overview' && <OverviewTab onError={setError} onGoTab={setTab} canUseMoney={canUseMoney} />}
          {tab === 'rooms' && <RoomsTab onError={setError} canEdit={Boolean(user && user.role !== 'guest' && !user.is_child_account)} />}
          {tab === 'maintenance' && <MaintenanceTab people={people} defaultAssignee={defaultAssignee} onError={setError} canUseMoney={canUseMoney} />}
          {tab === 'appliances' && <AppliancesTab onError={setError} />}
          {tab === 'pool' && <PoolTab onError={setError} canEdit={Boolean(user && user.role !== 'guest' && !user.is_child_account)} />}
          {tab === 'usage' && <UtilitiesTab onError={setError} canEdit={Boolean(user && user.role !== 'guest' && !user.is_child_account)} />}
          {tab === 'improvements' && <ImprovementsTab people={people} defaultAssignee={defaultAssignee} onError={setError} />}
          {tab === 'contacts' && <ContactsTab onError={setError} />}
          {tab === 'finances' && canUseMoney && <FinanceTab onError={setError} />}
        </>
      )}
    </div>
  )
}
