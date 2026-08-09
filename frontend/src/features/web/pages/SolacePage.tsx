import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../../api/client'
import type {
  SolaceBalanceForecast, SolaceBalanceSnapshot, SolaceBill, SolaceBillOccurrence, SolaceBillTimeline, SolaceBucket, SolaceCategory,
  SolaceCategoryReport, SolaceChecklistItem, SolaceChecklistPreference, SolaceCloseoutResponse,
  SolaceHealth, SolacePayday, SolacePayCyclePlan, SolacePurchase, SolaceSchedule,
  SolaceSettings, SolaceSubscription,
} from '../../../api/types'
import { Card } from '../../../components/Card'
import { Button } from '../../../components/Button'
import { Field, Input, SearchField, Select, fieldClass } from '../../../components/Field'
import { Tabs } from '../../../components/Tabs'
import { Badge, type BadgeTone } from '../../../components/Badge'
import { PageHeader } from '../../../components/PageHeader'
import { EmptyState } from '../../../components/EmptyState'
import { useUrlQueryState, useUrlTab } from '../../../hooks/useUrlTab'
import { UndoToast } from '../../../components/UndoToast'
import { CloseoutTab, HealthPanel, ManagementTab } from './SolaceManagement'
import { setSolaceCurrencySymbol, solaceMoney as money } from './solaceFormat'
import { useStacks } from '../../stacks/StacksContext'

const errMsg = (e: unknown) => (e instanceof Error ? e.message : 'Something went wrong.')
const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1).replace(/_/g, ' ')
const dateOnly = (iso: string | null) => iso ? new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : 'No date'
const fromLocalInput = (value: string) => value ? new Date(value).toISOString() : null
const toLocalInput = (iso: string | null) => {
  if (!iso) return ''
  const value = new Date(iso)
  const offset = value.getTimezoneOffset() * 60000
  return new Date(value.getTime() - offset).toISOString().slice(0, 16)
}
const dateKey = (iso: string) => {
  const value = new Date(iso)
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}
const currentMonthKey = () => {
  const value = new Date()
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}`
}
const monthBounds = (monthKey: string) => {
  const [year, month] = monthKey.split('-').map(Number)
  const last = new Date(year, month, 0).getDate()
  return { start: `${monthKey}-01`, end: `${monthKey}-${String(last).padStart(2, '0')}` }
}
const shiftMonth = (monthKey: string, offset: number) => {
  const [year, month] = monthKey.split('-').map(Number)
  const value = new Date(year, month - 1 + offset, 1)
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}`
}
const dayAfter = (dateValue: string) => {
  const value = new Date(`${dateValue.slice(0, 10)}T12:00:00`)
  value.setDate(value.getDate() + 1)
  return dateKey(value.toISOString())
}

type Tab = 'overview' | 'forecast' | 'schedule' | 'closeout' | 'plan' | 'bills' | 'buckets' | 'subscriptions' | 'purchases' | 'paydays' | 'checklist' | 'manage'
const TAB_KEYS: Tab[] = ['overview', 'forecast', 'schedule', 'closeout', 'plan', 'bills', 'buckets', 'subscriptions', 'purchases', 'paydays', 'checklist', 'manage']
const SOLACE_TABS: Array<{ key: Tab; label: string }> = [
  { key: 'overview', label: 'Overview' },
  { key: 'forecast', label: 'Forecast' },
  { key: 'schedule', label: 'Schedule' },
  { key: 'closeout', label: 'Closeout' },
  { key: 'plan', label: 'Pay plan' },
  { key: 'bills', label: 'Bills' },
  { key: 'buckets', label: 'Buckets' },
  { key: 'subscriptions', label: 'Subscriptions' },
  { key: 'purchases', label: 'Purchases' },
  { key: 'paydays', label: 'Paydays' },
  { key: 'checklist', label: 'Checklist' },
  { key: 'manage', label: 'Manage' },
]

const BILL_CATS = ['mortgage', 'utilities', 'insurance', 'council', 'debt', 'subscription', 'childcare', 'other']
type HomeDestination = '' | 'insurance_policy' | 'household_cost' | 'maintenance'
const homeDestinationForCategory = (category: string): HomeDestination => {
  const normalised = category.toLowerCase()
  if (normalised === 'insurance') return 'insurance_policy'
  if (['mortgage', 'utilities', 'council'].includes(normalised)) return 'household_cost'
  return ''
}
const homeDestinationPath = (recordType: string) =>
  recordType === 'maintenance' ? '/homestead?tab=maintenance' : '/homestead?tab=finances'
const RECURRENCE = [
  { label: 'One-off', value: '' },
  { label: 'Weekly', value: 'FREQ=WEEKLY' },
  { label: 'Fortnightly', value: 'FREQ=WEEKLY;INTERVAL=2' },
  { label: 'Monthly', value: 'FREQ=MONTHLY' },
  { label: 'Quarterly', value: 'FREQ=MONTHLY;INTERVAL=3' },
  { label: 'Six-monthly', value: 'FREQ=MONTHLY;INTERVAL=6' },
  { label: 'Yearly', value: 'FREQ=YEARLY' },
]
const subscriptionRecurrence = (cycle: string, fallback = '') => ({
  weekly: 'FREQ=WEEKLY',
  fortnightly: 'FREQ=WEEKLY;INTERVAL=2',
  monthly: 'FREQ=MONTHLY',
  quarterly: 'FREQ=MONTHLY;INTERVAL=3',
  yearly: 'FREQ=YEARLY',
} as Record<string, string>)[cycle] || fallback

function ReauthGate({ onUnlock }: { onUnlock: () => void }) {
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const submit = async () => {
    setSaving(true); setError('')
    try {
      await api.reauth(password)
      setPassword('')
      onUnlock()
    } catch (e) {
      setError(errMsg(e))
    } finally {
      setSaving(false)
    }
  }
  return (
    <div className="max-w-lg mx-auto pt-8">
      <Card contentClassName="p-5">
        <div className="flex flex-col gap-4">
          <div>
            <h2 className="text-xl font-bold text-ink">Unlock Solace</h2>
            <p className="mt-1 text-sm text-muted">Password re-authentication required.</p>
          </div>
          {error && <div className="rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-danger">{error}</div>}
          <Field label="Password">
            <Input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && password) submit() }}
              autoComplete="current-password"
            />
          </Field>
          <Button onClick={submit} loading={saving} disabled={!password}>Unlock</Button>
        </div>
      </Card>
    </div>
  )
}

function DueBadge({ iso, paid }: { iso: string | null; paid?: boolean }) {
  if (paid) return <Badge tone="success">Paid</Badge>
  if (!iso) return <Badge tone="neutral">No date</Badge>
  const diff = Math.round((new Date(iso).getTime() - Date.now()) / 86400000)
  let tone: BadgeTone = 'neutral'
  let label = dateOnly(iso)
  if (diff < 0) { tone = 'danger'; label = `${Math.abs(diff)}d overdue` }
  else if (diff === 0) { tone = 'primary'; label = 'Today' }
  else if (diff <= 7) { tone = 'warning'; label = `in ${diff}d` }
  return <Badge tone={tone}>{label}</Badge>
}

function CreatePanel({ label, children }: {
  label: string
  children: (close: () => void) => ReactNode
}) {
  const [open, setOpen] = useState(false)
  if (!open) return <Button variant="secondary" onClick={() => setOpen(true)} className="self-start">+ {label}</Button>
  return (
    <div className="space-y-2">
      <div className="flex justify-end">
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="min-h-10 rounded-xl px-3 text-sm font-semibold text-muted hover:bg-sunken hover:text-ink"
          aria-label={`Close ${label.toLowerCase()} form`}
        >
          Close form ✕
        </button>
      </div>
      {children(() => setOpen(false))}
    </div>
  )
}

function BillForm({ categories, onCreated, onError }: {
  categories: string[]; onCreated: () => void; onError: (message: string) => void
}) {
  const startingCategory = categories[0] || 'other'
  const [f, setF] = useState({
    name: '', category: startingCategory, provider: '', amount: '', due_at: '',
    recurrence_rule: '', end_date: '', is_autopay: false, include_in_set_aside: true,
    home_destination: homeDestinationForCategory(startingCategory) as HomeDestination,
  })
  const [saving, setSaving] = useState(false)
  const set = (k: string, v: string | boolean) => setF(prev => ({ ...prev, [k]: v }))
  const save = async () => {
    setSaving(true)
    try {
      await api.createSolaceBill({
        ...f,
        amount: f.amount || '0.00',
        due_at: fromLocalInput(f.due_at),
        end_date: f.end_date || null,
        is_all_day: true,
        is_active: true,
      })
      setF({
        name: '', category: startingCategory, provider: '', amount: '', due_at: '',
        recurrence_rule: '', end_date: '', is_autopay: false, include_in_set_aside: true,
        home_destination: homeDestinationForCategory(startingCategory),
      })
      onCreated()
    } catch (error) {
      onError(errMsg(error))
    } finally { setSaving(false) }
  }
  return (
    <Card contentClassName="p-4">
      <div className="mb-4 rounded-xl bg-primary-soft px-3 py-3 text-sm text-ink">
        <p className="font-semibold">Enter home information once</p>
        <p className="mt-0.5 text-muted-strong">Choose a Homestead destination below and this bill will appear in the right home workspace automatically.</p>
      </div>
      <div className="grid min-w-0 gap-3 sm:grid-cols-2 xl:grid-cols-3">
        <Field label="Bill"><Input value={f.name} onChange={e => set('name', e.target.value)} placeholder="Electricity" /></Field>
        <Field label="Provider"><Input value={f.provider} onChange={e => set('provider', e.target.value)} /></Field>
        <Field label="Amount"><Input type="number" step="0.01" value={f.amount} onChange={e => set('amount', e.target.value)} /></Field>
        <Field label="Category"><Select value={f.category} onChange={e => setF(prev => ({ ...prev, category: e.target.value, home_destination: homeDestinationForCategory(e.target.value) }))}>{categories.map(c => <option key={c} value={c}>{cap(c)}</option>)}</Select></Field>
        <Field label="First due"><input type="datetime-local" className={fieldClass} value={f.due_at} onChange={e => set('due_at', e.target.value)} /></Field>
        <Field label="Repeats"><Select value={f.recurrence_rule} onChange={e => set('recurrence_rule', e.target.value)}>{RECURRENCE.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}</Select></Field>
        <Field label="Organise in Homestead" hint="Homestead becomes the place for home details; Solace keeps the amount and payment schedule." className="sm:col-span-2 xl:col-span-3">
          <Select value={f.home_destination} onChange={e => set('home_destination', e.target.value)}>
            <option value="">No — finance only</option>
            <option value="insurance_policy">Home insurance / cover</option>
            <option value="household_cost">Rates, mortgage or home service</option>
            <option value="maintenance">Paid home maintenance</option>
          </Select>
        </Field>
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-[1fr_auto_auto_auto] xl:items-end">
        <Field label="Stop after (optional)">
          <Input type="date" value={f.end_date} onChange={e => set('end_date', e.target.value)} />
        </Field>
        <label className="flex min-h-11 items-center gap-2 text-sm text-muted">
          <input type="checkbox" checked={f.is_autopay} onChange={e => set('is_autopay', e.target.checked)} />
          Autopay
        </label>
        <label className="flex min-h-11 items-center gap-2 text-sm text-muted">
          <input
            type="checkbox"
            checked={f.include_in_set_aside}
            onChange={e => set('include_in_set_aside', e.target.checked)}
          />
          Include in set-aside planning
        </label>
        <Button onClick={save} loading={saving} disabled={!f.name.trim()} className="w-full sm:col-span-2 xl:col-span-1 xl:w-auto">Add bill</Button>
      </div>
    </Card>
  )
}

