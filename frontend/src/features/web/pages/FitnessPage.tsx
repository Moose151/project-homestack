import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { useSearchParams } from 'react-router-dom'

import { api } from '../../../api/client'
import type {
  FitnessExercise, FitnessMeasurement, FitnessProgram, FitnessRecord, FitnessSession,
  FitnessSessionExercise, FitnessSessionSet, Person,
} from '../../../api/types'
import { Button } from '../../../components/Button'
import { Card } from '../../../components/Card'
import { Field, fieldClass, SearchField } from '../../../components/Field'
import { PageHeader } from '../../../components/PageHeader'
import { InlineAlert } from '../../../components/PageState'
import { Tabs } from '../../../components/Tabs'
import { useUrlTab } from '../../../hooks/useUrlTab'
import { confirmDialog } from '../../../components/Dialogs'

declare global {
  interface String { replaceAll(searchValue: string, replaceValue: string): string }
}

type Tab = 'today' | 'programs' | 'history' | 'records' | 'exercises'
const TABS = [
  { key: 'today' as const, label: 'Train' }, { key: 'programs' as const, label: 'Programs' },
  { key: 'history' as const, label: 'History' }, { key: 'records' as const, label: 'Records' },
  { key: 'exercises' as const, label: 'Exercises' },
]
const input = fieldClass
const errorText = (error: unknown) => error instanceof Error ? error.message : 'Something went wrong.'
const personName = (person: Person) => person.preferred_name || person.display_name
const formatDuration = (seconds: number | null) => {
  if (seconds == null) return '—'
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60
  return hours ? `${hours}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}` : `${minutes}:${String(secs).padStart(2, '0')}`
}

/** Reads back the training the prefilled sets came from, so the weight on screen is explainable. */
const lastTimeSummary = (entry: FitnessSessionExercise) => {
  const history = entry.last_performance
  if (!history) return null
  const { weight_unit: weightUnit, distance_unit: distanceUnit } = entry.exercise
  const parts = history.sets.map(row => {
    if (row.weight && row.reps) return `${Number(row.weight)} ${weightUnit} × ${row.reps}`
    if (row.weight) return `${Number(row.weight)} ${weightUnit}`
    if (Number(row.distance)) return `${Number(row.distance)} ${distanceUnit}${row.duration_seconds ? ` in ${formatDuration(row.duration_seconds)}` : ''}`
    if (row.duration_seconds) return formatDuration(row.duration_seconds)
    if (row.reps) return `${row.reps} reps`
    return ''
  }).filter(Boolean)
  if (!parts.length) return null
  return `Last time, ${new Date(history.performed_at).toLocaleDateString()}: ${parts.join(' · ')}`
}

function Elapsed({ startedAt }: { startedAt: string }) {
  const [, redraw] = useState(0)
  useEffect(() => { const timer = window.setInterval(() => redraw(v => v + 1), 1000); return () => clearInterval(timer) }, [])
  return <span className="font-mono text-2xl font-black text-primary">{formatDuration(Math.max(0, Math.floor((Date.now() - new Date(startedAt).getTime()) / 1000)))}</span>
}

function SetEditor({ set, measurement, onSaved }: {
  set: FitnessSessionSet; measurement: FitnessMeasurement; onSaved: () => Promise<void>
}) {
  const [reps, setReps] = useState(set.reps?.toString() || '')
  const [weight, setWeight] = useState(set.weight || '')
  const [duration, setDuration] = useState(set.duration_seconds?.toString() || '')
  const [distance, setDistance] = useState(Number(set.distance) ? set.distance : '')
  const [busy, setBusy] = useState(false)
  const save = async (complete = set.is_completed) => {
    setBusy(true)
    try {
      await api.updateFitnessSessionSet(set.id, {
        reps: reps ? Number(reps) : null, weight: weight || null,
        duration_seconds: duration ? Number(duration) : null, distance: distance || '0',
        is_completed: complete,
      })
      await onSaved()
    } finally { setBusy(false) }
  }
  const small = `${input} !min-h-[42px] text-center`
  return (
    <div className={`grid grid-cols-[2.5rem_1fr_auto] items-end gap-2 rounded-xl p-2 ${set.is_completed ? 'bg-success/10 ring-1 ring-success/30' : 'bg-sunken'}`}>
      <span className="self-center text-center text-sm font-bold text-muted">{set.position + 1}</span>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {(measurement === 'reps_weight' || measurement === 'reps_only') && <Field label="Reps"><input className={small} type="number" min="0" inputMode="numeric" value={reps} onChange={e => setReps(e.target.value)} onBlur={() => save()} /></Field>}
        {measurement === 'reps_weight' && <Field label="Weight"><input className={small} type="number" min="0" step="0.25" inputMode="decimal" value={weight} onChange={e => setWeight(e.target.value)} onBlur={() => save()} /></Field>}
        {(measurement === 'duration' || measurement === 'distance_time') && <Field label="Seconds"><input className={small} type="number" min="0" inputMode="numeric" value={duration} onChange={e => setDuration(e.target.value)} onBlur={() => save()} /></Field>}
        {measurement === 'distance_time' && <Field label="Distance"><input className={small} type="number" min="0" step="0.001" inputMode="decimal" value={distance} onChange={e => setDistance(e.target.value)} onBlur={() => save()} /></Field>}
      </div>
      <button
        type="button" disabled={busy} aria-label={set.is_completed ? 'Mark set incomplete' : 'Complete set'}
        onClick={() => save(!set.is_completed)}
        className={`grid h-11 w-11 place-items-center rounded-xl border text-xl font-black ${set.is_completed ? 'border-success bg-success text-white' : 'border-line bg-surface text-muted'}`}
      >✓</button>
    </div>
  )
}

