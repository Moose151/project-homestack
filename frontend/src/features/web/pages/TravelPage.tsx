import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import { api } from '../../../api/client'
import type { Person, TravelBooking, TravelIdea, TravelItineraryItem, Trip } from '../../../api/types'
import { AssigneeSelect } from '../../../components/AssigneeSelect'
import { Badge } from '../../../components/Badge'
import { Button } from '../../../components/Button'
import { Card } from '../../../components/Card'
import { EmptyState } from '../../../components/EmptyState'
import { Field, Input, Select, Textarea } from '../../../components/Field'
import { Modal } from '../../../components/Modal'
import { PageHeader } from '../../../components/PageHeader'
import { DeleteAction, EditAction, RowActions } from '../../../components/RowActions'
import { ColourPicker } from '../../../components/ColourPicker'
import { Tabs } from '../../../components/Tabs'
import { confirmDialog } from '../../../components/Dialogs'

const errMsg = (error: unknown) => error instanceof Error ? error.message : 'Something went wrong.'
const money = (value: string | null, currency = 'AUD') => value == null ? '—' : Number(value).toLocaleString(undefined, { style: 'currency', currency })
const dateLabel = (value: string | null) => value ? new Date(`${value}T00:00:00`).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' }) : 'Dates not set'

type SharedForm = {
  title: string; destination: string; notes: string; start_date: string; end_date: string; trip_type: string
  colour: string; status: string; flights_required: boolean; accommodation_required: boolean
  participant_ids: number[]; hidden_from_user_ids: number[]; image_urls: string; rough_cost: string
}
const blankForm = (): SharedForm => ({ title: '', destination: '', notes: '', start_date: '', end_date: '', trip_type: 'multi_day', colour: '#2B7FD0', status: 'planning', flights_required: false, accommodation_required: false, participant_ids: [], hidden_from_user_ids: [], image_urls: '', rough_cost: '' })

