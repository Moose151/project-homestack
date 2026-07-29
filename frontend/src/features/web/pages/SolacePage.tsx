import { useEffect, useMemo, useState } from 'react'
import { api } from '../../../api/client'
import type {
  SolaceBill, SolaceBillOccurrence, SolaceBucket, SolaceChecklistItem, SolacePayday,
  SolacePayCyclePlan, SolacePurchase, SolaceSchedule, SolaceSubscription,
} from '../../../api/types'
import { Card } from '../../../components/Card'
import { Button } from '../../../components/Button'
import { Field, Input, Select, fieldClass } from '../../../components/Field'
import { Tabs } from '../../../components/Tabs'
import { Badge, type BadgeTone } from '../../../components/Badge'
import { PageHeader } from '../../../components/PageHeader'
import { EmptyState } from '../../../components/EmptyState'
import { useUrlQueryState, useUrlTab } from '../../../hooks/useUrlTab'
import { UndoToast } from '../../../components/UndoToast'

const errMsg = (e: unknown) => (e instanceof Error ? e.message : 'Something went wrong.')
const money = (v: string | number) => Number(v || 0).toLocaleString(undefined, { style: 'currency', currency: 'AUD' })
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

type Tab = 'overview' | 'schedule' | 'plan' | 'bills' | 'buckets' | 'subscriptions' | 'purchases' | 'paydays' | 'checklist'
const TAB_KEYS: Tab[] = ['overview', 'schedule', 'plan', 'bills', 'buckets', 'subscriptions', 'purchases', 'paydays', 'checklist']

const BILL_CATS = ['mortgage', 'utilities', 'insurance', 'council', 'debt', 'subscription', 'childcare', 'other']
const RECURRENCE = [
  { label: 'One-off', value: '' },
  { label: 'Weekly', value: 'FREQ=WEEKLY' },
  { label: 'Fortnightly', value: 'FREQ=WEEKLY;INTERVAL=2' },
  { label: 'Monthly', value: 'FREQ=MONTHLY' },
  { label: 'Quarterly', value: 'FREQ=MONTHLY;INTERVAL=3' },
  { label: 'Yearly', value: 'FREQ=YEARLY' },
]

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
      <Card className="p-5">
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

function BillForm({ onCreated }: { onCreated: () => void }) {
  const [f, setF] = useState({
    name: '', category: 'utilities', provider: '', amount: '', due_at: '',
    recurrence_rule: '', include_in_set_aside: true,
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
        is_all_day: true,
        is_active: true,
      })
      setF({
        name: '', category: 'utilities', provider: '', amount: '', due_at: '',
        recurrence_rule: '', include_in_set_aside: true,
      })
      onCreated()
    } finally { setSaving(false) }
  }
  return (
    <Card className="p-4">
      <div className="grid gap-3 lg:grid-cols-[1.4fr_1fr_0.8fr_1fr_1fr_auto]">
        <Field label="Bill"><Input value={f.name} onChange={e => set('name', e.target.value)} placeholder="Electricity" /></Field>
        <Field label="Provider"><Input value={f.provider} onChange={e => set('provider', e.target.value)} /></Field>
        <Field label="Amount"><Input type="number" step="0.01" value={f.amount} onChange={e => set('amount', e.target.value)} /></Field>
        <Field label="Category"><Select value={f.category} onChange={e => set('category', e.target.value)}>{BILL_CATS.map(c => <option key={c} value={c}>{cap(c)}</option>)}</Select></Field>
        <Field label="First due"><input type="datetime-local" className={fieldClass} value={f.due_at} onChange={e => set('due_at', e.target.value)} /></Field>
        <Field label="Repeats"><Select value={f.recurrence_rule} onChange={e => set('recurrence_rule', e.target.value)}>{RECURRENCE.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}</Select></Field>
        <div className="flex items-end"><Button onClick={save} loading={saving} disabled={!f.name.trim()} className="w-full">Add</Button></div>
      </div>
      <label className="mt-3 flex items-center gap-2 text-sm text-muted">
        <input
          type="checkbox"
          checked={f.include_in_set_aside}
          onChange={e => set('include_in_set_aside', e.target.checked)}
        />
        Include this bill in set-aside planning
      </label>
    </Card>
  )
}