function LiveSession({ session, exercises, reload, onDone }: {
  session: FitnessSession; exercises: FitnessExercise[]; reload: () => Promise<void>; onDone: () => void
}) {
  const [adding, setAdding] = useState(false)
  const [exerciseId, setExerciseId] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const change = async (action: () => Promise<unknown>) => {
    setBusy(true); setError(null)
    try { await action(); await reload() } catch (e) { setError(errorText(e)) } finally { setBusy(false) }
  }
  return (
    <div className="space-y-3">
      <Card className="border-primary/30" contentClassName="p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div><p className="font-black text-ink">{session.name}</p><p className="text-sm text-muted">Training as {session.person_name}</p></div>
          <Elapsed startedAt={session.started_at} />
        </div>
      </Card>
      {error && <InlineAlert message={error} />}
      {session.exercises.filter(row => row.status === 'active').map(entry => (
        <Card key={entry.id} contentClassName="p-3 sm:p-4">
          <div className="mb-3 flex items-start justify-between gap-2">
            <div>
              <h3 className="font-bold text-ink">{entry.exercise.name}</h3>
              <p className="text-xs text-muted">{entry.exercise.muscle_group} · {entry.exercise.measurement.replace('_', ' ')}</p>
              {lastTimeSummary(entry) && <p className="mt-1 text-xs font-semibold text-primary">{lastTimeSummary(entry)}</p>}
            </div>
            <Button size="sm" variant="ghost" disabled={busy} onClick={() => change(() => api.dropFitnessSessionExercise(entry.id))}>Drop</Button>
          </div>
          <div className="space-y-2">{entry.sets.map(set => <SetEditor key={set.id} set={set} measurement={entry.exercise.measurement} onSaved={reload} />)}</div>
          <Button size="sm" variant="secondary" className="mt-3" disabled={busy} onClick={() => change(() => api.addFitnessSessionSet(entry.id))}>+ Add set</Button>
        </Card>
      ))}
      {adding ? (
        <Card contentClassName="p-3 flex flex-col sm:flex-row gap-2">
          <select className={input} value={exerciseId} onChange={e => setExerciseId(e.target.value)}><option value="">Choose exercise…</option>{exercises.map(ex => <option key={ex.id} value={ex.id}>{ex.name}</option>)}</select>
          <Button disabled={!exerciseId || busy} onClick={() => change(async () => { await api.addFitnessSessionExercise(session.id, { exercise_id: Number(exerciseId), target_sets: 1 }); setAdding(false); setExerciseId('') })}>Add</Button>
          <Button variant="ghost" onClick={() => setAdding(false)}>Cancel</Button>
        </Card>
      ) : <Button variant="secondary" className="w-full" onClick={() => setAdding(true)}>+ Add or swap an exercise</Button>}
      <div className="sticky bottom-[calc(5rem+env(safe-area-inset-bottom))] z-10 flex gap-2 rounded-2xl border border-line bg-surface/95 p-2 shadow-soft backdrop-blur sm:static sm:bg-transparent sm:p-0 sm:shadow-none">
        <Button className="flex-1" loading={busy} onClick={() => change(async () => { await api.finishFitnessSession(session.id); onDone() })}>Finish workout</Button>
        <Button variant="danger" disabled={busy} onClick={async () => { if ((await confirmDialog({ title: 'Abandon this workout?', message: 'Logged sets will not count toward records.', confirmLabel: 'Abandon' }))) change(async () => { await api.abandonFitnessSession(session.id); onDone() }) }}>Abandon</Button>
      </div>
    </div>
  )
}

