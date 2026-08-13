import { useEffect, useMemo, useState, type FormEvent, type ReactNode } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { api } from '../../../api/client'
import type {
  SolaceAnnualSummary, SolaceBalanceForecast, SolaceBalanceSnapshot, SolaceBill,
  SolaceBillOccurrence, SolaceBillTimeline, SolaceBucket, SolaceBucketEntry,
  SolaceBucketPurpose, SolaceCategory, SolaceCategoryReport, SolaceChecklistItem,
  SolaceChecklistPreference, SolaceCloseoutResponse, SolaceCycleHistoryRow, SolaceHealth,
  SolaceNow, SolacePayCyclePlan, SolacePayday, SolacePurchase, SolaceSchedule, SolaceSettings
} from '../../../api/types'
import { Card } from '../../../components/Card'
import { Button } from '../../../components/Button'
import { Field, Input, SearchField, Select, fieldClass } from '../../../components/Field'
import { Modal } from '../../../components/Modal'
import { Tabs } from '../../../components/Tabs'
import { Badge, type BadgeTone } from '../../../components/Badge'
import { PageHeader } from '../../../components/PageHeader'
import { EmptyState } from '../../../components/EmptyState'
import { useUrlQueryState, useUrlTab } from '../../../hooks/useUrlTab'
import { UndoToast } from '../../../components/UndoToast'
import { StatCard } from '../../../components/StatCard'
import { SensitiveGate } from '../../../components/SensitiveGate'
import { CloseoutTab, HealthPanel, ManagementTab } from './SolaceManagement'
import { setSolaceCurrencySymbol, solaceMoney as money } from './solaceFormat'
import { useStacks } from '../../stacks/StacksContext'
import { confirmDialog } from '../../../components/Dialogs'
import { MobileListRow, MobileScreenHeader, MobileSection, MobileSummaryCard } from '../../../components/mobile'

const errMsg = (e: unknown) => (e instanceof Error ? e.message : 'Something went wrong.')
const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1).replace(/_/g, ' ')
const dateOnly = (iso: string | null) => iso ? new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : 'No date'
/** `yyyy-mm-dd` from the date input → ISO at local midnight. */
const fromLocalDateInput = (value: string) => value ? new Date(`${value}T00:00`).toISOString() : null
/** ISO → `yyyy-mm-dd` in local time, for a native date input. */
const toLocalDateInput = (iso: string | null) => {
  if (!iso) return ''
  const value = new Date(iso)
  if (Number.isNaN(value.getTime())) return ''
  const offset = value.getTimezoneOffset() * 60000
  return new Date(value.getTime() - offset).toISOString().slice(0, 10)
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

/**
 * Five destinations, not twelve.
 *
 * Money had a tab each for overview, forecast, schedule, closeout, pay plan, bills, buckets,
 * subscriptions, purchases, paydays, checklist and manage — a row nobody could scan, where the
 * common actions were as buried as the rare ones. They now group by the question being asked:
 * what do I owe now, what goes out, how is pay divided, how are we tracking, and setup.
 */
type Tab = 'now' | 'bills' | 'plan' | 'insights' | 'manage'
type BillsSection = 'bills' | 'schedule'
type PlanSection = 'payplan' | 'buckets' | 'paydays' | 'purchases'
type InsightsSection = 'forecast' | 'closeout' | 'history' | 'annual'

const SOLACE_TABS = [
  { key: 'now' as const, label: 'Now' },
  { key: 'bills' as const, label: 'Bills' },
  { key: 'plan' as const, label: 'Plan' },
  { key: 'insights' as const, label: 'Insights' },
  { key: 'manage' as const, label: 'Manage' },
]
const BILLS_SECTIONS = [
  { key: 'bills' as const, label: 'Bills' },
  { key: 'schedule' as const, label: 'Calendar' },
]
const PLAN_SECTIONS = [
  { key: 'payplan' as const, label: 'Pay plan' },
  { key: 'buckets' as const, label: 'Buckets' },
  { key: 'paydays' as const, label: 'Income' },
  { key: 'purchases' as const, label: 'Purchases' },
]
const INSIGHTS_SECTIONS = [
  { key: 'forecast' as const, label: 'Forecast' },
  { key: 'closeout' as const, label: 'Cycle closeout' },
  { key: 'history' as const, label: 'Cycle history' },
  { key: 'annual' as const, label: 'Year' },
]

/** Links and bookmarks made before the regrouping still land in the right place. */
const LEGACY_TABS: Record<string, [Tab, string | null]> = {
  overview: ['now', null], checklist: ['now', null],
  bills: ['bills', 'bills'], subscriptions: ['bills', 'bills'], schedule: ['bills', 'schedule'],
  plan: ['plan', 'payplan'], buckets: ['plan', 'buckets'], paydays: ['plan', 'paydays'],
  purchases: ['plan', 'purchases'],
  forecast: ['insights', 'forecast'], closeout: ['insights', 'closeout'],
  'cycle-history': ['insights', 'history'], 'annual-summary': ['insights', 'annual'],
  manage: ['manage', null],
}

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

// docs/36 §6.10: "Add Bill, Edit Bill, Add Bucket, Record Income and similar operations should
// use focused sheets or form screens instead of expanding long forms inside the surrounding
// finance page." One shared wrapper (Add bill/bucket/purchase/payday all use this) means fixing
// it once fixes all four, matching Calendar's EventModal reference pattern (Modal size="full").
function CreatePanel({ label, children }: {
  label: string
  children: (close: () => void) => ReactNode
}) {
  const [open, setOpen] = useState(false)
  if (!open) return <Button variant="secondary" onClick={() => setOpen(true)} className="self-start">+ {label}</Button>
  return (
    <Modal title={label} onClose={() => setOpen(false)} size="full">
      {children(() => setOpen(false))}
    </Modal>
  )
}

function BillForm({ categories, initialCategory, categoryLocked = false, nameLabel = 'Bill', submitLabel = 'Add bill', onCreated, onError }: {
  categories: string[]
  initialCategory?: string
  categoryLocked?: boolean
  nameLabel?: string
  submitLabel?: string
  onCreated: () => void
  onError: (message: string) => void
}) {
  const startingCategory = initialCategory || categories[0] || 'other'
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
        due_at: fromLocalDateInput(f.due_at),
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
        <Field label={nameLabel}><Input value={f.name} onChange={e => set('name', e.target.value)} placeholder={nameLabel === 'Subscription' ? 'Streaming service' : 'Electricity'} /></Field>
        <Field label="Provider"><Input value={f.provider} onChange={e => set('provider', e.target.value)} /></Field>
        <Field label="Amount"><Input type="number" step="0.01" value={f.amount} onChange={e => set('amount', e.target.value)} /></Field>
        <Field label="Category"><Select disabled={categoryLocked} value={f.category} onChange={e => setF(prev => ({ ...prev, category: e.target.value, home_destination: homeDestinationForCategory(e.target.value) }))}>{!categories.includes(f.category) && <option value={f.category}>{cap(f.category)}</option>}{categories.map(c => <option key={c} value={c}>{cap(c)}</option>)}</Select></Field>
        <Field label="First due"><input type="date" className={fieldClass} value={f.due_at} onChange={e => set('due_at', e.target.value)} /></Field>
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
        <Button onClick={save} loading={saving} disabled={!f.name.trim()} className="w-full sm:col-span-2 xl:col-span-1 xl:w-auto">{submitLabel}</Button>
      </div>
    </Card>
  )
}