function BillEditor({ bill, categories, reload, onError }: {
  bill: SolaceBill; categories: string[]; reload: () => void; onError: (message: string) => void
}) {
  const [f, setF] = useState({
    name: bill.name,
    provider: bill.provider,
    category: bill.category,
    amount: bill.amount,
    due_at: toLocalInput(bill.due_at),
    recurrence_rule: bill.recurrence_rule,
    end_date: bill.end_date || '',
    is_active: bill.is_active,
    is_autopay: bill.is_autopay,
    include_in_set_aside: bill.include_in_set_aside,
    home_destination: '' as HomeDestination,
    notes: bill.notes,
    occurrence_update_scope: 'future_unpaid' as 'future_unpaid' | 'all_unpaid',
  })
  const [saving, setSaving] = useState(false)
  const set = (key: string, value: string | boolean) => setF(previous => ({ ...previous, [key]: value }))
  const save = async () => {
    setSaving(true)
    try {
      await api.updateSolaceBill(bill.id, {
        ...f,
        due_at: fromLocalInput(f.due_at),
        end_date: f.end_date || null,
        amount: f.amount || '0.00',
      })
      reload()
    } catch (e) {
      onError(errMsg(e))
    } finally {
      setSaving(false)
    }
  }
  const remove = async () => {
    if (!window.confirm(`Delete ${bill.name} and its occurrence history?`)) return
    setSaving(true)
    try {
      await api.deleteSolaceBill(bill.id)
      reload()
    } catch (e) {
      onError(errMsg(e))
    } finally {
      setSaving(false)
    }
  }
  return (
    <details className="mt-3 border-t border-line pt-3">
      <summary className="cursor-pointer text-sm font-medium text-primary">Edit bill</summary>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <Field label="Name"><Input value={f.name} onChange={e => set('name', e.target.value)} /></Field>
        <Field label="Provider"><Input value={f.provider} onChange={e => set('provider', e.target.value)} /></Field>
        <Field label="Amount"><Input type="number" min="0" step="0.01" value={f.amount} onChange={e => set('amount', e.target.value)} /></Field>
        <Field label="Category">
          <Select value={f.category} onChange={e => set('category', e.target.value)}>
            {!categories.includes(f.category) && <option value={f.category}>{cap(f.category)}</option>}
            {categories.map(category => <option key={category} value={category}>{cap(category)}</option>)}
          </Select>
        </Field>
        <Field label="First due">
          <input type="datetime-local" className={fieldClass} value={f.due_at} onChange={e => set('due_at', e.target.value)} />
        </Field>
        <Field label="Repeats">
          <Select value={f.recurrence_rule} onChange={e => set('recurrence_rule', e.target.value)}>
            {f.recurrence_rule && !RECURRENCE.some(rule => rule.value === f.recurrence_rule) && (
              <option value={f.recurrence_rule}>Imported recurrence</option>
            )}
            {RECURRENCE.map(rule => <option key={rule.value} value={rule.value}>{rule.label}</option>)}
          </Select>
        </Field>
        <Field label="Stop after"><Input type="date" value={f.end_date} onChange={e => set('end_date', e.target.value)} /></Field>
        <Field label="Notes"><Input value={f.notes} onChange={e => set('notes', e.target.value)} /></Field>
        <Field label="Occurrence updates">
          <Select value={f.occurrence_update_scope} onChange={e => set('occurrence_update_scope', e.target.value)}>
            <option value="future_unpaid">Future unpaid only</option>
            <option value="all_unpaid">All unpaid in budget year</option>
          </Select>
        </Field>
        {!bill.source_node && (
          <Field label="Organise in Homestead" hint="Use the information already here—no re-entry needed." className="sm:col-span-2">
            <Select value={f.home_destination} onChange={e => set('home_destination', e.target.value)}>
              <option value="">Keep as finance only</option>
              <option value="insurance_policy">Home insurance / cover</option>
              <option value="household_cost">Rates, mortgage or home service</option>
              <option value="maintenance">Paid home maintenance</option>
            </Select>
          </Field>
        )}
      </div>
      <p className="mt-2 text-xs text-muted">Paid history is always preserved. Use all unpaid only when correcting the bill rule for the whole budget year.</p>
      <div className="mt-3 flex flex-wrap gap-4 text-sm text-muted">
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={f.is_active} onChange={e => set('is_active', e.target.checked)} />
          Active
        </label>
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={f.include_in_set_aside} onChange={e => set('include_in_set_aside', e.target.checked)} />
          Include in set-aside
        </label>
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={f.is_autopay} onChange={e => set('is_autopay', e.target.checked)} />
          Autopay
        </label>
      </div>
      <div className="mt-3 flex gap-2">
        <Button size="sm" onClick={save} loading={saving} disabled={!f.name.trim()}>Save</Button>
        <Button size="sm" variant="danger" onClick={remove} disabled={saving}>Delete</Button>
      </div>
    </details>
  )
}

function BillDetails({ bill }: { bill: SolaceBill }) {
  const [timeline, setTimeline] = useState<SolaceBillTimeline | null>(null)
  const [loading, setLoading] = useState(false)
  const [loadError, setLoadError] = useState('')
  const load = async () => {
    if (timeline || loading) return
    setLoading(true)
    setLoadError('')
    try {
      setTimeline(await api.getSolaceBillTimeline(bill.id))
    } catch (error) {
      setLoadError(errMsg(error))
    } finally {
      setLoading(false)
    }
  }
  const occurrenceList = (rows: SolaceBillOccurrence[], empty: string) => (
    rows.length === 0 ? <p className="text-sm text-muted">{empty}</p> : (
      <div className="space-y-2">
        {rows.map(row => (
          <div key={row.id} className="flex items-center justify-between gap-3 rounded-lg bg-sunken/50 px-3 py-2 text-sm">
            <div>
              <p className="font-medium text-ink">{new Date(row.due_at).toLocaleDateString()}</p>
              <p className="text-xs text-muted">
                {cap(row.status)}
                {row.paid_at ? ` · paid ${new Date(row.paid_at).toLocaleDateString()}` : ''}
              </p>
            </div>
            <span className="font-semibold text-ink">{money(row.amount)}</span>
          </div>
        ))}
      </div>
    )
  )
  return (
    <details className="mt-3 border-t border-line pt-3" onToggle={event => {
      if (event.currentTarget.open) void load()
    }}>
      <summary className="cursor-pointer text-sm font-medium text-primary">Details & occurrence history</summary>
      <div className="mt-3 space-y-4">
        <div className="grid gap-2 text-sm sm:grid-cols-2">
          <div><span className="text-muted">First due</span><p className="font-medium text-ink">{dateOnly(bill.due_at)}</p></div>
          <div><span className="text-muted">Stop after</span><p className="font-medium text-ink">{bill.end_date ? new Date(`${bill.end_date}T00:00:00`).toLocaleDateString() : 'No end date'}</p></div>
          <div><span className="text-muted">Payment</span><p className="font-medium text-ink">{bill.is_autopay ? 'Autopay' : 'Manual'}</p></div>
          <div><span className="text-muted">Account/provider</span><p className="font-medium text-ink">{bill.provider || 'Not recorded'}</p></div>
        </div>
        {loading && <p className="text-sm text-muted">Loading occurrence history…</p>}
        {loadError && (
          <div className="flex items-center justify-between gap-3 rounded-lg bg-danger/10 px-3 py-2 text-sm text-danger">
            <span>{loadError}</span>
            <Button size="sm" variant="ghost" onClick={() => { setTimeline(null); void load() }}>Retry</Button>
          </div>
        )}
        {timeline && (
          <div className="grid gap-4 lg:grid-cols-2">
            <div>
              <h4 className="mb-2 text-sm font-semibold text-ink">Upcoming occurrences</h4>
              {occurrenceList(timeline.upcoming, 'No upcoming occurrences generated.')}
            </div>
            <div>
              <h4 className="mb-2 text-sm font-semibold text-ink">Recent history</h4>
              {occurrenceList(timeline.history, 'No past occurrences yet.')}
            </div>
          </div>
        )}
      </div>
    </details>
  )
}