interface DraftExercise { exercise_id: number; target_sets: number; target_reps: number | null; target_weight: string | null; target_duration_seconds: number | null; target_distance: string | null; position: number }
interface DraftWorkout { name: string; position: number; exercises: DraftExercise[] }

function ProgramBuilder({ people, exercises, onSaved, onCancel }: { people: Person[]; exercises: FitnessExercise[]; onSaved: () => Promise<void>; onCancel: () => void }) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [personIds, setPersonIds] = useState<number[]>([])
  const [workouts, setWorkouts] = useState<DraftWorkout[]>([{ name: 'Day 1', position: 0, exercises: [] }])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const updateWorkout = (index: number, next: DraftWorkout) => setWorkouts(rows => rows.map((row, i) => i === index ? next : row))
  const submit = async (event: FormEvent) => {
    event.preventDefault(); setBusy(true); setError(null)
    try { await api.createFitnessProgram({ name, description, person_ids: personIds, workouts }); await onSaved(); onCancel() }
    catch (e) { setError(errorText(e)) } finally { setBusy(false) }
  }
  return (
    <form onSubmit={submit} className="space-y-3">
      {error && <InlineAlert message={error} />}
      <Card title="Program details"><div className="grid gap-3 sm:grid-cols-2"><Field label="Program name"><input required className={input} value={name} onChange={e => setName(e.target.value)} placeholder="Three-day strength" /></Field><Field label="Description"><input className={input} value={description} onChange={e => setDescription(e.target.value)} /></Field></div><div className="mt-3"><p className="mb-2 text-xs font-bold uppercase tracking-wide text-muted">Assign to</p><div className="flex flex-wrap gap-2">{people.map(person => <label key={person.id} className="flex min-h-11 items-center gap-2 rounded-xl bg-sunken px-3 text-sm text-ink"><input type="checkbox" checked={personIds.includes(person.id)} onChange={e => setPersonIds(ids => e.target.checked ? [...ids, person.id] : ids.filter(id => id !== person.id))} />{personName(person)}</label>)}</div></div></Card>
      {workouts.map((workout, wi) => (
        <Card key={wi} title={`Workout ${wi + 1}`}>
          <Field label="Workout name"><input required className={input} value={workout.name} onChange={e => updateWorkout(wi, { ...workout, name: e.target.value })} /></Field>
          <div className="mt-3 space-y-2">{workout.exercises.map((row, ei) => {
            const definition = exercises.find(ex => ex.id === row.exercise_id)
            return <div key={ei} className="grid gap-2 rounded-xl bg-sunken p-2 sm:grid-cols-[2fr_repeat(3,1fr)_auto]">
              <select aria-label="Exercise" className={input} value={row.exercise_id || ''} onChange={e => updateWorkout(wi, { ...workout, exercises: workout.exercises.map((x, i) => i === ei ? { ...x, exercise_id: Number(e.target.value) } : x) })}><option value="">Exercise…</option>{exercises.map(ex => <option key={ex.id} value={ex.id}>{ex.name}</option>)}</select>
              <Field label="Sets"><input className={input} type="number" min="1" value={row.target_sets} onChange={e => updateWorkout(wi, { ...workout, exercises: workout.exercises.map((x, i) => i === ei ? { ...x, target_sets: Number(e.target.value) } : x) })} /></Field>
              {(definition?.measurement === 'reps_weight' || definition?.measurement === 'reps_only') && <Field label="Reps"><input className={input} type="number" value={row.target_reps || ''} onChange={e => updateWorkout(wi, { ...workout, exercises: workout.exercises.map((x, i) => i === ei ? { ...x, target_reps: Number(e.target.value) || null } : x) })} /></Field>}
              {definition?.measurement === 'reps_weight' && <Field label="Weight"><input className={input} type="number" step="0.25" value={row.target_weight || ''} onChange={e => updateWorkout(wi, { ...workout, exercises: workout.exercises.map((x, i) => i === ei ? { ...x, target_weight: e.target.value || null } : x) })} /></Field>}
              {(definition?.measurement === 'duration' || definition?.measurement === 'distance_time') && <Field label="Target seconds"><input className={input} type="number" min="1" value={row.target_duration_seconds || ''} onChange={e => updateWorkout(wi, { ...workout, exercises: workout.exercises.map((x, i) => i === ei ? { ...x, target_duration_seconds: Number(e.target.value) || null } : x) })} /></Field>}
              {definition?.measurement === 'distance_time' && <Field label={`Distance (${definition.distance_unit})`}><input className={input} type="number" min="0" step="0.001" value={row.target_distance || ''} onChange={e => updateWorkout(wi, { ...workout, exercises: workout.exercises.map((x, i) => i === ei ? { ...x, target_distance: e.target.value || null } : x) })} /></Field>}
              <Button type="button" variant="ghost" onClick={() => updateWorkout(wi, { ...workout, exercises: workout.exercises.filter((_, i) => i !== ei) })}>Remove</Button>
            </div>
          })}</div>
          <Button type="button" size="sm" variant="secondary" className="mt-3" onClick={() => updateWorkout(wi, { ...workout, exercises: [...workout.exercises, { exercise_id: exercises[0]?.id || 0, target_sets: 3, target_reps: 8, target_weight: null, target_duration_seconds: null, target_distance: null, position: workout.exercises.length }] })}>+ Add exercise</Button>
        </Card>
      ))}
      <Button type="button" variant="secondary" onClick={() => setWorkouts(rows => [...rows, { name: `Day ${rows.length + 1}`, position: rows.length, exercises: [] }])}>+ Add workout day</Button>
      <div className="flex gap-2"><Button type="submit" loading={busy} disabled={!name.trim()}>Save program</Button><Button type="button" variant="ghost" onClick={onCancel}>Cancel</Button></div>
    </form>
  )
}

