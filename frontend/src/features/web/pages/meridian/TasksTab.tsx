import { useEffect, useMemo, useState } from 'react'
import { api } from '../../../../api/client'
import type { MeridianCategory, MeridianTask, MeridianTaskCompletion, Person } from '../../../../api/types'
import { Card } from '../../../../components/Card'
import { Button } from '../../../../components/Button'

type TaskFilter = 'all' | 'active' | 'pending' | 'hidden' | 'hot'

const inputClass = 'px-3 py-2 rounded-xl border border-line bg-raised text-sm text-ink placeholder-muted outline-none focus:ring-2 focus:ring-primary'

function Badge({ children, className = 'bg-sunken text-muted-strong' }: { children: React.ReactNode; className?: string }) {
  return <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${className}`}>{children}</span>
}

export function TasksTab({ canManage, pointsLabel }: { canManage: boolean; pointsLabel: string }) {
  const [tasks, setTasks] = useState<MeridianTask[]>([])
  const [categories, setCategories] = useState<MeridianCategory[]>([])
  const [people, setPeople] = useState<Person[]>([])
  const [completions, setCompletions] = useState<MeridianTaskCompletion[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<TaskFilter>('active')
  const [categoryId, setCategoryId] = useState('')
  const [personId, setPersonId] = useState('')
  const [showForm, setShowForm] = useState(false)
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
  const personName = (id: number | null) => people.find(p => p.id === id)?.display_name || ''

  const pendingByTask = useMemo(() => {
    const map = new Map<number, MeridianTaskCompletion[]>()
    completions.filter(c => c.status === 'submitted').forEach(c => {
      map.set(c.task_id, [...(map.get(c.task_id) || []), c])
    })
    return map
  }, [completions])

  const visible = useMemo(() => tasks.filter(t => {
    if (filter === 'active' && (!t.is_active || t.is_archived)) return false
    if (filter === 'pending' && !pendingByTask.has(t.id) && t.status !== 'pending') return false
    if (filter === 'hidden' && t.is_active && !t.is_archived) return false
    if (filter === 'hot' && !t.is_hot) return false
    if (categoryId && t.category_id !== Number(categoryId)) return false
    if (personId && t.assigned_to_person_id !== Number(personId)) return false
    return true
  }), [tasks, filter, categoryId, personId, pendingByTask])

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
        <div className="flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-muted font-medium">View</span>
            <select value={filter} onChange={e => setFilter(e.target.value as TaskFilter)} className={inputClass}>
              <option value="active">Active tasks</option>
              <option value="pending">Needs approval</option>
              <option value="hot">Hot tasks</option>
              <option value="hidden">Hidden or archived</option>
              <option value="all">All tasks</option>
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-muted font-medium">Category</span>
            <select value={categoryId} onChange={e => setCategoryId(e.target.value)} className={inputClass}>
              <option value="">All categories</option>
              {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-muted font-medium">Assigned to</span>
            <select value={personId} onChange={e => setPersonId(e.target.value)} className={inputClass}>
              <option value="">Anyone</option>
              {people.map(p => <option key={p.id} value={p.id}>{p.display_name}</option>)}
            </select>
          </label>
          {(filter !== 'active' || categoryId || personId) && (
            <Button size="sm" variant="ghost" onClick={() => { setFilter('active'); setCategoryId(''); setPersonId('') }}>
              Clear
            </Button>
          )}
          <Button size="sm" className="ml-auto" onClick={() => setShowForm(s => !s)}>
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
            <div className="overflow-x-auto">
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
                        personName={personName(task.assigned_to_person_id)}
                        onEdit={() => setEditingId(task.id)}
                        onToggleActive={() => act(api.updateMeridianTask(task.id, { is_active: !task.is_active }))}
                        onArchive={() => act(api.updateMeridianTask(task.id, { is_archived: !task.is_archived }))}
                        onDelete={() => { if (confirm(`Delete "${task.title}"?`)) act(api.deleteMeridianTask(task.id)) }}
                        onApprove={(id) => act(api.approveMeridianTaskCompletion(id))}
                        onReject={(id) => act(api.rejectMeridianTaskCompletion(id, prompt('Reason (optional)') || ''))}
                      />
                    )
                  ))}
                </tbody>
              </table>
            </div>
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
                        {c.person_display_name || personName(c.person_id)} · {statusLabel(c.status)} · {formatWhen(c.reviewed_at || c.submitted_at)}
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

function TaskEditRow({ task, categories, people, onCancel, onSaved, onError }: {
  task: MeridianTask
  categories: MeridianCategory[]
  people: Person[]
  onCancel: () => void
  onSaved: () => void
  onError: () => void
}) {
  const [f, setF] = useState({
    title: task.title,
    points: String(task.points),
    description: task.description,
    category_id: task.category_id ? String(task.category_id) : '',
    assigned_to_person_id: task.assigned_to_person_id ? String(task.assigned_to_person_id) : '',
    is_hot: task.is_hot,
    hot_bonus_points: String(task.hot_bonus_points),
    hot_label: task.hot_label,
    completion_behavior: task.completion_behavior,
    completion_scope: task.completion_scope,
  })
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
        assigned_to_person_id: f.assigned_to_person_id ? Number(f.assigned_to_person_id) : null,
        is_hot: f.is_hot,
        hot_bonus_points: Number(f.hot_bonus_points) || 0,
        hot_label: f.hot_label,
        completion_behavior: f.completion_behavior,
        completion_scope: f.completion_scope,
      })
      onSaved()
    } catch {
      onError()
    } finally {
      setSaving(false)
    }
  }

  return (
    <tr>
      <td colSpan={5} className="py-3">
        <div className="rounded-xl border border-line bg-sunken p-3">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
            <input className={`${inputClass} md:col-span-2`} value={f.title} onChange={e => set('title', e.target.value)} />
            <input className={inputClass} type="number" min="0" value={f.points} onChange={e => set('points', e.target.value)} />
            <select className={inputClass} value={f.assigned_to_person_id} onChange={e => set('assigned_to_person_id', e.target.value)}>
              <option value="">Anyone</option>
              {people.map(p => <option key={p.id} value={p.id}>{p.display_name}</option>)}
            </select>
            <textarea className={`${inputClass} md:col-span-2`} value={f.description} onChange={e => set('description', e.target.value)} />
            <select className={inputClass} value={f.category_id} onChange={e => set('category_id', e.target.value)}>
              <option value="">No category</option>
              {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
            <select className={inputClass} value={f.completion_behavior} onChange={e => set('completion_behavior', e.target.value as MeridianTask['completion_behavior'])}>
              <option value="stay_active">Repeatable</option>
              <option value="hide_after_approval">One-off</option>
            </select>
            <select className={inputClass} value={f.completion_scope} onChange={e => set('completion_scope', e.target.value as MeridianTask['completion_scope'])}>
              <option value="per_person">Per person</option>
              <option value="household">Household</option>
            </select>
            <label className="flex items-center gap-2 text-sm text-ink">
              <input type="checkbox" checked={f.is_hot} onChange={e => set('is_hot', e.target.checked)} /> Hot
            </label>
            {f.is_hot && (
              <>
                <input className={inputClass} type="number" min="0" value={f.hot_bonus_points} onChange={e => set('hot_bonus_points', e.target.value)} />
                <input className={inputClass} placeholder="Hot label" value={f.hot_label} onChange={e => set('hot_label', e.target.value)} />
              </>
            )}
          </div>
          <div className="mt-3 flex gap-2">
            <Button size="sm" loading={saving} disabled={!f.title.trim()} onClick={save}>Save</Button>
            <Button size="sm" variant="ghost" onClick={onCancel}>Cancel</Button>
          </div>
        </div>
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
    title: '', points: '5', description: '', category_id: '', assigned_to_person_id: '',
    is_hot: false, hot_bonus_points: '0', hot_label: '',
    completion_behavior: 'stay_active' as MeridianTask['completion_behavior'],
    completion_scope: 'per_person' as MeridianTask['completion_scope'],
  })
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
        assigned_to_person_id: f.assigned_to_person_id ? Number(f.assigned_to_person_id) : null,
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
      <form onSubmit={submit} className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">
        <input className={`${inputClass} sm:col-span-2`} placeholder="Task title" value={f.title} onChange={e => set('title', e.target.value)} />
        <input className={inputClass} type="number" min="0" placeholder="Points" value={f.points} onChange={e => set('points', e.target.value)} />
        <select className={inputClass} value={f.assigned_to_person_id} onChange={e => set('assigned_to_person_id', e.target.value)}>
          <option value="">Anyone</option>
          {people.map(p => <option key={p.id} value={p.id}>{p.display_name}</option>)}
        </select>
        <textarea className={`${inputClass} sm:col-span-2`} placeholder="Description" value={f.description} onChange={e => set('description', e.target.value)} />
        <select className={inputClass} value={f.category_id} onChange={e => set('category_id', e.target.value)}>
          <option value="">No category</option>
          {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <select className={inputClass} value={f.completion_behavior} onChange={e => set('completion_behavior', e.target.value as MeridianTask['completion_behavior'])}>
          <option value="stay_active">Repeatable</option>
          <option value="hide_after_approval">One-off</option>
        </select>
        <select className={inputClass} value={f.completion_scope} onChange={e => set('completion_scope', e.target.value as MeridianTask['completion_scope'])}>
          <option value="per_person">Per person</option>
          <option value="household">Household</option>
        </select>
        <label className="flex items-center gap-2 text-sm text-ink">
          <input type="checkbox" checked={f.is_hot} onChange={e => set('is_hot', e.target.checked)} /> Hot task
        </label>
        {f.is_hot && (
          <>
            <input className={inputClass} type="number" min="0" placeholder="Bonus points" value={f.hot_bonus_points} onChange={e => set('hot_bonus_points', e.target.value)} />
            <input className={inputClass} placeholder="Hot label" value={f.hot_label} onChange={e => set('hot_label', e.target.value)} />
          </>
        )}
        <div className="sm:col-span-2 xl:col-span-4">
          <Button type="submit" loading={saving} disabled={!f.title.trim()}>Create task</Button>
        </div>
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
  const personName = (id: number | null) => people.find(p => p.id === id)?.display_name || ''
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      {tasks.map(task => (
        <Card key={task.id}>
          <div className="flex flex-col gap-3">
            <div>
              <h3 className="font-bold text-ink">{task.title}</h3>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {task.is_hot && <Badge className="bg-danger-soft text-danger">Hot</Badge>}
                {task.assigned_to_person_id && <Badge>For {personName(task.assigned_to_person_id)}</Badge>}
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
  const candidates = task.assigned_to_person_id
    ? people.filter(p => p.id === task.assigned_to_person_id)
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