function PlanForm({ kind, people, existing, onCancel, onSaved, onError }: {
  kind: 'trip' | 'idea'; people: Person[]; existing?: Trip | TravelIdea | null
  onCancel: () => void; onSaved: (trip?: Trip) => void; onError: (message: string) => void
}) {
  const [f, setF] = useState<SharedForm>(() => existing ? {
    title: existing.title, destination: existing.destination, notes: existing.notes,
    start_date: 'start_date' in existing ? existing.start_date || '' : '', end_date: 'end_date' in existing ? existing.end_date || '' : '',
    trip_type: 'trip_type' in existing ? existing.trip_type : 'multi_day',
    colour: existing.colour, status: existing.status, flights_required: existing.flights_required,
    accommodation_required: existing.accommodation_required, participant_ids: existing.participant_ids,
    hidden_from_user_ids: existing.hidden_from_user_ids,
    image_urls: existing.images.map(image => image.image_url).join('\n'), rough_cost: 'rough_cost' in existing ? existing.rough_cost || '' : '',
  } : blankForm())
  const [busy, setBusy] = useState(false)
  const set = <K extends keyof SharedForm>(key: K, value: SharedForm[K]) => setF(previous => ({ ...previous, [key]: value }))
  const peopleWithLogins = people.filter(person => person.linked_user_id)
  const save = async (event: React.FormEvent) => {
    event.preventDefault(); if (!f.title.trim() || !f.destination.trim()) return
    setBusy(true)
    const images = f.image_urls.split('\n').map(value => value.trim()).filter(Boolean).map((image_url, position) => ({ image_url, position, is_cover: position === 0 }))
    const shared = { title: f.title.trim(), destination: f.destination.trim(), notes: f.notes, colour: f.colour,
      flights_required: f.flights_required, accommodation_required: f.accommodation_required,
      participant_ids: f.participant_ids, hidden_from_user_ids: f.hidden_from_user_ids, images }
    try {
      if (kind === 'trip') {
        const data = { ...shared, start_date: f.start_date || null, end_date: (f.trip_type === 'day_trip' ? f.start_date : f.end_date) || null, trip_type: f.trip_type, status: f.status }
        const row = existing ? await api.updateTrip(existing.id, data) : await api.createTrip(data)
        onSaved(row)
      } else {
        const data = { ...shared, rough_cost: f.rough_cost || null, currency: 'AUD' }
        if (existing) await api.updateTravelIdea(existing.id, data); else await api.createTravelIdea(data)
        onSaved()
      }
    } catch (error) { onError(errMsg(error)) } finally { setBusy(false) }
  }
  const formId = `travel-${kind}-form`
  return <Modal
    title={existing ? `Edit ${kind}` : kind === 'trip' ? 'Plan a trip' : 'Add somewhere to go'}
    onClose={onCancel}
    size="full"
    footer={<><Button type="button" variant="ghost" onClick={onCancel}>Cancel</Button><Button type="submit" form={formId} loading={busy} disabled={!f.title.trim() || !f.destination.trim()}>Save</Button></>}
  >
    <form id={formId} onSubmit={save} className="grid gap-3 sm:grid-cols-2">
      <Field label={kind === 'trip' ? 'Trip name' : 'Idea name'}><Input value={f.title} onChange={e => set('title', e.target.value)} placeholder="Japan 2027" data-autofocus /></Field>
      <Field label="Where"><Input value={f.destination} onChange={e => set('destination', e.target.value)} placeholder="Tokyo, Japan" /></Field>
      {kind === 'trip' && <><Field label="Trip type"><Select value={f.trip_type} onChange={e => set('trip_type', e.target.value)}><option value="multi_day">Multi-day trip</option><option value="day_trip">Day trip</option></Select></Field><Field label={f.trip_type === 'day_trip' ? 'Date' : 'Starts'}><Input type="date" value={f.start_date} onChange={e => set('start_date', e.target.value)} /></Field>{f.trip_type !== 'day_trip' && <Field label="Ends"><Input type="date" value={f.end_date} onChange={e => set('end_date', e.target.value)} /></Field>}</>}
      <Field label="Who is going" hint="Nobody selected means the whole household."><AssigneeSelect people={people} value={f.participant_ids} onChange={value => set('participant_ids', value)} /></Field>
      <Field label="Calendar colour"><ColourPicker value={f.colour} onChange={value => set('colour', value)} ariaLabel="Trip calendar colour" /></Field>
      <label className="flex items-center gap-2 rounded-xl border border-line p-3 text-sm"><input type="checkbox" checked={f.flights_required} onChange={e => set('flights_required', e.target.checked)} /> Flights required</label>
      <label className="flex items-center gap-2 rounded-xl border border-line p-3 text-sm"><input type="checkbox" checked={f.accommodation_required} onChange={e => set('accommodation_required', e.target.checked)} /> Accommodation required</label>
      {kind === 'trip' && <Field label="Planning state"><Select value={f.status} onChange={e => set('status', e.target.value)}><option value="planning">Planning</option><option value="ready_to_book">Ready to book</option><option value="booked">Booked</option><option value="travelling">Travelling</option><option value="completed">Completed</option><option value="cancelled">Cancelled</option></Select></Field>}
      {kind === 'idea' && <Field label="Rough total cost"><Input type="number" min="0" value={f.rough_cost} onChange={e => set('rough_cost', e.target.value)} placeholder="0.00" /></Field>}
      <Field label="Shared notes" className="sm:col-span-2"><Textarea value={f.notes} onChange={e => set('notes', e.target.value)} rows={4} placeholder="Ideas, links and things to remember…" /></Field>
      <Field label="Image links" hint="One public image URL per line; the first becomes the cover." className="sm:col-span-2"><Textarea value={f.image_urls} onChange={e => set('image_urls', e.target.value)} rows={3} placeholder="https://…/photo.jpg" /></Field>
      {peopleWithLogins.length > 0 && <Field label="Keep this a surprise" hint="Selected users will not see it in Travel, Calendar, Agenda, notifications, Search or Corners." className="sm:col-span-2"><div className="flex flex-wrap gap-2">{peopleWithLogins.map(person => { const userId = person.linked_user_id!; const hidden = f.hidden_from_user_ids.includes(userId); return <button key={person.id} type="button" onClick={() => set('hidden_from_user_ids', hidden ? f.hidden_from_user_ids.filter(id => id !== userId) : [...f.hidden_from_user_ids, userId])} className={`min-h-11 rounded-xl border px-3 text-sm ${hidden ? 'border-warning bg-warning-soft text-warning' : 'border-line text-muted'}`}>{hidden ? '🙈 Hidden from ' : 'Hide from '}{person.preferred_name || person.display_name}</button> })}</div></Field>}
    </form>
  </Modal>
}