function BasicExerciseLibrary({ exercises, reload }: { exercises: FitnessExercise[]; reload: () => Promise<void> }) {
  const [query, setQueryState] = useState('')
  const setQuery = (value: string | React.ChangeEvent<HTMLInputElement>) =>
    setQueryState(typeof value === 'string' ? value : value.target.value)
  const [adding, setAdding] = useState(false)
  const [name, setName] = useState('')
  const [type, setType] = useState('strength')
  const [muscle, setMuscle] = useState('')
  const [measurement, setMeasurement] = useState<FitnessMeasurement>('reps_weight')
  const visible = exercises.filter(ex => `${ex.name} ${ex.muscle_group}`.toLowerCase().includes(query.toLowerCase()))
  const save = async (e: FormEvent) => { e.preventDefault(); await api.createFitnessExercise({ name, exercise_type: type as FitnessExercise['exercise_type'], muscle_group: muscle, measurement }); setName(''); setAdding(false); await reload() }
  return <div className="space-y-3"><div className="flex gap-2"><SearchField value={query} onChange={setQuery} placeholder="Search by exercise or muscle group…" className="flex-1" /><Button onClick={() => setAdding(v => !v)}>+ Exercise</Button></div>{adding && <Card><form onSubmit={save} className="grid gap-2 sm:grid-cols-4"><Field label="Name"><input required className={input} value={name} onChange={e => setName(e.target.value)} /></Field><Field label="Type"><select className={input} value={type} onChange={e => setType(e.target.value)}>{['strength','running','swimming','cycling','cardio','mobility','sport'].map(value => <option key={value}>{value}</option>)}</select></Field><Field label="Muscle group"><input className={input} value={muscle} onChange={e => setMuscle(e.target.value)} /></Field><Field label="Recorded as"><select className={input} value={measurement} onChange={e => setMeasurement(e.target.value as FitnessMeasurement)}><option value="reps_weight">Reps + weight</option><option value="reps_only">Reps</option><option value="duration">Time</option><option value="distance_time">Distance + time</option></select></Field><Button type="submit">Save exercise</Button></form></Card>}<div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">{visible.map(ex => <Card key={ex.id} contentClassName="p-3"><p className="font-bold text-ink">{ex.name}</p><p className="text-xs text-muted">{ex.exercise_type} · {ex.muscle_group || 'General'} · {ex.measurement.replace('_', ' ')}</p></Card>)}</div></div>
}