function BillsTab({ bills, categories, reload, onOccurrence, onError }: {
  bills: SolaceBill[]
  categories: string[]
  reload: () => void
  onOccurrence: (id: number, action: 'paid' | 'unpaid' | 'skip') => Promise<SolaceBillOccurrence>
  onError: (m: string) => void
}) {
  const [undoOccurrence, setUndoOccurrence] = useState<{ id: number; name: string } | null>(null)
  const [paying, setPaying] = useState<number | null>(null)
  const [categoryFilter, setCategoryFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')
  const [billSort, setBillSort] = useState('name-asc')
  const pay = async (bill: SolaceBill) => {
    if (!bill.next_occurrence_id) return
    setPaying(bill.next_occurrence_id)
    try {
      const updated = await onOccurrence(bill.next_occurrence_id, 'paid')
      setUndoOccurrence({ id: updated.id, name: bill.name })
    } catch (e) {
      onError(errMsg(e))
    } finally {
      setPaying(null)
    }
  }
  const undo = async () => {
    if (!undoOccurrence) return
    const previous = undoOccurrence
    setUndoOccurrence(null)
    try {
      await onOccurrence(previous.id, 'unpaid')
    } catch (e) {
      onError(errMsg(e))
    }
  }
  const activeSetAside = bills.filter(bill => bill.is_active && bill.include_in_set_aside)
  const annualTotal = activeSetAside.reduce((sum, bill) => sum + Number(bill.annual_amount), 0)
  const fortnightlyTotal = activeSetAside.reduce((sum, bill) => sum + Number(bill.fortnightly_amount), 0)
  const visibleBills = useMemo(() => {
    const rows = bills.filter(bill => (
      (categoryFilter === 'all' || bill.category === categoryFilter)
      && (statusFilter === 'all' || (statusFilter === 'active' ? bill.is_active : !bill.is_active))
    ))
    return [...rows].sort((left, right) => {
      if (billSort === 'name-desc') return right.name.localeCompare(left.name)
      if (billSort === 'due-asc') return String(left.next_due_at || left.due_at || '9999').localeCompare(String(right.next_due_at || right.due_at || '9999'))
      if (billSort === 'amount-desc') return Number(right.amount) - Number(left.amount)
      if (billSort === 'annual-desc') return Number(right.annual_amount) - Number(left.annual_amount)
      if (billSort === 'category-asc') return left.category.localeCompare(right.category) || left.name.localeCompare(right.name)
      return left.name.localeCompare(right.name)
    })
  }, [billSort, bills, categoryFilter, statusFilter])
  return (
    <div className="flex flex-col gap-4">
      <CreatePanel label="Add bill">
        {close => <BillForm categories={categories} onCreated={() => { reload(); close() }} onError={onError} />}
      </CreatePanel>
      {bills.length > 0 && (
        <div className="grid gap-3 sm:grid-cols-3">
          <Card contentClassName="p-3"><p className="text-xl font-extrabold text-ink">{money(annualTotal)}</p><p className="text-xs text-muted">Annual recurring cost</p></Card>
          <Card contentClassName="p-3"><p className="text-xl font-extrabold text-ink">{money(fortnightlyTotal)}</p><p className="text-xs text-muted">Set aside per fortnight</p></Card>
          <Card contentClassName="p-3"><p className="text-xl font-extrabold text-ink">{new Set(activeSetAside.map(bill => bill.category)).size}</p><p className="text-xs text-muted">Active categories</p></Card>
        </div>
      )}
      {bills.length > 0 && (
        <Card contentClassName="p-3">
          <div className="grid gap-2 sm:grid-cols-3">
            <Select value={categoryFilter} onChange={event => setCategoryFilter(event.target.value)}>
              <option value="all">All categories</option>
              {[...new Set(bills.map(bill => bill.category))].sort().map(category => <option key={category} value={category}>{cap(category)}</option>)}
            </Select>
            <Select value={statusFilter} onChange={event => setStatusFilter(event.target.value)}>
              <option value="all">Active and paused</option>
              <option value="active">Active only</option>
              <option value="paused">Paused only</option>
            </Select>
            <Select value={billSort} onChange={event => setBillSort(event.target.value)}>
              <option value="name-asc">Name A–Z</option>
              <option value="name-desc">Name Z–A</option>
              <option value="due-asc">Next due</option>
              <option value="amount-desc">Highest payment</option>
              <option value="annual-desc">Highest annual cost</option>
              <option value="category-asc">Category</option>
            </Select>
          </div>
          <p className="mt-2 text-xs text-muted">Showing {visibleBills.length} of {bills.length} bills.</p>
        </Card>
      )}
      {bills.length === 0 ? <EmptyState icon="💸" title="No bills yet" hint="" /> : (
        visibleBills.length === 0 ? <EmptyState icon="🔎" title="No bills match these filters" hint="Try another category or status." /> : <div className="grid gap-3 lg:grid-cols-2">
          {visibleBills.map(b => (
            <Card key={b.id} contentClassName="p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <h3 className="font-semibold text-ink truncate">{b.name}</h3>
                  <p className="text-sm text-muted">{b.provider || cap(b.category)} · {money(b.amount)}</p>
                  {b.is_active && b.include_in_set_aside && (
                    <p className="text-xs text-muted">{money(b.fortnightly_amount)}/fortnight · {money(b.annual_amount)}/year</p>
                  )}
                  {b.source_node === 'homestead' && <div className="mt-1"><Badge tone="success">Managed in Homestead</Badge></div>}
                </div>
                <DueBadge iso={b.next_due_at || b.due_at} paid={b.is_paid && !b.recurrence_rule} />
              </div>
              {b.notes && <p className="mt-3 text-sm text-muted">{b.notes}</p>}
              <div className="mt-3 flex items-center gap-2">
                {b.recurrence_rule && <Badge tone="neutral">Recurring</Badge>}
                {b.is_autopay && <Badge tone="success">Autopay</Badge>}
                {!b.is_active && <Badge tone="neutral">Paused</Badge>}
                {b.next_occurrence_id && b.is_active && (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => pay(b)}
                    loading={paying === b.next_occurrence_id}
                  >
                    Mark next paid
                  </Button>
                )}
              </div>
              <BillDetails bill={b} />
              {b.source_node
                ? b.source_node === 'homestead'
                  ? <Link to={homeDestinationPath(b.source_record_type)} className="mt-3 flex min-h-11 items-center justify-between gap-3 border-t border-line pt-3 text-sm font-semibold text-primary">View and edit in Homestead <span aria-hidden>→</span></Link>
                  : <p className="mt-3 border-t border-line pt-3 text-xs text-muted">Edit this linked bill from {cap(b.source_node)}.</p>
                : <BillEditor bill={b} categories={categories} reload={reload} onError={onError} />}
            </Card>
          ))}
        </div>
      )}
      {undoOccurrence && (
        <UndoToast
          message={`${undoOccurrence.name} marked paid`}
          onUndo={undo}
          onDismiss={() => setUndoOccurrence(null)}
        />
      )}
    </div>
  )
}

function BucketForm({ onCreated, onError }: {
  onCreated: () => void; onError: (message: string) => void
}) {
  const [f, setF] = useState({
    name: '', category: '', target_amount: '', current_amount: '',
    allocation_method: 'percentage' as 'percentage' | 'fixed',
    allocation_value: '', rounding_increment: '1.00', cap_to_remaining: true,
  })
  const [saving, setSaving] = useState(false)
  const set = (k: string, v: string | boolean) => setF(prev => ({ ...prev, [k]: v }))
  const save = async () => {
    setSaving(true)
    try {
      await api.createSolaceBucket({
        ...f,
        target_amount: f.target_amount || '0.00',
        current_amount: f.current_amount || '0.00',
        allocation_value: f.allocation_value || '0.00',
      })
      setF({
        name: '', category: '', target_amount: '', current_amount: '',
        allocation_method: 'percentage', allocation_value: '',
        rounding_increment: '1.00', cap_to_remaining: true,
      })
      onCreated()
    } catch (error) {
      onError(errMsg(error))
    } finally { setSaving(false) }
  }
  return (
    <Card contentClassName="p-4">
      <h3 className="mb-3 font-semibold text-ink">New bucket and pay rule</h3>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-[1.3fr_1fr_0.9fr_0.8fr_0.8fr_0.8fr_auto]">
        <Field label="Bucket"><Input value={f.name} onChange={e => set('name', e.target.value)} placeholder="Emergency fund" /></Field>
        <Field label="Category"><Input value={f.category} onChange={e => set('category', e.target.value)} /></Field>
        <Field label="Pay rule">
          <Select value={f.allocation_method} onChange={e => set('allocation_method', e.target.value)}>
            <option value="percentage">Percentage</option>
            <option value="fixed">Fixed total</option>
          </Select>
        </Field>
        <Field label={f.allocation_method === 'percentage' ? 'Percent' : 'Amount'}>
          <Input type="number" min="0" step="0.01" value={f.allocation_value} onChange={e => set('allocation_value', e.target.value)} />
        </Field>
        <Field label="Round to">
          <Select value={f.rounding_increment} onChange={e => set('rounding_increment', e.target.value)}>
            {['0.01', '1.00', '5.00', '10.00'].map(v => <option key={v} value={v}>{money(v)}</option>)}
          </Select>
        </Field>
        <Field label="Goal"><Input type="number" min="0" step="0.01" value={f.target_amount} onChange={e => set('target_amount', e.target.value)} /></Field>
        <Field label="Saved"><Input type="number" min="0" step="0.01" value={f.current_amount} onChange={e => set('current_amount', e.target.value)} /></Field>
        <div className="flex items-end"><Button onClick={save} loading={saving} disabled={!f.name.trim()} className="w-full">Add</Button></div>
      </div>
      <label className="mt-3 flex items-center gap-2 text-sm text-muted">
        <input type="checkbox" checked={f.cap_to_remaining} onChange={e => set('cap_to_remaining', e.target.checked)} />
        Never allocate more than the remaining pay
      </label>
    </Card>
  )
}

function BucketRuleEditor({ bucket, reload, onError }: {
  bucket: SolaceBucket; reload: () => void; onError: (message: string) => void
}) {
  const [method, setMethod] = useState(bucket.allocation_method)
  const [name, setName] = useState(bucket.name)
  const [category, setCategory] = useState(bucket.category)
  const [target, setTarget] = useState(bucket.target_amount)
  const [current, setCurrent] = useState(bucket.current_amount)
  const [notes, setNotes] = useState(bucket.notes)
  const [value, setValue] = useState(bucket.allocation_value)
  const [rounding, setRounding] = useState(bucket.rounding_increment)
  const [capRemaining, setCapRemaining] = useState(bucket.cap_to_remaining)
  const [active, setActive] = useState(bucket.is_active)
  const [saving, setSaving] = useState(false)
  const save = async () => {
    setSaving(true)
    try {
      await api.updateSolaceBucket(bucket.id, {
        name,
        category,
        target_amount: target || '0.00',
        current_amount: current || '0.00',
        notes,
        allocation_method: method,
        allocation_value: value || '0.00',
        rounding_increment: rounding,
        cap_to_remaining: capRemaining,
        is_active: active,
      })
      reload()
    } catch (e) {
      onError(errMsg(e))
    } finally {
      setSaving(false)
    }
  }
  const remove = async () => {
    if (!window.confirm(`Delete the ${bucket.name} bucket?`)) return
    setSaving(true)
    try {
      await api.deleteSolaceBucket(bucket.id)
      reload()
    } catch (e) {
      onError(errMsg(e))
    } finally {
      setSaving(false)
    }
  }
  return (
    <details className="mt-4 border-t border-line pt-3">
      <summary className="cursor-pointer text-sm font-medium text-primary">Edit bucket</summary>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <Field label="Name"><Input value={name} onChange={e => setName(e.target.value)} /></Field>
        <Field label="Category"><Input value={category} onChange={e => setCategory(e.target.value)} /></Field>
        <Field label="Goal"><Input type="number" min="0" step="0.01" value={target} onChange={e => setTarget(e.target.value)} /></Field>
        <Field label="Saved"><Input type="number" min="0" step="0.01" value={current} onChange={e => setCurrent(e.target.value)} /></Field>
        <Field label="Rule">
          <Select value={method} onChange={e => setMethod(e.target.value as 'percentage' | 'fixed')}>
            <option value="percentage">Percentage</option>
            <option value="fixed">Fixed household total</option>
          </Select>
        </Field>
        <Field label={method === 'percentage' ? 'Percent' : 'Amount'}>
          <Input type="number" min="0" step="0.01" value={value} onChange={e => setValue(e.target.value)} />
        </Field>
        <Field label="Round to">
          <Select value={rounding} onChange={e => setRounding(e.target.value)}>
            {['0.01', '1.00', '5.00', '10.00'].map(v => <option key={v} value={v}>{money(v)}</option>)}
          </Select>
        </Field>
        <div className="flex flex-col justify-end gap-2 pb-1 text-sm text-muted">
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={capRemaining} onChange={e => setCapRemaining(e.target.checked)} />
            Cap to remaining pay
          </label>
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={active} onChange={e => setActive(e.target.checked)} />
            Include in pay plan
          </label>
        </div>
        <Field label="Notes"><Input value={notes} onChange={e => setNotes(e.target.value)} /></Field>
      </div>
      <div className="mt-3 flex gap-2">
        <Button size="sm" onClick={save} loading={saving} disabled={!name.trim()}>Save bucket</Button>
        <Button size="sm" variant="danger" onClick={remove} disabled={saving}>Delete</Button>
      </div>
    </details>
  )
}

