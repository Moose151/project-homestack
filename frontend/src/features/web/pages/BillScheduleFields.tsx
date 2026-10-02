import { useEffect, useState } from 'react'
import { api } from '../../../api/client'
import type { SolaceBillSchedule } from '../../../api/types'
import { Button } from '../../../components/Button'
import { Field, Input } from '../../../components/Field'

type Values = { name: string; amount: string; due_at: string; recurrence_rule: string; end_date: string; is_active?: boolean }
export function BillScheduleFields({ values, onEndDate }: { values: Values; onEndDate: (value: string) => void }) {
  const [ending, setEnding] = useState(Boolean(values.end_date))
  const [preview, setPreview] = useState<SolaceBillSchedule | null>(null)
  const [error, setError] = useState('')
  const { name, amount, due_at, recurrence_rule, end_date, is_active = true } = values
  useEffect(() => {
    let live = true
    setPreview(null); setError('')
    if (!due_at) return
    const timer = window.setTimeout(() => {
      api.previewSolaceBill({ name: name || 'Bill', amount: amount || '0.00', due_at: new Date(`${due_at}T00:00`).toISOString(), recurrence_rule, end_date: end_date || null, is_active })
        .then(result => { if (live) setPreview(result) })
        .catch(e => { if (live) setError(e instanceof Error ? e.message : 'Could not check the payment schedule.') })
    }, 250)
    return () => { live = false; window.clearTimeout(timer) }
  }, [name, amount, due_at, recurrence_rule, end_date, is_active])
  return <div className="space-y-3 rounded-xl bg-sunken p-3">
    {recurrence_rule && <>
      <label className="flex min-h-11 items-center gap-2 text-sm text-ink"><input type="checkbox" checked={ending} onChange={e => { setEnding(e.target.checked); if (!e.target.checked) onEndDate('') }} />Ends on a date</label>
      {ending ? <Field label="Last payment date"><Input type="date" value={end_date} onChange={e => onEndDate(e.target.value)} /></Field> : <p className="text-sm text-muted">Keeps repeating until you pause it.</p>}
      {end_date && <Button variant="secondary" size="sm" onClick={() => { onEndDate(''); setEnding(false) }}>Keep repeating — remove end date</Button>}
    </>}
    {preview?.issue && <p role="alert" className="text-sm font-semibold text-danger">{preview.issue}</p>}
    {preview && <p className="text-sm text-ink">{preview.next_dates.length ? `Next scheduled payments: ${preview.next_dates.map(value => new Date(value).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })).join(' · ')}` : `No future payments · ${preview.status}`}</p>}
    {!due_at && <p className="text-sm text-muted">Choose a payment date to preview the schedule.</p>}
    {error && <p role="alert" className="text-sm text-danger">{error}</p>}
  </div>
}