function ExerciseLibrary({ exercises, reload }: { exercises: FitnessExercise[]; reload: () => Promise<void> }) {
  const [editingId, setEditingId] = useState('')
  const selected = exercises.find(exercise => exercise.id === Number(editingId))
  const [name, setName] = useState('')
  const [muscleGroup, setMuscleGroup] = useState('')
  useEffect(() => {
    setName(selected?.name || '')
    setMuscleGroup(selected?.muscle_group || '')
  }, [selected?.id])
  const save = async (event: FormEvent) => {
    event.preventDefault()
    if (!selected) return
    await api.updateFitnessExercise(selected.id, { name, muscle_group: muscleGroup })
    setEditingId('')
    await reload()
  }
  return (
    <div className="space-y-3">
      <BasicExerciseLibrary exercises={exercises} reload={reload} />
      <Card title="Modify an exercise">
        <form onSubmit={save} className="grid gap-2 sm:grid-cols-[2fr_2fr_2fr_auto]">
          <Field label="Exercise">
            <select className={input} value={editingId} onChange={event => setEditingId(event.target.value)}>
              <option value="">Choose…</option>
              {exercises.map(exercise => <option key={exercise.id} value={exercise.id}>{exercise.name}</option>)}
            </select>
          </Field>
          <Field label="Name"><input className={input} disabled={!selected} value={name} onChange={event => setName(event.target.value)} /></Field>
          <Field label="Muscle group"><input className={input} disabled={!selected} value={muscleGroup} onChange={event => setMuscleGroup(event.target.value)} /></Field>
          <Button type="submit" disabled={!selected || !name.trim()} className="self-end">Save</Button>
        </form>
      </Card>
    </div>
  )
}

