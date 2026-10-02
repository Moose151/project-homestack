import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../../api/client'
import type { SolaceBalanceForecast } from '../../../api/types'
import { Badge } from '../../../components/Badge'
import { Button } from '../../../components/Button'
import { Card } from '../../../components/Card'
import { Field, Input, Select } from '../../../components/Field'
import { Modal } from '../../../components/Modal'
import { solaceMoney as money } from './solaceFormat'

const dateLabel = (value: string) => new Date(`${value.slice(0, 10)}T12:00:00`).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
const errorMessage = (e: unknown) => e instanceof Error ? e.message : 'Something went wrong.'
const amount = (value: string | null | undefined) => value == null ? '—' : money(value)

export function BalanceDialog({ asOf, onClose, onSaved }: { asOf?: string; onClose: () => void; onSaved: () => void }) {
  const [balance, setBalance] = useState('')
  const [date, setDate] = useState(() => {
    const yesterday = asOf ? new Date(`${asOf.slice(0, 10)}T12:00:00`) : new Date()
    yesterday.setDate(yesterday.getDate() - 1)
    return `${yesterday.getFullYear()}-${String(yesterday.getMonth() + 1).padStart(2, '0')}-${String(yesterday.getDate()).padStart(2, '0')}`
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const save = async (event: FormEvent) => {
    event.preventDefault()
    setSaving(true); setError('')
    try {
      await api.createSolaceBalance({ snapshot_date: date, balance, notes: '' })
      onSaved()
    } catch (e) { setError(errorMessage(e)) }
    finally { setSaving(false) }
  }
  return (
    <Modal title="Update bills-account balance" onClose={onClose} size="full">
      <form onSubmit={save} className="space-y-4">
        <p className="text-sm text-muted">Enter your bank’s closing balance on this date, after that day’s payments and transfers. The forecast starts on the following day.</p>
        <Field label="Balance date" htmlFor="account-balance-date"><Input id="account-balance-date" type="date" value={date} max={asOf?.slice(0, 10)} onChange={e => setDate(e.target.value)} required /></Field>
        <Field label="Closing balance" htmlFor="account-balance"><Input id="account-balance" data-autofocus type="number" step="0.01" value={balance} onChange={e => setBalance(e.target.value)} placeholder="0.00" required /></Field>
        {error && <p role="alert" className="text-sm text-danger">{error}</p>}
        <Button type="submit" loading={saving} disabled={!date || balance === ''}>Save balance</Button>
      </form>
    </Modal>
  )
}

export function MoneyAccountSummary({ forecast, onOpen }: { forecast: SolaceBalanceForecast | null; onOpen: () => void }) {
  if (!forecast) return <p className="text-sm text-muted">Loading bills-account forecast…</p>
  const risk = forecast.is_covered === false
  return (
    <Card contentClassName="p-4 sm:p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="font-bold text-ink">Bills account</h2>
        <Badge tone={risk ? 'danger' : 'neutral'}>{risk ? 'Top-up needed' : forecast.latest_balance ? 'Projected balance' : 'Add a balance to get started'}</Badge>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-3">
        <div><p className="text-xs text-muted">Last recorded balance</p><p className="text-xl font-bold text-ink">{amount(forecast.opening_balance)}</p>{forecast.latest_balance && <p className="text-xs text-muted">{dateLabel(forecast.latest_balance.snapshot_date)}</p>}</div>
        <div><p className="text-xs text-muted">Lowest projected balance</p><p className={`text-xl font-bold ${risk ? 'text-danger' : 'text-ink'}`}>{amount(forecast.lowest_balance)}</p><p className="text-xs text-muted">{forecast.lowest_balance_date && dateLabel(forecast.lowest_balance_date)}</p></div>
        <div><p className="text-xs text-muted">Bills over {forecast.horizon_months} months</p><p className="text-xl font-bold text-ink">{money(forecast.total_bills)}</p></div>
      </div>
      {risk && <p className="mt-3 text-sm font-semibold text-danger">Top up by {money(forecast.shortfall || '0')} to cover the projected low point. First shortfall: {dateLabel(forecast.first_shortfall_date || forecast.lowest_balance_date)}.</p>}
      {(forecast.warnings?.length ?? 0) > 0 && <p className="mt-3 text-sm text-warning">{forecast.warnings[0]}</p>}
      <Button className="mt-4 w-full sm:w-auto" variant="secondary" onClick={onOpen}>Open bills-account forecast</Button>
    </Card>
  )
}

function BalanceChart({ forecast }: { forecast: SolaceBalanceForecast }) {
  const [selected, setSelected] = useState(0)
  const points = [{ date: forecast.forecast_start, projected_balance: forecast.opening_balance }, ...forecast.timeline]
    .filter((row): row is { date: string; projected_balance: string } => row.projected_balance != null)
  if (!points.length) return null
  const values = points.map(row => Number(row.projected_balance))
  const low = Math.min(0, ...values)
  const high = Math.max(1, Number(forecast.buffer_amount), ...values)
  const range = high - low || 1
  const first = Date.parse(forecast.forecast_start)
  const last = Date.parse(forecast.through)
  const x = (date: string) => 10 + (Date.parse(date) - first) / Math.max(1, last - first) * 580
  const y = (value: number) => 150 - (value - low) / range * 130
  const index = Math.min(selected, points.length - 1)
  const point = points[index]
  const path = points.map((row, i) => `${i ? 'H' : 'M'} ${x(row.date)} ${i ? `V ${y(Number(row.projected_balance))}` : y(Number(row.projected_balance))}`).join(' ') + ` H ${x(forecast.through)}`
  return (
    <figure className="space-y-2" aria-label="Projected bills-account balance">
      <div className="flex flex-wrap justify-between gap-2 text-sm"><span className="text-muted">{dateLabel(point.date)}</span><strong className={Number(point.projected_balance) < 0 ? 'text-danger' : 'text-ink'}>{money(point.projected_balance)}</strong></div>
      <svg viewBox="0 0 600 170" className="w-full text-primary" role="img" aria-label={`Balance ranges from ${money(low)} to ${money(high)}. Use the slider or dated list to inspect it.`}>
        <line x1="10" x2="590" y1={y(0)} y2={y(0)} className="stroke-danger" strokeDasharray="4 4" />
        <line x1="10" x2="590" y1={y(Number(forecast.buffer_amount))} y2={y(Number(forecast.buffer_amount))} className="stroke-warning" strokeDasharray="2 4" />
        <path d={path} fill="none" stroke="currentColor" strokeWidth="2.5" />
        <circle cx={x(point.date)} cy={y(Number(point.projected_balance))} r="5" fill="currentColor" />
      </svg>
      <input className="min-h-11 w-full accent-primary" type="range" min="0" max={Math.max(0, points.length - 1)} value={index} onChange={e => setSelected(Number(e.target.value))} aria-label="Inspect forecast date" aria-valuetext={`${dateLabel(point.date)}: ${money(point.projected_balance)}`} />
      <figcaption className="text-xs text-muted">Move the slider to inspect each change. Dashed lines show zero and your {money(forecast.buffer_amount)} buffer. Balances are projected at the end of each day.</figcaption>
    </figure>
  )
}

export function ForecastTab({ initial, onBalance, onTransfers }: { initial: SolaceBalanceForecast | null; onBalance: () => void; onTransfers: () => void }) {
  const [forecast, setForecast] = useState(initial)
  const [months, setMonths] = useState(initial?.horizon_months || 12)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [coverageFilter, setCoverageFilter] = useState('all')
  const [showAll, setShowAll] = useState(false)
  const requestSeq = useRef(0)
  useEffect(() => { setForecast(initial); setMonths(initial?.horizon_months || 12); setLoading(false); setError(''); ++requestSeq.current }, [initial])
  useEffect(() => () => { ++requestSeq.current }, [])
  const refresh = async (nextMonths = months) => {
    const requestId = ++requestSeq.current
    setLoading(true); setError('')
    try {
      const result = await api.getSolaceForecast(nextMonths)
      if (requestId === requestSeq.current) { setForecast(result); setMonths(nextMonths); setShowAll(false) }
    } catch (e) { if (requestId === requestSeq.current) setError(errorMessage(e)) }
    finally { if (requestId === requestSeq.current) setLoading(false) }
  }
  if (!forecast) return <div className="space-y-3"><p className="text-muted">Forecast is not available.</p><Button onClick={() => refresh()} loading={loading}>Load forecast</Button>{error && <p role="alert" className="text-danger">{error}</p>}</div>
  const coverage = forecast.bill_coverage || []
  const includedCount = coverage.filter(row => row.included).length
  const rows = showAll ? forecast.timeline : forecast.timeline.slice(0, 20)
  const risk = forecast.is_covered === false
  return (
    <div className="space-y-4" aria-busy={loading}>
      <Card contentClassName="p-4 space-y-4">
        <div className="flex flex-wrap justify-between gap-3">
          <div><h2 className="text-lg font-bold text-ink">Bills-account forecast</h2><p className="text-sm text-muted">Will this account cover the bills, and when might it need a top-up?</p></div>
          <Button variant="secondary" onClick={onBalance}>{forecast.latest_balance ? 'Update balance' : 'Add balance'}</Button>
        </div>
        <div className="flex flex-wrap items-end gap-2">
          <Field label="Forecast period" htmlFor="forecast-period"><Select id="forecast-period" value={months} disabled={loading} onChange={e => void refresh(Number(e.target.value))}>{[1, 3, 6, 12, 18, 24].map(value => <option key={value} value={value}>{value} {value === 1 ? 'month' : 'months'}</option>)}</Select></Field>
          <Button variant="ghost" onClick={() => refresh()} loading={loading}>Refresh forecast</Button>
        </div>
        {error && <p role="alert" className="text-sm text-danger">{error} The last successful forecast is still shown.</p>}
        <p className="text-sm text-muted">{forecast.latest_balance ? `Starting with ${money(forecast.opening_balance || '0')} at the close of ${dateLabel(forecast.latest_balance.snapshot_date)}.` : `Add a closing balance to see projected balances. The account needs at least ${money(forecast.required_opening_balance)} at the start of this period, before your buffer.`} Projection through {dateLabel(forecast.through)}.</p>
        {(forecast.warnings?.length ?? 0) > 0 && <ul className="list-disc space-y-1 rounded-xl bg-warning/10 py-3 pl-7 pr-3 text-sm text-ink">{forecast.warnings.map(warning => <li key={warning}>{warning}</li>)}</ul>}
      </Card>
      {risk && <Card className="border-danger/30" contentClassName="p-4"><h3 className="font-bold text-danger">Top-up needed: {money(forecast.shortfall || '0')}</h3><p className="mt-1 text-sm text-muted">First projected shortfall on {dateLabel(forecast.first_shortfall_date || forecast.lowest_balance_date)}. The low point is {amount(forecast.lowest_balance)} on {dateLabel(forecast.lowest_balance_date)}.</p><Button variant="secondary" className="mt-3" onClick={onTransfers}>Review bills transfers</Button></Card>}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[
          ['Money coming in', `+${money(forecast.total_contributions)}`, 'Expected payday transfers into bills buckets'],
          ['Bills going out', `−${money(forecast.total_bills)}`, `${includedCount} bills with payments in this projection`],
          ['Lowest balance', amount(forecast.lowest_balance), forecast.lowest_balance_date ? dateLabel(forecast.lowest_balance_date) : 'Add an account balance'],
          ['Balance at the end', amount(forecast.ending_balance), dateLabel(forecast.through)],
        ].map(([label, value, hint]) => <Card key={label} contentClassName="p-3"><p className="text-xs text-muted">{label}</p><p className="mt-1 break-words text-xl font-bold text-ink">{value}</p><p className="mt-1 text-xs text-muted">{hint}</p></Card>)}
      </div>
      {forecast.latest_balance && <Card contentClassName="p-4"><BalanceChart forecast={forecast} /><p className="mt-3 text-sm text-muted">Projected headroom after keeping your buffer: <strong className="text-ink">{amount(forecast.safe_to_withdraw)}</strong>. This assumes all listed transfers arrive and scheduled costs are accurate; review the coverage below before moving money.</p></Card>}
      <Card contentClassName="p-4 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3"><h3 className="font-bold text-ink">Which bills are counted?</h3><Select aria-label="Forecast bill coverage" className="sm:!w-auto" value={coverageFilter} onChange={e => setCoverageFilter(e.target.value)}><option value="all">All bills ({coverage.length})</option><option value="included">Included ({includedCount})</option><option value="excluded">Not counted ({coverage.length - includedCount})</option></Select></div>
        <p className="text-sm text-muted">Bills paid from this account are counted even when set-aside planning is switched off. Open a bill to change its payment account or schedule.</p>
        <ul className="divide-y divide-line">{coverage.filter(row => coverageFilter === 'all' || row.included === (coverageFilter === 'included')).map(row => <li key={row.bill_id}><Link className="flex min-h-14 items-center justify-between gap-3 py-3 text-sm" to={`/solace?tab=bills&section=bills&bill=${row.bill_id}`}><span className="min-w-0"><span className="block font-semibold text-primary">{row.name}</span><span className="text-xs text-muted">{row.included ? `${row.payment_count} payments` : row.reason}</span></span><span className="shrink-0 font-semibold text-ink">{row.included ? money(row.total) : '—'} →</span></Link></li>)}</ul>
        {!coverage.length && <p className="text-sm text-muted">Add your bills to see what is included.</p>}
      </Card>
      <Card contentClassName="p-4 space-y-3">
        <h3 className="font-bold text-ink">Money in and out by date</h3>
        <p className="text-sm text-muted">Expected transfers and bill payments, with the balance after each day. Overdue unpaid bills before the opening date are carried into the first day. Paid bills use their payment date.</p>
        {!rows.length && <p className="text-sm text-muted">No payments or transfers in this period.</p>}
        <div className="divide-y divide-line">{rows.map(row => <details key={row.date} className="py-1"><summary className="flex min-h-14 cursor-pointer items-center justify-between gap-3 py-2"><span className="min-w-0"><span className="block text-sm font-semibold text-ink">{dateLabel(row.date)}</span><span className="block text-xs text-muted">{row.items.map(item => item.name).join(' · ')}</span><span className="block text-xs text-muted">In {money(row.contributions)} · Out {money(row.bills)}</span></span><strong className={`shrink-0 text-sm ${Number(row.projected_balance) < 0 ? 'text-danger' : 'text-ink'}`}>{amount(row.projected_balance)}</strong></summary><ul className="space-y-2 pb-3 pl-3 text-sm">{row.items.map((item, index) => <li key={`${item.kind}-${item.record_id}-${index}`} className="flex justify-between gap-3"><span className="text-muted">{item.kind === 'contribution' ? 'Transfer: ' : ''}{item.name}{item.status === 'paid' ? ' · Paid' : ''}</span><span className="shrink-0 font-medium text-ink">{item.kind === 'contribution' ? '+' : '−'}{money(item.amount)}</span></li>)}</ul></details>)}</div>
        {forecast.timeline.length > 20 && <Button variant="secondary" onClick={() => setShowAll(value => !value)}>{showAll ? 'Show fewer dates' : `Show all ${forecast.timeline.length} dates`}</Button>}
      </Card>
      <p className="text-xs text-muted">This is a plan based on recorded balances, scheduled bills and payday allocations. Transfers are assumed to arrive before payments on the same day. Update the balance regularly to account for other bank activity.</p>
    </div>
  )
}
