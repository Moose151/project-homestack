import { useEffect, useState } from 'react'
import { api } from '../../../api/client'
import type {
  SolaceBalanceSnapshot,
  SolaceBillImportPreview,
  SolaceCategory,
  SolaceCategoryReport,
  SolaceCloseoutResponse,
  SolaceHealth,
  SolaceSettings,
} from '../../../api/types'
import { Badge } from '../../../components/Badge'
import { Button } from '../../../components/Button'
import { Card } from '../../../components/Card'
import { EmptyState } from '../../../components/EmptyState'
import { Field, Input, Select } from '../../../components/Field'
import { solaceMoney as money } from './solaceFormat'

const cap = (value: string) => value.charAt(0).toUpperCase() + value.slice(1).replace(/_/g, ' ')
const errMsg = (error: unknown) => error instanceof Error ? error.message : 'Something went wrong.'

export function HealthPanel({ health, onManage }: {
  health: SolaceHealth | null
  onManage?: () => void
}) {
  if (!health) return null
  const tone = health.status === 'healthy' ? 'success' : health.status === 'error' ? 'danger' : 'warning'
  return (
    <Card className="p-4">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="font-bold text-ink">Finance health</h2>
            <Badge tone={tone}>{cap(health.status)}</Badge>
          </div>
          {health.issues.length === 0 ? (
            <p className="mt-2 text-sm text-muted">Income, bills, allocations and account balance are ready.</p>
          ) : (
            <ul className="mt-2 space-y-1 text-sm text-muted">
              {health.issues.slice(0, 4).map(issue => (
                <li key={issue.code}>• {issue.message}</li>
              ))}
            </ul>
          )}
        </div>
        {onManage && <Button size="sm" variant="ghost" onClick={onManage}>Review setup</Button>}
      </div>
    </Card>
  )
}

function CategoryEditor({ category, reload, onError }: {
  category: SolaceCategory
  reload: () => void
  onError: (message: string) => void
}) {
  const [name, setName] = useState(category.name)
  const [categoryType, setCategoryType] = useState(category.category_type)
  const [active, setActive] = useState(category.is_active)
  const [saving, setSaving] = useState(false)
  const save = async () => {
    setSaving(true)
    try {
      await api.updateSolaceCategory(category.id, {
        name,
        category_type: categoryType,
        is_active: active,
      })
      reload()
    } catch (error) {
      onError(errMsg(error))
    } finally {
      setSaving(false)
    }
  }
  const remove = async () => {
    if (!window.confirm(`Delete ${category.name}? Records using it will move to Other.`)) return
    setSaving(true)
    try {
      await api.deleteSolaceCategory(category.id)
      reload()
    } catch (error) {
      onError(errMsg(error))
    } finally {
      setSaving(false)
    }
  }
  return (
    <details className="border-t border-line pt-2">
      <summary className="cursor-pointer py-1 text-sm font-medium text-ink">
        {cap(category.name)} · {cap(category.category_type)}
        {!category.is_active && <span className="ml-2 text-muted">(hidden)</span>}
      </summary>
      <div className="grid gap-2 py-3 sm:grid-cols-[1fr_0.7fr_auto]">
        <Input value={name} onChange={event => setName(event.target.value)} />
        <Select value={categoryType} onChange={event => setCategoryType(event.target.value as SolaceCategory['category_type'])}>
          <option value="bill">Bills</option>
          <option value="purchase">Purchases</option>
          <option value="both">Both</option>
        </Select>
        <div className="flex gap-2">
          <Button size="sm" onClick={save} loading={saving} disabled={!name.trim()}>Save</Button>
          <Button size="sm" variant="danger" onClick={remove} disabled={saving}>Delete</Button>
        </div>
      </div>
      <label className="mb-3 flex items-center gap-2 text-sm text-muted">
        <input type="checkbox" checked={active} onChange={event => setActive(event.target.checked)} />
        Available in forms
      </label>
    </details>
  )
}

