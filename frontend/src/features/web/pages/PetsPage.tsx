import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../../api/client'
import type { Pet, PetSpecies, PetTreatment, PetAppointment, TreatmentType } from '../../../api/types'
import { Card } from '../../../components/Card'
import { Button } from '../../../components/Button'
import { Input, Textarea, Select, Field } from '../../../components/Field'
import { Tabs, type TabDef } from '../../../components/Tabs'
import { PageHeader } from '../../../components/PageHeader'
import { EmptyState } from '../../../components/EmptyState'
import { DateTimeField } from '../../../components/DateTimeField'
import { useAuth } from '../../auth/AuthContext'

const errMsg = (e: unknown) => (e instanceof Error ? e.message : 'Something went wrong.')

const SPECIES_EMOJI: Record<PetSpecies, string> = {
  dog: '🐕', cat: '🐈', bird: '🐦', fish: '🐟', reptile: '🦎', small_mammal: '🐹', other: '🐾',
}
const SPECIES_LABELS: Record<PetSpecies, string> = {
  dog: 'Dog', cat: 'Cat', bird: 'Bird', fish: 'Fish', reptile: 'Reptile', small_mammal: 'Small mammal', other: 'Other',
}
const TREATMENT_LABELS: Record<TreatmentType, string> = {
  flea: 'Flea', worming: 'Worming', vaccination: 'Vaccination', medication: 'Medication', grooming: 'Grooming', other: 'Other',
}
const RECURRENCE_OPTS = [
  { value: '', label: 'No repeat' },
  { value: 'FREQ=WEEKLY', label: 'Weekly' },
  { value: 'FREQ=WEEKLY;INTERVAL=2', label: 'Fortnightly' },
  { value: 'FREQ=MONTHLY', label: 'Monthly' },
  { value: 'FREQ=MONTHLY;INTERVAL=3', label: 'Every 3 months' },
  { value: 'FREQ=YEARLY', label: 'Yearly' },
]

function dueBadge(iso: string | null, overdue: boolean) {
  if (!iso) return null
  const d = new Date(iso)
  const days = Math.round((d.getTime() - Date.now()) / 86400000)
  const text = overdue ? `${Math.abs(days)}d overdue`
    : days === 0 ? 'Today' : days === 1 ? 'Tomorrow'
    : d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
  const tone = overdue ? 'bg-danger-soft text-danger' : days <= 1 ? 'bg-primary-soft text-primary' : 'bg-sunken text-muted-strong'
  return { text, tone }
}
const calendarDayHref = (iso: string | null) => iso ? `/calendar?date=${new Date(iso).toISOString().slice(0, 10)}` : '/calendar'

// ===========================================================================
// Treatment + appointment forms
// ===========================================================================

function TreatmentForm({ petId, onCreated, onError, onCancel }: {
  petId: number; onCreated: (t: PetTreatment) => void; onError: (m: string) => void; onCancel: () => void
}) {
  const [type, setType] = useState<TreatmentType>('flea')
  const [name, setName] = useState('')
  const [due, setDue] = useState<string | null>(null)
  const [recurrence, setRecurrence] = useState('FREQ=MONTHLY')
  const [busy, setBusy] = useState(false)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setBusy(true)
    try {
      const t = await api.createPetTreatment({
        pet_id: petId, treatment_type: type, name: name.trim(),
        next_due_at: due, recurrence_rule: recurrence,
      })
      onCreated(t)
    } catch (e) { onError(errMsg(e)) } finally { setBusy(false) }
  }

  return (
    <form onSubmit={submit} className="space-y-3 bg-sunken rounded-2xl p-3">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        <Select value={type} onChange={e => setType(e.target.value as TreatmentType)}>
          {Object.entries(TREATMENT_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </Select>
        <Input placeholder="Product / name (optional)" value={name} onChange={e => setName(e.target.value)} />
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        <Field label="Next due"><DateTimeField value={due} allDay onChange={({ value }) => setDue(value)} /></Field>
        <Field label="Repeat"><Select value={recurrence} onChange={e => setRecurrence(e.target.value)}>
          {RECURRENCE_OPTS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </Select></Field>
      </div>
      <div className="flex gap-2">
        <Button type="submit" size="sm" loading={busy}>Add treatment</Button>
        <Button type="button" size="sm" variant="ghost" onClick={onCancel}>Cancel</Button>
      </div>
    </form>
  )
}

function AppointmentForm({ petId, onCreated, onError, onCancel }: {
  petId: number; onCreated: (a: PetAppointment) => void; onError: (m: string) => void; onCancel: () => void
}) {
  const [title, setTitle] = useState('')
  const [provider, setProvider] = useState('')
  const [start, setStart] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!start) { onError('A date is required.'); return }
    setBusy(true)
    try {
      const a = await api.createPetAppointment({
        pet_id: petId, title: title.trim(), provider: provider.trim(), start_at: start,
      })
      onCreated(a)
    } catch (e) { onError(errMsg(e)) } finally { setBusy(false) }
  }

  return (
    <form onSubmit={submit} className="space-y-3 bg-sunken rounded-2xl p-3">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        <Input placeholder="Title (e.g. Annual check-up)" value={title} onChange={e => setTitle(e.target.value)} />
        <Input placeholder="Vet / provider" value={provider} onChange={e => setProvider(e.target.value)} />
      </div>
      <Field label="When"><DateTimeField value={start} allDay={false} allowAllDay={false} onChange={({ value }) => setStart(value)} /></Field>
      <div className="flex gap-2">
        <Button type="submit" size="sm" loading={busy}>Add appointment</Button>
        <Button type="button" size="sm" variant="ghost" onClick={onCancel}>Cancel</Button>
      </div>
    </form>
  )
}