const localDateTime = (value: string | null) => {
  if (!value) return ''
  const date = new Date(value)
  return new Date(date.getTime() - date.getTimezoneOffset() * 60_000).toISOString().slice(0, 16)
}

function BookingForm({ trip, initialKind, existing, onSaved, onCancel, onError }: { trip: Trip; initialKind: TravelBooking['kind']; existing?: TravelBooking | null; onSaved: () => void; onCancel: () => void; onError: (m: string) => void }) {
  const [f, setF] = useState(() => existing ? {
    kind: existing.kind, title: existing.title, provider: existing.provider,
    quoted_amount: existing.quoted_amount || '', booked_amount: existing.booked_amount || '',
    status: existing.status, start_at: localDateTime(existing.start_at), end_at: localDateTime(existing.end_at),
    book_by: existing.book_by || '', flight_number: existing.flight_number,
    departure_airport: existing.departure_airport, arrival_airport: existing.arrival_airport,
    location: existing.location, booking_reference: existing.booking_reference, notes: existing.notes,
  } : { kind: initialKind, title: initialKind === 'flight' ? 'Flights' : initialKind === 'accommodation' ? 'Accommodation' : '', provider: '', quoted_amount: '', booked_amount: '', status: 'planned', start_at: '', end_at: '', book_by: '', flight_number: '', departure_airport: '', arrival_airport: '', location: '', booking_reference: '', notes: '' })
  const [busy, setBusy] = useState(false); const set = (key: string, value: string) => setF(previous => ({ ...previous, [key]: value }))
  const save = async (event: React.FormEvent) => { event.preventDefault(); if (!f.title.trim()) return; setBusy(true); try { const data = { ...f, quoted_amount: f.quoted_amount || null, booked_amount: f.booked_amount || null, start_at: f.start_at ? new Date(f.start_at).toISOString() : null, end_at: f.end_at ? new Date(f.end_at).toISOString() : null, book_by: f.book_by || null, currency: 'AUD' }; if (existing) await api.updateTravelBooking(existing.id, data); else await api.createTravelBooking(trip.id, data); onSaved() } catch (error) { onError(errMsg(error)) } finally { setBusy(false) } }
  const formId = 'travel-booking-form'
  return <Modal
    title={existing ? `Edit ${existing.title}` : 'Add a booking'}
    onClose={onCancel}
    size="full"
    footer={<><Button type="button" variant="ghost" onClick={onCancel}>Cancel</Button><Button type="submit" form={formId} loading={busy}>{existing ? 'Save changes' : 'Add booking'}</Button></>}
  ><form id={formId} onSubmit={save} className="grid gap-3 sm:grid-cols-2">
    <Field label="Type"><Select value={f.kind} onChange={e => set('kind', e.target.value)}><option value="flight">Flight</option><option value="accommodation">Accommodation</option><option value="transport">Transport</option><option value="activity">Activity</option><option value="restaurant">Restaurant</option><option value="other">Other</option></Select></Field>
    <Field label="What is it?"><Input value={f.title} onChange={e => set('title', e.target.value)} data-autofocus /></Field><Field label="Provider"><Input value={f.provider} onChange={e => set('provider', e.target.value)} /></Field><Field label="Quoted whole-party total"><Input type="number" min="0" value={f.quoted_amount} onChange={e => set('quoted_amount', e.target.value)} /></Field>
    <Field label="Book by"><Input type="date" value={f.book_by} onChange={e => set('book_by', e.target.value)} /></Field><Field label="Status"><Select value={f.status} onChange={e => set('status', e.target.value)}><option value="researching">Researching</option><option value="planned">Planned</option><option value="booked">Booked</option></Select></Field>
    <Field label={f.kind === 'accommodation' ? 'Check-in' : 'Starts / departs'}><Input type="datetime-local" value={f.start_at} onChange={e => set('start_at', e.target.value)} /></Field><Field label={f.kind === 'accommodation' ? 'Check-out' : 'Ends / arrives'}><Input type="datetime-local" value={f.end_at} onChange={e => set('end_at', e.target.value)} /></Field>
    {f.kind === 'flight' && <><Field label="Flight number"><Input value={f.flight_number} onChange={e => set('flight_number', e.target.value)} /></Field><Field label="Route"><div className="flex gap-2"><Input value={f.departure_airport} onChange={e => set('departure_airport', e.target.value)} placeholder="BNE" /><Input value={f.arrival_airport} onChange={e => set('arrival_airport', e.target.value)} placeholder="NRT" /></div></Field></>}
    <Field label="Location"><Input value={f.location} onChange={e => set('location', e.target.value)} /></Field><Field label="Booking reference"><Input value={f.booking_reference} onChange={e => set('booking_reference', e.target.value)} /></Field>
    <Field label="Notes" className="sm:col-span-2"><Textarea value={f.notes} onChange={e => set('notes', e.target.value)} /></Field>
  </form></Modal>
}