function BalanceEditor({ row, reload, onError }: {
  row: SolaceBalanceSnapshot
  reload: () => void
  onError: (message: string) => void
}) {
  const [balance, setBalance] = useState(row.balance)
  const [date, setDate] = useState(row.snapshot_date)
  const [notes, setNotes] = useState(row.notes)
  const [saving, setSaving] = useState(false)
  const save = async () => {
    setSaving(true)
    try {
      await api.updateSolaceBalance(row.id, { balance, snapshot_date: date, notes })
      reload()
    } catch (error) {
      onError(errMsg(error))
    } finally {
      setSaving(false)
    }
  }
  const remove = async () => {
    if (!window.confirm('Delete this balance snapshot?')) return
    setSaving(true)
    try {
      await api.deleteSolaceBalance(row.id)
      reload()
    } catch (error) {
      onError(errMsg(error))
    } finally {
      setSaving(false)
    }
  }
  return (
    <details className="border-t border-line pt-2">
      <summary className="cursor-pointer py-1 text-sm text-ink">
        <span className="font-semibold">{money(row.balance)}</span>
        <span className="ml-2 text-muted">{new Date(`${row.snapshot_date}T00:00:00`).toLocaleDateString()}</span>
      </summary>
      <div className="grid gap-2 py-3 sm:grid-cols-[0.8fr_0.8fr_1fr_auto]">
        <Input type="date" value={date} onChange={event => setDate(event.target.value)} />
        <Input type="number" step="0.01" value={balance} onChange={event => setBalance(event.target.value)} />
        <Input value={notes} onChange={event => setNotes(event.target.value)} placeholder="Optional note" />
        <div className="flex gap-2">
          <Button size="sm" onClick={save} loading={saving}>Save</Button>
          <Button size="sm" variant="danger" onClick={remove} disabled={saving}>Delete</Button>
        </div>
      </div>
    </details>
  )
}