// ===========================================================================
// Pet card (with inline treatments + appointments)
// ===========================================================================

function TreatmentRow({ t, onChange, onDelete, onError }: {
  t: PetTreatment; onChange: (t: PetTreatment) => void; onDelete: (id: number) => void; onError: (m: string) => void
}) {
  const badge = dueBadge(t.next_due_at, t.is_overdue)
  const complete = async () => {
    try { onChange(await api.completePetTreatment(t.id)) } catch (e) { onError(errMsg(e)) }
  }
  const remove = async () => {
    if (!confirm('Delete this treatment?')) return
    try { await api.deletePetTreatment(t.id); onDelete(t.id) } catch (e) { onError(errMsg(e)) }
  }
  return (
    <li className="flex items-center gap-2 py-2 group">
      <div className="flex-1 min-w-0">
        <div className="text-sm text-ink truncate">{t.display_name}</div>
        <div className="flex items-center gap-1.5 mt-0.5">
          {t.next_due_at
            ? badge && <Link to={calendarDayHref(t.next_due_at)} className={`text-xs px-2 py-0.5 rounded-full font-medium ${badge.tone}`}>{badge.text}</Link>
            : <span className="text-xs text-muted">No reminder{t.last_done_at ? ` · last done ${new Date(t.last_done_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}` : ''}</span>}
          {t.recurrence_rule && <span className="text-xs text-muted">repeats</span>}
        </div>
      </div>
      {t.next_due_at && <Button size="sm" variant="secondary" onClick={complete}>Done</Button>}
      <button onClick={remove} className="opacity-0 group-hover:opacity-100 text-muted hover:text-danger text-lg leading-none transition" aria-label="Delete">×</button>
    </li>
  )
}