// One option per calendar day of the trip, e.g. "Day 1 · 12 Aug". Empty when dates aren't set
// yet — itinerary items can still exist as unscheduled "options to do" in that case.
function tripDays(trip: Trip): { date: string; label: string }[] {
  if (!trip.start_date) return []
  const end = trip.end_date || trip.start_date
  const days: { date: string; label: string }[] = []
  const cursor = new Date(`${trip.start_date}T00:00:00`)
  const last = new Date(`${end}T00:00:00`)
  let n = 1
  while (cursor <= last && n <= 60) {
    days.push({ date: cursor.toISOString().slice(0, 10), label: `Day ${n} · ${cursor.toLocaleDateString(undefined, { day: 'numeric', month: 'short' })}` })
    cursor.setDate(cursor.getDate() + 1); n += 1
  }
  return days
}

function ItineraryForm({ trip, existing, onCancel, onSaved, onError }: {
  trip: Trip; existing?: TravelItineraryItem | null
  onCancel: () => void; onSaved: () => void; onError: (m: string) => void
}) {
  const days = tripDays(trip)
  const [f, setF] = useState(() => existing ? {
    title: existing.title, location: existing.location, notes: existing.notes,
    scheduled_date: existing.scheduled_date || '', scheduled_time: existing.scheduled_time || '',
  } : { title: '', location: '', notes: '', scheduled_date: '', scheduled_time: '' })
  const [busy, setBusy] = useState(false)
  const set = (key: keyof typeof f, value: string) => setF(previous => ({ ...previous, [key]: value }))
  const save = async (event: React.FormEvent) => {
    event.preventDefault(); if (!f.title.trim()) return
    setBusy(true)
    const data = { title: f.title.trim(), location: f.location, notes: f.notes, scheduled_date: f.scheduled_date || null, scheduled_time: f.scheduled_date ? (f.scheduled_time || null) : null }
    try {
      if (existing) await api.updateItineraryItem(existing.id, data)
      else await api.createItineraryItem(trip.id, data)
      onSaved()
    } catch (error) { onError(errMsg(error)) } finally { setBusy(false) }
  }
  const formId = 'travel-itinerary-form'
  return <Modal
    title={existing ? `Edit ${existing.title}` : 'Add something to do'}
    onClose={onCancel}
    size="full"
    footer={<><Button type="button" variant="ghost" onClick={onCancel}>Cancel</Button><Button type="submit" form={formId} loading={busy} disabled={!f.title.trim()}>{existing ? 'Save changes' : 'Add to itinerary'}</Button></>}
  ><form id={formId} onSubmit={save} className="grid gap-3 sm:grid-cols-2">
    <Field label="What is it?" className="sm:col-span-2"><Input value={f.title} onChange={e => set('title', e.target.value)} placeholder="TeamLab museum" data-autofocus /></Field>
    <Field label="Day" hint={days.length ? undefined : 'Set trip dates to assign a day, or leave as an option to do.'}>
      <Select value={f.scheduled_date} onChange={e => set('scheduled_date', e.target.value)}>
        <option value="">Not yet scheduled — an option to do</option>
        {days.map(day => <option key={day.date} value={day.date}>{day.label}</option>)}
      </Select>
    </Field>
    <Field label="Time (optional)"><Input type="time" value={f.scheduled_time} onChange={e => set('scheduled_time', e.target.value)} disabled={!f.scheduled_date} /></Field>
    <Field label="Location"><Input value={f.location} onChange={e => set('location', e.target.value)} /></Field>
    <Field label="Notes" className="sm:col-span-2"><Textarea value={f.notes} onChange={e => set('notes', e.target.value)} rows={2} /></Field>
  </form></Modal>
}

