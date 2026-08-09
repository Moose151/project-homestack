import { useEffect, useState } from 'react'
import { api } from '../../../../api/client'
import type { MeridianRoutine, Person } from '../../../../api/types'
import { Card } from '../../../../components/Card'
import { Button } from '../../../../components/Button'
import { Field, Input, Textarea } from '../../../../components/ui'
import { AssigneeSelect, assigneeLabel } from '../../../../components/AssigneeSelect'
import { useAuth } from '../../../auth/AuthContext'

// Mirrors the legacy routines.html: daily-habit cards with done-today + streak badges and a
// Mark-Done button; admin create/manage. Points award immediately on completion.

const errMsg = (error: unknown) => error instanceof Error ? error.message : 'Something went wrong.'

export function RoutinesTab({ canManage, pointsLabel }: { canManage: boolean; pointsLabel: string }) {
  const { user } = useAuth()
  const [routines, setRoutines] = useState<MeridianRoutine[]>([])
  const [people, setPeople] = useState<Person[]>([])
  const [myPersonId, setMyPersonId] = useState<number | undefined>()
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const reload = async () => {
    setError(null)
    try {
      const ppl = await api.getPeople()
      setPeople(ppl)
      const mine = ppl.find(p => p.linked_user_id === user?.id)
      setMyPersonId(mine?.id)
      setRoutines(await api.getMeridianRoutines(mine?.id))
    } catch (e) {
      setError(errMsg(e))
    } finally {
      setLoading(false)
    }
  }
  useEffect(() => { reload() }, [])  // eslint-disable-line react-hooks/exhaustive-deps

  const peopleNames = (ids: number[]) => assigneeLabel(people, ids).replace('Whole family', '')

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
        <NewRoutineForm people={people} onCreated={() => { setShowForm(false); void reload() }} />
      )}

      {error && <p className="rounded-xl bg-danger-soft px-3 py-2 text-sm text-danger">{error}</p>}

      {routines.length === 0 ? (
        <p className="text-sm text-muted text-center py-8">No routines yet.</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
          {routines.map(r => (
            <RoutineCard key={r.id} routine={r} canManage={canManage} pointsLabel={pointsLabel}
              canComplete={!!myPersonId} assignedName={peopleNames(r.assigned_to_person_ids)}
              onChanged={reload} onError={setError} />
          ))}
        </div>
      )}
    </div>
  )
}

function RoutineCard({ routine, canManage, pointsLabel, canComplete, assignedName, onChanged, onError }: {
  routine: MeridianRoutine; canManage: boolean; pointsLabel: string; canComplete: boolean
  assignedName?: string; onChanged: () => Promise<void>; onError: (message: string) => void
}) {
  const [busy, setBusy] = useState(false)
  const done = !!routine.done_today

  const complete = async () => {
    setBusy(true)
    try {
      await api.completeMeridianRoutine(routine.id)
      await onChanged()
    } catch (e) {
      onError(errMsg(e))
    } finally {
      setBusy(false)
    }
  }
  const remove = async () => {
    if (!confirm(`Delete "${routine.title}"?`)) return
    setBusy(true)
    try {
      await api.deleteMeridianRoutine(routine.id)
      await onChanged()
    } catch (e) {
      onError(errMsg(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card className={done ? 'ring-2 ring-success/40' : ''}>
      <div className="flex flex-col h-full gap-2">
        <div className="flex items-start justify-between gap-2">
          <h3 className="font-bold text-ink">{done && '✅ '}{routine.title}</h3>
          {canManage && (
            <button type="button" disabled={busy} onClick={remove} className="grid min-h-10 min-w-10 place-items-center text-xl leading-none text-muted hover:text-danger disabled:opacity-40" aria-label={`Delete ${routine.title}`}>×</button>
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
  const [f, setF] = useState<{ title: string; points: string; description: string; assigned_to_person_ids: number[] }>(
    { title: '', points: '1', description: '', assigned_to_person_ids: [] },
  )
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const set = (k: string, v: string | number[]) => setF(prev => ({ ...prev, [k]: v }))

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!f.title.trim()) return
    setSaving(true); setError(null)
    try {
      await api.createMeridianRoutine({
        title: f.title.trim(), points: Number(f.points) || 1, description: f.description,
        assigned_to_person_ids: f.assigned_to_person_ids,
      })
      onCreated()
    } catch (e2) {
      setError(errMsg(e2))
    } finally { setSaving(false) }
  }

  return (
    <Card title="New routine">
      <form onSubmit={submit} className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {error && <p className="sm:col-span-2 rounded-xl bg-danger-soft px-3 py-2 text-sm text-danger">{error}</p>}
        <Field label="Routine name"><Input autoFocus placeholder="e.g. Brush teeth" value={f.title} onChange={e => set('title', e.target.value)} /></Field>
        <Field label="Points"><Input type="number" min="0" inputMode="numeric" value={f.points} onChange={e => set('points', e.target.value)} /></Field>
        <Field label="Who is it for?">
          <AssigneeSelect
            people={people}
            value={f.assigned_to_person_ids}
            onChange={ids => set('assigned_to_person_ids', ids)}
          />
        </Field>
        <Field label="Instructions"><Textarea placeholder="Optional details that make the routine clear." value={f.description} onChange={e => set('description', e.target.value)} /></Field>
        <div className="sm:col-span-2"><Button type="submit" loading={saving} disabled={!f.title.trim()}>Create routine</Button></div>
      </form>
    </Card>
  )
}
