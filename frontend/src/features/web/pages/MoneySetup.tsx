import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../../api/client'
import type { SolaceAccountTransfer, SolaceBalanceForecast, SolaceBill, SolaceSettings } from '../../../api/types'
import { Button } from '../../../components/Button'
import { Card } from '../../../components/Card'
import { Field, Input, Select } from '../../../components/Field'
import { Modal } from '../../../components/Modal'
import { solaceMoney as money } from './solaceFormat'

const message = (error: unknown) => error instanceof Error ? error.message : 'Could not save. Please try again.'
const day = (iso: string) => new Date(iso).toLocaleDateString()
const localDate = (iso?: string) => {
  const value = iso ? new Date(iso) : new Date()
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}-${String(value.getDate()).padStart(2, '0')}`
}
const frequencies = [
  { value: 'FREQ=WEEKLY;INTERVAL=2', label: 'Every fortnight' },
  { value: 'FREQ=WEEKLY', label: 'Every week' },
  { value: 'FREQ=MONTHLY', label: 'Every month' },
  { value: 'FREQ=YEARLY', label: 'Every year' },
  { value: '', label: 'Once only' },
]

function TransferEditor({ transfer, onClose, onSaved }: { transfer: SolaceAccountTransfer | null; onClose: () => void; onSaved: () => void }) {
  const [name, setName] = useState(transfer?.name || 'Bills account transfer')
  const [amount, setAmount] = useState(transfer?.amount || '')
  const [date, setDate] = useState(localDate(transfer?.due_at))
  const [rule, setRule] = useState(transfer?.recurrence_rule ?? 'FREQ=WEEKLY;INTERVAL=2')
  const [end, setEnd] = useState(transfer?.end_date || '')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const save = async (event: FormEvent) => {
    event.preventDefault(); setSaving(true); setError('')
    try {
      const data = { name, amount, due_at: new Date(`${date}T12:00:00`).toISOString(), recurrence_rule: rule, end_date: end || null }
      if (transfer) await api.updateSolaceTransfer(transfer.id, data)
      else await api.createSolaceTransfer(data)
      onSaved()
    } catch (e) { setError(message(e)) }
    finally { setSaving(false) }
  }
  return <Modal title={transfer ? 'Edit incoming transfer' : 'Add incoming transfer'} size="full" onClose={onClose}>
    <form className="space-y-4" onSubmit={save}>
      <p className="text-sm text-muted">The amount you move into this bank account. This schedules the forecast; it does not move money at your bank.</p>
      <Field label="Transfer name" htmlFor="transfer-name"><Input id="transfer-name" value={name} onChange={e => setName(e.target.value)} required /></Field>
      <Field label="Amount arriving" htmlFor="transfer-amount"><Input id="transfer-amount" data-autofocus type="number" min="0.01" step="0.01" value={amount} onChange={e => setAmount(e.target.value)} required /></Field>
      <Field label="Next transfer date" htmlFor="transfer-date"><Input id="transfer-date" type="date" value={date} onChange={e => setDate(e.target.value)} required /></Field>
      <Field label="How often?" htmlFor="transfer-repeat"><Select id="transfer-repeat" value={rule} onChange={e => setRule(e.target.value)}>{frequencies.map(f => <option key={f.value} value={f.value}>{f.label}</option>)}</Select></Field>
      <details open={!!transfer?.end_date}><summary className="min-h-11 cursor-pointer py-3 text-sm text-muted">Optional end date</summary><Field label="Last transfer date" htmlFor="transfer-end" hint="Leave blank to keep repeating."><Input id="transfer-end" type="date" min={date} value={end} onChange={e => setEnd(e.target.value)} /></Field><Button type="button" variant="ghost" onClick={() => setEnd('')}>Keep repeating</Button></details>
      {error && <p role="alert" className="text-sm text-danger">{error}</p>}
      <Button type="submit" loading={saving} disabled={!name.trim()}>Save transfer</Button>
    </form>
  </Modal>
}

export function MoneySetup({ settings, forecast, bills, onBalance, onBills, reload, onAdvanced }: {
  settings: SolaceSettings | null; forecast: SolaceBalanceForecast | null; bills: SolaceBill[]
  onBalance: () => void; onBills: () => void; reload: () => Promise<void>; onAdvanced: () => void
}) {
  const [transfers, setTransfers] = useState<SolaceAccountTransfer[]>([])
  const [editor, setEditor] = useState<SolaceAccountTransfer | 'new' | null>(null)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [loading, setLoading] = useState(true)
  const [buffer, setBuffer] = useState(settings?.default_buffer_amount || '0')
  useEffect(() => { setBuffer(settings?.default_buffer_amount || '0') }, [settings?.default_buffer_amount])
  const loadTransfers = async () => {
    setLoading(true)
    try { setTransfers(await api.getSolaceTransfers()); setError('') }
    catch (e) { setError(message(e)) }
    finally { setLoading(false) }
  }
  useEffect(() => { void loadTransfers() }, [])
  const changeSettings = async (data: Partial<SolaceSettings>) => {
    setSaving(true); setError('')
    try { await api.updateSolaceSettings(data); await reload() }
    catch (e) { setError(message(e)) }
    finally { setSaving(false) }
  }
  const mode = settings?.forecast_funding_source || 'pay_plan'
  const issues = bills.filter(bill => bill.schedule?.issue)
  return <div className="space-y-4">
    <div><h2 className="text-xl font-bold text-ink">Set up your bills account</h2><p className="mt-1 text-sm text-muted">Three things make the forecast work: a bank balance, the bills it pays, and money coming in.</p></div>
    {error && <p role="alert" className="rounded-xl bg-danger/10 p-3 text-sm text-danger">{error}</p>}
    <Card contentClassName="p-4 space-y-3">
      <h3 className="font-bold text-ink">1. Record a bank balance</h3>
      <p className="text-sm text-muted">{forecast?.latest_balance ? `${money(forecast.latest_balance.balance)} at the close of ${day(forecast.latest_balance.snapshot_date)}. Update this occasionally to keep the plan in step with your bank.` : 'Use the closing balance from your bank for a completed day. Money projects changes from the following day.'}</p>
      <Button variant="secondary" onClick={onBalance}>{forecast?.latest_balance ? 'Update account balance' : 'Add account balance'}</Button>
    </Card>
    <Card contentClassName="p-4 space-y-3">
      <h3 className="font-bold text-ink">2. Check the bills this account pays</h3>
      <p className="text-sm text-muted">{bills.filter(b => b.is_active && b.paid_from_bills_account).length} active bills assigned to this account. Check the amount, frequency and next payment dates.</p>
      {issues.map(bill => <Link key={bill.id} className="block rounded-xl bg-warning/10 p-3 text-sm text-ink" to={`/solace?tab=bills&section=bills&bill=${bill.id}`}><strong>{bill.name}: {bill.schedule?.status}</strong><span className="mt-1 block">{bill.schedule?.issue} Open bill →</span></Link>)}
      <Button variant="secondary" onClick={onBills}>Review bills</Button>
    </Card>
    <Card contentClassName="p-4 space-y-3">
      <h3 className="font-bold text-ink">3. Add money coming in</h3>
      <p className="text-sm text-muted">Enter the transfers that actually arrive in this account—for example, $2,700 every fortnight. Your full salary does not need to be entered.</p>
      <Field label="Where forecast deposits come from" htmlFor="funding-source"><Select id="funding-source" value={mode} disabled={saving} onChange={e => void changeSettings({ forecast_funding_source: e.target.value as SolaceSettings['forecast_funding_source'] })}><option value="transfers">Scheduled account transfers (simple)</option><option value="pay_plan">Existing payday allocations (advanced)</option></Select></Field>
      {mode === 'pay_plan' ? <div className="rounded-xl bg-sunken p-3 text-sm text-muted"><p>Your existing payday allocations still fund the forecast. To use the simple setup, add your incoming transfers below, then select Scheduled account transfers above. Only the selected method is counted.</p><Button variant="ghost" onClick={onAdvanced}>View existing allocations</Button></div> : <p className="text-sm text-muted">Only these transfers are counted. Salary allocations and buckets are not added again.</p>}
      {loading ? <p className="text-sm text-muted">Loading transfers…</p> : <ul className="divide-y divide-line">{transfers.map(transfer => <li key={transfer.id} className="flex flex-wrap items-center justify-between gap-3 py-3"><div><p className="text-sm font-semibold text-ink">{transfer.name}{!transfer.is_active && ' · Paused'}</p><p className="text-sm text-muted">{money(transfer.amount)} · {frequencies.find(f => f.value === transfer.recurrence_rule)?.label} · from {day(transfer.due_at)}</p></div><div className="flex gap-2"><Button size="sm" variant="secondary" onClick={() => setEditor(transfer)}>Edit</Button><Button size="sm" variant="ghost" disabled={saving} onClick={async () => { setSaving(true); try { await api.updateSolaceTransfer(transfer.id, { is_active: !transfer.is_active }); await loadTransfers(); await reload() } catch (e) { setError(message(e)) } finally { setSaving(false) } }}>{transfer.is_active ? 'Pause' : 'Resume'}</Button></div></li>)}</ul>}
      <Button onClick={() => setEditor('new')}>Add incoming transfer</Button>
      {!transfers.length && !loading && <p className="text-xs text-muted">No scheduled transfers yet.</p>}
    </Card>
    <details className="rounded-2xl border border-line bg-surface p-4"><summary className="min-h-11 cursor-pointer py-2 font-semibold text-ink">Optional safety buffer</summary><p className="mb-3 text-sm text-muted">Money you would like left in the account after bills. This is a minimum balance, not an extra payment every payday.</p><Field label="Keep at least" htmlFor="account-buffer"><Input id="account-buffer" type="number" min="0" step="0.01" value={buffer} onChange={e => setBuffer(e.target.value)} /></Field><Button className="mt-3" variant="secondary" loading={saving} onClick={() => void changeSettings({ default_buffer_amount: buffer || '0' })}>Save buffer</Button></details>
    {editor && <TransferEditor transfer={editor === 'new' ? null : editor} onClose={() => setEditor(null)} onSaved={() => { setEditor(null); void loadTransfers(); void reload() }} />}
  </div>
}
