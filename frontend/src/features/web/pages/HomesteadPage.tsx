import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../../api/client'
import type {
  Appliance, Improvement, ImprovementStatus, MaintenanceTask, Person, Property,
  ServiceProvider, HomesteadSearchResults, InsurancePolicy, HouseholdCost,
  RoomAreaType, RoomListResponse,
} from '../../../api/types'
import { Card } from '../../../components/Card'
import { Button } from '../../../components/Button'
import { Field, Input, SearchField, Textarea, Select, fieldClass } from '../../../components/Field'
import { Tabs } from '../../../components/Tabs'
import { Badge, type BadgeTone } from '../../../components/Badge'
import { PageHeader } from '../../../components/PageHeader'
import { EmptyState } from '../../../components/EmptyState'
import { Modal } from '../../../components/Modal'
import { DateTimeField } from '../../../components/DateTimeField'
import { AssigneeSelect, personIdForUser } from '../../../components/AssigneeSelect'
import { useAuth } from '../../auth/AuthContext'
import { useUrlAction, useUrlQueryState, useUrlTab } from '../../../hooks/useUrlTab'

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
const BILLING_CYCLES = [
  'weekly', 'fortnightly', 'monthly', 'quarterly', 'half_yearly', 'yearly', 'variable', 'other',
]

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