function ItineraryRow({ item, onEdit, onDeleted, onError }: {
  item: TravelItineraryItem; onEdit: () => void; onDeleted: () => void; onError: (m: string) => void
}) {
  const remove = async () => {
    if (!(await confirmDialog({ title: `Remove ${item.title}?`, confirmLabel: 'Remove' }))) return
    try { await api.deleteItineraryItem(item.id); onDeleted() } catch (error) { onError(errMsg(error)) }
  }
  return <div className="flex items-start gap-3 rounded-xl border border-line p-3">
    <div className="min-w-0 flex-1">
      <p className="font-bold text-ink">{item.title}</p>
      <p className="text-xs text-muted">
        {item.scheduled_time && <>{new Date(`2000-01-01T${item.scheduled_time}`).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })} · </>}
        {item.location || 'No location set'}
      </p>
      {item.notes && <p className="mt-1 text-xs text-muted-strong">{item.notes}</p>}
    </div>
    <EditAction label={item.title} onClick={onEdit} />
    <DeleteAction label={item.title} onClick={remove} />
  </div>
}

function TripDetail({ trip, people, onBack, onDeleted, reload, onError }: { trip: Trip; people: Person[]; onBack: () => void; onDeleted: () => Promise<void>; reload: () => void; onError: (m: string) => void }) {
  const [editing, setEditing] = useState(false); const [deleting, setDeleting] = useState(false); const [bookingKind, setBookingKind] = useState<TravelBooking['kind'] | null>(null); const [editingBooking, setEditingBooking] = useState<TravelBooking | null>(null)
  const [addingItinerary, setAddingItinerary] = useState(false); const [editingItineraryItem, setEditingItineraryItem] = useState<TravelItineraryItem | null>(null)
  const requiredDone = trip.booking_progress.required_types.every(kind => trip.booking_progress.booked_required_types.includes(kind))
  const setBooked = async (booking: TravelBooking) => { try { await api.updateTravelBooking(booking.id, { status: booking.status === 'booked' ? 'planned' : 'booked', booked_amount: booking.booked_amount || booking.quoted_amount }); reload() } catch (error) { onError(errMsg(error)) } }
  const deleteTrip = async () => {
    if (!(await confirmDialog({ title: `Delete ${trip.title}?`, message: 'This removes the trip, its bookings, deadlines and Calendar entries.', confirmLabel: 'Delete trip' }))) return
    setDeleting(true)
    try { await api.deleteTrip(trip.id); await onDeleted() }
    catch (error) { onError(errMsg(error)) }
    finally { setDeleting(false) }
  }
  if (editing) return <PlanForm kind="trip" people={people} existing={trip} onCancel={() => setEditing(false)} onSaved={() => { setEditing(false); reload() }} onError={onError} />
  return <div className="flex flex-col gap-4"><button onClick={onBack} className="self-start text-sm text-muted hover:text-primary">← All trips</button>
    {trip.images.length > 0 && <div className="grid grid-cols-2 gap-2 overflow-hidden rounded-2xl sm:grid-cols-4">{trip.images.slice(0, 4).map((image, index) => <img key={image.id} src={image.image_url} alt={image.caption || ''} className={`h-40 w-full object-cover ${index === 0 ? 'col-span-2 sm:h-52' : 'sm:h-52'}`} />)}</div>}
    <Card><div className="flex items-start justify-between gap-3"><div><div className="flex items-center gap-2"><span className="h-4 w-4 rounded-full" style={{ backgroundColor: trip.colour }} /><h1 className="text-xl font-black text-ink">{trip.title}</h1><Badge tone={trip.status === 'booked' ? 'success' : 'neutral'}>{trip.status.replace(/_/g, ' ')}</Badge>{trip.trip_type === 'day_trip' && <Badge tone="primary">Day trip</Badge>}</div><p className="mt-1 text-muted">{trip.destination} · {dateLabel(trip.start_date)}{trip.end_date && trip.end_date !== trip.start_date ? ` – ${dateLabel(trip.end_date)}` : ''}</p></div><RowActions><EditAction onClick={() => setEditing(true)} label={trip.title} disabled={deleting} /><DeleteAction onClick={deleteTrip} label={trip.title} disabled={deleting} /></RowActions></div>{trip.notes && <p className="mt-4 whitespace-pre-wrap text-sm text-muted-strong">{trip.notes}</p>}</Card>
    <div className="grid gap-3 sm:grid-cols-3"><Card><p className="text-xs font-bold uppercase text-muted">Bookings</p><p className="mt-1 text-2xl font-black">{trip.booking_progress.booked_count}/{trip.booking_progress.component_count}</p><p className="text-xs text-muted">{requiredDone ? 'Required travel covered' : 'Still needs booking'}</p></Card>{trip.cost_summary.map(row => <Card key={row.currency}><p className="text-xs font-bold uppercase text-muted">Expected · {row.currency}</p><p className="mt-1 text-2xl font-black">{money(row.quoted, row.currency)}</p><p className="text-xs text-muted">{money(row.booked, row.currency)} booked</p></Card>)}</div>
    {(bookingKind || editingBooking) && <BookingForm trip={trip} initialKind={bookingKind || editingBooking!.kind} existing={editingBooking} onCancel={() => { setBookingKind(null); setEditingBooking(null) }} onSaved={() => { setBookingKind(null); setEditingBooking(null); reload() }} onError={onError} />}
    <Card title="Travel & stays"><div className="mb-3 flex flex-wrap gap-2">{trip.flights_required && <Button size="sm" variant="secondary" onClick={() => setBookingKind('flight')}>+ Flight</Button>}{trip.accommodation_required && <Button size="sm" variant="secondary" onClick={() => setBookingKind('accommodation')}>+ Accommodation</Button>}<Button size="sm" variant="ghost" onClick={() => setBookingKind('activity')}>+ Other booking</Button></div>
      {!trip.bookings.length ? <p className="text-sm text-muted">No booking options yet.</p> : <div className="space-y-2">{trip.bookings.map(booking => <div key={booking.id} className="rounded-xl border border-line p-3"><div className="flex items-start gap-3"><button onClick={() => setBooked(booking)} className={`mt-0.5 grid h-6 w-6 place-items-center rounded-full border-2 ${booking.status === 'booked' ? 'border-success bg-success text-white' : 'border-line-strong'}`}>{booking.status === 'booked' ? '✓' : ''}</button><div className="min-w-0 flex-1"><p className="font-bold text-ink">{booking.title}</p><p className="text-xs text-muted">{booking.kind} · {booking.provider || 'Provider not set'} · {money(booking.booked_amount || booking.quoted_amount, booking.currency)}</p>{booking.book_by && booking.status !== 'booked' && <p className="mt-1 text-xs font-semibold text-warning">Book by {dateLabel(booking.book_by)} · shown in Agenda and Calendar</p>}{booking.start_at && <p className="mt-1 text-xs text-muted">{new Date(booking.start_at).toLocaleString()}{booking.end_at ? ` → ${new Date(booking.end_at).toLocaleString()}` : ''}</p>}</div><EditAction label={booking.title} onClick={() => { setBookingKind(null); setEditingBooking(booking) }} /><DeleteAction label={booking.title} onClick={async () => { if (await confirmDialog({ title: `Delete ${booking.title}?`, confirmLabel: 'Delete' })) { await api.deleteTravelBooking(booking.id); reload() } }} /></div></div>)}</div>}
    </Card>
    {(addingItinerary || editingItineraryItem) && <ItineraryForm trip={trip} existing={editingItineraryItem} onCancel={() => { setAddingItinerary(false); setEditingItineraryItem(null) }} onSaved={() => { setAddingItinerary(false); setEditingItineraryItem(null); reload() }} onError={onError} />}
    <Card title="Things to do">
      <div className="mb-3"><Button size="sm" variant="secondary" onClick={() => setAddingItinerary(true)}>+ Add something to do</Button></div>
      {!trip.itinerary_items.length ? <p className="text-sm text-muted">Nothing planned yet — add ideas here, with or without a day.</p> : (() => {
        const days = tripDays(trip)
        const dayDates = new Set(days.map(day => day.date))
        const forDate = (date: string) => trip.itinerary_items.filter(item => item.scheduled_date === date)
        const extraDates = [...new Set(trip.itinerary_items.filter(item => item.scheduled_date && !dayDates.has(item.scheduled_date)).map(item => item.scheduled_date as string))].sort()
        const unscheduled = trip.itinerary_items.filter(item => !item.scheduled_date)
        const group = (label: string, items: TravelItineraryItem[]) => !items.length ? null : (
          <div key={label}><p className="mb-2 text-xs font-bold uppercase text-muted">{label}</p><div className="space-y-2">
            {items.map(item => <ItineraryRow key={item.id} item={item} onEdit={() => setEditingItineraryItem(item)} onDeleted={reload} onError={onError} />)}
          </div></div>
        )
        return <div className="space-y-4">
          {days.map(day => group(day.label, forDate(day.date)))}
          {extraDates.map(date => group(dateLabel(date), forDate(date)))}
          {group('Options to do — not yet scheduled', unscheduled)}
        </div>
      })()}
    </Card>
  </div>
}