export function ManagementTab({ settings, categories, balances, report, health, reload, onError }: {
  settings: SolaceSettings | null
  categories: SolaceCategory[]
  balances: SolaceBalanceSnapshot[]
  report: SolaceCategoryReport | null
  health: SolaceHealth | null
  reload: () => void
  onError: (message: string) => void
}) {
  const [settingsForm, setSettingsForm] = useState({
    currency_symbol: '$',
    budget_year: '',
    cycle_anchor_date: '',
    default_buffer_amount: '0.00',
    payday_bill_handling: 'new_cycle' as SolaceSettings['payday_bill_handling'],
    show_help_tips: true,
    dashboard_reminders: true,
    due_soon_days: '3',
  })
  const [categoryName, setCategoryName] = useState('')
  const [categoryType, setCategoryType] = useState<SolaceCategory['category_type']>('both')
  const [balance, setBalance] = useState('')
  const [balanceDate, setBalanceDate] = useState(() => new Date().toISOString().slice(0, 10))
  const [saving, setSaving] = useState('')
  const [importFile, setImportFile] = useState<File | null>(null)
  const [importPreview, setImportPreview] = useState<SolaceBillImportPreview | null>(null)

  useEffect(() => {
    if (!settings) return
    setSettingsForm({
      currency_symbol: settings.currency_symbol,
      budget_year: settings.budget_year ? String(settings.budget_year) : '',
      cycle_anchor_date: settings.cycle_anchor_date || '',
      default_buffer_amount: settings.default_buffer_amount,
      payday_bill_handling: settings.payday_bill_handling,
      show_help_tips: settings.show_help_tips,
      dashboard_reminders: settings.dashboard_reminders,
      due_soon_days: String(settings.due_soon_days),
    })
  }, [settings])

  const saveSettings = async () => {
    setSaving('settings')
    try {
      await api.updateSolaceSettings({
        ...settingsForm,
        budget_year: settingsForm.budget_year ? Number(settingsForm.budget_year) : null,
        cycle_anchor_date: settingsForm.cycle_anchor_date || null,
        due_soon_days: Number(settingsForm.due_soon_days),
      })
      reload()
    } catch (error) {
      onError(errMsg(error))
    } finally {
      setSaving('')
    }
  }
  const addCategory = async () => {
    setSaving('category')
    try {
      await api.createSolaceCategory({
        name: categoryName.trim(),
        category_type: categoryType,
        position: (categories.length + 1) * 10,
      })
      setCategoryName('')
      reload()
    } catch (error) {
      onError(errMsg(error))
    } finally {
      setSaving('')
    }
  }
  const addBalance = async () => {
    setSaving('balance')
    try {
      await api.createSolaceBalance({
        snapshot_date: balanceDate,
        balance: balance || '0.00',
      })
      setBalance('')
      reload()
    } catch (error) {
      onError(errMsg(error))
    } finally {
      setSaving('')
    }
  }
  const previewImport = async () => {
    if (!importFile) return
    setSaving('import-preview')
    try {
      setImportPreview(await api.previewSolaceBillImport(importFile))
    } catch (error) {
      onError(errMsg(error))
    } finally {
      setSaving('')
    }
  }
  const confirmImport = async () => {
    setSaving('import-confirm')
    try {
      const result = await api.confirmSolaceBillImport()
      setImportPreview(null)
      setImportFile(null)
      reload()
      window.alert(`Imported ${result.imported_count} bill(s).${result.skipped_count ? ` Skipped ${result.skipped_count} invalid row(s).` : ''}`)
    } catch (error) {
      onError(errMsg(error))
    } finally {
      setSaving('')
    }
  }
  const cancelImport = async () => {
    setSaving('import-cancel')
    try {
      await api.cancelSolaceBillImport()
      setImportPreview(null)
      setImportFile(null)
    } catch (error) {
      onError(errMsg(error))
    } finally {
      setSaving('')
    }
  }

  return (
    <div className="space-y-4">
      <HealthPanel health={health} />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="p-4">
          <h2 className="font-bold text-ink">Solace settings</h2>
          <p className="mt-1 text-sm text-muted">Control cycle boundaries, display and the default safety buffer.</p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <Field label="Currency symbol">
              <Input value={settingsForm.currency_symbol} maxLength={8} onChange={event => setSettingsForm(previous => ({ ...previous, currency_symbol: event.target.value }))} />
            </Field>
            <Field label="Budget year">
              <Input type="number" value={settingsForm.budget_year} onChange={event => setSettingsForm(previous => ({ ...previous, budget_year: event.target.value }))} />
            </Field>
            <Field label="Pay-cycle anchor">
              <Input type="date" value={settingsForm.cycle_anchor_date} onChange={event => setSettingsForm(previous => ({ ...previous, cycle_anchor_date: event.target.value }))} />
            </Field>
            <Field label="Default buffer">
              <Input type="number" step="0.01" value={settingsForm.default_buffer_amount} onChange={event => setSettingsForm(previous => ({ ...previous, default_buffer_amount: event.target.value }))} />
            </Field>
            <Field label="Bills due on payday">
              <Select value={settingsForm.payday_bill_handling} onChange={event => setSettingsForm(previous => ({ ...previous, payday_bill_handling: event.target.value as SolaceSettings['payday_bill_handling'] }))}>
                <option value="new_cycle">Start the new cycle</option>
                <option value="previous_cycle">Finish the previous cycle</option>
              </Select>
            </Field>
            <Field label="Reminder window">
              <Select value={settingsForm.due_soon_days} onChange={event => setSettingsForm(previous => ({ ...previous, due_soon_days: event.target.value }))}>
                {[1, 2, 3, 5, 7, 14, 30].map(value => <option key={value} value={value}>{value} day{value === 1 ? '' : 's'} ahead</option>)}
              </Select>
            </Field>
          </div>
          <label className="mt-3 flex items-center gap-2 text-sm text-muted">
            <input type="checkbox" checked={settingsForm.show_help_tips} onChange={event => setSettingsForm(previous => ({ ...previous, show_help_tips: event.target.checked }))} />
            Show help tips
          </label>
          <label className="mt-2 flex items-center gap-2 text-sm text-muted">
            <input type="checkbox" checked={settingsForm.dashboard_reminders} onChange={event => setSettingsForm(previous => ({ ...previous, dashboard_reminders: event.target.checked }))} />
            Show generic Solace reminders in HomeStack notifications
          </label>
          <Button className="mt-4" size="sm" onClick={saveSettings} loading={saving === 'settings'}>Save settings</Button>
        </Card>

        <Card className="p-4">
          <h2 className="font-bold text-ink">Account balance</h2>
          <p className="mt-1 text-sm text-muted">Snapshots power the projected balance shown during cycle closeout.</p>
          <div className="mt-4 grid gap-2 sm:grid-cols-[0.8fr_0.8fr_auto]">
            <Input type="date" value={balanceDate} onChange={event => setBalanceDate(event.target.value)} />
            <Input type="number" step="0.01" value={balance} onChange={event => setBalance(event.target.value)} placeholder="Current balance" />
            <Button onClick={addBalance} loading={saving === 'balance'} disabled={!balance}>Add snapshot</Button>
          </div>
          <div className="mt-4">
            {balances.length === 0 ? <p className="text-sm text-muted">No balance history yet.</p> : balances.slice(0, 8).map(row => (
              <BalanceEditor key={row.id} row={row} reload={reload} onError={onError} />
            ))}
          </div>
        </Card>
      </div>

      <Card className="p-4">
        <h2 className="font-bold text-ink">Categories</h2>
        <p className="mt-1 text-sm text-muted">Custom categories are shared by bills, purchase plans and reports.</p>
        <div className="mt-4 grid gap-2 sm:grid-cols-[1fr_0.6fr_auto]">
          <Input value={categoryName} onChange={event => setCategoryName(event.target.value)} placeholder="New category" />
          <Select value={categoryType} onChange={event => setCategoryType(event.target.value as SolaceCategory['category_type'])}>
            <option value="bill">Bills</option>
            <option value="purchase">Purchases</option>
            <option value="both">Both</option>
          </Select>
          <Button onClick={addCategory} loading={saving === 'category'} disabled={!categoryName.trim()}>Add category</Button>
        </div>
        <div className="mt-4 grid gap-x-6 md:grid-cols-2">
          {categories.map(category => (
            <CategoryEditor key={category.id} category={category} reload={reload} onError={onError} />
          ))}
        </div>
      </Card>

      <Card className="p-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="font-bold text-ink">Category report</h2>
            <p className="text-sm text-muted">Active bills included in set-aside planning.</p>
          </div>
          {report && <p className="text-right text-sm text-muted">{money(report.fortnightly_total)}/fortnight<br />{money(report.annual_total)}/year</p>}
        </div>
        {!report || report.categories.length === 0 ? (
          <EmptyState icon="📊" title="No category totals yet" hint="Add active bills to populate this report." />
        ) : (
          <div className="mt-4 divide-y divide-line">
            {report.categories.map(row => (
              <div key={row.category} className="grid grid-cols-[1fr_auto_auto] gap-4 py-2 text-sm">
                <span className="font-medium text-ink">{cap(row.category)} <span className="text-muted">({row.bill_count})</span></span>
                <span className="text-muted">{money(row.fortnightly_total)}/fortnight</span>
                <span className="font-semibold text-ink">{money(row.annual_total)}/year</span>
              </div>
            ))}
          </div>
        )}
      </Card>

      <Card className="p-4">
        <h2 className="font-bold text-ink">Data tools</h2>
        <p className="mt-1 text-sm text-muted">Download readable copies or preview a CSV/XLSX bill import before anything is saved.</p>
        <div className="mt-4 flex flex-wrap gap-2">
          {[
            ['Bills CSV', 'bills'],
            ['Purchases CSV', 'purchases'],
            ['Income CSV', 'income'],
            ['Buckets CSV', 'buckets'],
          ].map(([label, kind]) => (
            <a key={kind} href={`/api/v1/solace/export/${kind}.csv`} className="inline-flex min-h-9 items-center rounded-lg border border-line px-3 text-sm font-medium text-ink hover:bg-sunken">
              {label}
            </a>
          ))}
          <a href="/api/v1/solace/export/backup.xlsx" className="inline-flex min-h-9 items-center rounded-lg bg-primary px-3 text-sm font-semibold text-white hover:opacity-90">
            Full XLSX backup
          </a>
        </div>
        <div className="mt-5 border-t border-line pt-4">
          <h3 className="font-semibold text-ink">Import recurring bills</h3>
          <div className="mt-3 flex flex-col gap-2 sm:flex-row">
            <input
              type="file"
              accept=".csv,.xlsx"
              className="min-w-0 flex-1 rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink"
              onChange={event => {
                setImportFile(event.target.files?.[0] || null)
                setImportPreview(null)
              }}
            />
            <Button onClick={previewImport} loading={saving === 'import-preview'} disabled={!importFile}>Preview import</Button>
          </div>
          {importPreview && (
            <div className="mt-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="text-sm text-muted">
                  {importPreview.ready_count} ready · {importPreview.error_count} with errors
                </p>
                <div className="flex gap-2">
                  <Button size="sm" onClick={confirmImport} loading={saving === 'import-confirm'} disabled={importPreview.ready_count === 0}>Import valid rows</Button>
                  <Button size="sm" variant="ghost" onClick={cancelImport} loading={saving === 'import-cancel'}>Cancel</Button>
                </div>
              </div>
              <div className="mt-3 max-h-80 overflow-auto rounded-lg border border-line">
                <table className="w-full min-w-[640px] text-left text-sm">
                  <thead className="sticky top-0 bg-sunken text-muted">
                    <tr><th className="p-2">Row</th><th className="p-2">Bill</th><th className="p-2">Amount</th><th className="p-2">Category</th><th className="p-2">Result</th></tr>
                  </thead>
                  <tbody className="divide-y divide-line">
                    {importPreview.rows.map(row => (
                      <tr key={row.source_row}>
                        <td className="p-2 text-muted">{row.source_row}</td>
                        <td className="p-2 font-medium text-ink">{row.name || 'Missing name'}</td>
                        <td className="p-2 text-ink">{money(row.amount || 0)}</td>
                        <td className="p-2 text-muted">{row.category || 'Other'}</td>
                        <td className="p-2">
                          {row.errors.length
                            ? <span className="text-danger">{row.errors.join('; ')}</span>
                            : <span className="text-success">Ready</span>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </Card>
    </div>
  )
}

export function CloseoutTab({ closeout, reload, onOccurrence, onError }: {
  closeout: SolaceCloseoutResponse | null
  reload: () => void
  onOccurrence: (id: number, action: 'paid' | 'unpaid' | 'skip') => Promise<unknown>
  onError: (message: string) => void
}) {
  const [notes, setNotes] = useState('')
  const [saving, setSaving] = useState(false)
  const [viewed, setViewed] = useState<SolaceCloseoutResponse | null>(closeout)
  useEffect(() => setViewed(closeout), [closeout])
  if (!viewed) return <EmptyState icon="🧾" title="Preparing cycle closeout" hint="Refresh Solace to calculate the current cycle." />
  const navigate = async (date?: string) => {
    setSaving(true)
    try {
      setViewed(date ? await api.getSolaceCloseout(date) : closeout)
    } catch (error) {
      onError(errMsg(error))
    } finally {
      setSaving(false)
    }
  }
  const act = async (action: 'close' | 'reopen') => {
    setSaving(true)
    try {
      await api.setSolaceCloseout(action, notes, viewed.plan.cycle_start)
      setViewed(await api.getSolaceCloseout(viewed.plan.cycle_start))
      reload()
    } catch (error) {
      onError(errMsg(error))
    } finally {
      setSaving(false)
    }
  }
  const occurrenceAction = async (id: number, action: 'paid' | 'unpaid' | 'skip') => {
    setSaving(true)
    try {
      await onOccurrence(id, action)
      setViewed(await api.getSolaceCloseout(viewed.plan.cycle_start))
      reload()
    } catch (error) {
      onError(errMsg(error))
    } finally {
      setSaving(false)
    }
  }
  return (
    <div className="space-y-4">
      <Card className="p-4">
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
          <div>
            <p className="text-sm text-muted">Current pay cycle</p>
            <h2 className="text-lg font-bold text-ink">
              {new Date(`${viewed.plan.cycle_start}T00:00:00`).toLocaleDateString()} – {new Date(`${viewed.plan.cycle_end}T00:00:00`).toLocaleDateString()}
            </h2>
            <p className="mt-1 text-xs text-muted">Bill window: {viewed.bill_window.start} to {viewed.bill_window.end}</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button size="sm" variant="ghost" disabled={saving} onClick={() => navigate()}>Current</Button>
            <Button
              size="sm"
              variant="ghost"
              disabled={saving}
              onClick={() => {
                const next = new Date(`${viewed.plan.cycle_end}T00:00:00`)
                next.setDate(next.getDate() + 1)
                void navigate(next.toISOString().slice(0, 10))
              }}
            >
              Next
            </Button>
            <Badge tone={viewed.closeout?.status === 'closed' ? 'success' : 'warning'}>
              {viewed.closeout?.status === 'closed' ? 'Closed' : 'Open'}
            </Badge>
          </div>
        </div>
      </Card>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {[
          ['Latest balance', viewed.latest_balance ? money(viewed.latest_balance.balance) : 'Not set'],
          ['Unpaid bills', money(viewed.summary.unpaid_total)],
          ['Projected balance', viewed.projected_balance === null ? 'Not available' : money(viewed.projected_balance)],
          ['Cycle income', money(viewed.plan.income_total)],
          ['Transfers done', `${viewed.summary.checklist_complete_count}/${viewed.summary.checklist_count}`],
        ].map(([label, value]) => (
          <Card key={label} className="p-4">
            <p className="text-xl font-extrabold text-ink">{value}</p>
            <p className="text-sm text-muted">{label}</p>
          </Card>
        ))}
      </div>
      <Card className="divide-y divide-line">
        {viewed.occurrences.length === 0 ? (
          <p className="p-4 text-sm text-muted">No bill occurrences fall in this cycle.</p>
        ) : viewed.occurrences.map(occurrence => (
          <div key={occurrence.id} className="flex flex-col justify-between gap-3 p-4 sm:flex-row sm:items-center">
            <div>
              <p className="font-semibold text-ink">{occurrence.bill_name}</p>
              <p className="text-sm text-muted">{new Date(occurrence.due_at).toLocaleDateString()} · {money(occurrence.amount)} · {cap(occurrence.status)}</p>
            </div>
            <div className="flex gap-2">
              {occurrence.status === 'upcoming' ? (
                <>
                  <Button size="sm" disabled={saving} onClick={() => occurrenceAction(occurrence.id, 'paid')}>Paid</Button>
                  <Button size="sm" variant="ghost" disabled={saving} onClick={() => occurrenceAction(occurrence.id, 'skip')}>Skip</Button>
                </>
              ) : (
                <Button size="sm" variant="ghost" disabled={saving} onClick={() => occurrenceAction(occurrence.id, 'unpaid')}>Restore unpaid</Button>
              )}
            </div>
          </div>
        ))}
      </Card>
      <Card className="p-4">
        <Field label="Closeout note">
          <Input value={notes} onChange={event => setNotes(event.target.value)} placeholder="Optional reconciliation note" />
        </Field>
        <div className="mt-3 flex gap-2">
          {viewed.closeout?.status === 'closed' ? (
            <Button variant="ghost" onClick={() => act('reopen')} loading={saving}>Reopen cycle</Button>
          ) : (
            <Button onClick={() => act('close')} loading={saving}>Close cycle</Button>
          )}
          {viewed.summary.unpaid_count > 0 && <p className="self-center text-sm text-muted">{viewed.summary.unpaid_count} bill(s) remain unpaid; this will be recorded in the closeout snapshot.</p>}
        </div>
      </Card>
    </div>
  )
}