function BillEditor({ bill, categories, reload, onError }: {
  bill: SolaceBill; categories: string[]; reload: () => void; onError: (message: string) => void
}) {
  const [open, setOpen] = useState(false)
  const [f, setF] = useState({
    name: bill.name,
    provider: bill.provider,
    category: bill.category,
    amount: bill.amount,
    due_at: toLocalDateInput(bill.due_at),
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
        due_at: fromLocalDateInput(f.due_at),
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
    if (!(await confirmDialog({ title: `Delete ${bill.name} and its occurrence history?`, confirmLabel: 'Delete' }))) return
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
  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="mt-3 min-h-11 border-t border-line pt-3 text-left text-sm font-medium text-primary hover:underline"
      >
        Edit bill
      </button>
    )
  }

  return (
    <Modal
      title={`Edit ${bill.name}`}
      onClose={() => setOpen(false)}
      size="full"
      footer={
        <>
          <Button size="sm" variant="danger" onClick={remove} disabled={saving}>Delete</Button>
          <Button variant="ghost" size="sm" onClick={() => setOpen(false)}>Cancel</Button>
          <Button size="sm" onClick={save} loading={saving} disabled={!f.name.trim()}>Save</Button>
        </>
      }
    >
      <div className="flex flex-col gap-3">
        <div className="grid gap-3 sm:grid-cols-2">
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
          <input type="date" className={fieldClass} value={f.due_at} onChange={e => set('due_at', e.target.value)} />
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
        <Field label="Amount updates" hint="Schedule changes always rebuild every unpaid date; paid and skipped history is kept.">
          <Select value={f.occurrence_update_scope} onChange={e => set('occurrence_update_scope', e.target.value)}>
            <option value="future_unpaid">Future unpaid amounts only</option>
            <option value="all_unpaid">All unpaid amounts in budget year</option>
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
        <div className="flex flex-wrap gap-4 text-sm text-muted">
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
      </div>
    </Modal>
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

function BillCard({ bill, categories, reload, onError, onPay, paying }: {
  bill: SolaceBill
  categories: string[]
  reload: () => void
  onError: (message: string) => void
  onPay: (bill: SolaceBill) => void
  paying: number | null
}) {
  return (
    <Card contentClassName="p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="font-semibold text-ink truncate">{bill.name}</h3>
          <p className="text-sm text-muted">{bill.provider || cap(bill.category)} · {money(bill.amount)}</p>
          {bill.is_active && bill.include_in_set_aside && (
            <p className="text-xs text-muted">{money(bill.fortnightly_amount)}/fortnight · {money(bill.annual_amount)}/year</p>
          )}
          {bill.source_node === 'homestead' && <div className="mt-1"><Badge tone="success">Shown in Homestead</Badge></div>}
        </div>
        <DueBadge iso={bill.next_due_at || bill.due_at} paid={bill.is_paid && !bill.recurrence_rule} />
      </div>
      {bill.notes && <p className="mt-3 text-sm text-muted">{bill.notes}</p>}
      <div className="mt-3 flex items-center gap-2">
        {bill.recurrence_rule && <Badge tone="neutral">Recurring</Badge>}
        {bill.is_autopay && <Badge tone="success">Autopay</Badge>}
        {!bill.is_active && <Badge tone="neutral">Paused</Badge>}
        {bill.next_occurrence_id && bill.is_active && (
          <Button
            size="sm"
            variant="ghost"
            onClick={() => onPay(bill)}
            loading={paying === bill.next_occurrence_id}
          >
            Mark next paid
          </Button>
        )}
      </div>
      <BillDetails bill={bill} />
      {bill.source_node === 'homestead' && (
        <Link to={homeDestinationPath(bill.source_record_type)} className="mt-3 flex min-h-11 items-center justify-between gap-3 border-t border-line pt-3 text-sm font-semibold text-primary">View home details in Homestead <span aria-hidden>→</span></Link>
      )}
      <BillEditor bill={bill} categories={categories} reload={reload} onError={onError} />
    </Card>
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
      {bills.length === 0 ? <EmptyState icon="💸" title="No bills yet" hint="Add a recurring or one-off bill to start forecasting what the household needs to set aside." /> : (
        visibleBills.length === 0 ? <EmptyState icon="🔎" title="No bills match these filters" hint="Try another category or status." /> : <div className="grid gap-3 lg:grid-cols-2">
          {visibleBills.map(b => (
            <BillCard
              key={b.id} bill={b} categories={categories} reload={reload} onError={onError}
              onPay={pay} paying={paying}
            />
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

function BucketForm({ buckets, onCreated, onError }: {
  buckets: SolaceBucket[]; onCreated: () => void; onError: (message: string) => void
}) {
  // cap_to_remaining defaults off: only one bucket may hold the leftover pay (the service
  // clears the flag on every other bucket), so defaulting every new bucket to true meant the
  // setting silently moved to whichever bucket was saved last.
  const [f, setF] = useState({
    name: '', purpose: 'savings', target_amount: '', current_amount: '',
    allocation_method: 'percentage' as 'percentage' | 'fixed',
    allocation_value: '', rounding_increment: '1.00', cap_to_remaining: false,
  })
  const [saving, setSaving] = useState(false)
  const allocatedPercentage = buckets.reduce(
    (sum, bucket) => sum + (
      bucket.is_active && bucket.allocation_method === 'percentage'
        ? Number(bucket.allocation_value)
        : 0
    ), 0,
  )
  const remainingPercentage = Math.max(0, 100 - allocatedPercentage)
  const leftoverBucket = buckets.find(bucket => bucket.is_active && bucket.cap_to_remaining)
  const exceedsPercentage = f.allocation_method === 'percentage'
    && Number(f.allocation_value || 0) > remainingPercentage
  const set = (k: string, v: string | boolean) => setF(prev => ({ ...prev, [k]: v }))
  const save = async () => {
    setSaving(true)
    try {
      await api.createSolaceBucket({
        ...f,
        purpose: f.purpose as SolaceBucketPurpose,
        target_amount: f.target_amount || '0.00',
        current_amount: f.current_amount || '0.00',
        allocation_value: f.allocation_value || '0.00',
      })
      setF({
        name: '', purpose: 'savings', target_amount: '', current_amount: '',
        allocation_method: 'percentage', allocation_value: '',
        rounding_increment: '1.00', cap_to_remaining: false,
      })
      onCreated()
    } catch (error) {
      onError(errMsg(error))
    } finally { setSaving(false) }
  }
  return (
    <Card contentClassName="p-4">
      <h3 className="mb-1 font-semibold text-ink">New bucket</h3>
      <p className="mb-4 text-sm text-muted">
        A bucket is somewhere a share of each pay goes. Name it, say what it is for, then say how
        it is funded.
      </p>

      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Name"><Input value={f.name} onChange={e => set('name', e.target.value)} placeholder="Emergency fund" /></Field>
        <Field label="What for" hint={BUCKET_PURPOSE_HINT[f.purpose]}>
          <Select value={f.purpose} onChange={e => set('purpose', e.target.value)}>
            {BUCKET_PURPOSES.map(row => <option key={row.value} value={row.value}>{row.label}</option>)}
          </Select>
        </Field>
      </div>

      <h4 className="mb-2 mt-5 text-sm font-semibold text-ink">Funded each pay</h4>
      <div className="grid gap-3 sm:grid-cols-3">
        <Field label="Rule">
          <Select value={f.allocation_method} onChange={e => set('allocation_method', e.target.value)}>
            <option value="percentage">Percentage of pay</option>
            <option value="fixed">Fixed household amount</option>
          </Select>
        </Field>
        <Field label={f.allocation_method === 'percentage' ? 'Percent of each pay' : 'Amount per cycle'}>
          <Input
            type="number" min="0"
            max={f.allocation_method === 'percentage' ? remainingPercentage : undefined}
            step="0.01" value={f.allocation_value}
            onChange={e => set('allocation_value', e.target.value)}
          />
        </Field>
        <Field label="Round to">
          <Select value={f.rounding_increment} onChange={e => set('rounding_increment', e.target.value)}>
            {['0.01', '1.00', '5.00', '10.00'].map(v => <option key={v} value={v}>{money(v)}</option>)}
          </Select>
        </Field>
      </div>
      <label className="mt-2 flex items-start gap-2 text-sm text-muted">
        <input
          type="checkbox" className="mt-1" checked={f.cap_to_remaining}
          onChange={e => set('cap_to_remaining', e.target.checked)}
        />
        <span>
          Give this bucket whatever is left over
          <span className="block text-xs text-muted">
            Only one bucket can hold the leftover pay. Ticking this moves it here from
            {leftoverBucket ? ` ${leftoverBucket.name}` : ' wherever it is now'}.
          </span>
        </span>
      </label>

      <h4 className="mb-2 mt-5 text-sm font-semibold text-ink">Goal <span className="font-normal text-muted">(optional)</span></h4>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Target amount"><Input type="number" min="0" step="0.01" value={f.target_amount} onChange={e => set('target_amount', e.target.value)} placeholder="0.00" /></Field>
        <Field label="Already in it"><Input type="number" min="0" step="0.01" value={f.current_amount} onChange={e => set('current_amount', e.target.value)} placeholder="0.00" /></Field>
      </div>

      <div className="mt-4">
        <Button onClick={save} loading={saving} disabled={!f.name.trim() || exceedsPercentage}>Add bucket</Button>
      </div>
      {f.allocation_method === 'percentage' && (
        <p className={`mt-2 text-xs ${exceedsPercentage ? 'text-danger' : 'text-muted'}`}>
          {remainingPercentage.toFixed(2)}% remains available across active buckets.
        </p>
      )}
      <label className="mt-3 flex items-center gap-2 text-sm text-muted">
        <input type="checkbox" checked={f.cap_to_remaining} onChange={e => set('cap_to_remaining', e.target.checked)} />
        Never allocate more than the remaining pay
      </label>
    </Card>
  )
}

const BUCKET_PURPOSES: { value: SolaceBucketPurpose; label: string }[] = [
  { value: 'bills', label: 'Bills' },
  { value: 'savings', label: 'Savings' },
  { value: 'spending', label: 'Spending' },
  { value: 'purchases', label: 'Planned purchases' },
  { value: 'other', label: 'Other' },
]

/** A bucket only has a goal worth showing a progress bar for if it has a target above zero. */
const hasGoal = (bucket: SolaceBucket) => Number(bucket.target_amount) > 0

const BUCKET_PURPOSE_LABEL: Record<string, string> = Object.fromEntries(
  BUCKET_PURPOSES.map(row => [row.value, row.label]),
)

/** What each purpose actually changes, so "What for" does not read as decoration.
 *
 * It is not: bills and planned purchases are the two the pay planner counts towards what the
 * household must set aside, and bills is what the bills-account forecast projects income into. */
const BUCKET_PURPOSE_HINT: Record<string, string> = {
  bills: 'Counted as money set aside for bills, and projected into the bills forecast.',
  purchases: 'Counted as money set aside for planned purchases.',
  savings: 'Tracked towards its goal; not counted as set aside for bills.',
  spending: 'Tracked towards its goal; not counted as set aside for bills.',
  other: 'Tracked towards its goal; not counted as set aside for bills.',
}

/**
 * Money in and out of one bucket.
 *
 * The balance used to be a number you overwrote in an edit form, so "what is in the car fund"
 * had no history and no explanation. Adding and spending are now the bucket's primary actions
 * and each one is recorded.
 */
function BucketMoney({ bucket, reload, onError }: {
  bucket: SolaceBucket; reload: () => void; onError: (message: string) => void
}) {
  const [open, setOpen] = useState(false)
  const [entries, setEntries] = useState<SolaceBucketEntry[]>([])
  const [kind, setKind] = useState<'deposit' | 'withdrawal'>('deposit')
  const [amount, setAmount] = useState('')
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)

  const loadEntries = async () => {
    try { setEntries(await api.getSolaceBucketEntries(bucket.id)) } catch (e) { onError(errMsg(e)) }
  }
  useEffect(() => { if (open) void loadEntries() }, [open, bucket.id])

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (!amount) return
    setBusy(true)
    try {
      await api.addSolaceBucketEntry(bucket.id, { kind, amount, note })
      setAmount(''); setNote('')
      await loadEntries()
      reload()
    } catch (e) { onError(errMsg(e)) } finally { setBusy(false) }
  }

  return (
    <div className="mt-3 border-t border-line pt-3">
      <form onSubmit={submit} className="flex flex-col gap-2 sm:flex-row sm:items-end">
        <Field label="Amount" className="sm:w-32">
          <Input
            type="number" min="0" step="0.01" inputMode="decimal" value={amount}
            onChange={e => setAmount(e.target.value)} placeholder="0.00"
          />
        </Field>
        <Field label="What for" className="flex-1">
          <Input value={note} onChange={e => setNote(e.target.value)} placeholder="Optional note" />
        </Field>
        <div className="flex gap-2">
          <Button
            type="submit" size="sm" className="flex-1 sm:flex-none" loading={busy && kind === 'deposit'}
            disabled={!amount || busy} onClick={() => setKind('deposit')}
          >Add</Button>
          <Button
            type="submit" size="sm" variant="secondary" className="flex-1 sm:flex-none"
            loading={busy && kind === 'withdrawal'} disabled={!amount || busy}
            onClick={() => setKind('withdrawal')}
          >Spend</Button>
        </div>
      </form>
      <button
        type="button" onClick={() => setOpen(value => !value)}
        className="mt-2 min-h-10 text-xs font-semibold text-primary"
        aria-expanded={open}
      >
        {open ? 'Hide history' : 'History'}
      </button>
      {open && (
        entries.length === 0 ? (
          <p className="text-xs text-muted">Nothing recorded yet.</p>
        ) : (
          <ul className="divide-y divide-line/70">
            {entries.map(entry => (
              <li key={entry.id} className="flex items-center justify-between gap-2 py-2">
                <div className="min-w-0">
                  <p className="text-sm text-ink">
                    {entry.kind === 'withdrawal' ? '−' : '+'}{money(entry.amount)}
                    {entry.note ? <span className="text-muted"> · {entry.note}</span> : ''}
                  </p>
                  <p className="text-[11px] text-muted">
                    {new Date(entry.occurred_at).toLocaleDateString()} · balance {money(entry.balance_after)}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={async () => {
                    if (!(await confirmDialog({
                      title: 'Remove this entry?',
                      message: 'The bucket balance goes back to what it was before it.',
                      confirmLabel: 'Remove',
                    }))) return
                    try {
                      await api.deleteSolaceBucketEntry(bucket.id, entry.id)
                      await loadEntries()
                      reload()
                    } catch (e) { onError(errMsg(e)) }
                  }}
                  className="grid min-h-10 min-w-10 place-items-center rounded-lg text-muted hover:text-danger"
                  aria-label="Remove entry"
                >×</button>
              </li>
            ))}
          </ul>
        )
      )}
    </div>
  )
}

function BucketRuleEditor({ bucket, buckets, reload, onError }: {
  bucket: SolaceBucket; buckets: SolaceBucket[]; reload: () => void; onError: (message: string) => void
}) {
  const [method, setMethod] = useState(bucket.allocation_method)
  const [name, setName] = useState(bucket.name)
  const [purpose, setPurpose] = useState(bucket.purpose)
  const [target, setTarget] = useState(bucket.target_amount)
  const [current, setCurrent] = useState(bucket.current_amount)
  const [notes, setNotes] = useState(bucket.notes)
  const [value, setValue] = useState(bucket.allocation_value)
  const [rounding, setRounding] = useState(bucket.rounding_increment)
  const [capRemaining, setCapRemaining] = useState(bucket.cap_to_remaining)
  const [active, setActive] = useState(bucket.is_active)
  const [saving, setSaving] = useState(false)
  const allocatedElsewhere = buckets.reduce(
    (sum, row) => sum + (
      row.id !== bucket.id && row.is_active && row.allocation_method === 'percentage'
        ? Number(row.allocation_value)
        : 0
    ), 0,
  )
  const availablePercentage = Math.max(0, 100 - allocatedElsewhere)
  const exceedsPercentage = active && method === 'percentage'
    && Number(value || 0) > availablePercentage
  const save = async () => {
    setSaving(true)
    try {
      await api.updateSolaceBucket(bucket.id, {
        name,
        purpose,
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
    if (!(await confirmDialog({ title: `Delete the ${bucket.name} bucket?`, confirmLabel: 'Delete' }))) return
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
        <Field label="What for" hint={BUCKET_PURPOSE_HINT[purpose]}>
          <Select value={purpose} onChange={e => setPurpose(e.target.value as SolaceBucketPurpose)}>
            {BUCKET_PURPOSES.map(row => <option key={row.value} value={row.value}>{row.label}</option>)}
          </Select>
        </Field>
        <Field label="Goal"><Input type="number" min="0" step="0.01" value={target} onChange={e => setTarget(e.target.value)} /></Field>
        <Field label="Already in it"><Input type="number" min="0" step="0.01" value={current} onChange={e => setCurrent(e.target.value)} /></Field>
        <Field label="Rule">
          <Select value={method} onChange={e => setMethod(e.target.value as 'percentage' | 'fixed')}>
            <option value="percentage">Percentage of pay</option>
            <option value="fixed">Fixed household amount</option>
          </Select>
        </Field>
        <Field label={method === 'percentage' ? 'Percent' : 'Amount'}>
          <Input
            type="number" min="0" max={method === 'percentage' ? availablePercentage : undefined}
            step="0.01" value={value} onChange={e => setValue(e.target.value)}
          />
        </Field>
        <Field label="Round to">
          <Select value={rounding} onChange={e => setRounding(e.target.value)}>
            {['0.01', '1.00', '5.00', '10.00'].map(v => <option key={v} value={v}>{money(v)}</option>)}
          </Select>
        </Field>
        <div className="flex flex-col justify-end gap-2 pb-1 text-sm text-muted">
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={capRemaining} onChange={e => setCapRemaining(e.target.checked)} />
            Give this bucket whatever is left over
          </label>
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={active} onChange={e => setActive(e.target.checked)} />
            Include in pay plan
          </label>
        </div>
        <Field label="Notes"><Input value={notes} onChange={e => setNotes(e.target.value)} /></Field>
      </div>
      {active && method === 'percentage' && (
        <p className={`mt-2 text-xs ${exceedsPercentage ? 'text-danger' : 'text-muted'}`}>
          Up to {availablePercentage.toFixed(2)}% is available for this bucket.
        </p>
      )}
      <div className="mt-3 flex gap-2">
        <Button size="sm" onClick={save} loading={saving} disabled={!name.trim() || exceedsPercentage}>Save bucket</Button>
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
        {close => <BucketForm buckets={buckets} onCreated={() => { reload(); close() }} onError={onError} />}
      </CreatePanel>
      {buckets.length === 0 ? <EmptyState icon="🪣" title="No buckets yet" hint="Create buckets for the purposes you regularly divide household income between." /> : (
        <div className="grid gap-3 lg:grid-cols-3">
          {buckets.map(b => (
            <Card key={b.id} contentClassName="p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <h3 className="font-semibold text-ink">{b.name}</h3>
                  {/* Was `b.category || 'Set-aside'` — category was free text the form never
                      filled in, so every bucket read "Set-aside" regardless of what it was for. */}
                  <p className="text-sm text-muted">{BUCKET_PURPOSE_LABEL[b.purpose] ?? 'Other'}</p>
                </div>
                {hasGoal(b) && (
                  <Badge tone={b.progress_percent >= 100 ? 'success' : 'primary'}>{b.progress_percent}%</Badge>
                )}
              </div>

              {/* A bills bucket normally has no target, and a 0% bar reading "$0.00 of $0.00"
                  said nothing. Show the balance instead, and the bar only when there is a goal. */}
              {hasGoal(b) ? (
                <>
                  <div className="mt-4 h-2 rounded-full bg-sunken overflow-hidden">
                    <div className="h-full bg-primary" style={{ width: `${b.progress_percent}%` }} />
                  </div>
                  <p className="mt-2 text-sm text-muted">{money(b.current_amount)} of {money(b.target_amount)}</p>
                </>
              ) : (
                <p className="mt-4 text-2xl font-semibold text-ink">{money(b.current_amount)}</p>
              )}

              <p className="mt-2 text-sm font-medium text-ink">
                {b.is_active
                  ? b.allocation_method === 'fixed'
                    ? `${money(b.allocation_value)} per household pay cycle`
                    : `${Number(b.allocation_value)}% of each pay`
                  : 'Excluded from pay plan'}
              </p>
              {b.is_active && b.cap_to_remaining && (
                <p className="mt-1 text-xs text-muted">Also takes whatever is left over each pay.</p>
              )}
              <BucketMoney bucket={b} reload={reload} onError={onError} />
              <BucketRuleEditor bucket={b} buckets={buckets} reload={reload} onError={onError} />
            </Card>
          ))}
        </div>
      )}
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
      await api.createSolacePurchase({ ...f, target_amount: f.target_amount || '0.00', saved_amount: f.saved_amount || '0.00', target_date: fromLocalDateInput(f.target_date), status: 'saving', is_all_day: true })
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
        <Field label="Target date"><input type="date" className={fieldClass} value={f.target_date} onChange={e => set('target_date', e.target.value)} /></Field>
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
    target_date: toLocalDateInput(purchase.target_date),
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
        target_date: fromLocalDateInput(values.target_date),
      })
      reload()
    } catch (error) {
      onError(errMsg(error))
    } finally {
      setSaving(false)
    }
  }
  const remove = async () => {
    if (!(await confirmDialog({ title: `Delete ${purchase.name}?`, confirmLabel: 'Delete' }))) return
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
        <Field label="Target date"><input type="date" className={fieldClass} value={f.target_date} onChange={event => set('target_date', event.target.value)} /></Field>
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
  const [f, setF] = useState({
    title: 'Payday', owner_name: 'Household', income_scope: 'individual',
    expected_amount: '', pay_at: '', recurrence_rule: 'FREQ=WEEKLY;INTERVAL=2',
  })
  const [saving, setSaving] = useState(false)
  const set = (k: string, v: string) => setF(prev => ({ ...prev, [k]: v }))
  const save = async () => {
    setSaving(true)
    try {
      await api.createSolacePayday({
        ...f,
        income_scope: f.income_scope as SolacePayday['income_scope'],
        expected_amount: f.expected_amount || '0.00',
        pay_at: fromLocalDateInput(f.pay_at),
        is_all_day: true,
        is_active: true,
      })
      setF({
        title: 'Payday', owner_name: 'Household', income_scope: 'individual',
        expected_amount: '', pay_at: '', recurrence_rule: 'FREQ=WEEKLY;INTERVAL=2',
      })
      onCreated()
    } catch (error) {
      onError(errMsg(error))
    } finally { setSaving(false) }
  }
  return (
    <Card contentClassName="p-4">
      <div className="grid gap-3 lg:grid-cols-[1.4fr_1fr_1fr_0.8fr_1fr_1fr_auto]">
        <Field label="Title"><Input value={f.title} onChange={e => set('title', e.target.value)} /></Field>
        <Field label="Whose income"><Input value={f.owner_name} onChange={e => set('owner_name', e.target.value)} placeholder="Household" /></Field>
        <Field label="Counts as" hint="Shared income is not attributed to a person.">
          <Select value={f.income_scope} onChange={e => set('income_scope', e.target.value)}>
            <option value="individual">One person's</option>
            <option value="shared">Shared</option>
          </Select>
        </Field>
        <Field label="Expected"><Input type="number" step="0.01" value={f.expected_amount} onChange={e => set('expected_amount', e.target.value)} /></Field>
        <Field label="Date"><input type="date" className={fieldClass} value={f.pay_at} onChange={e => set('pay_at', e.target.value)} /></Field>
        <Field label="Repeats"><Select value={f.recurrence_rule} onChange={e => set('recurrence_rule', e.target.value)}>{RECURRENCE.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}</Select></Field>
        <div className="flex items-end"><Button onClick={save} loading={saving} disabled={!f.title.trim()} className="w-full">Add</Button></div>
      </div>
    </Card>
  )
}

/** The lines of a shared income's custom split: a share each, and one line taking the rest. */
function IncomeSplitEditor({ payday, buckets, onError }: {
  payday: SolacePayday; buckets: SolaceBucket[]; onError: (message: string) => void
}) {
  const [lines, setLines] = useState(
    payday.allocations.map(row => ({
      bucket_id: String(row.bucket_id), percentage: row.percentage, is_remainder: row.is_remainder,
    })),
  )
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const update = (index: number, patch: Partial<typeof lines[number]>) =>
    setLines(rows => rows.map((row, i) => (i === index ? { ...row, ...patch } : row)))

  const save = async () => {
    setSaving(true); setSaved(false)
    try {
      await api.setSolaceIncomeAllocations(payday.id, lines
        .filter(row => row.bucket_id)
        .map(row => ({
          bucket_id: Number(row.bucket_id),
          percentage: row.percentage || '0.00',
          is_remainder: row.is_remainder,
        })))
      setSaved(true)
    } catch (e) { onError(errMsg(e)) } finally { setSaving(false) }
  }

  const total = lines.reduce((sum, row) => sum + (row.is_remainder ? 0 : Number(row.percentage || 0)), 0)
  return (
    <div className="mt-3 rounded-xl bg-sunken/60 p-3">
      <p className="text-xs font-extrabold uppercase tracking-[0.14em] text-muted">Custom split</p>
      <div className="mt-2 space-y-2">
        {lines.map((line, index) => (
          <div key={index} className="grid gap-2 sm:grid-cols-[2fr_1fr_auto_auto] sm:items-end">
            <Field label="Bucket">
              <Select value={line.bucket_id} onChange={e => update(index, { bucket_id: e.target.value })}>
                <option value="">Choose…</option>
                {buckets.map(bucket => <option key={bucket.id} value={bucket.id}>{bucket.name}</option>)}
              </Select>
            </Field>
            <Field label="Percent">
              <Input
                type="number" min="0" max="100" step="0.01" disabled={line.is_remainder}
                value={line.is_remainder ? '' : line.percentage}
                onChange={e => update(index, { percentage: e.target.value })}
                placeholder={line.is_remainder ? 'the rest' : ''}
              />
            </Field>
            <label className="flex min-h-11 items-center gap-2 text-xs text-muted-strong">
              <input
                type="checkbox" checked={line.is_remainder}
                onChange={e => setLines(rows => rows.map((row, i) => ({
                  ...row, is_remainder: i === index ? e.target.checked : false,
                })))}
              />
              Takes the rest
            </label>
            <Button type="button" size="sm" variant="ghost" onClick={() => setLines(rows => rows.filter((_, i) => i !== index))}>
              Remove
            </Button>
          </div>
        ))}
      </div>
      <p className={`mt-2 text-xs ${total > 100 ? 'text-danger' : 'text-muted'}`}>
        {total.toFixed(2)}% allocated by percentage
        {total > 100
          ? '; reduce the split to 100% or less before saving.'
          : lines.some(row => row.is_remainder) ? '; one line takes whatever is left.' : '. Anything not allocated stays in the account.'}
      </p>
      <div className="mt-2 flex flex-wrap gap-2">
        <Button type="button" size="sm" variant="secondary" onClick={() => setLines(rows => [...rows, { bucket_id: '', percentage: '', is_remainder: false }])}>
          + Add line
        </Button>
        <Button type="button" size="sm" loading={saving} disabled={total > 100} onClick={save}>Save split</Button>
        {saved && <span className="self-center text-xs font-semibold text-success">Saved</span>}
      </div>
    </div>
  )
}

function PaydaysTab({ paydays, buckets, reload, onError }: {
  paydays: SolacePayday[]; buckets: SolaceBucket[]; reload: () => void; onError: (message: string) => void
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
      owner_name: payday.owner_name,
      income_scope: payday.income_scope,
      allocation_mode: payday.allocation_mode,
      lump_bucket_id: payday.lump_bucket_id ? String(payday.lump_bucket_id) : '',
      expected_amount: payday.expected_amount,
      pay_at: toLocalDateInput(payday.pay_at),
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
          income_scope: f.income_scope as SolacePayday['income_scope'],
          allocation_mode: f.allocation_mode as SolacePayday['allocation_mode'],
          lump_bucket_id: f.lump_bucket_id ? Number(f.lump_bucket_id) : null,
          expected_amount: f.expected_amount || '0.00',
          pay_at: fromLocalDateInput(f.pay_at),
        })
        reload()
      } catch (error) {
        onError(errMsg(error))
      } finally {
        setSaving(false)
      }
    }
    const remove = async () => {
      if (!(await confirmDialog({ title: `Delete ${payday.title}?`, confirmLabel: 'Delete' }))) return
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
          <Field label="Whose income"><Input value={f.owner_name} onChange={event => set('owner_name', event.target.value)} /></Field>
          <Field label="Counts as" hint="Shared income stays out of the personal contribution split.">
            <Select value={f.income_scope} onChange={event => set('income_scope', event.target.value)}>
              <option value="individual">One person's</option>
              <option value="shared">Shared</option>
            </Select>
          </Field>
          {f.income_scope === 'shared' && (
            <Field label="Where it goes">
              <Select value={f.allocation_mode} onChange={event => set('allocation_mode', event.target.value)}>
                <option value="standard">Through the usual bucket rules</option>
                <option value="lump">All of it into one bucket</option>
                <option value="custom">Split across chosen buckets</option>
              </Select>
            </Field>
          )}
          {f.income_scope === 'shared' && f.allocation_mode === 'lump' && (
            <Field label="Bucket">
              <Select value={f.lump_bucket_id} onChange={event => set('lump_bucket_id', event.target.value)}>
                <option value="">Choose…</option>
                {buckets.map(bucket => <option key={bucket.id} value={bucket.id}>{bucket.name}</option>)}
              </Select>
            </Field>
          )}
          <Field label="Expected"><Input type="number" min="0" step="0.01" value={f.expected_amount} onChange={event => set('expected_amount', event.target.value)} /></Field>
          <Field label="Next date"><input type="date" className={fieldClass} value={f.pay_at} onChange={event => set('pay_at', event.target.value)} /></Field>
          <Field label="Repeats"><Select value={f.recurrence_rule} onChange={event => set('recurrence_rule', event.target.value)}>{RECURRENCE.map(rule => <option key={rule.value} value={rule.value}>{rule.label}</option>)}</Select></Field>
          <Field label="Notes"><Input value={f.notes} onChange={event => set('notes', event.target.value)} /></Field>
        </div>
        {f.income_scope === 'shared' && f.allocation_mode === 'custom' && (
          <IncomeSplitEditor payday={payday} buckets={buckets} onError={onError} />
        )}
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
        // The month used to be pinned to 760px, so a phone scrolled a calendar sideways and
        // could never see a week at once. The grid now fits the screen: below sm each day
        // carries coloured dots for what falls on it, and the labelled chips return where
        // there is room for them. The list view below remains the way to read the detail.
        <Card contentClassName="p-2 sm:p-3">
          <div className="grid grid-cols-7 text-center text-[11px] font-semibold uppercase tracking-wide text-muted sm:text-xs">
            {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map(day => (
              <div key={day} className="p-1 sm:p-2"><span className="sm:hidden">{day[0]}</span><span className="hidden sm:inline">{day}</span></div>
            ))}
          </div>
          <div className="grid grid-cols-7">
            {cells.map((day, index) => {
              if (!day) return <div key={`empty-${index}`} className="min-h-14 border border-line/60 bg-sunken/30 sm:min-h-28" />
              const key = `${month}-${String(day).padStart(2, '0')}`
              const dayEvents = eventsByDay.get(key) || []
              const dotClass = (event: typeof dayEvents[number]) =>
                event.kind === 'income' ? 'bg-success'
                  : event.occurrence.status === 'paid' ? 'bg-primary'
                    : event.occurrence.status === 'skipped' ? 'bg-line-strong' : 'bg-warning'
              return (
                <div key={key} className={`min-h-14 border border-line/60 p-1 sm:min-h-28 sm:p-2 ${key === todayKey ? 'bg-primary/5 ring-1 ring-inset ring-primary/40' : 'bg-surface'}`}>
                  <p className="text-[11px] font-semibold text-muted sm:text-xs">{day}</p>
                  <div className="mt-1 flex flex-wrap gap-0.5 sm:hidden" aria-hidden>
                    {dayEvents.slice(0, 4).map(event => (
                      <span key={event.key} className={`h-1.5 w-1.5 rounded-full ${dotClass(event)}`} />
                    ))}
                  </div>
                  {dayEvents.length > 0 && (
                    <span className="sr-only">{dayEvents.length} entries: {dayEvents.map(event => event.title).join(', ')}</span>
                  )}
                  <div className="mt-1 hidden space-y-1 sm:block">
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
          {/* On a phone the dots say when, not what; the month's entries follow in order. */}
          {events.length > 0 && (
            <div className="mt-3 grid gap-2 sm:hidden">{events.map(eventRow)}</div>
          )}
        </Card>
      ) : events.length === 0 ? (
        <EmptyState icon="🗓️" title="Nothing scheduled this month" hint="Recurring bills and active paydays will appear here." />
      ) : (
        <div className="grid gap-2">{events.map(eventRow)}</div>
      )}
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
        <Card contentClassName="p-3"><p className="text-lg font-bold text-ink">−{money(forecast.total_bills)}</p><p className="text-xs text-muted">Included bills due</p></Card>
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
                      <span className="text-muted">{item.kind === 'contribution' ? 'Transfer from' : 'Bill'} · {item.name}</span>
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

function PayPlan({ plan, generating, onGenerate, onSection, onError }: {
  plan: SolacePayCyclePlan | null
  generating: boolean
  onGenerate: (date?: string) => void
  onSection: (tab: Tab, section: string) => void
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
          action={<Button onClick={() => onSection('plan', 'paydays')}>Add payday</Button>}
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

      {/* Who contributed what. Shared income has no owner, so it is reported separately rather
          than inflating anybody's share. */}
      {viewed.people.length > 0 && (
        <Card contentClassName="p-4">
          <h3 className="font-bold text-ink">Individual contributions</h3>
          {Number(viewed.shared_income_total) > 0 && (
            <p className="mt-1 text-sm text-muted">
              Plus {money(viewed.shared_income_total)} shared income, which belongs to the household
              rather than to one person.
            </p>
          )}
          <div className="mt-3 space-y-3">
            {viewed.people.map(person => (
              <div key={person.owner_name} className="rounded-xl bg-sunken/60 p-3">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <p className="font-semibold text-ink">{person.owner_name}</p>
                  <p className="text-lg font-black text-ink">{money(person.income_total)}</p>
                </div>
                <p className="mt-0.5 text-xs text-muted">{person.sources.join(' · ')}</p>
                <ul className="mt-2 space-y-1">
                  {person.allocations.filter(row => Number(row.amount) > 0).map(row => (
                    <li key={row.bucket_id} className="flex justify-between gap-3 text-sm">
                      <span className="text-muted-strong">{row.bucket_name}</span>
                      <span className="font-semibold text-ink">{money(row.amount)}</span>
                    </li>
                  ))}
                </ul>
                <p className="mt-2 border-t border-line pt-2 text-xs text-muted">
                  {money(person.allocated_total)} transferred · {money(person.remaining)} left
                </p>
              </div>
            ))}
          </div>
        </Card>
      )}
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
          action={<Button onClick={() => onSection('plan', 'buckets')}>Configure buckets</Button>}
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

/**
 * The Money landing screen.
 *
 * Money used to open on six stat tiles that only linked elsewhere, so the question the household
 * actually opens it to ask — what do I still owe before the next payday, and can I tick it off —
 * meant guessing which of twelve tabs held the answer. This screen answers it directly and puts
 * Paid and Skip on the row itself.
 */
function CycleStrip({ now }: { now: SolaceNow }) {
  const dateLabel = (iso: string) =>
    new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, { day: 'numeric', month: 'short' })
  const days = now.days_until_cycle_end
  return (
    <Card contentClassName="p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs font-extrabold uppercase tracking-[0.14em] text-muted">This pay cycle</p>
          <p className="mt-0.5 text-lg font-black text-ink">
            {dateLabel(now.cycle_start)} – {dateLabel(now.cycle_end)}
          </p>
        </div>
        <div className="text-right">
          <p className="text-lg font-black text-ink">
            {days <= 0 ? 'Payday' : `${days} ${days === 1 ? 'day' : 'days'}`}
          </p>
          <p className="text-xs text-muted">{days <= 0 ? 'Cycle ends today' : 'until next payday'}</p>
        </div>
      </div>
    </Card>
  )
}

function DueRow({ occurrence, onAction }: {
  occurrence: SolaceBillOccurrence
  onAction: (id: number, action: 'paid' | 'unpaid' | 'skip') => Promise<SolaceBillOccurrence>
}) {
  const [saving, setSaving] = useState<'paid' | 'skip' | null>(null)
  const act = async (action: 'paid' | 'skip') => {
    setSaving(action)
    try { await onAction(occurrence.id, action) } finally { setSaving(null) }
  }
  return (
    <li className={`rounded-xl border p-3 ${occurrence.is_overdue ? 'border-danger/40 bg-danger-soft/40' : 'border-line bg-sunken/50'}`}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="font-semibold text-ink">{occurrence.bill_name}</p>
          <p className="mt-0.5 text-xs text-muted">
            {occurrence.is_overdue ? 'Overdue — ' : ''}due {new Date(occurrence.due_at).toLocaleDateString()}
            {occurrence.bill_category ? ` · ${occurrence.bill_category}` : ''}
          </p>
        </div>
        <p className="text-lg font-black text-ink">{money(occurrence.amount)}</p>
      </div>
      {/* Full-width on a phone: this is the action the screen exists for. */}
      <div className="mt-3 flex gap-2">
        <Button size="sm" className="flex-1" loading={saving === 'paid'} disabled={saving !== null} onClick={() => act('paid')}>
          Paid
        </Button>
        <Button size="sm" variant="ghost" className="flex-1 sm:flex-none" disabled={saving !== null} onClick={() => act('skip')}>
          Skip
        </Button>
      </div>
    </li>
  )
}

function NowTab({ now, health, checklist, onAction, onTab, onSection }: {
  now: SolaceNow | null
  health: SolaceHealth | null
  checklist: ReactNode
  onAction: (id: number, action: 'paid' | 'unpaid' | 'skip') => Promise<SolaceBillOccurrence>
  onTab: (tab: Tab) => void
  onSection: (tab: Tab, section: string) => void
}) {
  if (!now) return <div className="h-64 animate-pulse rounded-2xl bg-sunken" />

  const setAside = now.set_aside
  return (
    <div className="space-y-4">
      {/* Only while something is still unconfigured — a healthy setup needs no banner. */}
      {health && health.status !== 'healthy' && <HealthPanel health={health} onManage={() => onTab('manage')} />}
      <CycleStrip now={now} />

      <Card contentClassName="p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="font-black text-ink">Due before next payday</h2>
            <p className="mt-0.5 text-xs text-muted">
              {now.due.length === 0
                ? 'Nothing left to pay this cycle'
                : `${now.due.length} ${now.due.length === 1 ? 'bill' : 'bills'} still to pay`}
              {now.overdue_count > 0 ? ` · ${now.overdue_count} overdue` : ''}
            </p>
          </div>
          <p className="text-2xl font-black text-ink">{money(now.due_total)}</p>
        </div>

        {now.due.length === 0 ? (
          <p className="mt-4 rounded-xl bg-success-soft px-3 py-2.5 text-sm text-success">
            All clear. {now.paid_this_cycle_count > 0
              ? `${money(now.paid_this_cycle_total)} paid so far this cycle.`
              : 'Nothing is due before the next payday.'}
          </p>
        ) : (
          <ul className="mt-4 space-y-2">
            {now.due.map(occurrence => (
              <DueRow key={occurrence.id} occurrence={occurrence} onAction={onAction} />
            ))}
          </ul>
        )}

        {now.paid_this_cycle_count > 0 && now.due.length > 0 && (
          <p className="mt-3 text-xs text-muted">
            {money(now.paid_this_cycle_total)} already paid this cycle across{' '}
            {now.paid_this_cycle_count} {now.paid_this_cycle_count === 1 ? 'bill' : 'bills'}.
          </p>
        )}
      </Card>

      {setAside && (
        <Card contentClassName="p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="font-black text-ink">Set aside</h2>
              <p className="mt-0.5 text-xs text-muted">
                {setAside.is_covered
                  ? 'Your bills buckets cover what is coming'
                  : `${money(setAside.shortfall)} short of what upcoming bills need`}
              </p>
            </div>
            <p className="text-xl font-black text-ink">{money(now.bucket_total)}</p>
          </div>
          <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
            {([
              ['Recurring bills', setAside.recurring_bills],
              ['Planned purchases', setAside.planned_purchases],
              ['Buffer', setAside.buffer],
              ['Needed each pay', setAside.required_total],
            ] as const).map(([label, value]) => (
              <div key={label} className="rounded-xl bg-sunken px-3 py-2">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-muted">{label}</p>
                <p className="text-sm font-bold text-ink">{money(value)}</p>
              </div>
            ))}
          </div>
          <div className="mt-3 flex flex-col gap-2 sm:flex-row">
            <Button size="sm" variant="secondary" className="w-full sm:w-auto" onClick={() => onSection('plan', 'buckets')}>
              Open buckets
            </Button>
            <Button size="sm" variant="ghost" className="w-full sm:w-auto" onClick={() => onSection('plan', 'payplan')}>
              Pay plan
            </Button>
          </div>
        </Card>
      )}

      {checklist}

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard label="Income this cycle" value={money(now.income_total)} onClick={() => onSection('plan', 'paydays')} />
        <StatCard label="Set aside" value={money(now.bucket_total)} onClick={() => onSection('plan', 'buckets')} />
        <StatCard label="Paid this cycle" value={money(now.paid_this_cycle_total)} onClick={() => onSection('bills', 'schedule')} />
        <StatCard label="Forecast" value="Open" onClick={() => onTab('insights')} />
      </div>
    </div>
  )
}

function MoneyMobileHome({ now, health, onTab, onSection, onAction }: {
  now: SolaceNow | null
  health: SolaceHealth | null
  onTab: (tab: Tab) => void
  onSection: (tab: Tab, section: string) => void
  onAction: (id: number, action: 'paid' | 'unpaid' | 'skip') => Promise<SolaceBillOccurrence>
}) {
  const [payingId, setPayingId] = useState<number | null>(null)
  if (!now) return <div className="h-64 animate-pulse rounded-2xl bg-sunken" />
  const lines = [
    `${money(now.due_total)} due before next payday`,
    `${money(now.bucket_total)} set aside`,
    `${now.days_until_cycle_end <= 0 ? 'Payday today' : `${now.days_until_cycle_end} days until next pay cycle`}`,
  ]
  const nextDue = now.due.slice(0, 3)
  return (
    <div className="flex flex-col gap-4 sm:hidden">
      {health && health.status !== 'healthy' && <HealthPanel health={health} onManage={() => onTab('manage')} />}
      <MobileSummaryCard title="Current position" lines={lines} tone={now.overdue_count > 0 ? 'attention' : 'neutral'} />
      <MobileSection title="Coming up">
        {nextDue.length === 0 ? (
          <p className="rounded-2xl border border-line bg-surface px-4 py-3 text-sm text-muted shadow-soft">Nothing left to pay this cycle.</p>
        ) : nextDue.map(occurrence => (
          <MobileListRow
            key={occurrence.id}
            icon="💸"
            title={occurrence.bill_name}
            subtitle={dateOnly(occurrence.due_at)}
            chevron={false}
            trailing={(
              <div className="flex flex-col items-end gap-1">
                <span className="font-semibold text-ink">{money(occurrence.amount)}</span>
                <Button
                  size="sm"
                  loading={payingId === occurrence.id}
                  onClick={async () => {
                    setPayingId(occurrence.id)
                    try { await onAction(occurrence.id, 'paid') }
                    finally { setPayingId(null) }
                  }}
                >Mark paid</Button>
              </div>
            )}
          />
        ))}
        {nextDue.length > 0 && (
          <Button variant="ghost" className="w-full" onClick={() => onSection('bills', 'schedule')}>Open payment schedule</Button>
        )}
      </MobileSection>
      <MobileSection title="Money">
        <MobileListRow icon="🧾" title="Bills" subtitle="Bills and payment schedule" onClick={() => onSection('bills', 'bills')} />
        <MobileListRow icon="✅" title="Pay plan" subtitle="This cycle's checklist and allocations" onClick={() => onSection('plan', 'payplan')} />
        <MobileListRow icon="🪣" title="Buckets" subtitle="Set-asides and rules" onClick={() => onSection('plan', 'buckets')} />
        <MobileListRow icon="🛒" title="Purchases" subtitle="Planned spending goals" onClick={() => onSection('plan', 'purchases')} />
        <MobileListRow icon="📈" title="Insights" subtitle="Forecasts and history" onClick={() => onTab('insights')} />
        <MobileListRow icon="⚙️" title="Manage" subtitle="Settings and balances" onClick={() => onTab('manage')} />
      </MobileSection>
    </div>
  )
}

/** Past pay cycles. These were being recorded at closeout and then never shown again. */
function CycleHistoryTab({ onError }: { onError: (message: string) => void }) {
  const [rows, setRows] = useState<SolaceCycleHistoryRow[] | null>(null)
  useEffect(() => {
    api.getSolaceCycleHistory().then(setRows).catch(e => { onError(errMsg(e)); setRows([]) })
  }, [])

  if (!rows) return <div className="h-40 animate-pulse rounded-2xl bg-sunken" />
  if (rows.length === 0) {
    return (
      <EmptyState
        icon="🗂"
        title="No closed cycles yet"
        hint="Closing a pay cycle records what was paid, skipped and left outstanding. They collect here."
      />
    )
  }
  return (
    <div className="space-y-2">
      {rows.map(row => (
        <Card key={row.id} contentClassName="p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <p className="font-bold text-ink">{dateOnly(row.cycle_start)} – {dateOnly(row.cycle_end)}</p>
                <Badge tone={row.status === 'closed' ? 'success' : 'warning'}>
                  {row.status === 'closed' ? 'Closed' : 'Still open'}
                </Badge>
              </div>
              {row.notes && <p className="mt-1 text-sm text-muted">{row.notes}</p>}
            </div>
            <p className="text-xl font-black text-ink">{money(row.paid_total)}<span className="ml-1 text-xs font-medium text-muted">paid</span></p>
          </div>
          <div className="mt-3 grid grid-cols-3 gap-2 border-t border-line pt-3 text-center">
            {([
              ['Paid', row.paid_count, row.paid_total],
              ['Outstanding', row.unpaid_count, row.unpaid_total],
              ['Skipped', row.skipped_count, row.skipped_total],
            ] as const).map(([label, count, total]) => (
              <div key={label}>
                <p className="text-[11px] font-semibold uppercase tracking-wide text-muted">{label}</p>
                <p className="text-sm font-bold text-ink">{money(total)}</p>
                <p className="text-[11px] text-muted">{count} {count === 1 ? 'bill' : 'bills'}</p>
              </div>
            ))}
          </div>
        </Card>
      ))}
    </div>
  )
}

/** A year of bills, grouped by category and then by the bills inside it. */
function AnnualSummaryTab({ onError }: { onError: (message: string) => void }) {
  const [yearType, setYearType] = useState<'calendar' | 'financial'>('calendar')
  const [summary, setSummary] = useState<SolaceAnnualSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    api.getSolaceAnnualSummary(yearType)
      .then(setSummary)
      .catch(e => onError(errMsg(e)))
      .finally(() => setLoading(false))
  }, [yearType])

  return (
    <div className="space-y-4">
      <Card contentClassName="p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-xs font-extrabold uppercase tracking-[0.14em] text-muted">Year</p>
            <p className="mt-0.5 text-lg font-black text-ink">{summary?.period_label || '—'}</p>
            {summary && (
              <p className="text-xs text-muted">{dateOnly(summary.period_start)} – {dateOnly(summary.period_end)}</p>
            )}
          </div>
          <Field label="Counting">
            <Select value={yearType} onChange={event => setYearType(event.target.value as 'calendar' | 'financial')}>
              <option value="calendar">Calendar year</option>
              <option value="financial">Financial year (Jul–Jun)</option>
            </Select>
          </Field>
        </div>
        {summary && (
          <div className="mt-4 grid grid-cols-3 gap-2 border-t border-line pt-3 text-center">
            {([
              ['Total', summary.grand_total],
              ['Paid', summary.grand_paid],
              ['Outstanding', summary.grand_outstanding],
            ] as const).map(([label, value]) => (
              <div key={label}>
                <p className="text-[11px] font-semibold uppercase tracking-wide text-muted">{label}</p>
                <p className="text-base font-black text-ink">{money(value)}</p>
              </div>
            ))}
          </div>
        )}
      </Card>

      {loading ? (
        <div className="h-40 animate-pulse rounded-2xl bg-sunken" />
      ) : !summary || summary.categories.length === 0 ? (
        <EmptyState
          icon="📅"
          title="Nothing billed in this year"
          hint="Add recurring bills and their occurrences will total up here."
        />
      ) : (
        <div className="space-y-2">
          {summary.categories.map(category => {
            const open = expanded === category.name
            return (
              <Card key={category.name} contentClassName="p-0">
                {/* Tapping a category shows the bills inside it, which is the question that
                    follows "why is this category so big". */}
                <button
                  type="button"
                  onClick={() => setExpanded(open ? null : category.name)}
                  className="flex w-full items-center justify-between gap-3 p-4 text-left"
                  aria-expanded={open}
                >
                  <div className="min-w-0">
                    <p className="font-semibold text-ink">{cap(category.name)}</p>
                    <p className="mt-0.5 text-xs text-muted">
                      {money(category.paid)} paid · {money(category.unpaid)} outstanding
                      {Number(category.skipped) > 0 ? ` · ${money(category.skipped)} skipped` : ''}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-lg font-black text-ink">{money(category.total)}</span>
                    <span className="text-muted" aria-hidden>{open ? '▾' : '▸'}</span>
                  </div>
                </button>
                {open && (
                  <ul className="divide-y divide-line/70 border-t border-line px-4">
                    {category.bills.map(bill => (
                      <li key={bill.name} className="flex justify-between gap-3 py-2.5 text-sm">
                        <span className="text-muted-strong">{bill.name}</span>
                        <span className="font-semibold text-ink">{money(bill.total)}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}

export function SolacePage() {
  const [unlocked, setUnlocked] = useState(false)
  const { nodes } = useStacks()
  const requiresPasswordUnlock = nodes.find(node => node.key === 'solace')?.requires_reauthentication ?? true
  const [tab, setTab] = useUrlTab<Tab>('now', SOLACE_TABS.map(row => row.key))
  const [billsSection, setBillsSection] = useUrlTab<BillsSection>('bills', BILLS_SECTIONS.map(row => row.key), 'section')
  const [planSection, setPlanSection] = useUrlTab<PlanSection>('payplan', PLAN_SECTIONS.map(row => row.key), 'section')
  const [insightsSection, setInsightsSection] = useUrlTab<InsightsSection>('forecast', INSIGHTS_SECTIONS.map(row => row.key), 'section')
  const [now, setNow] = useState<SolaceNow | null>(null)
  const navigate = useNavigate()
  const location = useLocation()

  // A link written before the regrouping still knows where it meant to go.
  useEffect(() => {
    const params = new URLSearchParams(location.search)
    const requested = params.get('tab')
    const mapped = requested ? LEGACY_TABS[requested] : undefined
    if (!mapped || SOLACE_TABS.some(row => row.key === requested)) return
    const [nextTab, section] = mapped
    if (nextTab === 'now') params.delete('tab')
    else params.set('tab', nextTab)
    if (section) params.set('section', section)
    const search = params.toString()
    navigate({ pathname: location.pathname, search: search ? `?${search}` : '' }, { replace: true })
  }, [location.search, location.pathname, navigate])

  const goSection = (nextTab: Tab, section: string) => {
    const params = new URLSearchParams(location.search)
    if (nextTab === 'now') params.delete('tab')
    else params.set('tab', nextTab)
    params.set('section', section)
    const search = params.toString()
    navigate({ pathname: location.pathname, search: search ? `?${search}` : '' })
  }
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [bills, setBills] = useState<SolaceBill[]>([])
  const [paydays, setPaydays] = useState<SolacePayday[]>([])
  const [purchases, setPurchases] = useState<SolacePurchase[]>([])
  const [buckets, setBuckets] = useState<SolaceBucket[]>([])
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

  const billCategoryNames = useMemo(() => {
    const names = categories
      .filter(category => category.is_active && ['bill', 'both'].includes(category.category_type))
      .map(category => category.name)
    return names.length ? names : BILL_CATS
  }, [categories])
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
      setBuckets(data.buckets); setChecklist(data.checklist)
      setPlan(data.plan); setSettings(data.settings); setCategories(data.categories)
      setBalances(data.balances); setHealth(data.health); setCategoryReport(data.category_report)
      setCloseout(data.closeout); setForecast(data.forecast)
      setChecklistPreferences(data.checklist_preferences)
      setUnlocked(true)
      void loadSchedule()
      void api.getSolaceNow().then(setNow).catch(() => {})
    } catch (e) {
      setError(errMsg(e))
      if (String(errMsg(e)).includes('re-authentication')) setUnlocked(false)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (unlocked) void loadSchedule(scheduleMonth)
    // scheduleMonth is the explicit navigation state for this request.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scheduleMonth])

  // Every other node searches as you type; Money asking for a button press was the odd one.
  useEffect(() => {
    if (!unlocked) return
    const term = q.trim()
    const id = setTimeout(() => {
      if (!term) { void load(); return }
      api.searchSolace(term)
        .then(r => {
          setBills(r.bills); setPaydays(r.paydays); setPurchases(r.purchases)
          setBuckets(r.buckets); setChecklist(r.checklist)
        })
        .catch(e => setError(errMsg(e)))
    }, 300)
    return () => clearTimeout(id)
  }, [q, unlocked])

  const generateChecklist = async (date?: string) => {
    setGeneratingChecklist(true); setError('')
    try {
      const [items, selectedPlan] = await Promise.all([
        api.generateSolacePlanChecklist(date),
        api.getSolacePlan(date),
      ])
      setChecklist(items)
      setPlan(selectedPlan)
      setTab('now')
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
      setNow(await api.getSolaceNow())
      void loadSchedule()
      return updated
    } catch (e) {
      setError(errMsg(e))
      throw e
    }
  }

  if (requiresPasswordUnlock && !unlocked) return <SensitiveGate nodeName="Money" onUnlock={() => setUnlocked(true)} />

  return (
    <div className="flex flex-col gap-5">
      <PageHeader title="Money" icon="💸" />
      {error && <div className="rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-danger">{error}</div>}
      <div className="flex flex-col gap-2 sm:flex-row">
        <SearchField
          value={q}
          onChange={e => setQ(e.target.value)}
          onClear={() => setQ('')}
          placeholder="Search bills, plans and purchases…"
        />
        <Button variant="ghost" onClick={load} loading={loading} className="sm:flex-none">Refresh</Button>
      </div>
      <div className="hidden sm:block">
        <Tabs
          tabs={SOLACE_TABS}
          active={tab}
          onChange={setTab}
          mobileSelectLabel="Solace section"
        />
      </div>
      {tab === 'now' && (
        <>
          <MoneyMobileHome now={now} health={health} onTab={setTab} onSection={goSection} onAction={updateOccurrence} />
          <div className="hidden sm:block">
            <NowTab
              now={now}
              health={health}
              onAction={updateOccurrence}
              onTab={setTab}
              onSection={goSection}
              checklist={
                <ChecklistTab
                  items={checklist}
                  preferences={checklistPreferences}
                  plan={plan}
                  generating={generatingChecklist}
                  reload={load}
                  onGenerate={generateChecklist}
                  onChange={setChecklist}
                  onError={setError}
                />
              }
            />
          </div>
        </>
      )}

      {tab === 'bills' && (
        <div className="flex flex-col gap-4">
          <MobileScreenHeader className="sm:hidden" title={billsSection === 'schedule' ? 'Payment schedule' : 'Bills'} showBack onBack={() => setTab('now')} />
          <Tabs tabs={BILLS_SECTIONS} active={billsSection} onChange={setBillsSection} variant="secondary" />
          {billsSection === 'bills' && (
            <BillsTab
              bills={bills}
              categories={billCategoryNames}
              reload={load}
              onOccurrence={updateOccurrence}
              onError={setError}
            />
          )}
          {billsSection === 'schedule' && (
            <ScheduleTab
              schedule={schedule}
              month={scheduleMonth}
              loading={scheduleLoading}
              onMonth={setScheduleMonth}
              onAction={updateOccurrence}
            />
          )}
        </div>
      )}

      {tab === 'plan' && (
        <div className="flex flex-col gap-4">
          <MobileScreenHeader className="sm:hidden" title={PLAN_SECTIONS.find(row => row.key === planSection)?.label ?? 'Pay plan'} showBack onBack={() => setTab('now')} />
          <Tabs tabs={PLAN_SECTIONS} active={planSection} onChange={setPlanSection} variant="secondary" />
          {planSection === 'payplan' && <PayPlan plan={plan} generating={generatingChecklist} onGenerate={generateChecklist} onSection={goSection} onError={setError} />}
          {planSection === 'buckets' && <BucketsTab buckets={buckets} reload={load} onError={setError} />}
          {planSection === 'paydays' && <PaydaysTab paydays={paydays} buckets={buckets} reload={load} onError={setError} />}
          {planSection === 'purchases' && (
            <PurchasesTab
              purchases={purchases}
              categories={categories.filter(category => category.is_active && ['purchase', 'both'].includes(category.category_type)).map(category => category.name)}
              reload={load}
              onError={setError}
            />
          )}
        </div>
      )}

      {tab === 'insights' && (
        <div className="flex flex-col gap-4">
          <MobileScreenHeader className="sm:hidden" title="Insights" showBack onBack={() => setTab('now')} />
          <Tabs tabs={INSIGHTS_SECTIONS} active={insightsSection} onChange={setInsightsSection} variant="secondary" />
          {insightsSection === 'forecast' && <ForecastTab initial={forecast} onManage={() => setTab('manage')} onError={setError} />}
          {insightsSection === 'closeout' && <CloseoutTab closeout={closeout} reload={load} onOccurrence={updateOccurrence} onError={setError} />}
          {insightsSection === 'history' && <CycleHistoryTab onError={setError} />}
          {insightsSection === 'annual' && <AnnualSummaryTab onError={setError} />}
        </div>
      )}

      {tab === 'manage' && (
        <div className="flex flex-col gap-4">
          <MobileScreenHeader className="sm:hidden" title="Manage" showBack onBack={() => setTab('now')} />
          <ManagementTab
            settings={settings}
            categories={categories}
            balances={balances}
            report={categoryReport}
            health={health}
            reload={load}
            onError={setError}
          />
        </div>
      )}
    </div>
  )
}
