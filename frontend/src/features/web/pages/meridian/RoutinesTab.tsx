import { useEffect, useState } from 'react'
import { api } from '../../../../api/client'
import type { MeridianRoutine, Person } from '../../../../api/types'
import { Card } from '../../../../components/Card'
import { Button } from '../../../../components/Button'
import { useAuth } from '../../../auth/AuthContext'

// Mirrors the legacy routines.html: daily-habit cards with done-today + streak badges and a
// Mark-Done button; admin create/manage. Points award immediately on completion.

export function RoutinesTab({ canManage, pointsLabel }: { canManage: boolean; pointsLabel: string }) {
  const { user } = useAuth()
  const [routines, setRoutines] = useState<MeridianRoutine[]>([])
  const [people, setPeople] = useState<Person[]>([])
  const [myPersonId, setMyPersonId] = useState<number | undefined>()
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)

  const reload = async () => {
    const ppl = await api.getPeople().catch(() => [])
    setPeople(ppl)
    const mine = ppl.find(p => p.linked_user_id === user?.id)
    setMyPersonId(mine?.id)
    const r = await api.getMeridianRoutines(mine?.id).catch(() => [])
    setRoutines(r)
    setLoading(false)
  }
  useEffect(() => { reload() }, [])  // eslint-disable-line react-hooks/exhaustive-deps

  const personName = (id: number | null) => people.find(p => p.id === id)?.display_name

  if (loading) return <div className="h-32 rounded-2xl bg-sunken animate-pulse" />

  return (
    <div className="flex flex-col gap-4">
      {canManage && (
        <div className="flex justify-end">
          <Button size="sm" variant="secondary" onClick={() => setShowForm(s => !s)}>
            {showForm ? 'Close' : 'New routine'}
          </Button>
        </div>
      )}
      {canManage && showForm && (
        <NewRoutineForm people={people} onCreated={() => { setShowForm(false); reload() }} />
      )}

      {routines.length === 0 ? (
        <p className="text-sm text-muted text-center py-8">No routines yet.</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
          {routines.map(r => (
            <RoutineCard key={r.id} routine={r} canManage={canManage} pointsLabel={pointsLabel}
              canComplete={!!myPersonId} assignedName={personName(r.assigned_to_person_id)}
              onChanged={reload} />
          ))}
        </div>
      )}
    </div>
  )
}

function RoutineCard({ routine, canManage, pointsLabel, canComplete, assignedName, onChanged }: {
  routine: MeridianRoutine; canManage: boolean; pointsLabel: string; canComplete: boolean
  assignedName?: string; onChanged: () => void
}) {
  const [busy, setBusy] = useState(false)
  const done = !!routine.done_today

  const complete = async () => {
    setBusy(true)
    try { await api.completeMeridianRoutine(routine.id) } finally { setBusy(false); onChanged() }
  }
  const remove = async () => {
    if (!confirm(`Delete "${routine.title}"?`)) return
    await api.deleteMeridianRoutine(routine.id).catch(() => {})
    onChanged()
  }

  return (
    <Card className={done ? 'ring-2 ring-success/40' : ''}>
      <div className="flex flex-col h-full gap-2">
        <div className="flex items-start justify-between gap-2">
          <h3 className="font-bold text-ink">{done && '✅ '}{routine.title}</h3>
          {canManage && (
            <button onClick={remove} className="text-muted hover:text-danger text-lg leading-none" aria-label="Delete">×</button>
          )}
        </div>
        <div className="flex flex-wrap gap-1.5">
          <span className="text-xs px-2 py-0.5 rounded-full bg-primary-soft text-primary font-semibold">+{routine.points} {pointsLabel}</span>
          {(routine.streak ?? 0) > 0 && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-warning-soft text-warning font-semibold">🔥 {routine.streak}-day streak</span>
          )}
          {assignedName && <span className="text-xs px-2 py-0.5 rounded-full bg-sunken text-muted-strong">For {assignedName}</span>}
        </div>
        {routine.description && <p className="text-sm text-muted">{routine.description}</p>}
        <div className="mt-auto pt-2">
          {done ? (
            <Button size="sm" variant="secondary" disabled className="w-full">✓ Done today</Button>
          ) : canComplete ? (
            <Button size="sm" loading={busy} className="w-full" onClick={complete}>Mark done</Button>
          ) : (
            <p className="text-xs text-muted text-center">Complete on the kiosk</p>
          )}
        </div>
      </div>
    </Card>
  )
}

function NewRoutineForm({ people, onCreated }: { people: Person[]; onCreated: () => void }) {
  const [f, setF] = useState({ title: '', points: '1', description: '', assigned_to_person_id: '' })
  const [saving, setSaving] = useState(false)
  const set = (k: string, v: string) => setF(prev => ({ ...prev, [k]: v }))
  const input = 'px-3 py-2 rounded-xl border border-line bg-raised text-sm text-ink placeholder-muted outline-none focus:ring-2 focus:ring-primary'

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!f.title.trim()) return
    setSaving(true)
    try {
      await api.createMeridianRoutine({
        title: f.title.trim(), points: Number(f.points) || 1, description: f.description,
        assigned_to_person_id: f.assigned_to_person_id ? Number(f.assigned_to_person_id) : null,
      })
      onCreated()
    } finally { setSaving(false) }
  }

  return (
    <Card title="New routine">
      <form onSubmit={submit} className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <input className={input} placeholder="Routine (e.g. Brush teeth)" value={f.title} onChange={e => set('title', e.target.value)} />
        <input className={input} type="number" min="0" placeholder="Points" value={f.points} onChange={e => set('points', e.target.value)} />
        <select className={input} value={f.assigned_to_person_id} onChange={e => set('assigned_to_person_id', e.target.value)}>
          <option value="">Everyone</option>
          {people.map(p => <option key={p.id} value={p.id}>{p.display_name}</option>)}
        </select>
        <input className={input} placeholder="Description (optional)" value={f.description} onChange={e => set('description', e.target.value)} />
        <div className="sm:col-span-2"><Button type="submit" loading={saving} disabled={!f.title.trim()}>Create routine</Button></div>
      </form>
    </Card>
  )
}