export function TravelPage() {
  const [params, setParams] = useSearchParams(); const tab = params.get('tab') === 'ideas' ? 'ideas' : 'trips'; const selectedId = Number(params.get('trip') || 0); const selectedIdeaId = Number(params.get('idea') || 0)
  const [trips, setTrips] = useState<Trip[]>([]); const [ideas, setIdeas] = useState<TravelIdea[]>([]); const [people, setPeople] = useState<Person[]>([]); const [creating, setCreating] = useState(false); const [editingIdea, setEditingIdea] = useState<TravelIdea | null>(null); const [error, setError] = useState<string | null>(null); const [loading, setLoading] = useState(true)
  const load = async () => { try { const [tripRows, ideaRows, peopleRows] = await Promise.all([api.getTrips(), api.getTravelIdeas(), api.getPeople()]); setTrips(tripRows); setIdeas(ideaRows); setPeople(peopleRows) } catch (e) { setError(errMsg(e)) } finally { setLoading(false) } }
  useEffect(() => { void load() }, [])
  useEffect(() => { if (selectedIdeaId && ideas.length) setEditingIdea(ideas.find(row => row.id === selectedIdeaId) ?? null) }, [selectedIdeaId, ideas])
  const selected = trips.find(row => row.id === selectedId)
  const setTab = (next: string) => { setParams(next === 'ideas' ? { tab: 'ideas' } : {}); setCreating(false); setEditingIdea(null) }
  if (selected) return <TripDetail trip={selected} people={people} onBack={() => setParams({})} onDeleted={async () => { setParams({}); await load() }} reload={load} onError={setError} />
  return <div className="flex flex-col gap-4"><PageHeader title="Trips & holidays" icon="✈️" subtitle="From somewhere you would love to go through to fully booked." actions={<Button size="sm" onClick={() => setCreating(true)}>+ {tab === 'ideas' ? 'Destination' : 'Trip'}</Button>} />
    <Tabs tabs={[{ key: 'trips', label: 'Trips', badge: trips.length || undefined }, { key: 'ideas', label: 'To go', badge: ideas.filter(row => row.status === 'active').length || undefined }]} active={tab} onChange={setTab} />
    {error && <div className="rounded-xl bg-danger-soft p-3 text-sm text-danger">{error}</div>}
    {(creating || editingIdea) && <PlanForm kind={tab === 'ideas' ? 'idea' : 'trip'} people={people} existing={editingIdea} onCancel={() => { setCreating(false); setEditingIdea(null) }} onSaved={(trip) => { setCreating(false); setEditingIdea(null); void load(); if (trip) setParams({ trip: String(trip.id) }) }} onError={setError} />}
    {loading ? <div className="h-40 animate-pulse rounded-2xl bg-sunken" /> : tab === 'trips' ? (!trips.length ? <EmptyState icon="✈️" title="No trips planned" hint="Create a trip, or promote an idea from To go when you are ready." /> : <div className="grid gap-4 lg:grid-cols-2">{trips.map(trip => <button key={trip.id} onClick={() => setParams({ trip: String(trip.id) })} className="overflow-hidden rounded-2xl border border-line bg-surface text-left transition hover:-translate-y-0.5 hover:shadow-sm">{trip.images[0] && <img src={trip.images[0].image_url} alt="" className="h-36 w-full object-cover" />}<div className="p-4"><div className="flex items-center gap-2"><span className="h-3 w-3 rounded-full" style={{ backgroundColor: trip.colour }} /><h2 className="font-black text-ink">{trip.title}</h2><Badge tone={trip.status === 'booked' ? 'success' : 'neutral'}>{trip.status.replace(/_/g, ' ')}</Badge>{trip.trip_type === 'day_trip' && <Badge tone="primary">Day trip</Badge>}</div><p className="mt-1 text-sm text-muted">{trip.destination} · {dateLabel(trip.start_date)}</p><p className="mt-3 text-xs text-muted">{trip.booking_progress.booked_count}/{trip.booking_progress.component_count} booked{trip.cost_summary[0] ? ` · ${money(trip.cost_summary[0].quoted, trip.cost_summary[0].currency)} expected` : ''}</p></div></button>)}</div>)
      : (!ideas.filter(row => row.status !== 'archived').length ? <EmptyState icon="🗺️" title="Nowhere on the list yet" hint="Add places the household would love to visit without planning everything today." /> : <div className="grid gap-4 lg:grid-cols-2">{ideas.filter(row => row.status !== 'archived').map(idea => <Card key={idea.id}>{idea.images[0] && <img src={idea.images[0].image_url} alt="" className="-mx-5 -mt-3 mb-3 h-36 w-[calc(100%+2.5rem)] rounded-t-2xl object-cover" />}<h2 className="font-black text-ink">{idea.title}</h2><p className="text-sm text-muted">{idea.destination}{idea.rough_cost ? ` · roughly ${money(idea.rough_cost, idea.currency)}` : ''}</p><div className="mt-3 flex gap-2">{idea.status === 'active' ? <Button size="sm" onClick={async () => { try { const trip = await api.convertTravelIdea(idea.id); await load(); setParams({ trip: String(trip.id) }) } catch (e) { setError(errMsg(e)) } }}>Plan this trip →</Button> : <Badge tone="success">Converted</Badge>}<EditAction label={idea.title} onClick={() => { setCreating(false); setEditingIdea(idea) }} /><DeleteAction label={idea.title} onClick={async () => { if (await confirmDialog({ title: `Remove ${idea.title}?`, confirmLabel: 'Remove' })) { await api.deleteTravelIdea(idea.id); load() } }} /></div></Card>)}</div>)}
  </div>
}