function PetCard({ pet, onChange, onDelete, onError, canDelete }: {
  pet: Pet; onChange: (p: Pet) => void; onDelete: (id: number) => void; onError: (m: string) => void; canDelete: boolean
}) {
  const [expanded, setExpanded] = useState(false)
  const [editing, setEditing] = useState(false)
  const [treatments, setTreatments] = useState<PetTreatment[] | null>(null)
  const [appointments, setAppointments] = useState<PetAppointment[] | null>(null)
  const [addingT, setAddingT] = useState(false)
  const [addingA, setAddingA] = useState(false)
  const [form, setForm] = useState({ name: pet.name, species: pet.species, breed: pet.breed, vet_name: pet.vet_name, vet_phone: pet.vet_phone, microchip_number: pet.microchip_number, notes: pet.notes })
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!expanded || treatments !== null) return
    api.getPetTreatments({ pet: pet.id }).then(setTreatments).catch(e => onError(errMsg(e)))
    api.getPetAppointments({ pet: pet.id, upcoming: true }).then(setAppointments).catch(e => onError(errMsg(e)))
  }, [expanded])

  const saveEdit = async (e: React.FormEvent) => {
    e.preventDefault()
    setBusy(true)
    try { onChange(await api.updatePet(pet.id, form)); setEditing(false) }
    catch (e) { onError(errMsg(e)) } finally { setBusy(false) }
  }
  const remove = async () => {
    if (!confirm(`Delete "${pet.name}"? Their treatments and appointments go too.`)) return
    try { await api.deletePet(pet.id); onDelete(pet.id) } catch (e) { onError(errMsg(e)) }
  }

  if (editing) {
    return (
      <Card>
        <form onSubmit={saveEdit} className="space-y-2">
          <Input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} placeholder="Name" />
          <div className="grid grid-cols-2 gap-2">
            <Select value={form.species} onChange={e => setForm(f => ({ ...f, species: e.target.value as PetSpecies }))}>
              {Object.entries(SPECIES_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </Select>
            <Input value={form.breed} onChange={e => setForm(f => ({ ...f, breed: e.target.value }))} placeholder="Breed" />
            <Input value={form.vet_name} onChange={e => setForm(f => ({ ...f, vet_name: e.target.value }))} placeholder="Vet name" />
            <Input value={form.vet_phone} onChange={e => setForm(f => ({ ...f, vet_phone: e.target.value }))} placeholder="Vet phone" />
          </div>
          <Input value={form.microchip_number} onChange={e => setForm(f => ({ ...f, microchip_number: e.target.value }))} placeholder="Microchip number" />
          <Textarea value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} placeholder="Notes" rows={2} />
          <div className="flex gap-2"><Button type="submit" size="sm" loading={busy}>Save</Button><Button type="button" size="sm" variant="ghost" onClick={() => setEditing(false)}>Cancel</Button></div>
        </form>
      </Card>
    )
  }

  return (
    <Card className="group">
      <div className="flex items-start gap-3">
        <span className="text-3xl leading-none flex-shrink-0">{pet.avatar || SPECIES_EMOJI[pet.species]}</span>
        <button className="text-left min-w-0 flex-1" onClick={() => setExpanded(v => !v)}>
          <div className="font-semibold text-ink truncate">{pet.name}</div>
          <div className="text-xs text-muted">{SPECIES_LABELS[pet.species]}{pet.breed ? ` · ${pet.breed}` : ''}</div>
        </button>
        <div className="flex flex-shrink-0 gap-1 opacity-0 group-hover:opacity-100 transition">
          <button onClick={() => setEditing(true)} className="rounded-lg px-2 py-1 text-xs text-muted hover:bg-sunken hover:text-ink">Edit</button>
          {canDelete && <button onClick={remove} className="rounded-lg px-2 py-1 text-xs text-muted hover:text-danger">Delete</button>}
        </div>
      </div>

      {expanded && (
        <div className="mt-3 border-t border-line pt-3 space-y-4">
          {(pet.vet_name || pet.microchip_number || pet.notes) && (
            <div className="text-xs text-muted space-y-0.5">
              {pet.vet_name && <div>🩺 {pet.vet_name}{pet.vet_phone ? ` · ${pet.vet_phone}` : ''}</div>}
              {pet.microchip_number && <div>🔖 Chip {pet.microchip_number}</div>}
              {pet.notes && <div className="text-muted-strong whitespace-pre-wrap">{pet.notes}</div>}
            </div>
          )}

          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-semibold text-muted-strong uppercase tracking-wide">Treatments</span>
              {!addingT && <button onClick={() => setAddingT(true)} className="text-xs text-primary hover:underline">+ Add</button>}
            </div>
            {addingT && <TreatmentForm petId={pet.id} onError={onError} onCancel={() => setAddingT(false)}
              onCreated={t => { setTreatments(prev => [...(prev ?? []), t]); setAddingT(false) }} />}
            {treatments === null ? <p className="text-xs text-muted">Loading…</p>
              : treatments.length === 0 ? <p className="text-xs text-muted">No treatments yet.</p>
              : <ul className="divide-y divide-line">{treatments.map(t => (
                  <TreatmentRow key={t.id} t={t} onError={onError}
                    onChange={u => setTreatments(prev => prev!.map(x => x.id === u.id ? u : x))}
                    onDelete={id => setTreatments(prev => prev!.filter(x => x.id !== id))} />
                ))}</ul>}
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-semibold text-muted-strong uppercase tracking-wide">Appointments</span>
              {!addingA && <button onClick={() => setAddingA(true)} className="text-xs text-primary hover:underline">+ Add</button>}
            </div>
            {addingA && <AppointmentForm petId={pet.id} onError={onError} onCancel={() => setAddingA(false)}
              onCreated={a => { setAppointments(prev => [...(prev ?? []), a]); setAddingA(false) }} />}
            {appointments === null ? <p className="text-xs text-muted">Loading…</p>
              : appointments.length === 0 ? <p className="text-xs text-muted">No upcoming appointments.</p>
              : <ul className="divide-y divide-line">{appointments.map(a => (
                  <li key={a.id} className="flex items-center justify-between gap-2 py-2 text-sm">
                    <span className="text-ink truncate">{a.display_title}{a.provider ? ` · ${a.provider}` : ''}</span>
                    <Link to={calendarDayHref(a.start_at)} className="text-xs text-primary flex-shrink-0">{new Date(a.start_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}</Link>
                  </li>
                ))}</ul>}
          </div>
        </div>
      )}
    </Card>
  )
}