function BucketsTab({ buckets, reload, onError }: {
  buckets: SolaceBucket[]; reload: () => void; onError: (message: string) => void
}) {
  return (
    <div className="flex flex-col gap-4">
      <CreatePanel label="Add bucket">
        {close => <BucketForm onCreated={() => { reload(); close() }} onError={onError} />}
      </CreatePanel>
      {buckets.length === 0 ? <EmptyState icon="🪣" title="No buckets yet" hint="" /> : (
        <div className="grid gap-3 lg:grid-cols-3">
          {buckets.map(b => (
            <Card key={b.id} contentClassName="p-4">
              <div className="flex items-start justify-between gap-3">
                <div><h3 className="font-semibold text-ink">{b.name}</h3><p className="text-sm text-muted">{b.category || 'Set-aside'}</p></div>
                <Badge tone={b.progress_percent >= 100 ? 'success' : 'primary'}>{b.progress_percent}%</Badge>
              </div>
              <div className="mt-4 h-2 rounded-full bg-sunken overflow-hidden">
                <div className="h-full bg-primary" style={{ width: `${b.progress_percent}%` }} />
              </div>
              <p className="mt-2 text-sm text-muted">{money(b.current_amount)} of {money(b.target_amount)}</p>
              <p className="mt-2 text-sm font-medium text-ink">
                {b.is_active
                  ? b.allocation_method === 'fixed'
                    ? `${money(b.allocation_value)} per household pay cycle`
                    : `${Number(b.allocation_value)}% of each pay`
                  : 'Excluded from pay plan'}
              </p>
              <BucketRuleEditor bucket={b} reload={reload} onError={onError} />
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}

function SubscriptionForm({ onCreated, onError }: {
  onCreated: () => void; onError: (message: string) => void
}) {
  const [f, setF] = useState({ name: '', provider: '', amount: '', billing_cycle: 'monthly', next_renewal_at: '' })
  const [saving, setSaving] = useState(false)
  const set = (k: string, v: string) => setF(prev => ({ ...prev, [k]: v }))
  const save = async () => {
    setSaving(true)
    try {
      await api.createSolaceSubscription({ ...f, amount: f.amount || '0.00', next_renewal_at: fromLocalInput(f.next_renewal_at), recurrence_rule: subscriptionRecurrence(f.billing_cycle), is_all_day: true, is_active: true })
      setF({ name: '', provider: '', amount: '', billing_cycle: 'monthly', next_renewal_at: '' })
      onCreated()
    } catch (error) {
      onError(errMsg(error))
    } finally { setSaving(false) }
  }
  return (
    <Card contentClassName="p-4">
      <div className="grid gap-3 lg:grid-cols-[1.3fr_1fr_0.7fr_1fr_1fr_auto]">
        <Field label="Subscription"><Input value={f.name} onChange={e => set('name', e.target.value)} /></Field>
        <Field label="Provider"><Input value={f.provider} onChange={e => set('provider', e.target.value)} /></Field>
        <Field label="Amount"><Input type="number" step="0.01" value={f.amount} onChange={e => set('amount', e.target.value)} /></Field>
        <Field label="Cycle"><Select value={f.billing_cycle} onChange={e => set('billing_cycle', e.target.value)}>{['weekly', 'fortnightly', 'monthly', 'quarterly', 'yearly', 'other'].map(c => <option key={c} value={c}>{cap(c)}</option>)}</Select></Field>
        <Field label="Renewal"><input type="datetime-local" className={fieldClass} value={f.next_renewal_at} onChange={e => set('next_renewal_at', e.target.value)} /></Field>
        <div className="flex items-end"><Button onClick={save} loading={saving} disabled={!f.name.trim()} className="w-full">Add</Button></div>
      </div>
    </Card>
  )
}

function SubscriptionEditor({ subscription, reload, onError }: {
  subscription: SolaceSubscription; reload: () => void; onError: (message: string) => void
}) {
  const [f, setF] = useState({
    name: subscription.name,
    provider: subscription.provider,
    amount: subscription.amount,
    billing_cycle: subscription.billing_cycle,
    next_renewal_at: toLocalInput(subscription.next_renewal_at),
    is_active: subscription.is_active,
    notes: subscription.notes,
  })
  const [saving, setSaving] = useState(false)
  const set = (key: string, value: string | boolean) => setF(previous => ({ ...previous, [key]: value }))
  const save = async () => {
    setSaving(true)
    try {
      await api.updateSolaceSubscription(subscription.id, {
        ...f,
        amount: f.amount || '0.00',
        next_renewal_at: fromLocalInput(f.next_renewal_at),
        recurrence_rule: subscriptionRecurrence(f.billing_cycle, subscription.recurrence_rule),
      })
      reload()
    } catch (error) {
      onError(errMsg(error))
    } finally {
      setSaving(false)
    }
  }
  const remove = async () => {
    if (!window.confirm(`Delete ${subscription.name}?`)) return
    setSaving(true)
    try {
      await api.deleteSolaceSubscription(subscription.id)
      reload()
    } catch (error) {
      onError(errMsg(error))
    } finally {
      setSaving(false)
    }
  }
  return (
    <details className="mt-3 border-t border-line pt-3">
      <summary className="cursor-pointer text-sm font-medium text-primary">Edit subscription</summary>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <Field label="Name"><Input value={f.name} onChange={event => set('name', event.target.value)} /></Field>
        <Field label="Provider"><Input value={f.provider} onChange={event => set('provider', event.target.value)} /></Field>
        <Field label="Amount"><Input type="number" step="0.01" value={f.amount} onChange={event => set('amount', event.target.value)} /></Field>
        <Field label="Cycle"><Select value={f.billing_cycle} onChange={event => set('billing_cycle', event.target.value)}>{['weekly', 'fortnightly', 'monthly', 'quarterly', 'yearly', 'other'].map(cycle => <option key={cycle} value={cycle}>{cap(cycle)}</option>)}</Select></Field>
        <Field label="Renewal"><input type="datetime-local" className={fieldClass} value={f.next_renewal_at} onChange={event => set('next_renewal_at', event.target.value)} /></Field>
        <Field label="Notes"><Input value={f.notes} onChange={event => set('notes', event.target.value)} /></Field>
      </div>
      <label className="mt-3 flex items-center gap-2 text-sm text-muted">
        <input type="checkbox" checked={f.is_active} onChange={event => set('is_active', event.target.checked)} />
        Active
      </label>
      <div className="mt-3 flex gap-2">
        <Button size="sm" onClick={save} loading={saving} disabled={!f.name.trim()}>Save</Button>
        <Button size="sm" variant="danger" onClick={remove} disabled={saving}>Delete</Button>
      </div>
    </details>
  )
}

function SubscriptionsTab({ subscriptions, reload, onError }: {
  subscriptions: SolaceSubscription[]; reload: () => void; onError: (message: string) => void
}) {
  return (
    <div className="flex flex-col gap-4">
      <CreatePanel label="Add subscription">
        {close => <SubscriptionForm onCreated={() => { reload(); close() }} onError={onError} />}
      </CreatePanel>
      <div className="grid gap-3 lg:grid-cols-3">
        {subscriptions.map(s => (
          <Card key={s.id} contentClassName="p-4">
            <div className="flex items-start justify-between gap-3">
              <div><h3 className="font-semibold text-ink">{s.name}</h3><p className="text-sm text-muted">{s.provider || cap(s.billing_cycle)} · {money(s.amount)}</p></div>
              <DueBadge iso={s.next_renewal_at} />
            </div>
            {!s.is_active && <div className="mt-2"><Badge tone="neutral">Paused</Badge></div>}
            <SubscriptionEditor subscription={s} reload={reload} onError={onError} />
          </Card>
        ))}
      </div>
    </div>
  )
}

function PurchaseForm({ categories, onCreated, onError }: {
  categories: string[]; onCreated: () => void; onError: (message: string) => void
}) {
  const [f, setF] = useState({ name: '', category: '', target_amount: '', saved_amount: '', target_date: '', priority: 'medium' })
  const [saving, setSaving] = useState(false)
  const set = (k: string, v: string) => setF(prev => ({ ...prev, [k]: v }))
  const save = async () => {
    setSaving(true)
    try {
      await api.createSolacePurchase({ ...f, target_amount: f.target_amount || '0.00', saved_amount: f.saved_amount || '0.00', target_date: fromLocalInput(f.target_date), status: 'saving', is_all_day: true })
      setF({ name: '', category: '', target_amount: '', saved_amount: '', target_date: '', priority: 'medium' })
      onCreated()
    } catch (error) {
      onError(errMsg(error))
    } finally { setSaving(false) }
  }
  return (
    <Card contentClassName="p-4">
      <div className="grid gap-3 lg:grid-cols-[1.3fr_1fr_0.8fr_0.8fr_1fr_auto]">
        <Field label="Purchase"><Input value={f.name} onChange={e => set('name', e.target.value)} /></Field>
        <Field label="Category"><Select value={f.category} onChange={e => set('category', e.target.value)}><option value="">Choose…</option>{categories.map(category => <option key={category} value={category}>{cap(category)}</option>)}</Select></Field>
        <Field label="Target"><Input type="number" step="0.01" value={f.target_amount} onChange={e => set('target_amount', e.target.value)} /></Field>
        <Field label="Saved"><Input type="number" step="0.01" value={f.saved_amount} onChange={e => set('saved_amount', e.target.value)} /></Field>
        <Field label="Target date"><input type="datetime-local" className={fieldClass} value={f.target_date} onChange={e => set('target_date', e.target.value)} /></Field>
        <Field label="Priority"><Select value={f.priority} onChange={e => set('priority', e.target.value)}>{['low', 'medium', 'high'].map(value => <option key={value} value={value}>{cap(value)}</option>)}</Select></Field>
        <div className="flex items-end"><Button onClick={save} loading={saving} disabled={!f.name.trim()} className="w-full">Add</Button></div>
      </div>
    </Card>
  )
}

function PurchaseEditor({ purchase, categories, reload, onError }: {
  purchase: SolacePurchase; categories: string[]; reload: () => void; onError: (message: string) => void
}) {
  const [f, setF] = useState({
    name: purchase.name,
    category: purchase.category,
    target_amount: purchase.target_amount,
    saved_amount: purchase.saved_amount,
    target_date: toLocalInput(purchase.target_date),
    priority: purchase.priority,
    status: purchase.status,
    notes: purchase.notes,
  })
  const [saving, setSaving] = useState(false)
  const set = (key: string, value: string) => setF(previous => ({ ...previous, [key]: value }))
  const save = async (override?: Partial<typeof f>) => {
    setSaving(true)
    try {
      const values = { ...f, ...override }
      await api.updateSolacePurchase(purchase.id, {
        ...values,
        target_amount: values.target_amount || '0.00',
        saved_amount: values.saved_amount || '0.00',
        target_date: fromLocalInput(values.target_date),
      })
      reload()
    } catch (error) {
      onError(errMsg(error))
    } finally {
      setSaving(false)
    }
  }
  const remove = async () => {
    if (!window.confirm(`Delete ${purchase.name}?`)) return
    setSaving(true)
    try {
      await api.deleteSolacePurchase(purchase.id)
      reload()
    } catch (error) {
      onError(errMsg(error))
    } finally {
      setSaving(false)
    }
  }
  return (
    <details className="mt-3 border-t border-line pt-3">
      <summary className="cursor-pointer text-sm font-medium text-primary">Edit purchase</summary>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <Field label="Name"><Input value={f.name} onChange={event => set('name', event.target.value)} /></Field>
        <Field label="Category"><Select value={f.category} onChange={event => set('category', event.target.value)}>{!categories.includes(f.category) && <option value={f.category}>{cap(f.category)}</option>}{categories.map(category => <option key={category} value={category}>{cap(category)}</option>)}</Select></Field>
        <Field label="Target"><Input type="number" min="0" step="0.01" value={f.target_amount} onChange={event => set('target_amount', event.target.value)} /></Field>
        <Field label="Saved"><Input type="number" min="0" step="0.01" value={f.saved_amount} onChange={event => set('saved_amount', event.target.value)} /></Field>
        <Field label="Target date"><input type="datetime-local" className={fieldClass} value={f.target_date} onChange={event => set('target_date', event.target.value)} /></Field>
        <Field label="Priority"><Select value={f.priority} onChange={event => set('priority', event.target.value)}>{['low', 'medium', 'high'].map(value => <option key={value} value={value}>{cap(value)}</option>)}</Select></Field>
        <Field label="Status"><Select value={f.status} onChange={event => set('status', event.target.value)}>{['planned', 'saving', 'ready', 'bought', 'cancelled'].map(value => <option key={value} value={value}>{cap(value)}</option>)}</Select></Field>
        <Field label="Notes"><Input value={f.notes} onChange={event => set('notes', event.target.value)} /></Field>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        <Button size="sm" onClick={() => save()} loading={saving} disabled={!f.name.trim()}>Save</Button>
        {purchase.status !== 'bought' && <Button size="sm" variant="ghost" onClick={() => save({ status: 'bought', saved_amount: f.target_amount })} disabled={saving}>Mark bought</Button>}
        <Button size="sm" variant="danger" onClick={remove} disabled={saving}>Delete</Button>
      </div>
    </details>
  )
}

function PurchasesTab({ purchases, categories, reload, onError }: {
  purchases: SolacePurchase[]; categories: string[]; reload: () => void; onError: (message: string) => void
}) {
  const QuickSave = ({ purchase }: { purchase: SolacePurchase }) => {
    const [amount, setAmount] = useState('')
    const [saving, setSaving] = useState(false)
    const add = async () => {
      setSaving(true)
      try {
        await api.addSolacePurchaseSavings(purchase.id, amount)
        setAmount('')
        reload()
      } catch (error) {
        onError(errMsg(error))
      } finally {
        setSaving(false)
      }
    }
    if (!purchase.is_open || Number(purchase.remaining_amount) <= 0) return null
    return (
      <div className="mt-3 flex gap-2">
        <Input
          type="number"
          min="0.01"
          max={purchase.remaining_amount}
          step="0.01"
          value={amount}
          onChange={event => setAmount(event.target.value)}
          onKeyDown={event => { if (event.key === 'Enter' && Number(amount) > 0) void add() }}
          placeholder="Add saved amount"
        />
        <Button size="sm" variant="ghost" onClick={add} loading={saving} disabled={Number(amount) <= 0}>Add</Button>
      </div>
    )
  }
  return (
    <div className="flex flex-col gap-4">
      <CreatePanel label="Add purchase">
        {close => <PurchaseForm categories={categories} onCreated={() => { reload(); close() }} onError={onError} />}
      </CreatePanel>
      <div className="grid gap-3 lg:grid-cols-3">
        {purchases.map(p => (
          <Card key={p.id} contentClassName="p-4">
            <div className="flex items-start justify-between gap-3">
              <div><h3 className="font-semibold text-ink">{p.name}</h3><p className="text-sm text-muted">{p.category || 'Planned'} · {money(p.saved_amount)} saved</p></div>
              <Badge tone={p.priority === 'high' ? 'warning' : 'neutral'}>{p.progress_percent}%</Badge>
            </div>
            <div className="mt-4 h-2 rounded-full bg-sunken overflow-hidden"><div className="h-full bg-primary" style={{ width: `${p.progress_percent}%` }} /></div>
            <p className="mt-2 text-sm text-muted">{money(p.remaining_amount)} left · {dateOnly(p.target_date)}</p>
            <div className="mt-2"><Badge tone={p.status === 'bought' ? 'success' : p.status === 'cancelled' ? 'neutral' : 'primary'}>{cap(p.status)}</Badge></div>
            <QuickSave purchase={p} />
            <PurchaseEditor purchase={p} categories={categories} reload={reload} onError={onError} />
          </Card>
        ))}
      </div>
    </div>
  )
}

function PaydayForm({ onCreated, onError }: {
  onCreated: () => void; onError: (message: string) => void
}) {
  const [f, setF] = useState({ title: 'Payday', expected_amount: '', pay_at: '', recurrence_rule: 'FREQ=WEEKLY;INTERVAL=2' })
  const [saving, setSaving] = useState(false)
  const set = (k: string, v: string) => setF(prev => ({ ...prev, [k]: v }))
  const save = async () => {
    setSaving(true)
    try {
      await api.createSolacePayday({
        ...f,
        expected_amount: f.expected_amount || '0.00',
        pay_at: fromLocalInput(f.pay_at),
        is_all_day: true,
        is_active: true,
      })
      setF({ title: 'Payday', expected_amount: '', pay_at: '', recurrence_rule: 'FREQ=WEEKLY;INTERVAL=2' })
      onCreated()
    } catch (error) {
      onError(errMsg(error))
    } finally { setSaving(false) }
  }
  return (
    <Card contentClassName="p-4">
      <div className="grid gap-3 lg:grid-cols-[1.4fr_0.8fr_1fr_1fr_auto]">
        <Field label="Title"><Input value={f.title} onChange={e => set('title', e.target.value)} /></Field>
        <Field label="Expected"><Input type="number" step="0.01" value={f.expected_amount} onChange={e => set('expected_amount', e.target.value)} /></Field>
        <Field label="Date"><input type="datetime-local" className={fieldClass} value={f.pay_at} onChange={e => set('pay_at', e.target.value)} /></Field>
        <Field label="Repeats"><Select value={f.recurrence_rule} onChange={e => set('recurrence_rule', e.target.value)}>{RECURRENCE.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}</Select></Field>
        <div className="flex items-end"><Button onClick={save} loading={saving} disabled={!f.title.trim()} className="w-full">Add</Button></div>
      </div>
    </Card>
  )
}

function PaydaysTab({ paydays, reload, onError }: {
  paydays: SolacePayday[]; reload: () => void; onError: (message: string) => void
}) {
  const toggle = async (payday: SolacePayday) => {
    try {
      await api.updateSolacePayday(payday.id, { is_active: !payday.is_active })
      reload()
    } catch (e) {
      onError(errMsg(e))
    }
  }
  const PaydayEditor = ({ payday }: { payday: SolacePayday }) => {
    const [f, setF] = useState({
      title: payday.title,
      expected_amount: payday.expected_amount,
      pay_at: toLocalInput(payday.pay_at),
      recurrence_rule: payday.recurrence_rule,
      notes: payday.notes,
    })
    const [saving, setSaving] = useState(false)
    const set = (key: string, value: string) => setF(previous => ({ ...previous, [key]: value }))
    const save = async () => {
      setSaving(true)
      try {
        await api.updateSolacePayday(payday.id, {
          ...f,
          expected_amount: f.expected_amount || '0.00',
          pay_at: fromLocalInput(f.pay_at),
        })
        reload()
      } catch (error) {
        onError(errMsg(error))
      } finally {
        setSaving(false)
      }
    }
    const remove = async () => {
      if (!window.confirm(`Delete ${payday.title}?`)) return
      setSaving(true)
      try {
        await api.deleteSolacePayday(payday.id)
        reload()
      } catch (error) {
        onError(errMsg(error))
      } finally {
        setSaving(false)
      }
    }
    return (
      <details className="mt-3 border-t border-line pt-3">
        <summary className="cursor-pointer text-sm font-medium text-primary">Edit income source</summary>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <Field label="Title"><Input value={f.title} onChange={event => set('title', event.target.value)} /></Field>
          <Field label="Expected"><Input type="number" min="0" step="0.01" value={f.expected_amount} onChange={event => set('expected_amount', event.target.value)} /></Field>
          <Field label="Next date"><input type="datetime-local" className={fieldClass} value={f.pay_at} onChange={event => set('pay_at', event.target.value)} /></Field>
          <Field label="Repeats"><Select value={f.recurrence_rule} onChange={event => set('recurrence_rule', event.target.value)}>{RECURRENCE.map(rule => <option key={rule.value} value={rule.value}>{rule.label}</option>)}</Select></Field>
          <Field label="Notes"><Input value={f.notes} onChange={event => set('notes', event.target.value)} /></Field>
        </div>
        <div className="mt-3 flex gap-2">
          <Button size="sm" onClick={save} loading={saving} disabled={!f.title.trim()}>Save</Button>
          <Button size="sm" variant="danger" onClick={remove} disabled={saving}>Delete</Button>
        </div>
      </details>
    )
  }
  return (
    <div className="flex flex-col gap-4">
      <CreatePanel label="Add payday">
        {close => <PaydayForm onCreated={() => { reload(); close() }} onError={onError} />}
      </CreatePanel>
      <div className="grid gap-3 lg:grid-cols-3">
        {paydays.map(p => (
          <Card key={p.id} contentClassName="p-4">
            <div className="flex items-start justify-between gap-3">
              <div><h3 className="font-semibold text-ink">{p.title}</h3><p className="text-sm text-muted">{money(p.expected_amount)}</p></div>
              <Badge tone={p.is_active ? 'success' : 'neutral'}>{p.is_active ? 'Included' : 'Paused'}</Badge>
            </div>
            <div className="mt-3 flex items-center justify-between gap-3">
              <div className="text-sm">
                <p className="font-medium text-ink">Upcoming {dateOnly(p.next_pay_at)}</p>
                <p className="text-xs text-muted">Known anchor {dateOnly(p.pay_at)}</p>
              </div>
              <Button size="sm" variant="ghost" onClick={() => toggle(p)}>
                {p.is_active ? 'Pause' : 'Include'}
              </Button>
            </div>
            <PaydayEditor payday={p} />
          </Card>
        ))}
      </div>
    </div>
  )
}

function ChecklistTab({ items, preferences, plan, generating, reload, onGenerate, onChange, onError }: {
  items: SolaceChecklistItem[]
  preferences: SolaceChecklistPreference[]
  plan: SolacePayCyclePlan | null
  generating: boolean
  reload: () => void
  onGenerate: (date?: string) => void
  onChange: (items: SolaceChecklistItem[]) => void
  onError: (m: string) => void
}) {
  const [title, setTitle] = useState('')
  const [saving, setSaving] = useState(false)
  const [viewedPlan, setViewedPlan] = useState(plan)
  const [loadingCycle, setLoadingCycle] = useState(false)
  useEffect(() => setViewedPlan(plan), [plan])
  const openCycle = async (date?: string) => {
    setLoadingCycle(true)
    try {
      const selectedPlan = await api.getSolacePlan(date)
      const selectedItems = await api.getSolaceChecklist({
        date: selectedPlan.cycle_start,
        latest: false,
      })
      setViewedPlan(selectedPlan)
      onChange(selectedItems)
    } catch (error) {
      onError(errMsg(error))
    } finally {
      setLoadingCycle(false)
    }
  }
  const add = async () => {
    setSaving(true)
    try {
      await api.createSolaceChecklistItem({ title })
      setTitle('')
      await openCycle(viewedPlan?.cycle_start)
    }
    catch (e) { onError(errMsg(e)) }
    finally { setSaving(false) }
  }
  const toggle = async (item: SolaceChecklistItem) => {
    const optimistic = { ...item, is_complete: !item.is_complete }
    onChange(items.map(row => row.id === item.id ? optimistic : row))
    try {
      const updated = await api.updateSolaceChecklistItem(item.id, { is_complete: !item.is_complete })
      onChange(items.map(row => row.id === item.id ? updated : row))
    } catch (e) {
      onChange(items)
      onError(errMsg(e))
    }
  }
  const remove = async (item: SolaceChecklistItem) => {
    try {
      if (item.source_key) {
        await api.setSolaceChecklistPreference({
          source_key: item.source_key,
          label: item.title,
          is_hidden: true,
        })
      } else {
        await api.deleteSolaceChecklistItem(item.id)
      }
      reload()
    } catch (e) {
      onError(errMsg(e))
    }
  }
  const restore = async (preference: SolaceChecklistPreference) => {
    try {
      await api.setSolaceChecklistPreference({
        source_key: preference.source_key,
        label: preference.label,
        is_hidden: false,
      })
      reload()
    } catch (e) {
      onError(errMsg(e))
    }
  }
  return (
    <div className="flex flex-col gap-4">
      {viewedPlan && (
        <Card contentClassName="p-4">
          <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
            <div>
              <p className="text-sm font-medium text-muted">Payday checklist</p>
              <h2 className="text-lg font-bold text-ink">{dateOnly(viewedPlan.cycle_start)} – {dateOnly(viewedPlan.cycle_end)}</h2>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button size="sm" variant="ghost" onClick={() => openCycle()} disabled={loadingCycle}>Current</Button>
              <Button size="sm" variant="ghost" onClick={() => openCycle(dayAfter(viewedPlan.cycle_end))} loading={loadingCycle}>Next</Button>
              <Button size="sm" onClick={() => onGenerate(viewedPlan.cycle_start)} loading={generating} disabled={viewedPlan.buckets.length === 0}>
                Create / refresh
              </Button>
            </div>
          </div>
        </Card>
      )}
      <Card contentClassName="p-4">
        <div className="flex flex-col gap-3 sm:flex-row">
          <Input value={title} onChange={e => setTitle(e.target.value)} placeholder="Move money to bills account" />
          <Button onClick={add} loading={saving} disabled={!title.trim()}>Add</Button>
        </div>
      </Card>
      {items.length === 0 ? (
        <EmptyState icon="✅" title="No checklist items for this cycle" hint="Create the generated transfer checklist or add a household item." />
      ) : <div className="grid gap-2">
        {items.map(item => (
          <div key={item.id} className="flex items-center rounded-lg border border-line bg-surface">
            <button onClick={() => toggle(item)} className="flex min-w-0 flex-1 items-center justify-between px-4 py-3 text-left hover:bg-sunken/40">
              <span className={item.is_complete ? 'text-muted line-through' : 'text-ink'}>
                {item.title}
                {Number(item.amount_hint) > 0 && <span className="ml-2 text-sm text-muted">{money(item.amount_hint)}</span>}
              </span>
              <div className="flex items-center gap-2">
                {item.cycle_start && <span className="hidden text-xs text-muted sm:inline">{dateOnly(item.cycle_start)}</span>}
                <Badge tone={item.is_complete ? 'success' : 'neutral'}>{item.is_complete ? 'Done' : 'Todo'}</Badge>
              </div>
            </button>
            <Button size="sm" variant="ghost" className="mr-2" onClick={() => remove(item)}>
              {item.source_key ? 'Hide' : 'Delete'}
            </Button>
          </div>
        ))}
      </div>}
      {preferences.some(preference => preference.is_hidden) && (
        <Card contentClassName="p-4">
          <h3 className="font-semibold text-ink">Hidden generated items</h3>
          <div className="mt-3 divide-y divide-line">
            {preferences.filter(preference => preference.is_hidden).map(preference => (
              <div key={preference.id} className="flex items-center justify-between gap-3 py-2">
                <span className="text-sm text-muted">{preference.label}</span>
                <Button size="sm" variant="ghost" onClick={() => restore(preference)}>Restore</Button>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}

type ScheduleEvent =
  | { kind: 'bill'; key: string; due_at: string; title: string; amount: string; occurrence: SolaceBillOccurrence }
  | { kind: 'income'; key: string; due_at: string; title: string; amount: string }

function OccurrenceActions({ occurrence, onAction }: {
  occurrence: SolaceBillOccurrence
  onAction: (id: number, action: 'paid' | 'unpaid' | 'skip') => Promise<SolaceBillOccurrence>
}) {
  const [saving, setSaving] = useState(false)
  const act = async (action: 'paid' | 'unpaid' | 'skip') => {
    setSaving(true)
    try { await onAction(occurrence.id, action) } finally { setSaving(false) }
  }
  if (occurrence.status === 'paid') {
    return <Button size="sm" variant="ghost" disabled={saving} onClick={() => act('unpaid')}>Mark unpaid</Button>
  }
  if (occurrence.status === 'skipped') {
    return <Button size="sm" variant="ghost" disabled={saving} onClick={() => act('unpaid')}>Restore</Button>
  }
  return (
    <div className="flex gap-1">
      <Button size="sm" variant="ghost" loading={saving} onClick={() => act('paid')}>Paid</Button>
      <Button size="sm" variant="ghost" disabled={saving} onClick={() => act('skip')}>Skip</Button>
    </div>
  )
}

function ScheduleTab({ schedule, month, loading, onMonth, onAction }: {
  schedule: SolaceSchedule | null
  month: string
  loading: boolean
  onMonth: (month: string) => void
  onAction: (id: number, action: 'paid' | 'unpaid' | 'skip') => Promise<SolaceBillOccurrence>
}) {
  const [view, setView] = useState<'calendar' | 'list'>(() =>
    window.matchMedia('(max-width: 639px)').matches ? 'list' : 'calendar'
  )
  const [year, monthNumber] = month.split('-').map(Number)
  const label = new Date(year, monthNumber - 1, 1).toLocaleDateString(undefined, { month: 'long', year: 'numeric' })
  const events = useMemo<ScheduleEvent[]>(() => {
    if (!schedule) return []
    return [
      ...schedule.occurrences.map(occurrence => ({
        kind: 'bill' as const,
        key: `bill-${occurrence.id}`,
        due_at: occurrence.due_at,
        title: occurrence.bill_name,
        amount: occurrence.amount,
        occurrence,
      })),
      ...schedule.income_events.map((income, index) => ({
        kind: 'income' as const,
        key: `income-${income.payday_id}-${index}`,
        due_at: income.due_at,
        title: income.title,
        amount: income.amount,
      })),
    ].sort((a, b) => a.due_at.localeCompare(b.due_at) || a.title.localeCompare(b.title))
  }, [schedule])
  const eventsByDay = useMemo(() => {
    const grouped = new Map<string, ScheduleEvent[]>()
    events.forEach(event => grouped.set(dateKey(event.due_at), [...(grouped.get(dateKey(event.due_at)) || []), event]))
    return grouped
  }, [events])
  const dayCount = new Date(year, monthNumber, 0).getDate()
  const firstOffset = (new Date(year, monthNumber - 1, 1).getDay() + 6) % 7
  const cells = Array.from({ length: firstOffset + dayCount }, (_, index) => index < firstOffset ? null : index - firstOffset + 1)
  const todayKey = dateKey(new Date().toISOString())

  const eventRow = (event: ScheduleEvent) => (
    <Card key={event.key} contentClassName="p-3">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <div className="flex min-w-0 items-center gap-3">
          <div className={`grid h-10 w-10 shrink-0 place-items-center rounded-lg ${event.kind === 'income' ? 'bg-success/10' : 'bg-warning/10'}`}>
            {event.kind === 'income' ? '↙' : '↗'}
          </div>
          <div className="min-w-0">
            <p className="truncate font-semibold text-ink">{event.title}</p>
            <p className="text-sm text-muted">
              {dateOnly(event.due_at)} · {money(event.amount)}
              {event.kind === 'bill' ? ` · ${cap(event.occurrence.status)}` : ' · Expected income'}
            </p>
          </div>
        </div>
        {event.kind === 'bill' && <OccurrenceActions occurrence={event.occurrence} onAction={onAction} />}
      </div>
    </Card>
  )

  return (
    <div className="space-y-4">
      <Card contentClassName="p-3">
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
          <div className="flex items-center gap-2">
            <Button size="sm" variant="ghost" onClick={() => onMonth(shiftMonth(month, -1))}>‹</Button>
            <div className="min-w-40 text-center">
              <h2 className="font-bold text-ink">{label}</h2>
              {loading && <p className="text-xs text-muted">Updating…</p>}
            </div>
            <Button size="sm" variant="ghost" onClick={() => onMonth(shiftMonth(month, 1))}>›</Button>
            <Button size="sm" variant="ghost" onClick={() => onMonth(currentMonthKey())}>Today</Button>
          </div>
          <div className="flex rounded-lg bg-sunken p-1">
            <button className={`rounded-md px-3 py-1.5 text-sm ${view === 'calendar' ? 'bg-surface font-semibold text-ink shadow-sm' : 'text-muted'}`} onClick={() => setView('calendar')}>Calendar</button>
            <button className={`rounded-md px-3 py-1.5 text-sm ${view === 'list' ? 'bg-surface font-semibold text-ink shadow-sm' : 'text-muted'}`} onClick={() => setView('list')}>List</button>
          </div>
        </div>
      </Card>
      {schedule && (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
          {[
            ['Bills', schedule.summary.bills_total],
            ['Paid', schedule.summary.paid_total],
            ['Unpaid', schedule.summary.unpaid_total],
            ['Skipped', schedule.summary.skipped_total],
            ['Income', schedule.summary.income_total],
          ].map(([title, value]) => (
            <Card key={title} contentClassName="p-3">
              <p className="text-lg font-extrabold text-ink">{money(value)}</p>
              <p className="text-xs text-muted">{title}</p>
            </Card>
          ))}
        </div>
      )}
      {view === 'calendar' ? (
        <Card className="overflow-x-auto" contentClassName="p-3">
          <div className="min-w-[760px]">
            <div className="grid grid-cols-7 text-center text-xs font-semibold uppercase tracking-wide text-muted">
              {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map(day => <div key={day} className="p-2">{day}</div>)}
            </div>
            <div className="grid grid-cols-7">
              {cells.map((day, index) => {
                if (!day) return <div key={`empty-${index}`} className="min-h-28 border border-line/60 bg-sunken/30" />
                const key = `${month}-${String(day).padStart(2, '0')}`
                const dayEvents = eventsByDay.get(key) || []
                return (
                  <div key={key} className={`min-h-28 border border-line/60 p-2 ${key === todayKey ? 'bg-primary/5 ring-1 ring-inset ring-primary/40' : 'bg-surface'}`}>
                    <p className="text-xs font-semibold text-muted">{day}</p>
                    <div className="mt-1 space-y-1">
                      {dayEvents.map(event => (
                        <div
                          key={event.key}
                          className={`rounded px-1.5 py-1 text-[11px] leading-tight ${event.kind === 'income' ? 'bg-success/10 text-success' : event.occurrence.status === 'paid' ? 'bg-primary/10 text-primary' : event.occurrence.status === 'skipped' ? 'bg-sunken text-muted' : 'bg-warning/10 text-ink'}`}
                          title={`${event.title} · ${money(event.amount)}`}
                        >
                          <p className="truncate font-semibold">{event.title}</p>
                          <p>{money(event.amount)}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </Card>
      ) : events.length === 0 ? (
        <EmptyState icon="🗓️" title="Nothing scheduled this month" hint="Recurring bills and active paydays will appear here." />
      ) : (
        <div className="grid gap-2">{events.map(eventRow)}</div>
      )}
    </div>
  )
}

function Overview({ bills, buckets, subscriptions, purchases, health, closeout, forecast, onTab }: {
  bills: SolaceBill[]; buckets: SolaceBucket[]; subscriptions: SolaceSubscription[]
  purchases: SolacePurchase[]; health: SolaceHealth | null; closeout: SolaceCloseoutResponse | null
  forecast: SolaceBalanceForecast | null
  onTab: (t: Tab) => void
}) {
  const unpaidTotal = useMemo(() => bills.filter(b => !b.is_paid).reduce((sum, b) => sum + Number(b.amount || 0), 0), [bills])
  const bucketTotal = useMemo(() => buckets.reduce((sum, b) => sum + Number(b.current_amount || 0), 0), [buckets])
  const subTotal = useMemo(() => subscriptions.filter(s => s.is_active).reduce((sum, s) => sum + Number(s.amount || 0), 0), [subscriptions])
  const openPurchases = purchases.filter(p => p.is_open)
  const stat = (label: string, value: string, tab: Tab, tone: BadgeTone) => (
    <button onClick={() => onTab(tab)} className="rounded-lg border border-line bg-surface p-4 text-left hover:bg-sunken/40">
      <div className="flex items-center justify-between gap-3">
        <span className="text-2xl font-extrabold text-ink">{value}</span>
        <Badge tone={tone}>View</Badge>
      </div>
      <p className="mt-1 text-sm text-muted">{label}</p>
    </button>
  )
  return (
    <div className="space-y-4">
      <HealthPanel health={health} onManage={() => onTab('manage')} />
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {stat(
          `Available to withdraw (${forecast?.horizon_months || 12} mo)`,
          forecast?.safe_to_withdraw === null || forecast?.safe_to_withdraw === undefined ? 'Not set' : money(forecast.safe_to_withdraw),
          'forecast',
          forecast?.is_covered === false ? 'danger' : forecast?.safe_to_withdraw && Number(forecast.safe_to_withdraw) > 0 ? 'success' : 'primary',
        )}
        {stat('Unpaid this cycle', closeout ? money(closeout.summary.unpaid_total) : money(unpaidTotal), 'closeout', closeout?.summary.unpaid_count ? 'warning' : 'success')}
        {stat('Set aside', money(bucketTotal), 'buckets', 'primary')}
        {stat('Planned purchases', String(openPurchases.length), 'purchases', openPurchases.length ? 'warning' : 'success')}
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        {stat('Active subscriptions', money(subTotal), 'subscriptions', 'neutral')}
        {stat('Pay-cycle status', closeout?.closeout?.status === 'closed' ? 'Closed' : 'Open', 'closeout', closeout?.closeout?.status === 'closed' ? 'success' : 'warning')}
      </div>
    </div>
  )
}

function ForecastTab({ initial, onManage, onError }: {
  initial: SolaceBalanceForecast | null
  onManage: () => void
  onError: (message: string) => void
}) {
  const [forecast, setForecast] = useState(initial)
  const [months, setMonths] = useState(initial?.horizon_months || 12)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setForecast(initial)
    setMonths(initial?.horizon_months || 12)
  }, [initial])

  const refresh = async (nextMonths = months) => {
    setLoading(true)
    try {
      setForecast(await api.getSolaceForecast(nextMonths))
    } catch (error) {
      onError(errMsg(error))
    } finally {
      setLoading(false)
    }
  }

  if (!forecast) {
    return <EmptyState icon="📈" title="Forecast is not available" hint="Refresh Solace to calculate the bills-account forecast." />
  }
  if (!forecast.latest_balance) {
    return (
      <div className="space-y-4">
        <EmptyState
          icon="🏦"
          title="Record the bills-account balance"
          hint={`Solace needs an opening balance to calculate what can be withdrawn. Based on scheduled cash flow, at least ${money(forecast.required_opening_balance)} is required through ${dateOnly(forecast.through)}.`}
          action={<Button onClick={onManage}>Add balance</Button>}
        />
      </div>
    )
  }

  const covered = forecast.is_covered === true
  return (
    <div className="space-y-4">
      <Card contentClassName="p-4">
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold text-ink">Bills-account forecast</h2>
              <Badge tone={covered ? 'success' : 'danger'}>{covered ? 'All covered' : 'Shortfall'}</Badge>
            </div>
            <p className="mt-1 text-sm text-muted">
              From the {money(forecast.opening_balance || '0')} balance recorded {dateOnly(forecast.latest_balance.snapshot_date)} through {dateOnly(forecast.through)}.
            </p>
          </div>
          <div className="flex items-end gap-2">
            <Field label="Forecast period">
              <Select
                value={months}
                onChange={event => {
                  const value = Number(event.target.value)
                  setMonths(value)
                  void refresh(value)
                }}
              >
                {[3, 6, 12, 18, 24].map(value => <option key={value} value={value}>{value} months</option>)}
              </Select>
            </Field>
            <Button variant="ghost" onClick={() => refresh()} loading={loading}>Refresh</Button>
          </div>
        </div>
      </Card>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Card contentClassName="p-4">
          <p className="text-sm font-medium text-muted">Available to withdraw</p>
          <p className={`mt-1 text-3xl font-extrabold ${covered ? 'text-success' : 'text-danger'}`}>
            {covered ? money(forecast.safe_to_withdraw || '0') : money('0')}
          </p>
          <p className="mt-1 text-xs text-muted">Keeps every listed bill covered plus the {money(forecast.buffer_amount)} safety buffer.</p>
        </Card>
        <Card contentClassName="p-4">
          <p className="text-sm font-medium text-muted">Bills-only surplus</p>
          <p className="mt-1 text-2xl font-extrabold text-ink">{money(forecast.bills_only_surplus || '0')}</p>
          <p className="mt-1 text-xs text-muted">Maximum before preserving the safety buffer.</p>
        </Card>
        <Card contentClassName="p-4">
          <p className="text-sm font-medium text-muted">Lowest forecast balance</p>
          <p className={`mt-1 text-2xl font-extrabold ${Number(forecast.lowest_balance) < 0 ? 'text-danger' : 'text-ink'}`}>{money(forecast.lowest_balance || '0')}</p>
          <p className="mt-1 text-xs text-muted">Reached {dateOnly(forecast.lowest_balance_date)}.</p>
        </Card>
        <Card contentClassName="p-4">
          <p className="text-sm font-medium text-muted">Ending balance</p>
          <p className="mt-1 text-2xl font-extrabold text-ink">{money(forecast.ending_balance || '0')}</p>
          <p className="mt-1 text-xs text-muted">After expected transfers and bills.</p>
        </Card>
      </div>

      {!covered && (
        <Card className="border-danger/30 bg-danger/5" contentClassName="p-4">
          <h3 className="font-bold text-danger">Projected shortfall of {money(forecast.shortfall || '0')}</h3>
          <p className="mt-1 text-sm text-muted">
            The account first reaches its lowest point on {dateOnly(forecast.lowest_balance_date)}. Increase Bills-bucket transfers or top up the account before then.
          </p>
        </Card>
      )}

      <div className="grid gap-3 sm:grid-cols-3">
        <Card contentClassName="p-3"><p className="text-lg font-bold text-success">+{money(forecast.total_contributions)}</p><p className="text-xs text-muted">Expected Bills-bucket transfers</p></Card>
        <Card contentClassName="p-3"><p className="text-lg font-bold text-ink">−{money(forecast.total_bills)}</p><p className="text-xs text-muted">Included bills + subscriptions due</p></Card>
        <Card contentClassName="p-3"><p className="text-lg font-bold text-ink">{money(forecast.required_opening_balance)}</p><p className="text-xs text-muted">Minimum opening balance required</p></Card>
      </div>

      <Card className="overflow-hidden">
        <div className="border-b border-line px-4 py-3">
          <h3 className="font-bold text-ink">Forecast timeline</h3>
          <p className="text-sm text-muted">Transfers are added and bills are deducted on their scheduled dates.</p>
        </div>
        {forecast.timeline.length === 0 ? (
          <p className="p-4 text-sm text-muted">No scheduled bills or Bills-bucket transfers in this period.</p>
        ) : (
          <div className="divide-y divide-line">
            {forecast.timeline.map(row => (
              <details key={row.date} className="px-4 py-3">
                <summary className="grid cursor-pointer list-none grid-cols-[1fr_auto] items-center gap-3 sm:grid-cols-[1fr_auto_auto_auto]">
                  <span className="font-semibold text-ink">{dateOnly(row.date)}</span>
                  <span className="hidden text-sm text-success sm:block">+{money(row.contributions)}</span>
                  <span className="hidden text-sm text-muted sm:block">−{money(row.bills)}</span>
                  <span className={`font-bold ${Number(row.projected_balance) < 0 ? 'text-danger' : 'text-ink'}`}>{money(row.projected_balance || '0')}</span>
                </summary>
                <div className="mt-3 space-y-1 border-t border-line pt-2 text-sm">
                  {row.items.map((item, index) => (
                    <div key={`${item.kind}-${item.record_id}-${index}`} className="flex justify-between gap-3">
                      <span className="text-muted">{item.kind === 'contribution' ? 'Transfer from' : item.kind === 'subscription' ? 'Subscription' : 'Bill'} · {item.name}</span>
                      <span className={item.kind === 'contribution' ? 'font-medium text-success' : 'font-medium text-ink'}>
                        {item.kind === 'contribution' ? '+' : '−'}{money(item.amount)}
                      </span>
                    </div>
                  ))}
                </div>
              </details>
            ))}
          </div>
        )}
      </Card>
      <p className="text-xs text-muted">
        Forecasts use expected income allocations and scheduled bill amounts; they are not bank transactions. Update the balance snapshot whenever the real account changes materially.
      </p>
    </div>
  )
}

function PayPlan({ plan, generating, onGenerate, onTab, onError }: {
  plan: SolacePayCyclePlan | null
  generating: boolean
  onGenerate: (date?: string) => void
  onTab: (tab: Tab) => void
  onError: (message: string) => void
}) {
  const [viewed, setViewed] = useState(plan)
  const [loadingCycle, setLoadingCycle] = useState(false)
  useEffect(() => setViewed(plan), [plan])
  const openCycle = async (date?: string) => {
    setLoadingCycle(true)
    try {
      setViewed(await api.getSolacePlan(date))
    } catch (error) {
      onError(errMsg(error))
    } finally {
      setLoadingCycle(false)
    }
  }
  if (!viewed) {
    return (
      <EmptyState
        icon="🧮"
        title="Pay plan is not available"
        hint="Refresh Solace to calculate the current cycle."
      />
    )
  }
  return (
    <div className="space-y-4">
      <Card contentClassName="p-4">
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
          <div>
            <p className="text-sm font-medium text-muted">Pay cycle</p>
            <h2 className="text-lg font-bold text-ink">{dateOnly(viewed.cycle_start)} – {dateOnly(viewed.cycle_end)}</h2>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="ghost" onClick={() => openCycle()} disabled={loadingCycle}>Current</Button>
            <Button size="sm" variant="ghost" onClick={() => openCycle(dayAfter(viewed.cycle_end))} loading={loadingCycle}>Next</Button>
            <Button onClick={() => onGenerate(viewed.cycle_start)} loading={generating} disabled={viewed.buckets.length === 0}>
              Create payday checklist
            </Button>
          </div>
        </div>
      </Card>
      {viewed.sources.length === 0 && (
        <EmptyState
          icon="🧮"
          title="No income in this pay cycle"
          hint="The set-aside requirement is still shown below. Add an income source to calculate the transfer split."
          action={<Button onClick={() => onTab('paydays')}>Add payday</Button>}
        />
      )}
      <div className="grid gap-3 sm:grid-cols-3">
        {[
          ['Expected income', money(viewed.income_total)],
          ['Bucket transfers', money(viewed.allocated_total)],
          ['Remaining after transfers', money(viewed.remaining)],
        ].map(([label, value]) => (
          <Card key={label} contentClassName="p-4">
            <p className="text-2xl font-extrabold text-ink">{value}</p>
            <p className="mt-1 text-sm text-muted">{label}</p>
          </Card>
        ))}
      </div>
      <Card contentClassName="p-4">
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-bold text-ink">Required fortnightly set-aside</h3>
              <Badge tone={viewed.set_aside.is_covered ? 'success' : 'warning'}>
                {viewed.set_aside.is_covered ? 'Covered' : `${money(viewed.set_aside.shortfall)} short`}
              </Badge>
            </div>
            <p className="mt-1 text-sm text-muted">What needs to be reserved for bills, purchase goals and the safety buffer.</p>
          </div>
          <p className="text-2xl font-extrabold text-ink">{money(viewed.set_aside.required_total)}</p>
        </div>
        <div className="mt-4 grid gap-2 border-t border-line pt-3 text-sm sm:grid-cols-4">
          <div><p className="text-muted">Recurring bills</p><p className="font-semibold text-ink">{money(viewed.set_aside.recurring_bills)}</p></div>
          <div><p className="text-muted">Planned purchases</p><p className="font-semibold text-ink">{money(viewed.set_aside.planned_purchases)}</p></div>
          <div><p className="text-muted">Buffer</p><p className="font-semibold text-ink">{money(viewed.set_aside.buffer)}</p></div>
          <div><p className="text-muted">Bills buckets</p><p className="font-semibold text-ink">{money(viewed.set_aside.bills_bucket_total)}</p></div>
        </div>
      </Card>
      {viewed.buckets.length === 0 ? (
        <EmptyState
          icon="🪣"
          title="No active allocation rules"
          hint="Set a percentage or fixed pay-cycle amount on at least one bucket."
          action={<Button onClick={() => onTab('buckets')}>Configure buckets</Button>}
        />
      ) : (
        <Card className="divide-y divide-line">
          {viewed.buckets.map(bucket => (
            <div key={bucket.bucket_id} className="flex items-center justify-between gap-3 px-4 py-3">
              <div>
                <p className="font-semibold text-ink">{bucket.bucket_name}</p>
                <p className="text-sm text-muted">{bucket.category || 'Set-aside'}</p>
              </div>
              <p className="text-lg font-bold text-ink">{money(bucket.amount)}</p>
            </div>
          ))}
        </Card>
      )}
      <div className="grid gap-3 lg:grid-cols-2">
        {viewed.sources.map(source => (
          <Card key={source.payday_id} contentClassName="p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="font-semibold text-ink">{source.title}</h3>
                <p className="text-sm text-muted">
                  {source.pay_dates.map(dateOnly).join(', ')}
                </p>
              </div>
              <p className="font-bold text-ink">{money(source.income_total)}</p>
            </div>
            <div className="mt-3 space-y-2 border-t border-line pt-3 text-sm">
              {source.allocations.filter(row => Number(row.amount) > 0).map(row => (
                <div key={row.bucket_id} className="flex justify-between gap-3">
                  <span className="text-muted">{row.bucket_name}{row.capped ? ' (capped)' : ''}</span>
                  <span className="font-medium text-ink">{money(row.amount)}</span>
                </div>
              ))}
              <div className="flex justify-between gap-3 border-t border-line pt-2">
                <span className="font-medium text-muted">Remaining</span>
                <span className="font-bold text-ink">{money(source.remaining)}</span>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  )
}

export function SolacePage() {
  const [unlocked, setUnlocked] = useState(false)
  const { nodes } = useStacks()
  const requiresPasswordUnlock = nodes.find(node => node.key === 'solace')?.requires_reauthentication ?? true
  const [tab, setTab] = useUrlTab<Tab>('overview', TAB_KEYS)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [bills, setBills] = useState<SolaceBill[]>([])
  const [paydays, setPaydays] = useState<SolacePayday[]>([])
  const [purchases, setPurchases] = useState<SolacePurchase[]>([])
  const [buckets, setBuckets] = useState<SolaceBucket[]>([])
  const [subscriptions, setSubscriptions] = useState<SolaceSubscription[]>([])
  const [checklist, setChecklist] = useState<SolaceChecklistItem[]>([])
  const [checklistPreferences, setChecklistPreferences] = useState<SolaceChecklistPreference[]>([])
  const [plan, setPlan] = useState<SolacePayCyclePlan | null>(null)
  const [settings, setSettings] = useState<SolaceSettings | null>(null)
  const [categories, setCategories] = useState<SolaceCategory[]>([])
  const [balances, setBalances] = useState<SolaceBalanceSnapshot[]>([])
  const [health, setHealth] = useState<SolaceHealth | null>(null)
  const [categoryReport, setCategoryReport] = useState<SolaceCategoryReport | null>(null)
  const [closeout, setCloseout] = useState<SolaceCloseoutResponse | null>(null)
  const [forecast, setForecast] = useState<SolaceBalanceForecast | null>(null)
  const [generatingChecklist, setGeneratingChecklist] = useState(false)
  const [schedule, setSchedule] = useState<SolaceSchedule | null>(null)
  const [scheduleMonth, setScheduleMonth] = useState(currentMonthKey)
  const [scheduleLoading, setScheduleLoading] = useState(false)
  const [q, setQ] = useUrlQueryState()

  useEffect(() => {
    if (!requiresPasswordUnlock) setUnlocked(true)
  }, [requiresPasswordUnlock])

  const loadSchedule = async (month = scheduleMonth) => {
    const { start, end } = monthBounds(month)
    setScheduleLoading(true)
    try {
      setSchedule(await api.getSolaceSchedule(start, end))
    } catch (e) {
      setError(errMsg(e))
    } finally {
      setScheduleLoading(false)
    }
  }

  const load = async () => {
    setLoading(true); setError('')
    try {
      const data = await api.getSolaceBootstrap()
      setSolaceCurrencySymbol(data.settings.currency_symbol)
      setBills(data.bills); setPaydays(data.paydays); setPurchases(data.purchases)
      setBuckets(data.buckets); setSubscriptions(data.subscriptions); setChecklist(data.checklist)
      setPlan(data.plan); setSettings(data.settings); setCategories(data.categories)
      setBalances(data.balances); setHealth(data.health); setCategoryReport(data.category_report)
      setCloseout(data.closeout); setForecast(data.forecast)
      setChecklistPreferences(data.checklist_preferences)
      setUnlocked(true)
      void loadSchedule()
    } catch (e) {
      setError(errMsg(e))
      if (String(errMsg(e)).includes('re-authentication')) setUnlocked(false)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!unlocked) return
    if (q.trim()) search()
    else load()
    // Unlock is the transition that triggers the initial protected load/search.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [unlocked])

  useEffect(() => {
    if (unlocked) void loadSchedule(scheduleMonth)
    // scheduleMonth is the explicit navigation state for this request.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scheduleMonth])

  const search = async () => {
    if (!q.trim()) return load()
    try {
      const r = await api.searchSolace(q.trim())
      setBills(r.bills); setPaydays(r.paydays); setPurchases(r.purchases); setBuckets(r.buckets); setSubscriptions(r.subscriptions); setChecklist(r.checklist)
    } catch (e) { setError(errMsg(e)) }
  }

  const generateChecklist = async (date?: string) => {
    setGeneratingChecklist(true); setError('')
    try {
      const [items, selectedPlan] = await Promise.all([
        api.generateSolacePlanChecklist(date),
        api.getSolacePlan(date),
      ])
      setChecklist(items)
      setPlan(selectedPlan)
      setTab('checklist')
    } catch (e) {
      setError(errMsg(e))
    } finally {
      setGeneratingChecklist(false)
    }
  }

  const updateOccurrence = async (id: number, action: 'paid' | 'unpaid' | 'skip') => {
    setError('')
    try {
      const updated = await api.updateSolaceOccurrence(id, action)
      setSchedule(previous => previous ? {
        ...previous,
        occurrences: previous.occurrences.map(row => row.id === updated.id ? updated : row),
      } : previous)
      setBills(await api.getSolaceBills())
      setForecast(await api.getSolaceForecast())
      void loadSchedule()
      return updated
    } catch (e) {
      setError(errMsg(e))
      throw e
    }
  }

  if (requiresPasswordUnlock && !unlocked) return <ReauthGate onUnlock={() => setUnlocked(true)} />

  return (
    <div className="mx-auto max-w-7xl space-y-5">
      <PageHeader title="Solace" subtitle="Bills, set-asides and planned purchases" icon="💸" />
      {error && <div className="rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-danger">{error}</div>}
      <div className="flex flex-col gap-2 sm:flex-row">
        <SearchField
          value={q}
          onChange={e => setQ(e.target.value)}
          onClear={() => { setQ(''); void load() }}
          onKeyDown={e => { if (e.key === 'Enter') void search() }}
          placeholder="Search Solace"
        />
        <div className="flex gap-2">
          <Button variant="secondary" onClick={search} className="flex-1 sm:flex-none">Search</Button>
          <Button variant="ghost" onClick={load} loading={loading} className="flex-1 sm:flex-none">Refresh</Button>
        </div>
      </div>
      <Tabs
        tabs={SOLACE_TABS}
        active={tab}
        onChange={setTab}
        mobileSelectLabel="Solace section"
      />
      {tab === 'overview' && <Overview bills={bills} buckets={buckets} subscriptions={subscriptions} purchases={purchases} health={health} closeout={closeout} forecast={forecast} onTab={setTab} />}
      {tab === 'forecast' && <ForecastTab initial={forecast} onManage={() => setTab('manage')} onError={setError} />}
      {tab === 'schedule' && (
        <ScheduleTab
          schedule={schedule}
          month={scheduleMonth}
          loading={scheduleLoading}
          onMonth={setScheduleMonth}
          onAction={updateOccurrence}
        />
      )}
      {tab === 'closeout' && <CloseoutTab closeout={closeout} reload={load} onOccurrence={updateOccurrence} onError={setError} />}
      {tab === 'plan' && <PayPlan plan={plan} generating={generatingChecklist} onGenerate={generateChecklist} onTab={setTab} onError={setError} />}
      {tab === 'bills' && <BillsTab bills={bills} categories={(categories.filter(category => category.is_active && ['bill', 'both'].includes(category.category_type)).map(category => category.name).length ? categories.filter(category => category.is_active && ['bill', 'both'].includes(category.category_type)).map(category => category.name) : BILL_CATS)} reload={load} onOccurrence={updateOccurrence} onError={setError} />}
      {tab === 'buckets' && <BucketsTab buckets={buckets} reload={load} onError={setError} />}
      {tab === 'subscriptions' && <SubscriptionsTab subscriptions={subscriptions} reload={load} onError={setError} />}
      {tab === 'purchases' && <PurchasesTab purchases={purchases} categories={categories.filter(category => category.is_active && ['purchase', 'both'].includes(category.category_type)).map(category => category.name)} reload={load} onError={setError} />}
      {tab === 'paydays' && <PaydaysTab paydays={paydays} reload={load} onError={setError} />}
      {tab === 'checklist' && <ChecklistTab items={checklist} preferences={checklistPreferences} plan={plan} generating={generatingChecklist} reload={load} onGenerate={generateChecklist} onChange={setChecklist} onError={setError} />}
      {tab === 'manage' && (
        <ManagementTab
          settings={settings}
          categories={categories}
          balances={balances}
          report={categoryReport}
          health={health}
          reload={load}
          onError={setError}
        />
      )}
    </div>
  )
}