export function FitnessPage() {
  const [tab, setTab] = useUrlTab<Tab>('today', TABS.map(row => row.key))
  const [searchParams] = useSearchParams()
  const selectedSessionId = Number(searchParams.get('session') || 0)
  const selectedProgramId = Number(searchParams.get('program') || 0)
  const [people, setPeople] = useState<Person[]>([])
  const [exercises, setExercises] = useState<FitnessExercise[]>([])
  const [programs, setPrograms] = useState<FitnessProgram[]>([])
  const [sessions, setSessions] = useState<FitnessSession[]>([])
  const [records, setRecords] = useState<FitnessRecord[]>([])
  const [building, setBuilding] = useState(false)
  const [startPerson, setStartPerson] = useState('')
  const [error, setError] = useState<string | null>(null)
  const load = async () => {
    try {
      const [p, ex, plans, logs, prs] = await Promise.all([api.getPeople(), api.getFitnessExercises(), api.getFitnessPrograms(), api.getFitnessSessions(), api.getFitnessRecords()])
      setPeople(p); setExercises(ex); setPrograms(plans); setSessions(logs); setRecords(prs)
      if (!startPerson && p[0]) setStartPerson(String(p[0].id))
    } catch (e) { setError(errorText(e)) }
  }
  useEffect(() => { load() }, [])
  useEffect(() => { if (selectedSessionId) setTab('history') }, [selectedSessionId, setTab])
  useEffect(() => { if (selectedProgramId) setTab('programs') }, [selectedProgramId, setTab])
  useEffect(() => {
    if (selectedProgramId && programs.length) window.setTimeout(() => document.getElementById(`fitness-program-${selectedProgramId}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' }), 0)
  }, [selectedProgramId, programs])
  const active = sessions.find(session => session.status === 'active')
  const reloadActive = async () => { const logs = await api.getFitnessSessions(); setSessions(logs) }
  const recordLabel = (record: FitnessRecord) => {
    if (record.kind === 'fastest_time') return `${formatDuration(Number(record.value))} for ${Number(record.distance)} ${record.distance_unit}`
    if (record.kind === 'longest_distance') return `${Number(record.value)} ${record.distance_unit}`
    if (record.kind === 'max_reps') return `${Number(record.value)} reps`
    return `${Number(record.value).toFixed(1)} ${record.weight_unit}`
  }
  // docs/36 §6.11: preserve the live-workout screen's own focus — during an active session,
  // drop the page header and tab row rather than surrounding it with unrelated navigation.
  const inLiveSession = tab === 'today' && Boolean(active)
  return <div className="space-y-4">{!inLiveSession && <PageHeader title="Fitness & training" subtitle="Programs, live workouts and household personal bests" icon="🏋️" />}{error && <InlineAlert tone="danger">{error}</InlineAlert>}{!inLiveSession && <Tabs tabs={TABS} active={tab} onChange={setTab} mobileSelectLabel="Fitness section" />}
    {tab === 'today' && (active ? <LiveSession session={active} exercises={exercises} reload={reloadActive} onDone={async () => { await load(); setTab('history') }} /> : <div className="space-y-3"><Card title="Start a workout"><Field label="Who is training?"><select className={input} value={startPerson} onChange={e => setStartPerson(e.target.value)}>{people.map(person => <option key={person.id} value={person.id}>{personName(person)}</option>)}</select></Field></Card>{programs.filter(program => !startPerson || program.assignments.some(a => a.person_id === Number(startPerson))).map(program => <Card key={program.id} title={program.name}><p className="mb-3 text-sm text-muted">{program.description || `${program.workouts.length} workout days`}</p><div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">{program.workouts.map(workout => <button key={workout.id} onClick={async () => { await api.startFitnessSession({ person_id: Number(startPerson), workout_id: workout.id }); await load() }} className="min-h-16 rounded-xl bg-primary px-4 py-3 text-left font-bold text-white"><span className="block">Start {workout.name}</span><span className="text-xs font-normal opacity-80">{workout.exercises.length} exercises</span></button>)}</div></Card>)}<Button variant="secondary" onClick={async () => { await api.startFitnessSession({ person_id: Number(startPerson), name: 'Open workout' }); await load() }}>Start an empty workout</Button></div>)}
    {tab === 'programs' && (building ? <ProgramBuilder people={people} exercises={exercises} onSaved={load} onCancel={() => setBuilding(false)} /> : <div className="space-y-3"><Button onClick={() => setBuilding(true)}>+ New program</Button>{programs.map(program => <div key={program.id} id={`fitness-program-${program.id}`} className={selectedProgramId === program.id ? 'rounded-2xl ring-2 ring-primary ring-offset-2 ring-offset-paper' : ''}><Card title={program.name}><p className="text-sm text-muted">{program.description || 'No description'}</p><p className="mt-2 text-xs font-semibold text-primary">{program.workouts.length} days · {program.assignments.map(a => a.person_name).join(', ') || 'Not assigned'}</p><div className="mt-3 space-y-2">{program.workouts.map(workout => <div key={workout.id} className="rounded-xl bg-sunken p-3"><p className="font-bold text-ink">{workout.name}</p><p className="text-xs text-muted">{workout.exercises.map(row => `${row.exercise.name} × ${row.target_sets}`).join(' · ') || 'No exercises'}</p></div>)}</div></Card></div>)}</div>)}
    {tab === 'history' && <div className="space-y-3">{sessions.filter(session => session.status !== 'active').map(session => <div key={session.id} id={`fitness-session-${session.id}`} className={selectedSessionId === session.id ? 'rounded-2xl ring-2 ring-primary ring-offset-2 ring-offset-paper' : ''}><Card><details open={selectedSessionId === session.id}><summary className="cursor-pointer list-none"><div className="flex justify-between gap-3"><div><p className="font-bold text-ink">{session.person_name} · {session.name}</p><p className="text-xs text-muted">{new Date(session.started_at).toLocaleString()} · {formatDuration(session.duration_seconds)} · {session.total_reps} reps · {Number(session.total_volume).toLocaleString()} kg volume</p></div><span className="text-sm font-bold text-primary">{session.personal_records.length ? `🏆 ${session.personal_records.length}` : 'Details ▾'}</span></div></summary><div className="mt-3 space-y-2 border-t border-line pt-3">{session.exercises.filter(entry => entry.status === 'active').map(entry => <div key={entry.id} className="rounded-xl bg-sunken p-3"><p className="font-bold text-ink">{entry.exercise.name}</p><p className="mt-1 text-xs text-muted">{entry.sets.filter(set => set.is_completed).map(set => set.weight && set.reps ? `${Number(set.weight)} ${entry.exercise.weight_unit} × ${set.reps}` : set.reps ? `${set.reps} reps` : Number(set.distance) ? `${Number(set.distance)} ${entry.exercise.distance_unit}${set.duration_seconds ? ` in ${formatDuration(set.duration_seconds)}` : ''}` : set.duration_seconds ? formatDuration(set.duration_seconds) : '').filter(Boolean).join(' · ') || 'No completed sets'}</p></div>)}</div></details></Card></div>)}</div>}
    {tab === 'records' && <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{records.map(record => <Card key={record.id}><p className="text-xs font-bold uppercase tracking-wide text-muted">{record.person_name}</p><p className="mt-1 font-black text-ink">{record.exercise_name}</p><p className="mt-2 text-xl font-black text-primary">{recordLabel(record)}</p><p className="text-xs text-muted">{record.kind.replaceAll('_', ' ')} · {new Date(record.achieved_at).toLocaleDateString()}</p></Card>)}</div>}
    {tab === 'exercises' && <ExerciseLibrary exercises={exercises} reload={load} />}
  </div>
}
