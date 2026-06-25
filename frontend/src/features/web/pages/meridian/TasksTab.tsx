import { useEffect, useMemo, useState } from 'react'
import { api } from '../../../../api/client'
import type { MeridianCategory, MeridianTask, Person } from '../../../../api/types'
import { Card } from '../../../../components/Card'
import { Button } from '../../../../components/Button'

// Mirrors the legacy tasks.html board: filters (all/hot + category), task cards with hot /
// behaviour / category / assignee badges, base+bonus points, and role-aware actions.

const STATUS_BADGE: Record<string, string> = {
  pending: 'bg-warning-soft text-warning',
  approved: 'bg-success-soft text-success',
  rejected: 'bg-danger-soft text-danger',
}

function Badge({ children, className = 'bg-sunken text-muted-strong' }: { children: React.ReactNode; className?: string }) {
  return <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${className}`}>{children}</span>
}

export function TasksTab({ canManage, pointsLabel }: { canManage: boolean; pointsLabel: string }) {
  const [tasks, setTasks] = useState<MeridianTask[]>([])
  const [categories, setCategories] = useState<MeridianCategory[]>([])
  const [people, setPeople] = useState<Person[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<'all' | 'hot'>('all')
  const [categoryId, setCategoryId] = useState<string>('')
  const [showForm, setShowForm] = useState(false)

  const reload = () =>
    Promise.all([
      api.getMeridianTasks(),
      api.getMeridianCategories('task').catch(() => []),
      api.getPeople().catch(() => []),
    ]).then(([t, c, p]) => { setTasks(t); setCategories(c); setPeople(p) })
      .finally(() => setLoading(false))

  useEffect(() => { reload() }, [])

  const catName = (id: number | null) => categories.find(c => c.id === id)?.name
  const personName = (id: number | null) => people.find(p => p.id === id)?.display_name

  const visible = useMemo(() => tasks.filter(t =>
    (filter !== 'hot' || t.is_hot) &&
    (!categoryId || t.category_id === Number(categoryId)),
  ), [tasks, filter, categoryId])

  const act = async (p: Promise<unknown>) => { await p.catch(() => {}); await reload() }

  if (loading) return <div className="h-32 rounded-2xl bg-sunken animate-pulse" />

  return (
    <div className="flex flex-col gap-4">
      {/* Filters */}
      <Card>
        <div className="flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-muted font-medium">Filter</span>
            <select value={filter} onChange={e => setFilter(e.target.value as 'all' | 'hot')}
              className="px-3 py-2 rounded-xl border border-line bg-raised text-ink text-sm">
              <option value="all">All tasks</option>
              <option value="hot">🔥 Hot tasks</option>
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-muted font-medium">Category</span>
            <select value={categoryId} onChange={e => setCategoryId(e.target.value)}
              className="px-3 py-2 rounded-xl border border-line bg-raised text-ink text-sm">
              <option value="">All categories</option>
              {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </label>
          {(filter === 'hot' || categoryId) && (
            <Button size="sm" variant="ghost" onClick={() => { setFilter('all'); setCategoryId('') }}>
              Clear
            </Button>
          )}
          {canManage && (
            <Button size="sm" className="ml-auto" onClick={() => setShowForm(s => !s)}>
              {showForm ? 'Close' : 'New task'}
            </Button>
          )}
        </div>
      </Card>

      {canManage && showForm && (
        <NewTaskForm categories={categories} people={people}
          onCreated={() => { setShowForm(false); reload() }} />
      )}

      {visible.length === 0 ? (
        <p className="text-sm text-muted text-center py-8">No tasks match.</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {visible.map(task => (
            <Card key={task.id} className={task.is_hot ? 'ring-2 ring-danger/40' : ''}>
              <div className="flex flex-col h-full gap-3">
                <div>
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="font-bold text-ink">{task.title}</h3>
                    {canManage && (
                      <button onClick={() => { if (confirm(`Delete "${task.title}"?`)) act(api.deleteMeridianTask(task.id)) }}
                        className="text-muted hover:text-danger text-lg leading-none" aria-label="Delete">×</button>
                    )}
                  </div>
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {!task.is_active && canManage && <Badge>Hidden</Badge>}
                    {task.is_hot && <Badge className="bg-danger-soft text-danger">🔥 Hot</Badge>}
                    <Badge className={task.completion_behavior === 'hide_after_approval' ? 'bg-sunken text-muted-strong' : 'bg-success-soft text-success'}>
                      {task.completion_behavior === 'hide_after_approval' ? 'One-off' : 'Repeatable'}
                    </Badge>
                    {catName(task.category_id) && <Badge>{catName(task.category_id)}</Badge>}
                    {task.assigned_to_person_id && <Badge>For {personName(task.assigned_to_person_id)}</Badge>}
                    {task.status !== 'available' && (
                      <Badge className={STATUS_BADGE[task.status] ?? ''}>{task.status}</Badge>
                    )}
                  </div>
                </div>

                {task.is_hot && task.hot_label && <p className="text-sm font-semibold text-danger">{task.hot_label}</p>}
                <p className="text-sm text-muted">{task.description || 'No description provided.'}</p>

                <div className="mt-auto pt-2">
                  <div className="mb-2">
                    <span className="inline-flex items-center gap-1 text-sm font-bold text-primary">★ {task.award_value} {pointsLabel}</span>
                    {task.is_hot && task.hot_bonus_points > 0 && (
                      <span className="text-xs text-muted ml-2">Base {task.points} + bonus {task.hot_bonus_points}</span>
                    )}
                  </div>

                  {task.status === 'available' && (
                    <CompleteControls task={task} people={people} canManage={canManage} onDone={reload} />
                  )}
                  {task.status === 'pending' && canManage && (
                    <div className="flex gap-2">
                      <Button size="sm" onClick={() => act(api.approveMeridianTask(task.id))}>Approve</Button>
                      <Button size="sm" variant="ghost"
                        onClick={() => act(api.rejectMeridianTask(task.id, prompt('Reason (optional)') || ''))}>Reject</Button>
                    </div>
                  )}
                  {task.status === 'pending' && !canManage && (
                    <Button size="sm" variant="secondary" disabled className="w-full">Awaiting approval</Button>
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}

function CompleteControls({ task, people, canManage, onDone }: {
  task: MeridianTask; people: Person[]; canManage: boolean; onDone: () => void
}) {
  const [busy, setBusy] = useState(false)
  const complete = async (personId?: number) => {
    setBusy(true)
    try { await api.completeMeridianTask(task.id, personId) } finally { setBusy(false); onDone() }
  }
  if (canManage) {
    // Admin/manager can mark complete on someone's behalf (legacy "Mark Complete For…").
    const candidates = people.filter(p => p.linked_user_id || p.profile_type === 'child')
    return (
      <div className="flex flex-wrap gap-2">
        {(task.assigned_to_person_id ? candidates.filter(p => p.id === task.assigned_to_person_id) : candidates)
          .slice(0, 4).map(p => (
            <Button key={p.id} size="sm" variant="secondary" loading={busy} onClick={() => complete(p.id)}>
              {p.display_name}
            </Button>
          ))}
      </div>
    )
  }
  return <Button size="sm" loading={busy} className="w-full" onClick={() => complete()}>Submit as complete</Button>
}

function NewTaskForm({ categories, people, onCreated }: {
  categories: MeridianCategory[]; people: Person[]; onCreated: () => void
}) {
  const [f, setF] = useState({
    title: '', points: '5', description: '', category_id: '', assigned_to_person_id: '',
    is_hot: false, hot_bonus_points: '0', hot_label: '',
    completion_behavior: 'stay_active' as 'stay_active' | 'hide_after_approval',
  })
  const [saving, setSaving] = useState(false)
  const set = (k: string, v: unknown) => setF(prev => ({ ...prev, [k]: v }))

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!f.title.trim()) return
    setSaving(true)
    try {
      await api.createMeridianTask({
        title: f.title.trim(), points: Number(f.points) || 0, description: f.description,
        is_hot: f.is_hot, hot_bonus_points: Number(f.hot_bonus_points) || 0, hot_label: f.hot_label,
        completion_behavior: f.completion_behavior,
        category_id: f.category_id ? Number(f.category_id) : null,
        assigned_to_person_id: f.assigned_to_person_id ? Number(f.assigned_to_person_id) : null,
      })
      onCreated()
    } finally { setSaving(false) }
  }

  const input = 'px-3 py-2 rounded-xl border border-line bg-raised text-sm text-ink placeholder-muted outline-none focus:ring-2 focus:ring-primary'

  return (
    <Card title="New task">
      <form onSubmit={submit} className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <input className={input} placeholder="Task title…" value={f.title} onChange={e => set('title', e.target.value)} />
        <input className={input} type="number" min="0" placeholder="Points" value={f.points} onChange={e => set('points', e.target.value)} />
        <textarea className={`${input} sm:col-span-2`} placeholder="Description (optional)" value={f.description} onChange={e => set('description', e.target.value)} />
        <select className={input} value={f.category_id} onChange={e => set('category_id', e.target.value)}>
          <option value="">No category</option>
          {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <select className={input} value={f.assigned_to_person_id} onChange={e => set('assigned_to_person_id', e.target.value)}>
          <option value="">Anyone</option>
          {people.map(p => <option key={p.id} value={p.id}>{p.display_name}</option>)}
        </select>
        <select className={input} value={f.completion_behavior} onChange={e => set('completion_behavior', e.target.value)}>
          <option value="stay_active">Repeatable (stays active)</option>
          <option value="hide_after_approval">One-off (hides after approval)</option>
        </select>
        <label className="flex items-center gap-2 text-sm text-ink">
          <input type="checkbox" checked={f.is_hot} onChange={e => set('is_hot', e.target.checked)} /> Hot task
        </label>
        {f.is_hot && (
          <>
            <input className={input} type="number" min="0" placeholder="Bonus points" value={f.hot_bonus_points} onChange={e => set('hot_bonus_points', e.target.value)} />
            <input className={input} placeholder="Hot label (e.g. 'Today only!')" value={f.hot_label} onChange={e => set('hot_label', e.target.value)} />
          </>
        )}
        <div className="sm:col-span-2">
          <Button type="submit" loading={saving} disabled={!f.title.trim()}>Create task</Button>
        </div>
      </form>
    </Card>
  )
}