function OverviewTab({ onError, onGoTab }: { onError: (m: string) => void; onGoTab: (t: Tab) => void }) {
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
    <button onClick={() => onGoTab(tab)} className="flex-1 rounded-2xl border border-line bg-surface p-4 text-left hover:bg-sunken/40">
      <div className="flex items-center justify-between">
        <span className="text-2xl font-extrabold text-ink">{n}</span>
        <Badge tone={n > 0 ? tone : 'neutral'}>{n > 0 ? 'view' : 'clear'}</Badge>
      </div>
      <p className="mt-1 text-sm text-muted">{label}</p>
    </button>
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
            <p className="text-sm text-muted">Insurance, rates and utilities are protected and synced into Solace.</p>
          </div>
          <Button variant="secondary" size="sm" onClick={() => onGoTab('finances')}>Open finances</Button>
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
              <Field label="Icon"><Input value={form.icon} onChange={e => setForm(f => ({ ...f, icon: e.target.value }))} placeholder="🛋️" /></Field>
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

      {data.rooms.length === 0 ? (
        <EmptyState icon="🚪" title="No rooms or areas yet" hint="Start with the spaces you want to plan — rooms, garage, garden, patio or any other area." />
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
      )}

      <div className="rounded-xl border border-dashed border-line px-4 py-3 text-sm text-muted">
        Floor-plan view is a future visual layer; every room already has a stable page for the map to open.
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Maintenance tab
// ---------------------------------------------------------------------------

function MaintenanceTab({ people, defaultAssignee, onError }: {
  people: Person[]; defaultAssignee: number | null; onError: (m: string) => void
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
    recurrence_rule: '', appliance_id: 0, provider_id: 0, assigned_to_person_id: defaultAssignee ?? 0, notes: '',
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

  const startAdd = () => { setEditId(null); setF({ ...blank, assigned_to_person_id: defaultAssignee ?? 0 }); setOpen(true) }
  const startEdit = (t: MaintenanceTask) => {
    setEditId(t.id)
    setF({
      title: t.title, category: t.category, next_due_at: t.next_due_at, is_all_day: t.is_all_day,
      recurrence_rule: t.recurrence_rule, appliance_id: t.appliance_id ?? 0, provider_id: t.provider_id ?? 0,
      assigned_to_person_id: t.assigned_to_person_id ?? 0, notes: t.notes,
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
      assigned_to_person_id: f.assigned_to_person_id || null,
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
    if (!confirm(`Delete "${t.title}"?`)) return
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
              <AssigneeSelect people={people} value={f.assigned_to_person_id || null}
                onChange={v => set('assigned_to_person_id', v ?? 0)} className={fieldClass} />
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
            const assignee = t.assigned_to_person_id ? people.find(p => p.id === t.assigned_to_person_id) : null
            return (
              <div key={t.id} className="group flex flex-col gap-3 rounded-xl border border-line p-3 sm:flex-row sm:items-center">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium text-ink">{t.title}</span>
                    <Badge>{cap(t.category)}</Badge>
                    {t.solace_bill_ref && (
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
                  {!t.solace_bill_ref && <Button size="sm" variant="ghost" onClick={() => startCost(t)}>Track cost</Button>}
                  <div className="flex items-center gap-1 sm:opacity-0 sm:transition-opacity sm:group-hover:opacity-100 sm:group-focus-within:opacity-100">
                    <button onClick={() => startEdit(t)} className="min-h-10 rounded-lg px-3 py-1 text-xs text-muted hover:bg-sunken hover:text-ink">Edit</button>
                    <button onClick={() => remove(t)} className="grid h-10 w-10 place-items-center rounded-lg text-muted hover:bg-danger-soft hover:text-danger" aria-label="Delete">✕</button>
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
    if (!confirm(`Delete "${a.name}"?`)) return
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
                    <button onClick={() => startEdit(a)} className="rounded-lg px-2 py-1 text-xs text-muted hover:bg-sunken hover:text-ink">Edit</button>
                    <button onClick={() => remove(a)} className="rounded-lg px-2 py-1 text-xs text-muted hover:text-danger" aria-label="Delete">✕</button>
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

function ImprovementsTab({ people, defaultAssignee, onError }: {
  people: Person[]; defaultAssignee: number | null; onError: (m: string) => void
}) {
  const [items, setItems] = useState<Improvement[]>([])
  const [loading, setLoading] = useState(true)
  const [open, setOpen] = useState(false)
  const [editId, setEditId] = useState<number | null>(null)
  const blank = {
    title: '', description: '', status: 'idea', priority: 'medium', room: '',
    target_date: null as string | null, is_all_day: true, assigned_to_person_id: defaultAssignee ?? 0,
  }
  const [f, setF] = useState(blank)
  const [saving, setSaving] = useState(false)
  const set = (k: string, v: unknown) => setF(prev => ({ ...prev, [k]: v }))

  const load = () => { api.getImprovements().then(setItems).catch(e => onError(errMsg(e))).finally(() => setLoading(false)) }
  useEffect(load, [])

  const startAdd = () => { setEditId(null); setF({ ...blank, assigned_to_person_id: defaultAssignee ?? 0 }); setOpen(true) }
  const startEdit = (i: Improvement) => {
    setEditId(i.id)
    setF({
      title: i.title, description: i.description, status: i.status, priority: i.priority, room: i.room,
      target_date: i.target_date, is_all_day: i.is_all_day, assigned_to_person_id: i.assigned_to_person_id ?? 0,
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
      assigned_to_person_id: f.assigned_to_person_id || null,
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
    if (!confirm(`Delete "${i.title}"?`)) return
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
            <button onClick={() => startEdit(i)} className="rounded-lg px-2 py-1 text-xs text-muted hover:bg-sunken hover:text-ink">Edit</button>
            <button onClick={() => remove(i)} className="rounded-lg px-2 py-1 text-xs text-muted hover:text-danger" aria-label="Delete">✕</button>
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
              <AssigneeSelect people={people} value={f.assigned_to_person_id || null}
                onChange={v => set('assigned_to_person_id', v ?? 0)} className={fieldClass} />
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
    if (!confirm(`Delete "${p.name}"?`)) return
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
                  <button onClick={() => startEdit(p)} className="rounded-lg px-2 py-1 text-xs text-muted hover:bg-sunken hover:text-ink">Edit</button>
                  <button onClick={() => remove(p)} className="rounded-lg px-2 py-1 text-xs text-muted hover:text-danger" aria-label="Delete">✕</button>
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
// Costs & cover — password protected, mirrored to Solace through backend events
// ---------------------------------------------------------------------------

const EMPTY_POLICY = {
  name: '', policy_type: 'building_contents', provider: '', policy_number: '',
  premium_amount: '', billing_cycle: 'yearly', next_renewal_at: null as string | null,
  standard_excess: '', additional_excesses: '', coverage_summary: '',
  contact_phone: '', portal_url: '', is_active: true, notes: '',
}

const EMPTY_COST = {
  name: '', cost_type: 'rates', provider: '', account_number: '', amount: '',
  billing_cycle: 'quarterly', next_due_at: null as string | null,
  is_active: true, notes: '',
}

function FinanceTab({ onError }: { onError: (m: string) => void }) {
  const [unlocked, setUnlocked] = useState(false)
  const [checking, setChecking] = useState(true)
  const [password, setPassword] = useState('')
  const [unlocking, setUnlocking] = useState(false)
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

  const unlock = async (e: React.FormEvent) => {
    e.preventDefault()
    setUnlocking(true)
    try {
      await api.reauth(password)
      await load()
      setPassword('')
    } catch (e) {
      onError(errMsg(e))
    } finally {
      setUnlocking(false)
    }
  }

  if (checking) return <div className="h-40 rounded-2xl bg-sunken animate-pulse" />
  if (!unlocked) {
    return (
      <Card>
        <form onSubmit={unlock} className="mx-auto flex max-w-md flex-col gap-4 py-3">
          <div>
            <h2 className="text-lg font-bold text-ink">Unlock costs &amp; cover</h2>
            <p className="mt-1 text-sm text-muted">
              Policy numbers and household costs are financial data, so your password is required.
            </p>
          </div>
          <Field label="Password">
            <Input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              autoComplete="current-password"
              autoFocus
            />
          </Field>
          <Button type="submit" loading={unlocking} disabled={!password}>Unlock</Button>
        </form>
      </Card>
    )
  }

  const startPolicy = (policy?: InsurancePolicy) => {
    if (policy) {
      setPolicyEdit(policy.id)
      setPolicyForm({
        name: policy.name, policy_type: policy.policy_type, provider: policy.provider,
        policy_number: policy.policy_number, premium_amount: policy.premium_amount,
        billing_cycle: policy.billing_cycle, next_renewal_at: policy.next_renewal_at,
        standard_excess: policy.standard_excess, additional_excesses: policy.additional_excesses,
        coverage_summary: policy.coverage_summary, contact_phone: policy.contact_phone,
        portal_url: policy.portal_url, is_active: policy.is_active, notes: policy.notes,
      })
    } else {
      setPolicyEdit(null)
      setPolicyForm(EMPTY_POLICY)
    }
    setShowPolicyForm(true)
  }

  const savePolicy = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!policyForm.name.trim()) return
    setSaving(true)
    const payload = {
      ...policyForm,
      name: policyForm.name.trim(),
      premium_amount: policyForm.premium_amount || '0.00',
      standard_excess: policyForm.standard_excess || '0.00',
    }
    try {
      if (policyEdit) await api.updateInsurancePolicy(policyEdit, payload)
      else await api.createInsurancePolicy(payload)
      setShowPolicyForm(false)
      await load()
    } catch (e) {
      onError(errMsg(e))
    } finally {
      setSaving(false)
    }
  }

  const removePolicy = async (policy: InsurancePolicy) => {
    if (!confirm(`Delete insurance policy "${policy.name}"? Its linked Solace bill will also be removed.`)) return
    try {
      await api.deleteInsurancePolicy(policy.id)
      await load()
    } catch (e) {
      onError(errMsg(e))
    }
  }

  const startCost = (cost?: HouseholdCost) => {
    if (cost) {
      setCostEdit(cost.id)
      setCostForm({
        name: cost.name, cost_type: cost.cost_type, provider: cost.provider,
        account_number: cost.account_number, amount: cost.amount,
        billing_cycle: cost.billing_cycle, next_due_at: cost.next_due_at,
        is_active: cost.is_active, notes: cost.notes,
      })
    } else {
      setCostEdit(null)
      setCostForm(EMPTY_COST)
    }
    setShowCostForm(true)
  }

  const saveCost = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!costForm.name.trim()) return
    setSaving(true)
    const payload = {
      ...costForm,
      name: costForm.name.trim(),
      amount: costForm.amount || '0.00',
    }
    try {
      if (costEdit) await api.updateHouseholdCost(costEdit, payload)
      else await api.createHouseholdCost(payload)
      setShowCostForm(false)
      await load()
    } catch (e) {
      onError(errMsg(e))
    } finally {
      setSaving(false)
    }
  }

  const removeCost = async (cost: HouseholdCost) => {
    if (!confirm(`Delete "${cost.name}"? Its linked Solace bill will also be removed.`)) return
    try {
      await api.deleteHouseholdCost(cost.id)
      await load()
    } catch (e) {
      onError(errMsg(e))
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
          <p className="font-semibold text-ink">One home record, one finance schedule</p>
          <p className="mt-0.5 text-muted-strong">Add details here and Solace updates automatically, or organise an existing Solace bill into Homestead without entering it again.</p>
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
            <p className="text-sm text-muted">Policy details, premiums, excesses and renewals.</p>
          </div>
          {!showPolicyForm && <Button size="sm" onClick={() => startPolicy()}>+ Policy</Button>}
        </div>

        {showPolicyForm && (
          <Card title={policyEdit ? 'Edit insurance policy' : 'New insurance policy'}>
            <form onSubmit={savePolicy} className="flex flex-col gap-3">
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                <Field label="Policy name"><Input value={policyForm.name} onChange={e => setPolicy('name', e.target.value)} placeholder="Home & contents" autoFocus /></Field>
                <Field label="Policy type"><Select value={policyForm.policy_type} onChange={e => setPolicy('policy_type', e.target.value)}>{POLICY_TYPES.map(v => <option key={v} value={v}>{cap(v)}</option>)}</Select></Field>
                <Field label="Insurer"><Input value={policyForm.provider} onChange={e => setPolicy('provider', e.target.value)} /></Field>
                <Field label="Policy number"><Input value={policyForm.policy_number} onChange={e => setPolicy('policy_number', e.target.value)} autoComplete="off" /></Field>
                <Field label="Premium"><Input type="number" min="0" step="0.01" value={policyForm.premium_amount} onChange={e => setPolicy('premium_amount', e.target.value)} /></Field>
                <Field label="Billing cycle"><Select value={policyForm.billing_cycle} onChange={e => setPolicy('billing_cycle', e.target.value)}>{BILLING_CYCLES.filter(v => v !== 'variable').map(v => <option key={v} value={v}>{cap(v)}</option>)}</Select></Field>
                <Field label="Next renewal"><DateTimeField value={policyForm.next_renewal_at} allDay onChange={({ value }) => setPolicy('next_renewal_at', value)} /></Field>
                <Field label="Standard excess"><Input type="number" min="0" step="0.01" value={policyForm.standard_excess} onChange={e => setPolicy('standard_excess', e.target.value)} /></Field>
                <Field label="Claims phone"><Input type="tel" value={policyForm.contact_phone} onChange={e => setPolicy('contact_phone', e.target.value)} /></Field>
              </div>
              <Field label="Other excesses" hint="For example: flood $1,500; accidental damage $500."><Textarea rows={2} value={policyForm.additional_excesses} onChange={e => setPolicy('additional_excesses', e.target.value)} /></Field>
              <Field label="Coverage summary"><Textarea rows={2} value={policyForm.coverage_summary} onChange={e => setPolicy('coverage_summary', e.target.value)} /></Field>
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Policy portal"><Input type="url" value={policyForm.portal_url} onChange={e => setPolicy('portal_url', e.target.value)} placeholder="https://…" /></Field>
                <Field label="Notes"><Textarea rows={2} value={policyForm.notes} onChange={e => setPolicy('notes', e.target.value)} /></Field>
              </div>
              <label className="flex min-h-[44px] items-center gap-2 text-sm text-ink"><input type="checkbox" checked={policyForm.is_active} onChange={e => setPolicy('is_active', e.target.checked)} /> Active policy</label>
              <div className="flex justify-end gap-2">
                <Button type="button" variant="ghost" size="sm" onClick={() => setShowPolicyForm(false)}>Cancel</Button>
                <Button type="submit" size="sm" loading={saving} disabled={!policyForm.name.trim()}>Save &amp; sync</Button>
              </div>
            </form>
          </Card>
        )}

        {shownPolicies.length === 0 ? (
          <EmptyState icon="🛡️" title={q ? 'No matching policies' : 'No insurance policies yet'} hint={q ? 'Try a different search.' : 'Add your building, contents or combined cover so renewal and excess details are easy to find.'} />
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
                            <Badge tone="success">Synced to Solace →</Badge>
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
                      <button onClick={() => startPolicy(policy)} className="min-h-10 rounded-lg px-3 py-1 text-sm text-muted hover:bg-sunken hover:text-ink">Edit</button>
                      <button onClick={() => removePolicy(policy)} className="grid h-10 w-10 place-items-center rounded-lg text-muted hover:bg-danger-soft hover:text-danger" aria-label="Delete">✕</button>
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
            <p className="text-sm text-muted">Water, gas, electricity, rates and other recurring home costs.</p>
          </div>
          {!showCostForm && <Button size="sm" onClick={() => startCost()}>+ Cost</Button>}
        </div>

        {showCostForm && (
          <Card title={costEdit ? 'Edit household cost' : 'New household cost'}>
            <form onSubmit={saveCost} className="flex flex-col gap-3">
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                <Field label="Name"><Input value={costForm.name} onChange={e => setCost('name', e.target.value)} placeholder="Council rates" autoFocus /></Field>
                <Field label="Type"><Select value={costForm.cost_type} onChange={e => setCost('cost_type', e.target.value)}>{COST_TYPES.map(v => <option key={v} value={v}>{cap(v)}</option>)}</Select></Field>
                <Field label="Provider"><Input value={costForm.provider} onChange={e => setCost('provider', e.target.value)} /></Field>
                <Field label="Account number"><Input value={costForm.account_number} onChange={e => setCost('account_number', e.target.value)} autoComplete="off" /></Field>
                <Field label="Expected / latest amount"><Input type="number" min="0" step="0.01" value={costForm.amount} onChange={e => setCost('amount', e.target.value)} /></Field>
                <Field label="Billing cycle"><Select value={costForm.billing_cycle} onChange={e => setCost('billing_cycle', e.target.value)}>{BILLING_CYCLES.map(v => <option key={v} value={v}>{cap(v)}</option>)}</Select></Field>
                <Field label="Next due"><DateTimeField value={costForm.next_due_at} allDay onChange={({ value }) => setCost('next_due_at', value)} /></Field>
                <Field label="Notes" className="sm:col-span-2"><Textarea rows={2} value={costForm.notes} onChange={e => setCost('notes', e.target.value)} /></Field>
              </div>
              <label className="flex min-h-[44px] items-center gap-2 text-sm text-ink"><input type="checkbox" checked={costForm.is_active} onChange={e => setCost('is_active', e.target.checked)} /> Active cost</label>
              <div className="flex justify-end gap-2">
                <Button type="button" variant="ghost" size="sm" onClick={() => setShowCostForm(false)}>Cancel</Button>
                <Button type="submit" size="sm" loading={saving} disabled={!costForm.name.trim()}>Save &amp; sync</Button>
              </div>
            </form>
          </Card>
        )}

        {shownCosts.length === 0 ? (
          <EmptyState icon="🧾" title={q ? 'No matching household costs' : 'No household costs yet'} hint={q ? 'Try a different search.' : 'Add rates, water, gas and other services. Each one is mirrored into Solace automatically.'} />
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
                            <Badge tone="success">Synced to Solace →</Badge>
                          </Link>
                        )}
                      </div>
                      <p className="mt-1 text-sm text-muted">{cost.provider || cap(cost.cost_type)} · {money(cost.amount)} / {cap(cost.billing_cycle).toLowerCase()}</p>
                      {cost.account_number && <p className="text-sm text-muted-strong">Account {cost.account_number}</p>}
                      {due && <div className="mt-2"><Badge tone={due.tone}>Due {due.text.toLowerCase()}</Badge></div>}
                      {cost.notes && <p className="mt-2 whitespace-pre-wrap text-sm text-muted">{cost.notes}</p>}
                    </div>
                    <div className="flex flex-shrink-0 justify-end gap-1 border-t border-line pt-2 sm:border-0 sm:pt-0">
                      <button onClick={() => startCost(cost)} className="min-h-10 rounded-lg px-3 py-1 text-sm text-muted hover:bg-sunken hover:text-ink">Edit</button>
                      <button onClick={() => removeCost(cost)} className="grid h-10 w-10 place-items-center rounded-lg text-muted hover:bg-danger-soft hover:text-danger" aria-label="Delete">✕</button>
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

type Tab = 'overview' | 'rooms' | 'maintenance' | 'appliances' | 'improvements' | 'contacts' | 'finances'
const TAB_KEYS: Tab[] = ['overview', 'rooms', 'maintenance', 'appliances', 'improvements', 'contacts', 'finances']

export function HomesteadPage() {
  const { user } = useAuth()
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

  return (
    <div className="flex flex-col gap-5">
      <PageHeader title="Homestead" icon="🏠" subtitle="Your home — rooms, upkeep, appliances, contacts and improvements." />

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
              { key: 'improvements', label: 'improvements' },
              { key: 'contacts', label: 'contacts' },
              { key: 'finances', label: 'costs & cover' },
            ]}
            active={tab}
            onChange={setTab}
            className="w-full sm:w-fit"
            mobileSelectLabel="Homestead section"
          />

          {tab === 'overview' && <OverviewTab onError={setError} onGoTab={setTab} />}
          {tab === 'rooms' && <RoomsTab onError={setError} canEdit={Boolean(user && user.role !== 'guest' && !user.is_child_account)} />}
          {tab === 'maintenance' && <MaintenanceTab people={people} defaultAssignee={defaultAssignee} onError={setError} />}
          {tab === 'appliances' && <AppliancesTab onError={setError} />}
          {tab === 'improvements' && <ImprovementsTab people={people} defaultAssignee={defaultAssignee} onError={setError} />}
          {tab === 'contacts' && <ContactsTab onError={setError} />}
          {tab === 'finances' && <FinanceTab onError={setError} />}
        </>
      )}
    </div>
  )
}