// ===========================================================================
// Pets tab (profiles)
// ===========================================================================

function PetsTab({ pets, reload, isAdmin, onError }: {
  pets: Pet[]; reload: () => void; isAdmin: boolean; onError: (m: string) => void
}) {
  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  const [species, setSpecies] = useState<PetSpecies>('dog')
  const [breed, setBreed] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return
    setBusy(true)
    try {
      await api.createPet({ name: name.trim(), species, breed: breed.trim() })
      setName(''); setBreed(''); setSpecies('dog'); setOpen(false); reload()
    } catch (e) { onError(errMsg(e)) } finally { setBusy(false) }
  }

  return (
    <div className="space-y-4">
      {open ? (
        <form onSubmit={submit} className="space-y-3 bg-sunken rounded-2xl p-4">
          <Input autoFocus placeholder="Pet name" value={name} onChange={e => setName(e.target.value)} />
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Select value={species} onChange={e => setSpecies(e.target.value as PetSpecies)}>
              {Object.entries(SPECIES_LABELS).map(([v, l]) => <option key={v} value={v}>{SPECIES_EMOJI[v as PetSpecies]} {l}</option>)}
            </Select>
            <Input placeholder="Breed (optional)" value={breed} onChange={e => setBreed(e.target.value)} />
          </div>
          <div className="flex gap-2"><Button type="submit" loading={busy}>Add pet</Button><Button type="button" variant="ghost" onClick={() => setOpen(false)}>Cancel</Button></div>
        </form>
      ) : (
        <Button variant="secondary" onClick={() => setOpen(true)}>+ Add pet</Button>
      )}

      {pets.length === 0 ? (
        <EmptyState icon="🐾" title="No pets yet" hint="Add a pet to track treatments, vet visits and care notes." />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          {pets.map(p => (
            <PetCard key={p.id} pet={p} canDelete={isAdmin}
              onChange={() => reload()} onDelete={() => reload()} onError={onError} />
          ))}
        </div>
      )}
    </div>
  )
}

// ===========================================================================
// Reminders tab (all due treatments)
// ===========================================================================

function RemindersTab({ onError }: { onError: (m: string) => void }) {
  const [treatments, setTreatments] = useState<PetTreatment[]>([])
  const [loading, setLoading] = useState(true)

  const load = () => {
    setLoading(true)
    api.getPetTreatments({ due: true }).then(setTreatments).catch(e => onError(errMsg(e))).finally(() => setLoading(false))
  }
  useEffect(load, [])

  if (loading) return <Card><p className="text-sm text-muted">Loading…</p></Card>
  if (treatments.length === 0) return <EmptyState icon="✅" title="Nothing due" hint="Treatment reminders show up here as they come due." />
  return (
    <Card>
      <ul className="divide-y divide-line -mt-1">
        {treatments.map(t => {
          const badge = dueBadge(t.next_due_at, t.is_overdue)
          return (
            <li key={t.id} className="flex items-center gap-3 py-2.5">
              <div className="flex-1 min-w-0">
                <div className="text-sm text-ink truncate"><span className="text-muted">{t.pet_name}</span> · {t.display_name}</div>
                {badge && <Link to={calendarDayHref(t.next_due_at)} className={`text-xs px-2 py-0.5 rounded-full font-medium ${badge.tone}`}>{badge.text}</Link>}
              </div>
              <Button size="sm" variant="secondary" onClick={async () => { try { await api.completePetTreatment(t.id); load() } catch (e) { onError(errMsg(e)) } }}>Done</Button>
            </li>
          )
        })}
      </ul>
    </Card>
  )
}

// ===========================================================================
// Appointments tab
// ===========================================================================

