import { useEffect, useMemo, useState } from 'react'
import { api } from '../../../../api/client'
import type { MeridianCategory, MeridianTask, MeridianTaskCompletion, Person } from '../../../../api/types'
import { Card } from '../../../../components/Card'
import { Button } from '../../../../components/Button'
import { fieldClass } from '../../../../components/ui'
import { AssigneeSelect, assigneeLabel } from '../../../../components/AssigneeSelect'
import { useUrlAction } from '../../../../hooks/useUrlTab'
import { confirmDialog, promptDialog } from '../../../../components/Dialogs'

/** One wording for sending a submission back, on the phone keyboard rather than a system box. */
const askRejectionReason = () => promptDialog({
  title: 'Send this back?', label: 'Reason (optional)',
  placeholder: 'What needs doing differently?', confirmLabel: 'Send back',
})

type TaskFilter = 'all' | 'active' | 'pending' | 'hidden' | 'hot'

// Adopt the shared field look (single source of truth) so Meridian inputs match every node.
const inputClass = fieldClass

// Weekly recurrence as RRULE (D8): a repeating task re-arms on the chosen weekdays.
const WEEKDAYS: { code: string; label: string }[] = [
  { code: 'MO', label: 'Mon' }, { code: 'TU', label: 'Tue' }, { code: 'WE', label: 'Wed' },
  { code: 'TH', label: 'Thu' }, { code: 'FR', label: 'Fri' }, { code: 'SA', label: 'Sat' }, { code: 'SU', label: 'Sun' },
]

function parseByday(rule: string): string[] {
  const m = /BYDAY=([A-Z,]+)/.exec(rule || '')
  return m ? m[1].split(',').filter(Boolean) : []
}
function buildRrule(days: string[]): string {
  return days.length ? `FREQ=WEEKLY;BYDAY=${days.join(',')}` : ''
}

function WeekdayPicker({ days, onChange }: { days: string[]; onChange: (d: string[]) => void }) {
  const toggle = (code: string) =>
    onChange(days.includes(code) ? days.filter(d => d !== code) : [...days, code])
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <span className="text-xs text-muted mr-1">Repeats weekly on</span>
      {WEEKDAYS.map(d => (
        <button
          key={d.code}
          type="button"
          onClick={() => toggle(d.code)}
          className={`h-8 w-9 rounded-lg text-xs font-semibold transition-colors ${
            days.includes(d.code) ? 'bg-primary text-white' : 'bg-sunken text-muted hover:text-ink'
          }`}
        >
          {d.label}
        </button>
      ))}
      {days.length > 0 && (
        <button type="button" onClick={() => onChange([])} className="ml-1 text-xs text-muted hover:text-danger">clear</button>
      )}
    </div>
  )
}

