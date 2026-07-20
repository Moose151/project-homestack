import { useEffect, useState } from 'react'
import { api } from '../../../api/client'
import type {
  Appliance, Improvement, ImprovementStatus, MaintenanceTask, Person, Property,
  ServiceProvider, HomesteadSearchResults,
} from '../../../api/types'
import { Card } from '../../../components/Card'
import { Button } from '../../../components/Button'
import { Field, Input, Textarea, Select, fieldClass } from '../../../components/Field'
import { Tabs } from '../../../components/Tabs'
import { Badge, type BadgeTone } from '../../../components/Badge'
import { PageHeader } from '../../../components/PageHeader'
import { EmptyState } from '../../../components/EmptyState'
import { DateTimeField } from '../../../components/DateTimeField'
import { AssigneeSelect, personIdForUser } from '../../../components/AssigneeSelect'
import { useAuth } from '../../auth/AuthContext'

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

      <p className="px-1 text-xs text-muted">
        🔗 Coming soon — bills, rates &amp; mortgage from the Finances node, and full renovations from the
        Projects node, will surface here and link back to their records.
      </p>
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
  const [editId, setEditId] = useState<number | null>(null)
  const blank = {
    title: '', category: 'general', next_due_at: null as string | null, is_all_day: true,
    recurrence_rule: '', appliance_id: 0, provider_id: 0, assigned_to_person_id: defaultAssignee ?? 0, notes: '',
  }
  const [f, setF] = useState(blank)
  const [saving, setSaving] = useState(false)
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
              <Button variant="ghost" size="sm" onClick={() => setOpen(false)}>Cancel</Button>
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
              <div key={t.id} className="flex items-center gap-3 rounded-xl border border-line p-3 group">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium text-ink">{t.title}</span>
                    <Badge>{cap(t.category)}</Badge>
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
                {t.next_due_at && <Button size="sm" variant="secondary" onClick={() => complete(t)}>Done</Button>}
                <div className="flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                  <button onClick={() => startEdit(t)} className="rounded-lg px-2 py-1 text-xs text-muted hover:bg-sunken hover:text-ink">Edit</button>
                  <button onClick={() => remove(t)} className="rounded-lg px-2 py-1 text-xs text-muted hover:text-danger" aria-label="Delete">✕</button>
                </div>
              </div>
            )
          })}
        </div>
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
              <Button variant="ghost" size="sm" onClick={() => setOpen(false)}>Cancel</Button>
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
                  <div className="flex flex-shrink-0 items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
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
          <div className="flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
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
              <Button variant="ghost" size="sm" onClick={() => setOpen(false)}>Cancel</Button>
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
              <Button variant="ghost" size="sm" onClick={() => setOpen(false)}>Cancel</Button>
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
                <div className="flex flex-shrink-0 items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
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
  const empty = !results.appliances.length && !results.maintenance.length && !results.providers.length && !results.improvements.length
  if (empty) return <p className="py-8 text-center text-sm text-muted">No matches.</p>
  const row = (key: string, main: string, sub?: string) => (
    <div key={key} className="flex items-center justify-between gap-3 rounded-lg bg-sunken px-3 py-1.5 text-sm">
      <span className="text-ink">{main}</span>{sub && <span className="text-xs text-muted">{sub}</span>}
    </div>
  )
  return (
    <div className="flex flex-col gap-4">
      {results.maintenance.length > 0 && <Section title="Maintenance">{results.maintenance.map(t => row(`m${t.id}`, t.title, cap(t.category)))}</Section>}
      {results.appliances.length > 0 && <Section title="Appliances">{results.appliances.map(a => row(`a${a.id}`, a.name, [a.brand, a.model_number].filter(Boolean).join(' ')))}</Section>}
      {results.improvements.length > 0 && <Section title="Improvements">{results.improvements.map(i => row(`i${i.id}`, i.title, cap(i.status)))}</Section>}
      {results.providers.length > 0 && <Section title="Contacts">{results.providers.map(p => row(`p${p.id}`, p.name, cap(p.trade)))}</Section>}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Homestead page
// ---------------------------------------------------------------------------

type Tab = 'overview' | 'maintenance' | 'appliances' | 'improvements' | 'contacts'

export function HomesteadPage() {
  const { user } = useAuth()
  const [tab, setTab] = useState<Tab>('overview')
  const [people, setPeople] = useState<Person[]>([])
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState('')
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
      <PageHeader title="Homestead" icon="🏠" subtitle="Your home — upkeep, appliances, contacts and improvements." />

      <Input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search maintenance, appliances, contacts, improvements…" />

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
              { key: 'maintenance', label: 'maintenance' },
              { key: 'appliances', label: 'appliances' },
              { key: 'improvements', label: 'improvements' },
              { key: 'contacts', label: 'contacts' },
            ]}
            active={tab}
            onChange={setTab}
            className="w-full sm:w-fit"
          />

          {tab === 'overview' && <OverviewTab onError={setError} onGoTab={setTab} />}
          {tab === 'maintenance' && <MaintenanceTab people={people} defaultAssignee={defaultAssignee} onError={setError} />}
          {tab === 'appliances' && <AppliancesTab onError={setError} />}
          {tab === 'improvements' && <ImprovementsTab people={people} defaultAssignee={defaultAssignee} onError={setError} />}
          {tab === 'contacts' && <ContactsTab onError={setError} />}
        </>
      )}
    </div>
  )
}