function AppointmentsTab({ onError }: { onError: (m: string) => void }) {
  const [appointments, setAppointments] = useState<PetAppointment[]>([])
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    api.getPetAppointments({ upcoming: true }).then(setAppointments).catch(e => onError(errMsg(e))).finally(() => setLoading(false))
  }, [])

  if (loading) return <Card><p className="text-sm text-muted">Loading…</p></Card>
  if (appointments.length === 0) return <EmptyState icon="🗓" title="No upcoming appointments" hint="Add vet or grooming appointments from a pet's card." />
  return (
    <Card>
      <ul className="divide-y divide-line -mt-1">
        {appointments.map(a => (
          <li key={a.id} className="flex items-center gap-3 py-2.5">
            <div className="flex-1 min-w-0">
              <div className="text-sm text-ink truncate"><span className="text-muted">{a.pet_name}</span> · {a.display_title}</div>
              {a.provider && <div className="text-xs text-muted">{a.provider}{a.location ? ` · ${a.location}` : ''}</div>}
            </div>
            <Link to={calendarDayHref(a.start_at)} className="text-xs text-primary flex-shrink-0">
              {new Date(a.start_at).toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })}
            </Link>
          </li>
        ))}
      </ul>
    </Card>
  )
}

// ===========================================================================
// Page
// ===========================================================================

type Tab = 'pets' | 'reminders' | 'appointments'
const TABS: TabDef<Tab>[] = [
  { key: 'pets', label: 'Pets' },
  { key: 'reminders', label: 'Reminders' },
  { key: 'appointments', label: 'Appointments' },
]

export function PetsPage() {
  const { user } = useAuth()
  const [tab, setTab] = useState<Tab>('pets')
  const [pets, setPets] = useState<Pet[]>([])
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<{ pets: Pet[]; treatments: PetTreatment[]; appointments: PetAppointment[] } | null>(null)

  const load = () => api.getPets().then(setPets).catch(e => setError(errMsg(e)))
  useEffect(() => { load() }, [])

  useEffect(() => {
    const q = query.trim()
    if (q.length < 2) { setResults(null); return }
    const id = setTimeout(() => { api.searchPets(q).then(setResults).catch(e => setError(errMsg(e))) }, 300)
    return () => clearTimeout(id)
  }, [query])

  // Delete is admin/manager-gated in the UI; the backend enforces it regardless.
  const isAdmin = user?.role === 'admin' || user?.role === 'manager'

  return (
    <div className="space-y-5 max-w-5xl mx-auto">
      <PageHeader title="Pets" icon="🐾" subtitle="Pet profiles, treatment reminders and vet appointments." />

      <Input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search pets, treatments and appointments…" />

      {error && (
        <div className="flex items-center justify-between gap-3 bg-danger-soft text-danger text-sm rounded-xl px-4 py-2.5">
          <span>{error}</span>
          <button onClick={() => setError(null)} aria-label="Dismiss">×</button>
        </div>
      )}

      {results !== null ? (
        (results.pets.length + results.treatments.length + results.appointments.length) === 0 ? (
          <EmptyState icon="🔍" title="No matches" hint="Try a pet name, treatment or vet." />
        ) : (
          <div className="flex flex-col gap-4">
            {results.pets.length > 0 && (
              <div className="flex flex-col gap-1.5">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted">Pets</p>
                {results.pets.map(p => <Card key={`p${p.id}`}><span className="text-sm text-ink">{SPECIES_EMOJI[p.species]} {p.name}</span></Card>)}
              </div>
            )}
            {results.treatments.length > 0 && (
              <div className="flex flex-col gap-1.5">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted">Treatments</p>
                {results.treatments.map(t => <Card key={`t${t.id}`}><span className="text-sm text-ink">{t.pet_name} · {t.display_name}</span></Card>)}
              </div>
            )}
            {results.appointments.length > 0 && (
              <div className="flex flex-col gap-1.5">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted">Appointments</p>
                {results.appointments.map(a => <Card key={`a${a.id}`}><span className="text-sm text-ink">{a.pet_name} · {a.display_title}</span></Card>)}
              </div>
            )}
          </div>
        )
      ) : (
        <>
          <Tabs tabs={TABS} active={tab} onChange={setTab} />
          {tab === 'pets' && <PetsTab pets={pets} reload={load} isAdmin={isAdmin} onError={setError} />}
          {tab === 'reminders' && <RemindersTab onError={setError} />}
          {tab === 'appointments' && <AppointmentsTab onError={setError} />}
        </>
      )}
    </div>
  )
}