function BillEditor({ bill, reload, onError }: {
  bill: SolaceBill; reload: () => void; onError: (message: string) => void
}) {
  const [f, setF] = useState({
    name: bill.name,
    provider: bill.provider,
    category: bill.category,
    amount: bill.amount,
    due_at: toLocalInput(bill.due_at),
    recurrence_rule: bill.recurrence_rule,
    is_active: bill.is_active,
    include_in_set_aside: bill.include_in_set_aside,
  })
  const [saving, setSaving] = useState(false)
  const set = (key: string, value: string | boolean) => setF(previous => ({ ...previous, [key]: value }))
  const save = async () => {
    setSaving(true)
    try {
      await api.updateSolaceBill(bill.id, {
        ...f,
        due_at: fromLocalInput(f.due_at),
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
            {BILL_CATS.map(category => <option key={category} value={category}>{cap(category)}</option>)}
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
      </div>
      <div className="mt-3 flex flex-wrap gap-4 text-sm text-muted">
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={f.is_active} onChange={e => set('is_active', e.target.checked)} />
          Active
        </label>
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={f.include_in_set_aside} onChange={e => set('include_in_set_aside', e.target.checked)} />
          Include in set-aside
        </label>
      </div>
      <div className="mt-3 flex gap-2">
        <Button size="sm" onClick={save} loading={saving} disabled={!f.name.trim()}>Save</Button>
        <Button size="sm" variant="danger" onClick={remove} disabled={saving}>Delete</Button>
      </div>
    </details>
  )
}

function BillsTab({ bills, reload, onOccurrence, onError }: {
  bills: SolaceBill[]
  reload: () => void
  onOccurrence: (id: number, action: 'paid' | 'unpaid' | 'skip') => Promise<SolaceBillOccurrence>
  onError: (m: string) => void
}) {
  const [undoOccurrence, setUndoOccurrence] = useState<{ id: number; name: string } | null>(null)
  const [paying, setPaying] = useState<number | null>(null)
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
  return (
    <div className="flex flex-col gap-4">
      <BillForm onCreated={reload} />
      {bills.length > 0 && (
        <div className="grid gap-3 sm:grid-cols-3">
          <Card className="p-3"><p className="text-xl font-extrabold text-ink">{money(annualTotal)}</p><p className="text-xs text-muted">Annual recurring cost</p></Card>
          <Card className="p-3"><p className="text-xl font-extrabold text-ink">{money(fortnightlyTotal)}</p><p className="text-xs text-muted">Set aside per fortnight</p></Card>
          <Card className="p-3"><p className="text-xl font-extrabold text-ink">{new Set(activeSetAside.map(bill => bill.category)).size}</p><p className="text-xs text-muted">Active categories</p></Card>
        </div>
      )}
      {bills.length === 0 ? <EmptyState icon="💸" title="No bills yet" hint="" /> : (
        <div className="grid gap-3 lg:grid-cols-2">
          {bills.map(b => (
            <Card key={b.id} className="p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <h3 className="font-semibold text-ink truncate">{b.name}</h3>
                  <p className="text-sm text-muted">{b.provider || cap(b.category)} · {money(b.amount)}</p>
                  {b.is_active && b.include_in_set_aside && (
                    <p className="text-xs text-muted">{money(b.fortnightly_amount)}/fortnight · {money(b.annual_amount)}/year</p>
                  )}
                  {b.source_node === 'homestead' && <div className="mt-1"><Badge tone="success">Synced from Homestead</Badge></div>}
                </div>
                <DueBadge iso={b.next_due_at || b.due_at} paid={b.is_paid && !b.recurrence_rule} />
              </div>
              {b.notes && <p className="mt-3 text-sm text-muted">{b.notes}</p>}
              <div className="mt-3 flex items-center gap-2">
                {b.recurrence_rule && <Badge tone="neutral">Recurring</Badge>}
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
              {b.source_node
                ? <p className="mt-3 border-t border-line pt-3 text-xs text-muted">Edit this linked bill from {cap(b.source_node)}.</p>
                : <BillEditor bill={b} reload={reload} onError={onError} />}
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

function BucketForm({ onCreated }: { onCreated: () => void }) {
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
    } finally { setSaving(false) }
  }
  return (
    <Card className="p-4">
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
  const [value, setValue] = useState(bucket.allocation_value)
  const [rounding, setRounding] = useState(bucket.rounding_increment)
  const [capRemaining, setCapRemaining] = useState(bucket.cap_to_remaining)
  const [active, setActive] = useState(bucket.is_active)
  const [saving, setSaving] = useState(false)
  const save = async () => {
    setSaving(true)
    try {
      await api.updateSolaceBucket(bucket.id, {
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
  return (
    <details className="mt-4 border-t border-line pt-3">
      <summary className="cursor-pointer text-sm font-medium text-primary">Allocation settings</summary>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
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
      </div>
      <Button className="mt-3" size="sm" onClick={save} loading={saving}>Save rule</Button>
    </details>
  )
}

function BucketsTab({ buckets, reload, onError }: {
  buckets: SolaceBucket[]; reload: () => void; onError: (message: string) => void
}) {
  return (
    <div className="flex flex-col gap-4">
      <BucketForm onCreated={reload} />
      {buckets.length === 0 ? <EmptyState icon="🪣" title="No buckets yet" hint="" /> : (
        <div className="grid gap-3 lg:grid-cols-3">
          {buckets.map(b => (
            <Card key={b.id} className="p-4">
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

function SubscriptionForm({ onCreated }: { onCreated: () => void }) {
  const [f, setF] = useState({ name: '', provider: '', amount: '', billing_cycle: 'monthly', next_renewal_at: '' })
  const [saving, setSaving] = useState(false)
  const set = (k: string, v: string) => setF(prev => ({ ...prev, [k]: v }))
  const save = async () => {
    setSaving(true)
    try {
      await api.createSolaceSubscription({ ...f, amount: f.amount || '0.00', next_renewal_at: fromLocalInput(f.next_renewal_at), is_all_day: true, is_active: true })
      setF({ name: '', provider: '', amount: '', billing_cycle: 'monthly', next_renewal_at: '' })
      onCreated()
    } finally { setSaving(false) }
  }
  return (
    <Card className="p-4">
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

function SubscriptionsTab({ subscriptions, reload }: { subscriptions: SolaceSubscription[]; reload: () => void }) {
  return (
    <div className="flex flex-col gap-4">
      <SubscriptionForm onCreated={reload} />
      <div className="grid gap-3 lg:grid-cols-3">
        {subscriptions.map(s => (
          <Card key={s.id} className="p-4">
            <div className="flex items-start justify-between gap-3">
              <div><h3 className="font-semibold text-ink">{s.name}</h3><p className="text-sm text-muted">{s.provider || cap(s.billing_cycle)} · {money(s.amount)}</p></div>
              <DueBadge iso={s.next_renewal_at} />
            </div>
          </Card>
        ))}
      </div>
    </div>
  )
}

function PurchaseForm({ onCreated }: { onCreated: () => void }) {
  const [f, setF] = useState({ name: '', category: '', target_amount: '', saved_amount: '', target_date: '', priority: 'medium' })
  const [saving, setSaving] = useState(false)
  const set = (k: string, v: string) => setF(prev => ({ ...prev, [k]: v }))
  const save = async () => {
    setSaving(true)
    try {
      await api.createSolacePurchase({ ...f, target_amount: f.target_amount || '0.00', saved_amount: f.saved_amount || '0.00', target_date: fromLocalInput(f.target_date), status: 'saving', is_all_day: true })
      setF({ name: '', category: '', target_amount: '', saved_amount: '', target_date: '', priority: 'medium' })
      onCreated()
    } finally { setSaving(false) }
  }
  return (
    <Card className="p-4">
      <div className="grid gap-3 lg:grid-cols-[1.3fr_1fr_0.8fr_0.8fr_1fr_auto]">
        <Field label="Purchase"><Input value={f.name} onChange={e => set('name', e.target.value)} /></Field>
        <Field label="Category"><Input value={f.category} onChange={e => set('category', e.target.value)} /></Field>
        <Field label="Target"><Input type="number" step="0.01" value={f.target_amount} onChange={e => set('target_amount', e.target.value)} /></Field>
        <Field label="Saved"><Input type="number" step="0.01" value={f.saved_amount} onChange={e => set('saved_amount', e.target.value)} /></Field>
        <Field label="Target date"><input type="datetime-local" className={fieldClass} value={f.target_date} onChange={e => set('target_date', e.target.value)} /></Field>
        <div className="flex items-end"><Button onClick={save} loading={saving} disabled={!f.name.trim()} className="w-full">Add</Button></div>
      </div>
    </Card>
  )
}

function PurchasesTab({ purchases, reload }: { purchases: SolacePurchase[]; reload: () => void }) {
  return (
    <div className="flex flex-col gap-4">
      <PurchaseForm onCreated={reload} />
      <div className="grid gap-3 lg:grid-cols-3">
        {purchases.map(p => (
          <Card key={p.id} className="p-4">
            <div className="flex items-start justify-between gap-3">
              <div><h3 className="font-semibold text-ink">{p.name}</h3><p className="text-sm text-muted">{p.category || 'Planned'} · {money(p.saved_amount)} saved</p></div>
              <Badge tone={p.priority === 'high' ? 'warning' : 'neutral'}>{p.progress_percent}%</Badge>
            </div>
            <div className="mt-4 h-2 rounded-full bg-sunken overflow-hidden"><div className="h-full bg-primary" style={{ width: `${p.progress_percent}%` }} /></div>
            <p className="mt-2 text-sm text-muted">{money(p.remaining_amount)} left · {dateOnly(p.target_date)}</p>
          </Card>
        ))}
      </div>
    </div>
  )
}

function PaydayForm({ onCreated }: { onCreated: () => void }) {
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
    } finally { setSaving(false) }
  }
  return (
    <Card className="p-4">
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
  return (
    <div className="flex flex-col gap-4">
      <PaydayForm onCreated={reload} />
      <div className="grid gap-3 lg:grid-cols-3">
        {paydays.map(p => (
          <Card key={p.id} className="p-4">
            <div className="flex items-start justify-between gap-3">
              <div><h3 className="font-semibold text-ink">{p.title}</h3><p className="text-sm text-muted">{money(p.expected_amount)}</p></div>
              <Badge tone={p.is_active ? 'success' : 'neutral'}>{p.is_active ? 'Included' : 'Paused'}</Badge>
            </div>
            <div className="mt-3 flex items-center justify-between gap-3">
              <DueBadge iso={p.pay_at} />
              <Button size="sm" variant="ghost" onClick={() => toggle(p)}>
                {p.is_active ? 'Pause' : 'Include'}
              </Button>
            </div>
          </Card>
        ))}
      </div>
    </div>
  )
}

function ChecklistTab({ items, reload, onChange, onError }: {
  items: SolaceChecklistItem[]
  reload: () => void
  onChange: (items: SolaceChecklistItem[]) => void
  onError: (m: string) => void
}) {
  const [title, setTitle] = useState('')
  const [saving, setSaving] = useState(false)
  const add = async () => {
    setSaving(true)
    try { await api.createSolaceChecklistItem({ title }); setTitle(''); reload() }
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
  return (
    <div className="flex flex-col gap-4">
      <Card className="p-4">
        <div className="flex flex-col gap-3 sm:flex-row">
          <Input value={title} onChange={e => setTitle(e.target.value)} placeholder="Move money to bills account" />
          <Button onClick={add} loading={saving} disabled={!title.trim()}>Add</Button>
        </div>
      </Card>
      <div className="grid gap-2">
        {items.map(item => (
          <button key={item.id} onClick={() => toggle(item)} className="flex items-center justify-between rounded-lg border border-line bg-surface px-4 py-3 text-left hover:bg-sunken/40">
            <span className={item.is_complete ? 'text-muted line-through' : 'text-ink'}>
              {item.title}
              {Number(item.amount_hint) > 0 && <span className="ml-2 text-sm text-muted">{money(item.amount_hint)}</span>}
            </span>
            <div className="flex items-center gap-2">
              {item.cycle_start && <span className="hidden text-xs text-muted sm:inline">{dateOnly(item.cycle_start)}</span>}
              <Badge tone={item.is_complete ? 'success' : 'neutral'}>{item.is_complete ? 'Done' : 'Todo'}</Badge>
            </div>
          </button>
        ))}
      </div>
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
  const [view, setView] = useState<'calendar' | 'list'>('calendar')
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
    <Card key={event.key} className="p-3">
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
      <Card className="p-3">
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
            <Card key={title} className="p-3">
              <p className="text-lg font-extrabold text-ink">{money(value)}</p>
              <p className="text-xs text-muted">{title}</p>
            </Card>
          ))}
        </div>
      )}
      {view === 'calendar' ? (
        <Card className="overflow-x-auto p-3">
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

function Overview({ bills, buckets, subscriptions, purchases, onTab }: {
  bills: SolaceBill[]; buckets: SolaceBucket[]; subscriptions: SolaceSubscription[]
  purchases: SolacePurchase[]; onTab: (t: Tab) => void
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
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
      {stat('Unpaid bills', money(unpaidTotal), 'bills', unpaidTotal ? 'warning' : 'success')}
      {stat('Set aside', money(bucketTotal), 'buckets', 'primary')}
      {stat('Active subscriptions', money(subTotal), 'subscriptions', 'neutral')}
      {stat('Planned purchases', String(openPurchases.length), 'purchases', openPurchases.length ? 'warning' : 'success')}
    </div>
  )
}

function PayPlan({ plan, generating, onGenerate, onTab }: {
  plan: SolacePayCyclePlan | null
  generating: boolean
  onGenerate: () => void
  onTab: (tab: Tab) => void
}) {
  if (!plan || plan.sources.length === 0) {
    return (
      <EmptyState
        icon="🧮"
        title="No income in this pay cycle"
        hint="Add a payday with its next date, amount and repeat pattern to calculate the household split."
        action={<Button onClick={() => onTab('paydays')}>Add payday</Button>}
      />
    )
  }
  return (
    <div className="space-y-4">
      <Card className="p-4">
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
          <div>
            <p className="text-sm font-medium text-muted">Pay cycle</p>
            <h2 className="text-lg font-bold text-ink">{dateOnly(plan.cycle_start)} – {dateOnly(plan.cycle_end)}</h2>
          </div>
          <Button onClick={onGenerate} loading={generating} disabled={plan.buckets.length === 0}>
            Create payday checklist
          </Button>
        </div>
      </Card>
      <div className="grid gap-3 sm:grid-cols-3">
        {[
          ['Expected income', money(plan.income_total)],
          ['Bucket transfers', money(plan.allocated_total)],
          ['Remaining after transfers', money(plan.remaining)],
        ].map(([label, value]) => (
          <Card key={label} className="p-4">
            <p className="text-2xl font-extrabold text-ink">{value}</p>
            <p className="mt-1 text-sm text-muted">{label}</p>
          </Card>
        ))}
      </div>
      {plan.buckets.length === 0 ? (
        <EmptyState
          icon="🪣"
          title="No active allocation rules"
          hint="Set a percentage or fixed pay-cycle amount on at least one bucket."
          action={<Button onClick={() => onTab('buckets')}>Configure buckets</Button>}
        />
      ) : (
        <Card className="divide-y divide-line">
          {plan.buckets.map(bucket => (
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
        {plan.sources.map(source => (
          <Card key={source.payday_id} className="p-4">
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
  const [tab, setTab] = useUrlTab<Tab>('overview', TAB_KEYS)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [bills, setBills] = useState<SolaceBill[]>([])
  const [paydays, setPaydays] = useState<SolacePayday[]>([])
  const [purchases, setPurchases] = useState<SolacePurchase[]>([])
  const [buckets, setBuckets] = useState<SolaceBucket[]>([])
  const [subscriptions, setSubscriptions] = useState<SolaceSubscription[]>([])
  const [checklist, setChecklist] = useState<SolaceChecklistItem[]>([])
  const [plan, setPlan] = useState<SolacePayCyclePlan | null>(null)
  const [generatingChecklist, setGeneratingChecklist] = useState(false)
  const [schedule, setSchedule] = useState<SolaceSchedule | null>(null)
  const [scheduleMonth, setScheduleMonth] = useState(currentMonthKey)
  const [scheduleLoading, setScheduleLoading] = useState(false)
  const [q, setQ] = useUrlQueryState()

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
      const [bs, ps, pu, bu, su, ch, pl] = await Promise.all([
        api.getSolaceBills(), api.getSolacePaydays(), api.getSolacePurchases(),
        api.getSolaceBuckets(), api.getSolaceSubscriptions(), api.getSolaceChecklist(),
        api.getSolacePlan(),
      ])
      setBills(bs); setPaydays(ps); setPurchases(pu); setBuckets(bu); setSubscriptions(su); setChecklist(ch); setPlan(pl)
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

  const generateChecklist = async () => {
    setGeneratingChecklist(true); setError('')
    try {
      const items = await api.generateSolacePlanChecklist()
      setChecklist(items)
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
      void loadSchedule()
      return updated
    } catch (e) {
      setError(errMsg(e))
      throw e
    }
  }

  if (!unlocked) return <ReauthGate onUnlock={() => setUnlocked(true)} />

  return (
    <div className="max-w-5xl mx-auto space-y-5">
      <PageHeader title="Solace" subtitle="Bills, set-asides and planned purchases" icon="💸" />
      {error && <div className="rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-danger">{error}</div>}
      <div className="flex flex-col gap-2 sm:flex-row">
        <Input value={q} onChange={e => setQ(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') search() }} placeholder="Search Solace" />
        <Button variant="ghost" onClick={search}>Search</Button>
        <Button variant="ghost" onClick={load} loading={loading}>Refresh</Button>
      </div>
      <Tabs
        tabs={[
          { key: 'overview', label: 'Overview' },
          { key: 'schedule', label: 'Schedule' },
          { key: 'plan', label: 'Pay plan' },
          { key: 'bills', label: 'Bills' },
          { key: 'buckets', label: 'Buckets' },
          { key: 'subscriptions', label: 'Subscriptions' },
          { key: 'purchases', label: 'Purchases' },
          { key: 'paydays', label: 'Paydays' },
          { key: 'checklist', label: 'Checklist' },
        ]}
        active={tab}
        onChange={k => setTab(k as Tab)}
      />
      {tab === 'overview' && <Overview bills={bills} buckets={buckets} subscriptions={subscriptions} purchases={purchases} onTab={setTab} />}
      {tab === 'schedule' && (
        <ScheduleTab
          schedule={schedule}
          month={scheduleMonth}
          loading={scheduleLoading}
          onMonth={setScheduleMonth}
          onAction={updateOccurrence}
        />
      )}
      {tab === 'plan' && <PayPlan plan={plan} generating={generatingChecklist} onGenerate={generateChecklist} onTab={setTab} />}
      {tab === 'bills' && <BillsTab bills={bills} reload={load} onOccurrence={updateOccurrence} onError={setError} />}
      {tab === 'buckets' && <BucketsTab buckets={buckets} reload={load} onError={setError} />}
      {tab === 'subscriptions' && <SubscriptionsTab subscriptions={subscriptions} reload={load} />}
      {tab === 'purchases' && <PurchasesTab purchases={purchases} reload={load} />}
      {tab === 'paydays' && <PaydaysTab paydays={paydays} reload={load} onError={setError} />}
      {tab === 'checklist' && <ChecklistTab items={checklist} reload={load} onChange={setChecklist} onError={setError} />}
    </div>
  )
}