function Badge({ children, className = 'bg-sunken text-muted-strong' }: { children: React.ReactNode; className?: string }) {
  return <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${className}`}>{children}</span>
}

export function TasksTab({ canManage, pointsLabel, searchQuery = '' }: {
  canManage: boolean
  pointsLabel: string
  searchQuery?: string
}) {
  const [tasks, setTasks] = useState<MeridianTask[]>([])
  const [categories, setCategories] = useState<MeridianCategory[]>([])
  const [people, setPeople] = useState<Person[]>([])
  const [completions, setCompletions] = useState<MeridianTaskCompletion[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<TaskFilter>('active')
  const [categoryId, setCategoryId] = useState('')
  const [personId, setPersonId] = useState('')
  const [showForm, setShowForm] = useState(false)
  useUrlAction('task', () => setShowForm(true))
  const [editingId, setEditingId] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)

  const reload = async () => {
    setError(null)
    try {
      const [taskRows, cats, personRows, completionRows] = await Promise.all([
        api.getMeridianTasks(),
        api.getMeridianCategories('task').catch(() => []),
        api.getPeople().catch(() => []),
        canManage ? api.getMeridianTaskCompletions().catch(() => []) : Promise.resolve([]),
      ])
      setTasks(taskRows)
      setCategories(cats)
      setPeople(personRows)
      setCompletions(completionRows)
    } catch {
      setError('Tasks could not be refreshed.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { reload() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const catName = (id: number | null) => categories.find(c => c.id === id)?.name || ''
  // Assignment is a set: name one person, or say how many share it.
  const peopleNames = (ids: number[]) => assigneeLabel(people, ids).replace('Whole family', '')

  const pendingByTask = useMemo(() => {
    const map = new Map<number, MeridianTaskCompletion[]>()
    completions.filter(c => c.status === 'submitted').forEach(c => {
      map.set(c.task_id, [...(map.get(c.task_id) || []), c])
    })
    return map
  }, [completions])

  const visible = useMemo(() => tasks.filter(t => {
    const query = searchQuery.trim().toLowerCase()
    if (query && !`${t.title} ${t.description}`.toLowerCase().includes(query)) return false
    if (filter === 'active' && (!t.is_active || t.is_archived)) return false
    if (filter === 'pending' && !pendingByTask.has(t.id) && t.status !== 'pending') return false
    if (filter === 'hidden' && t.is_active && !t.is_archived) return false
    if (filter === 'hot' && !t.is_hot) return false
    if (categoryId && t.category_id !== Number(categoryId)) return false
    if (personId && !t.assigned_to_person_ids.includes(Number(personId))) return false
    return true
  }), [tasks, filter, categoryId, personId, pendingByTask, searchQuery])

  const setFailure = () => setError('That change did not save. Refresh and try again.')

  const act = async (work: Promise<unknown>) => {
    setError(null)
    try {
      await work
      await reload()
    } catch {
      setFailure()
    }
  }

  if (loading) return <div className="h-32 rounded-2xl bg-sunken animate-pulse" />

  if (!canManage) {
    return (
      <SelfServiceTasks
        tasks={visible}
        people={people}
        pointsLabel={pointsLabel}
        reload={reload}
      />
    )
  }

  return (
    <div className="flex flex-col gap-4">
      {error && (
        <div className="rounded-xl border border-danger/30 bg-danger-soft px-4 py-3 text-sm text-danger">
          {error}
        </div>
      )}

      <Card>
        <div className="grid grid-cols-2 gap-3 sm:flex sm:flex-wrap sm:items-end">
          <label className="col-span-2 flex flex-col gap-1 text-sm sm:col-span-1">
            <span className="text-muted font-medium">View</span>
            <select value={filter} onChange={e => setFilter(e.target.value as TaskFilter)} className={inputClass}>
              <option value="active">Active tasks</option>
              <option value="pending">Needs approval</option>
              <option value="hot">Hot tasks</option>
              <option value="hidden">Hidden or archived</option>
              <option value="all">All tasks</option>
            </select>
          </label>
          <label className="flex min-w-0 flex-col gap-1 text-sm">
            <span className="text-muted font-medium">Category</span>
            <select value={categoryId} onChange={e => setCategoryId(e.target.value)} className={inputClass}>
              <option value="">All categories</option>
              {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </label>
          <label className="flex min-w-0 flex-col gap-1 text-sm">
            <span className="text-muted font-medium">Assigned to</span>
            <select value={personId} onChange={e => setPersonId(e.target.value)} className={inputClass}>
              <option value="">Anyone</option>
              {people.map(p => <option key={p.id} value={p.id}>{p.display_name}</option>)}
            </select>
          </label>
          {(filter !== 'active' || categoryId || personId) && (
            <Button size="sm" variant="ghost" className="w-full sm:w-auto" onClick={() => { setFilter('active'); setCategoryId(''); setPersonId('') }}>
              Clear
            </Button>
          )}
          <Button size="sm" className="col-start-2 w-full sm:ml-auto sm:w-auto" onClick={() => setShowForm(s => !s)}>
            {showForm ? 'Close' : 'New task'}
          </Button>
        </div>
      </Card>

      {showForm && (
        <NewTaskForm
          categories={categories}
          people={people}
          onCreated={() => { setShowForm(false); reload() }}
          onError={setFailure}
        />
      )}

      <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_360px] gap-4">
        <Card title="Task management">
          {visible.length === 0 ? (
            <p className="text-sm text-muted py-4">No tasks match these filters.</p>
          ) : (
            <>
              <div className="flex flex-col gap-3 lg:hidden">
                {visible.map(task => (
                  editingId === task.id ? (
                    <TaskEditForm
                      key={task.id}
                      task={task}
                      categories={categories}
                      people={people}
                      onCancel={() => setEditingId(null)}
                      onSaved={() => { setEditingId(null); reload() }}
                      onError={setFailure}
                    />
                  ) : (
                    <TaskMobileCard
                      key={task.id}
                      task={task}
                      pending={pendingByTask.get(task.id) || []}
                      pointsLabel={pointsLabel}
                      categoryName={catName(task.category_id)}
                      personName={peopleNames(task.assigned_to_person_ids)}
                      onEdit={() => setEditingId(task.id)}
                      onToggleActive={() => act(api.updateMeridianTask(task.id, { is_active: !task.is_active }))}
                      onArchive={() => act(api.updateMeridianTask(task.id, { is_archived: !task.is_archived }))}
                      onDelete={async () => { if ((await confirmDialog({ title: `Delete "${task.title}"?`, confirmLabel: 'Delete' }))) act(api.deleteMeridianTask(task.id)) }}
                      onApprove={(id) => act(api.approveMeridianTaskCompletion(id))}
                      onReject={async (id) => { const reason = await askRejectionReason(); if (reason !== null) act(api.rejectMeridianTaskCompletion(id, reason)) }}
                    />
                  )
                ))}
              </div>
              <div className="hidden overflow-x-auto lg:block">
              <table className="w-full min-w-[780px] text-sm">
                <thead>
                  <tr className="border-b border-line text-left text-xs font-semibold uppercase tracking-wide text-muted">
                    <th className="py-2 pr-3">Task</th>
                    <th className="py-2 pr-3">Owner</th>
                    <th className="py-2 pr-3">Value</th>
                    <th className="py-2 pr-3">Status</th>
                    <th className="py-2 pr-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line/70">
                  {visible.map(task => (
                    editingId === task.id ? (
                      <TaskEditRow
                        key={task.id}
                        task={task}
                        categories={categories}
                        people={people}
                        onCancel={() => setEditingId(null)}
                        onSaved={() => { setEditingId(null); reload() }}
                        onError={setFailure}
                      />
                    ) : (
                      <TaskRow
                        key={task.id}
                        task={task}
                        pending={pendingByTask.get(task.id) || []}
                        pointsLabel={pointsLabel}
                        categoryName={catName(task.category_id)}
                        personName={peopleNames(task.assigned_to_person_ids)}
                        onEdit={() => setEditingId(task.id)}
                        onToggleActive={() => act(api.updateMeridianTask(task.id, { is_active: !task.is_active }))}
                        onArchive={() => act(api.updateMeridianTask(task.id, { is_archived: !task.is_archived }))}
                        onDelete={async () => { if ((await confirmDialog({ title: `Delete "${task.title}"?`, confirmLabel: 'Delete' }))) act(api.deleteMeridianTask(task.id)) }}
                        onApprove={(id) => act(api.approveMeridianTaskCompletion(id))}
                        onReject={async (id) => { const reason = await askRejectionReason(); if (reason !== null) act(api.rejectMeridianTaskCompletion(id, reason)) }}
                      />
                    )
                  ))}
                </tbody>
              </table>
              </div>
            </>
          )}
        </Card>

        <Card title="Recent completions">
          {completions.length === 0 ? (
            <p className="text-sm text-muted py-3">No task completion history yet.</p>
          ) : (
            <ul className="divide-y divide-line/70">
              {completions.slice(0, 10).map(c => (
                <li key={c.id} className="py-2">
                  <div className="flex items-start gap-2">
                    <StatusDot status={c.status} />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-semibold text-ink">{c.task_title}</p>
                      <p className="text-xs text-muted">
                        {c.person_display_name || people.find(p => p.id === c.person_id)?.display_name || ''} · {statusLabel(c.status)} · {formatWhen(c.reviewed_at || c.submitted_at)}
                      </p>
                      {c.rejection_reason && <p className="mt-1 text-xs text-danger">{c.rejection_reason}</p>}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </div>
  )
}

function TaskMobileCard({
  task,
  pending,
  pointsLabel,
  categoryName,
  personName,
  onEdit,
  onToggleActive,
  onArchive,
  onDelete,
  onApprove,
  onReject,
}: {
  task: MeridianTask
  pending: MeridianTaskCompletion[]
  pointsLabel: string
  categoryName: string
  personName: string
  onEdit: () => void
  onToggleActive: () => void
  onArchive: () => void
  onDelete: () => void
  onApprove: (completionId: number) => void
  onReject: (completionId: number) => void
}) {
  return (
    <article className="rounded-2xl border border-line bg-surface p-3.5 shadow-soft">
      <div className="flex items-start gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <h3 className="min-w-0 flex-1 break-words font-extrabold text-ink">{task.title}</h3>
            {task.is_archived
              ? <Badge>Archived</Badge>
              : task.is_active
                ? <Badge className="bg-success-soft text-success">Active</Badge>
                : <Badge>Hidden</Badge>}
          </div>
          <p className="mt-1 text-xs text-muted">{personName || 'Anyone'}{categoryName ? ` · ${categoryName}` : ''}</p>
        </div>
        <div className="flex-shrink-0 rounded-xl bg-primary-soft px-2.5 py-1.5 text-right text-primary">
          <span className="block text-base font-black leading-none">★ {task.award_value}</span>
          <span className="text-[9px] font-bold uppercase tracking-wide">{pointsLabel}</span>
        </div>
      </div>

      <div className="mt-2 flex flex-wrap gap-1.5">
        {task.is_hot && <Badge className="bg-danger-soft text-danger">{task.hot_label || 'Hot'}</Badge>}
        <Badge>{task.completion_behavior === 'hide_after_approval' ? 'One-off' : 'Repeatable'}</Badge>
        <Badge>{task.completion_scope === 'household' ? 'Household' : 'Per person'}</Badge>
        {task.recurrence_rule && (
          <Badge className="bg-primary-soft text-primary">↻ {parseByday(task.recurrence_rule).map(d => WEEKDAYS.find(w => w.code === d)?.label).join(' ')}</Badge>
        )}
        {task.status !== 'available' && <Badge className="bg-warning-soft text-warning">{task.status}</Badge>}
      </div>

      {task.description && <p className="mt-2 text-sm leading-relaxed text-muted line-clamp-3">{task.description}</p>}

      {pending.length > 0 && (
        <div className="mt-3 flex flex-col gap-2">
          {pending.map(completion => (
            <div key={completion.id} className="rounded-xl bg-warning-soft p-2.5 text-xs text-warning">
              <p><strong>{completion.person_display_name}</strong> submitted {formatWhen(completion.submitted_at)}</p>
              <div className="mt-2 grid grid-cols-2 gap-2">
                <button className="min-h-10 rounded-lg bg-warning px-2 font-bold text-white" onClick={() => onApprove(completion.id)}>Approve</button>
                <button className="min-h-10 rounded-lg border border-warning/30 px-2 font-bold" onClick={() => onReject(completion.id)}>Reject</button>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="mt-3 grid grid-cols-2 gap-2 border-t border-line pt-3">
        <Button size="sm" variant="secondary" onClick={onEdit}>Edit task</Button>
        <details className="group relative">
          <summary className="grid min-h-10 cursor-pointer list-none place-items-center rounded-xl text-sm font-semibold text-muted-strong hover:bg-sunken">More</summary>
          <div className="mt-2 grid grid-cols-3 gap-1.5 rounded-xl bg-sunken p-2">
            <button className="min-h-10 rounded-lg px-1 text-xs font-semibold text-muted-strong hover:bg-surface" onClick={onToggleActive}>{task.is_active ? 'Hide' : 'Show'}</button>
            <button className="min-h-10 rounded-lg px-1 text-xs font-semibold text-muted-strong hover:bg-surface" onClick={onArchive}>{task.is_archived ? 'Restore' : 'Archive'}</button>
            <button className="min-h-10 rounded-lg px-1 text-xs font-semibold text-danger hover:bg-danger-soft" onClick={onDelete}>Delete</button>
          </div>
        </details>
      </div>
    </article>
  )
}

function TaskRow({
  task,
  pending,
  pointsLabel,
  categoryName,
  personName,
  onEdit,
  onToggleActive,
  onArchive,
  onDelete,
  onApprove,
  onReject,
}: {
  task: MeridianTask
  pending: MeridianTaskCompletion[]
  pointsLabel: string
  categoryName: string
  personName: string
  onEdit: () => void
  onToggleActive: () => void
  onArchive: () => void
  onDelete: () => void
  onApprove: (completionId: number) => void
  onReject: (completionId: number) => void
}) {
  return (
    <tr className="align-top">
      <td className="py-3 pr-3">
        <div className="font-semibold text-ink">{task.title}</div>
        <div className="mt-1 flex flex-wrap gap-1.5">
          {task.is_hot && <Badge className="bg-danger-soft text-danger">Hot</Badge>}
          {categoryName && <Badge>{categoryName}</Badge>}
          <Badge>{task.completion_behavior === 'hide_after_approval' ? 'One-off' : 'Repeatable'}</Badge>
          <Badge>{task.completion_scope === 'household' ? 'Household' : 'Per person'}</Badge>
          {task.recurrence_rule && (
            <Badge className="bg-primary-soft text-primary">↻ {parseByday(task.recurrence_rule).map(d => WEEKDAYS.find(w => w.code === d)?.label).join(' ')}</Badge>
          )}
        </div>
        {task.description && <p className="mt-1 max-w-xl text-xs text-muted line-clamp-2">{task.description}</p>}
        {pending.length > 0 && (
          <div className="mt-2 flex flex-col gap-1.5">
            {pending.map(c => (
              <div key={c.id} className="flex flex-wrap items-center gap-2 rounded-lg bg-warning-soft px-2 py-1 text-xs text-warning">
                <span className="font-semibold">{c.person_display_name}</span>
                <span>submitted {formatWhen(c.submitted_at)}</span>
                <button className="font-semibold underline" onClick={() => onApprove(c.id)}>Approve</button>
                <button className="font-semibold underline" onClick={() => onReject(c.id)}>Reject</button>
              </div>
            ))}
          </div>
        )}
      </td>
      <td className="py-3 pr-3 text-muted-strong">{personName || 'Anyone'}</td>
      <td className="py-3 pr-3">
        <span className="font-bold text-primary">★ {task.award_value}</span>
        <span className="ml-1 text-xs text-muted">{pointsLabel}</span>
        {task.is_hot && task.hot_bonus_points > 0 && (
          <div className="text-xs text-muted">Base {task.points} + {task.hot_bonus_points}</div>
        )}
      </td>
      <td className="py-3 pr-3">
        <div className="flex flex-wrap gap-1.5">
          {task.is_archived ? <Badge>Archived</Badge> : task.is_active ? <Badge className="bg-success-soft text-success">Active</Badge> : <Badge>Hidden</Badge>}
          {task.status !== 'available' && <Badge className="bg-warning-soft text-warning">{task.status}</Badge>}
        </div>
      </td>
      <td className="py-3 pr-0">
        <div className="flex justify-end gap-1.5">
          <Button size="sm" variant="ghost" onClick={onEdit}>Edit</Button>
          <Button size="sm" variant="ghost" onClick={onToggleActive}>{task.is_active ? 'Hide' : 'Show'}</Button>
          <Button size="sm" variant="ghost" onClick={onArchive}>{task.is_archived ? 'Unarchive' : 'Archive'}</Button>
          <Button size="sm" variant="ghost" onClick={onDelete}>Delete</Button>
        </div>
      </td>
    </tr>
  )
}

interface TaskEditProps {
  task: MeridianTask
  categories: MeridianCategory[]
  people: Person[]
  onCancel: () => void
  onSaved: () => void
  onError: () => void
}

function TaskEditForm({ task, categories, people, onCancel, onSaved, onError }: TaskEditProps) {
  const [f, setF] = useState({
    title: task.title,
    points: String(task.points),
    description: task.description,
    category_id: task.category_id ? String(task.category_id) : '',
    assigned_to_person_ids: task.assigned_to_person_ids,
    is_hot: task.is_hot,
    hot_bonus_points: String(task.hot_bonus_points),
    hot_label: task.hot_label,
    completion_behavior: task.completion_behavior,
    completion_scope: task.completion_scope,
  })
  const [recurDays, setRecurDays] = useState<string[]>(parseByday(task.recurrence_rule))
  const [saving, setSaving] = useState(false)
  const set = (key: string, value: unknown) => setF(prev => ({ ...prev, [key]: value }))

  const save = async () => {
    if (!f.title.trim()) return
    setSaving(true)
    try {
      await api.updateMeridianTask(task.id, {
        title: f.title.trim(),
        points: Number(f.points) || 0,
        description: f.description,
        category_id: f.category_id ? Number(f.category_id) : null,
        assigned_to_person_ids: f.assigned_to_person_ids,
        is_hot: f.is_hot,
        hot_bonus_points: Number(f.hot_bonus_points) || 0,
        hot_label: f.hot_label,
        completion_behavior: f.completion_behavior,
        completion_scope: f.completion_scope,
        recurrence_rule: buildRrule(recurDays),
      })
      onSaved()
    } catch {
      onError()
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="rounded-2xl border border-primary/30 bg-primary-soft/30 p-3">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h3 className="text-sm font-extrabold text-ink">Edit task</h3>
        <button type="button" onClick={onCancel} className="grid h-9 w-9 place-items-center rounded-xl text-muted hover:bg-surface" aria-label="Close task editor">✕</button>
      </div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
            <label className="flex flex-col gap-1 text-xs font-semibold text-muted md:col-span-2">Task name
              <input className={inputClass} value={f.title} onChange={e => set('title', e.target.value)} />
            </label>
            <label className="flex flex-col gap-1 text-xs font-semibold text-muted">Points
              <input className={inputClass} type="number" min="0" value={f.points} onChange={e => set('points', e.target.value)} />
            </label>
            <label className="flex flex-col gap-1 text-xs font-semibold text-muted">Assigned to
              <AssigneeSelect
                people={people}
                value={f.assigned_to_person_ids}
                onChange={ids => set('assigned_to_person_ids', ids)}
              />
            </label>
            <label className="flex flex-col gap-1 text-xs font-semibold text-muted md:col-span-2">Description
              <textarea className={inputClass} value={f.description} onChange={e => set('description', e.target.value)} />
            </label>
            <label className="flex flex-col gap-1 text-xs font-semibold text-muted">Category
              <select className={inputClass} value={f.category_id} onChange={e => set('category_id', e.target.value)}>
                <option value="">No category</option>
                {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </label>
            <label className="flex flex-col gap-1 text-xs font-semibold text-muted">Completion
              <select className={inputClass} value={f.completion_behavior} onChange={e => set('completion_behavior', e.target.value as MeridianTask['completion_behavior'])}>
                <option value="stay_active">Repeatable</option>
                <option value="hide_after_approval">One-off</option>
              </select>
            </label>
            <label className="flex flex-col gap-1 text-xs font-semibold text-muted">Completion scope
              <select className={inputClass} value={f.completion_scope} onChange={e => set('completion_scope', e.target.value as MeridianTask['completion_scope'])}>
                <option value="per_person">Per person</option>
                <option value="household">Household</option>
              </select>
            </label>
            <label className="flex min-h-11 items-center gap-2 text-sm font-semibold text-ink">
              <input type="checkbox" checked={f.is_hot} onChange={e => set('is_hot', e.target.checked)} /> Hot task
            </label>
            {f.is_hot && (
              <>
                <label className="flex flex-col gap-1 text-xs font-semibold text-muted">Bonus points
                  <input className={inputClass} type="number" min="0" value={f.hot_bonus_points} onChange={e => set('hot_bonus_points', e.target.value)} />
                </label>
                <label className="flex flex-col gap-1 text-xs font-semibold text-muted">Hot label
                  <input className={inputClass} placeholder="Extra credit" value={f.hot_label} onChange={e => set('hot_label', e.target.value)} />
                </label>
              </>
            )}
          </div>
          {f.completion_behavior === 'stay_active' && (
            <div className="mt-3"><WeekdayPicker days={recurDays} onChange={setRecurDays} /></div>
          )}
          <div className="mt-3 grid grid-cols-2 gap-2 sm:flex">
            <Button size="sm" loading={saving} disabled={!f.title.trim()} onClick={save}>Save changes</Button>
            <Button size="sm" variant="ghost" onClick={onCancel}>Cancel</Button>
          </div>
    </div>
  )
}

function TaskEditRow(props: TaskEditProps) {
  return (
    <tr>
      <td colSpan={5} className="py-3">
        <TaskEditForm {...props} />
      </td>
    </tr>
  )
}

function NewTaskForm({ categories, people, onCreated, onError }: {
  categories: MeridianCategory[]
  people: Person[]
  onCreated: () => void
  onError: () => void
}) {
  const [f, setF] = useState({
    title: '', points: '5', description: '', category_id: '', assigned_to_person_ids: [] as number[],
    is_hot: false, hot_bonus_points: '0', hot_label: '',
    completion_behavior: 'stay_active' as MeridianTask['completion_behavior'],
    completion_scope: 'per_person' as MeridianTask['completion_scope'],
  })
  const [recurDays, setRecurDays] = useState<string[]>([])
  const [saving, setSaving] = useState(false)
  const set = (k: string, v: unknown) => setF(prev => ({ ...prev, [k]: v }))

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!f.title.trim()) return
    setSaving(true)
    try {
      await api.createMeridianTask({
        title: f.title.trim(),
        points: Number(f.points) || 0,
        description: f.description,
        is_hot: f.is_hot,
        hot_bonus_points: Number(f.hot_bonus_points) || 0,
        hot_label: f.hot_label,
        completion_behavior: f.completion_behavior,
        completion_scope: f.completion_scope,
        category_id: f.category_id ? Number(f.category_id) : null,
        assigned_to_person_ids: f.assigned_to_person_ids,
        recurrence_rule: buildRrule(recurDays),
      })
      onCreated()
    } catch {
      onError()
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card title="New task">
      <form onSubmit={submit} className="flex flex-col gap-3">
        <div className="grid grid-cols-2 gap-3">
          <label className="col-span-2 flex flex-col gap-1 text-xs font-semibold text-muted">Task name
            <input className={inputClass} placeholder="e.g. Empty the dishwasher" value={f.title} onChange={e => set('title', e.target.value)} autoFocus />
          </label>
          <label className="flex min-w-0 flex-col gap-1 text-xs font-semibold text-muted">Points
            <input className={inputClass} type="number" min="0" value={f.points} onChange={e => set('points', e.target.value)} />
          </label>
          <label className="flex min-w-0 flex-col gap-1 text-xs font-semibold text-muted">Who can do it
            <AssigneeSelect
              people={people}
              value={f.assigned_to_person_ids}
              onChange={ids => set('assigned_to_person_ids', ids)}
            />
          </label>
        </div>

        <details className="group rounded-xl border border-line">
          <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between px-3 text-sm font-semibold text-muted-strong">
            Schedule, category and other options
            <span className="text-xs transition-transform group-open:rotate-180">▾</span>
          </summary>
          <div className="grid grid-cols-1 gap-3 border-t border-line p-3 sm:grid-cols-2 xl:grid-cols-4">
            <label className="flex flex-col gap-1 text-xs font-semibold text-muted sm:col-span-2">Description
              <textarea className={inputClass} placeholder="Optional instructions" value={f.description} onChange={e => set('description', e.target.value)} />
            </label>
            <label className="flex flex-col gap-1 text-xs font-semibold text-muted">Category
              <select className={inputClass} value={f.category_id} onChange={e => set('category_id', e.target.value)}>
                <option value="">No category</option>
                {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </label>
            <label className="flex flex-col gap-1 text-xs font-semibold text-muted">Task type
              <select className={inputClass} value={f.completion_behavior} onChange={e => set('completion_behavior', e.target.value as MeridianTask['completion_behavior'])}>
                <option value="stay_active">Repeatable</option>
                <option value="hide_after_approval">One-off</option>
              </select>
            </label>
            <label className="flex flex-col gap-1 text-xs font-semibold text-muted">Completion scope
              <select className={inputClass} value={f.completion_scope} onChange={e => set('completion_scope', e.target.value as MeridianTask['completion_scope'])}>
                <option value="per_person">Per person</option>
                <option value="household">Household</option>
              </select>
            </label>
            <label className="flex min-h-11 items-center gap-2 text-sm font-semibold text-ink">
              <input type="checkbox" checked={f.is_hot} onChange={e => set('is_hot', e.target.checked)} /> Hot task
            </label>
            {f.is_hot && (
              <>
                <label className="flex flex-col gap-1 text-xs font-semibold text-muted">Bonus points
                  <input className={inputClass} type="number" min="0" value={f.hot_bonus_points} onChange={e => set('hot_bonus_points', e.target.value)} />
                </label>
                <label className="flex flex-col gap-1 text-xs font-semibold text-muted">Hot label
                  <input className={inputClass} placeholder="Extra credit" value={f.hot_label} onChange={e => set('hot_label', e.target.value)} />
                </label>
              </>
            )}
            {f.completion_behavior === 'stay_active' && (
              <div className="sm:col-span-2 xl:col-span-4"><WeekdayPicker days={recurDays} onChange={setRecurDays} /></div>
            )}
          </div>
        </details>

        <Button type="submit" loading={saving} disabled={!f.title.trim()} className="w-full sm:w-auto sm:self-start">Create task</Button>
      </form>
    </Card>
  )
}

function SelfServiceTasks({ tasks, people, pointsLabel, reload }: {
  tasks: MeridianTask[]
  people: Person[]
  pointsLabel: string
  reload: () => void
}) {
  // Assignment is a set: name one person, or say how many share it.
  const peopleNames = (ids: number[]) => assigneeLabel(people, ids).replace('Whole family', '')
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      {tasks.map(task => (
        <Card key={task.id}>
          <div className="flex flex-col gap-3">
            <div>
              <h3 className="font-bold text-ink">{task.title}</h3>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {task.is_hot && <Badge className="bg-danger-soft text-danger">Hot</Badge>}
                {task.assigned_to_person_ids.length > 0 && <Badge>For {peopleNames(task.assigned_to_person_ids)}</Badge>}
                {task.status === 'pending' && <Badge className="bg-warning-soft text-warning">Awaiting approval</Badge>}
              </div>
            </div>
            {task.description && <p className="text-sm text-muted">{task.description}</p>}
            <div className="mt-auto">
              <p className="mb-2 text-sm font-bold text-primary">★ {task.award_value} {pointsLabel}</p>
              {task.status === 'available' ? (
                <CompleteControls task={task} people={people} onDone={reload} />
              ) : (
                <Button size="sm" variant="secondary" disabled className="w-full">Awaiting approval</Button>
              )}
            </div>
          </div>
        </Card>
      ))}
      {tasks.length === 0 && <p className="text-sm text-muted text-center py-8 md:col-span-2 xl:col-span-3">No tasks available.</p>}
    </div>
  )
}

function CompleteControls({ task, people, onDone }: {
  task: MeridianTask
  people: Person[]
  onDone: () => void
}) {
  const [busy, setBusy] = useState(false)
  const complete = async (personId?: number) => {
    setBusy(true)
    try { await api.completeMeridianTask(task.id, personId) } finally { setBusy(false); onDone() }
  }
  // An unassigned task is open to anyone; an assigned one only to the people named on it.
  const candidates = task.assigned_to_person_ids.length > 0
    ? people.filter(p => task.assigned_to_person_ids.includes(p.id))
    : people.filter(p => p.linked_user_id || p.profile_type === 'child')

  if (candidates.length > 1) {
    return (
      <div className="flex flex-wrap gap-2">
        {candidates.slice(0, 4).map(p => (
          <Button key={p.id} size="sm" variant="secondary" loading={busy} onClick={() => complete(p.id)}>
            {p.display_name}
          </Button>
        ))}
      </div>
    )
  }
  return <Button size="sm" loading={busy} className="w-full" onClick={() => complete(candidates[0]?.id)}>Submit as complete</Button>
}

function StatusDot({ status }: { status: MeridianTaskCompletion['status'] }) {
  const cls = status === 'approved' ? 'bg-success' : status === 'rejected' ? 'bg-danger' : 'bg-warning'
  return <span className={`mt-1 h-2.5 w-2.5 rounded-full ${cls}`} />
}

function statusLabel(status: MeridianTaskCompletion['status']) {
  if (status === 'submitted') return 'submitted'
  if (status === 'approved') return 'approved'
  return 'rejected'
}

function formatWhen(value: string | null) {
  if (!value) return ''
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleString([], { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })
}
