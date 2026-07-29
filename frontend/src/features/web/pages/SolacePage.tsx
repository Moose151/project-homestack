import { useEffect, useMemo, useState } from 'react'
import { api } from '../../../api/client'
import type {
  SolaceBill, SolaceBucket, SolaceChecklistItem, SolacePayday,
  SolacePayCyclePlan, SolacePurchase, SolaceSubscription,
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

type Tab = 'overview' | 'plan' | 'bills' | 'buckets' | 'subscriptions' | 'purchases' | 'paydays' | 'checklist'
const TAB_KEYS: Tab[] = ['overview', 'plan', 'bills', 'buckets', 'subscriptions', 'purchases', 'paydays', 'checklist']

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
  const [f, setF] = useState({ name: '', category: 'utilities', provider: '', amount: '', due_at: '', recurrence_rule: '' })
  const [saving, setSaving] = useState(false)
  const set = (k: string, v: string) => setF(prev => ({ ...prev, [k]: v }))
  const save = async () => {
    setSaving(true)
    try {
      await api.createSolaceBill({ ...f, amount: f.amount || '0.00', due_at: fromLocalInput(f.due_at), is_all_day: true })
      setF({ name: '', category: 'utilities', provider: '', amount: '', due_at: '', recurrence_rule: '' })
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
        <Field label="Due"><input type="datetime-local" className={fieldClass} value={f.due_at} onChange={e => set('due_at', e.target.value)} /></Field>
        <Field label="Repeats"><Select value={f.recurrence_rule} onChange={e => set('recurrence_rule', e.target.value)}>{RECURRENCE.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}</Select></Field>
        <div className="flex items-end"><Button onClick={save} loading={saving} disabled={!f.name.trim()} className="w-full">Add</Button></div>
      </div>
    </Card>
  )
}

function BillsTab({ bills, reload, onChange, onError }: {
  bills: SolaceBill[]
  reload: () => void
  onChange: (bills: SolaceBill[]) => void
  onError: (m: string) => void
}) {
  const [undoBill, setUndoBill] = useState<SolaceBill | null>(null)
  const pay = async (bill: SolaceBill) => {
    const optimistic = { ...bill, is_paid: true, paid_at: new Date().toISOString() }
    onChange(bills.map(row => row.id === bill.id ? optimistic : row))
    try {
      const updated = await api.markSolaceBillPaid(bill.id)
      onChange(bills.map(row => row.id === bill.id ? updated : row))
      setUndoBill(bill)
    } catch (e) {
      onChange(bills)
      onError(errMsg(e))
    }
  }
  const undo = async () => {
    if (!undoBill) return
    const previous = undoBill
    setUndoBill(null)
    onChange(bills.map(row => row.id === previous.id ? previous : row))
    try {
      const updated = await api.updateSolaceBill(previous.id, { is_paid: false, paid_at: null })
      onChange(bills.map(row => row.id === previous.id ? updated : row))
    } catch (e) {
      onError(errMsg(e))
    }
  }
  return (
    <div className="flex flex-col gap-4">
      <BillForm onCreated={reload} />
      {bills.length === 0 ? <EmptyState icon="💸" title="No bills yet" hint="" /> : (
        <div className="grid gap-3 lg:grid-cols-2">
          {bills.map(b => (
            <Card key={b.id} className="p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <h3 className="font-semibold text-ink truncate">{b.name}</h3>
                  <p className="text-sm text-muted">{b.provider || cap(b.category)} · {money(b.amount)}</p>
                  {b.source_node === 'homestead' && <div className="mt-1"><Badge tone="success">Synced from Homestead</Badge></div>}
                </div>
                <DueBadge iso={b.due_at} paid={b.is_paid} />
              </div>
              {b.notes && <p className="mt-3 text-sm text-muted">{b.notes}</p>}
              {!b.is_paid && <Button size="sm" variant="ghost" className="mt-3" onClick={() => pay(b)}>Mark paid</Button>}
            </Card>
          ))}
        </div>
      )}
      {undoBill && <UndoToast message={`${undoBill.name} marked paid`} onUndo={undo} onDismiss={() => setUndoBill(null)} />}
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
  const [q, setQ] = useUrlQueryState()

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
      {tab === 'plan' && <PayPlan plan={plan} generating={generatingChecklist} onGenerate={generateChecklist} onTab={setTab} />}
      {tab === 'bills' && <BillsTab bills={bills} reload={load} onChange={setBills} onError={setError} />}
      {tab === 'buckets' && <BucketsTab buckets={buckets} reload={load} onError={setError} />}
      {tab === 'subscriptions' && <SubscriptionsTab subscriptions={subscriptions} reload={load} />}
      {tab === 'purchases' && <PurchasesTab purchases={purchases} reload={load} />}
      {tab === 'paydays' && <PaydaysTab paydays={paydays} reload={load} onError={setError} />}
      {tab === 'checklist' && <ChecklistTab items={checklist} reload={load} onChange={setChecklist} onError={setError} />}
    </div>
  )
}
