import { useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../../api/client'
import type {
  CalendarEvent, CalendarEventWrite, Person, RotatingSchedule,
  RotatingScheduleOccurrence, RotatingScheduleWrite,
} from '../../../api/types'
import { Button } from '../../../components/Button'
import { Modal } from '../../../components/Modal'
import { Field, Input, Select } from '../../../components/Field'
import { PageHeader } from '../../../components/PageHeader'
import { EmptyState } from '../../../components/EmptyState'
import { DateTimeField } from '../../../components/DateTimeField'
import { Popover } from '../../../components/Popover'
import { AssigneeSelect, personIdForUser } from '../../../components/AssigneeSelect'
import { parseQuickEvent, quickEventPreview } from '../../../lib/quickParse'
import { sourceColour, sourcePath } from '../../../lib/sourceLinks'
import { useAuth } from '../../auth/AuthContext'
import { useStacks } from '../../stacks/StacksContext'
import { useUrlAction } from '../../../hooks/useUrlTab'
import { confirmDialog } from '../../../components/Dialogs'
import { ColourPicker } from '../../../components/ColourPicker'
import { isPhoneViewport } from '../../../lib/viewport'

// ---------------------------------------------------------------------------
// Date helpers (no external deps)
// ---------------------------------------------------------------------------

type View = 'month' | 'week' | 'day' | 'agenda'

const errMsg = (e: unknown) => (e instanceof Error ? e.message : 'Something went wrong.')

/** Which filter layer an event belongs to. Calendar sources are layers in their own right,
 *  rather than disappearing into the household's own "HomeStack" bucket. */
function layerKey(event: CalendarEvent) {
  if (event.calendar_source_id) return `src:${event.calendar_source_id}`
  return event.source_node || '__direct__'
}
const startOfDay = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate())
const addDays = (d: Date, n: number) => { const x = new Date(d); x.setDate(x.getDate() + n); return x }
const addMonths = (d: Date, n: number) => {
  const x = new Date(d.getFullYear(), d.getMonth() + n, 1)
  const lastDay = new Date(x.getFullYear(), x.getMonth() + 1, 0).getDate()
  x.setDate(Math.min(d.getDate(), lastDay))
  return x
}
const sameDay = (a: Date, b: Date) => a.toDateString() === b.toDateString()
const isToday = (d: Date) => sameDay(d, new Date())
const dateKey = (d: Date) => {
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}
const dateFromKey = (value: string) => new Date(`${value}T00:00:00`)

function startOfWeek(d: Date, weekStart: number) {
  const x = startOfDay(d)
  const diff = (x.getDay() - weekStart + 7) % 7
  return addDays(x, -diff)
}

function monthGrid(anchor: Date, weekStart: number): Date[] {
  const first = new Date(anchor.getFullYear(), anchor.getMonth(), 1)
  const gridStart = startOfWeek(first, weekStart)
  return Array.from({ length: 42 }, (_, i) => addDays(gridStart, i))
}

function fmtTime(iso: string, time24: boolean) {
  return new Date(iso).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit', hour12: !time24 })
}

// Node accents and source deep links come from the shared module so the Calendar and the
// Hub's Upcoming card can never drift apart.
const DEFAULT_COLOUR = '#9CA3AF'

// ---------------------------------------------------------------------------
// Event modal (create / edit standalone events) — common fields up top, the
// rest collapsed under "More options" so the frequent case is just title + start.
// ---------------------------------------------------------------------------

export function EventModal({
  event, defaultDate, people, defaultAssignee, onClose, onSaved, onError,
}: {
  event: CalendarEvent | null
  defaultDate: Date | null
  people: Person[]
  defaultAssignee: number[]
  onClose: () => void
  onSaved: () => void
  onError: (m: string) => void
}) {
  // A source-managed entry is read-only locally: the next sync would overwrite any edit, so it
  // gets the same detail panel as a node-synced event rather than pretending to be editable.
  const synced = !!event?.is_synced || !!event?.is_source_managed
  const base = event ? new Date(event.start_at) : (defaultDate ?? new Date())
  const [f, setF] = useState({
    title: event?.title ?? '',
    // 'reminder' is offered only when creating: it saves an Atlas reminder through the shared
    // reminder API rather than a calendar event, so it is a choice of *what to create*, not a
    // calendar event_kind. Existing entries keep their own kind.
    event_kind: event?.event_kind === 'appointment' ? 'appointment' : 'event',
    body: '',
    notifications_enabled: true,
    start_at: base.toISOString(),
    end_at: event?.end_at ?? '',
    is_all_day: event?.is_all_day ?? false,
    location: event?.location ?? '',
    provider: event?.provider ?? '',
    contact: event?.contact ?? '',
    colour: event?.colour ?? '',
    assigned_to_person_ids: event ? event.assigned_to_person_ids : defaultAssignee,
    visibility: event?.visibility ?? 'household',
  })
  // Reveal advanced fields automatically when editing an event that already uses them.
  const [showMore, setShowMore] = useState(
    !!(event && (event.end_at || event.location || event.assigned_to_person_ids.length > 0 || event.colour || event.visibility === 'private')),
  )
  const [saving, setSaving] = useState(false)
  const set = (k: string, v: unknown) => setF(prev => ({ ...prev, [k]: v }))

  const isReminder = !event && f.event_kind === 'reminder'

  const save = async () => {
    if (!f.title.trim()) return
    setSaving(true)
    try {
      if (isReminder) {
        // The real reminder record — same model and API the Atlas reminders tab uses, so it
        // schedules notifications and syncs itself back onto the calendar.
        await api.createReminder({
          title: f.title.trim(),
          body: f.body.trim(),
          due_at: new Date(f.start_at).toISOString(),
          is_all_day: f.is_all_day,
          assigned_to_person_ids: f.assigned_to_person_ids,
          notifications_enabled: f.notifications_enabled,
        })
        onSaved()
        return
      }
      const payload: CalendarEventWrite = {
        title: f.title.trim(),
        event_kind: f.event_kind as 'event' | 'appointment',
        start_at: new Date(f.start_at).toISOString(),
        end_at: f.end_at ? new Date(f.end_at).toISOString() : null,
        is_all_day: f.is_all_day,
        location: f.location,
        provider: f.provider,
        contact: f.contact,
        colour: f.colour,
        assigned_to_person_ids: f.assigned_to_person_ids,
        visibility: f.visibility,
      }
      if (event) await api.updateEvent(event.id, payload)
      else await api.createEvent(payload)
      onSaved()
    } catch (e) {
      onError(errMsg(e))
    } finally {
      setSaving(false)
    }
  }

  const remove = async () => {
    if (!event || !(await confirmDialog({ title: `Delete "${event.title}"?`, confirmLabel: 'Delete' }))) return
    try { await api.deleteEvent(event.id); onSaved() } catch (e) { onError(errMsg(e)) }
  }

  const title = event ? (synced ? 'Event' : 'Edit event') : isReminder ? 'New reminder' : 'New event'

  if (synced) {
    const href = sourcePath(event!)
    return (
      <Modal title={title} onClose={onClose} size="sm">
        <div className="flex flex-col gap-2 text-sm">
          <p className="font-medium text-ink">{event!.title}</p>
          <p className="text-muted">{new Date(event!.start_at).toLocaleString()}</p>
          {event!.location && <p className="text-muted">📍 {event!.location}</p>}
          {event!.description && <p className="whitespace-pre-wrap text-muted">{event!.description}</p>}
          <p className="mt-1 text-xs text-muted">
            {event!.is_source_managed
              ? <>This entry comes from <span className="font-medium">{event!.calendar_source_name}</span> and is kept up to date automatically.</>
              : <>This event comes from <span className="font-medium capitalize">{event!.source_node}</span> and is edited there, not on the calendar.</>}
          </p>
          {event!.is_source_managed && (
            <Link
              to="/calendar/sources"
              onClick={onClose}
              className="mt-2 flex min-h-11 items-center justify-between rounded-xl bg-primary-soft px-3 py-2 text-sm font-semibold text-primary"
            >
              Calendar source settings <span aria-hidden>→</span>
            </Link>
          )}
          {!event!.is_source_managed && href && (
            <Link
              to={href}
              onClick={onClose}
              className="mt-2 flex min-h-11 items-center justify-between rounded-xl bg-primary-soft px-3 py-2 text-sm font-semibold text-primary"
            >
              Open the source record <span aria-hidden>→</span>
            </Link>
          )}
        </div>
      </Modal>
    )
  }

  return (
    <Modal
      title={title}
      onClose={onClose}
      // docs/36 §6.2: create/edit becomes a near/full-height phone sheet with sticky Save — the
      // 'full' size is edge-to-edge/near-viewport-height on phone, capped at 'lg' on desktop.
      size="full"
      footer={
        <>
          {event && <button onClick={remove} className="mr-auto text-sm text-danger hover:underline">Delete</button>}
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button onClick={save} loading={saving} disabled={!f.title.trim()}>Save</Button>
        </>
      }
    >
      <div className="flex flex-col gap-3">
        <Field label="Type">
          <Select aria-label="Type" value={f.event_kind} onChange={e => set('event_kind', e.target.value)}>
            <option value="event">Event</option>
            <option value="appointment">Appointment</option>
            {!event && <option value="reminder">Reminder</option>}
          </Select>
        </Field>
        <Input placeholder="Title" value={f.title} onChange={e => set('title', e.target.value)} data-autofocus />
        <Field label={isReminder ? 'Remind me at' : 'Start'}>
          <DateTimeField
            value={f.start_at}
            allDay={f.is_all_day}
            onChange={({ value, allDay }) => setF(prev => ({ ...prev, start_at: value ?? prev.start_at, is_all_day: allDay }))}
          />
        </Field>

        {isReminder ? (
          <div className="flex flex-col gap-3">
            <Field label="Notes (optional)">
              <Input placeholder="Anything worth remembering" value={f.body} onChange={e => set('body', e.target.value)} />
            </Field>
            <Field label="Remind">
              <AssigneeSelect people={people}
                value={f.assigned_to_person_ids || null}
                onChange={v => set('assigned_to_person_ids', v ?? 0)} />
            </Field>
            <label className="flex min-h-11 items-center gap-2 text-sm text-ink">
              <input
                type="checkbox"
                checked={f.notifications_enabled}
                onChange={e => set('notifications_enabled', e.target.checked)}
              />
              Send a notification when it is time
            </label>
            <p className="text-xs text-muted">
              Saved in Lists &amp; Notes and shown on your calendar. Open the reminder to edit it.
            </p>
          </div>
        ) : !showMore ? (
          <button
            type="button"
            onClick={() => setShowMore(true)}
            className="self-start text-sm font-medium text-primary hover:underline"
          >
            ▾ More options
          </button>
        ) : (
          <div className="flex flex-col gap-3 border-t border-line pt-3">
            <Field label="End (optional)">
              <DateTimeField
                value={f.end_at || null}
                allDay={f.is_all_day}
                allowAllDay={false}
                onChange={({ value }) => set('end_at', value ?? '')}
              />
            </Field>
            <Field label="Location (optional)">
              <Input placeholder="Where" value={f.location} onChange={e => set('location', e.target.value)} />
            </Field>
            {f.event_kind === 'appointment' && <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Provider (optional)"><Input placeholder="Doctor, salon, business…" value={f.provider} onChange={e => set('provider', e.target.value)} /></Field>
              <Field label="Contact (optional)"><Input placeholder="Phone, email or booking reference" value={f.contact} onChange={e => set('contact', e.target.value)} /></Field>
            </div>}
            <div className="grid grid-cols-2 gap-2">
              <Field label="Assigned to">
                <AssigneeSelect people={people}
                  value={f.assigned_to_person_ids || null}
                  onChange={v => set('assigned_to_person_ids', v ?? 0)} />
              </Field>
              <Field label="Visibility">
                <Select value={f.visibility} onChange={e => set('visibility', e.target.value)}>
                  <option value="household">Household</option>
                  <option value="private">Private</option>
                </Select>
              </Field>
            </div>
            <Field label="Colour">
              <ColourPicker value={f.colour} onChange={value => set('colour', value)} allowClear ariaLabel="Event colour" />
            </Field>
          </div>
        )}
      </div>
    </Modal>
  )
}

// ---------------------------------------------------------------------------
// Inline quick-add (day + agenda views) — one line, parses a time from the text.
// ---------------------------------------------------------------------------

function QuickAddBar({ baseDate, time24, onAdd }: {
  baseDate: Date
  time24: boolean
  onAdd: (text: string) => Promise<void>
}) {
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const preview = quickEventPreview(text, baseDate, time24)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    const t = text.trim()
    if (!t) return
    setBusy(true)
    try { await onAdd(t); setText('') } finally { setBusy(false) }
  }

  return (
    <form onSubmit={submit} className="rounded-2xl border border-line bg-surface p-2">
      <div className="flex items-center gap-2">
        <span className="pl-1.5 text-muted-strong" aria-hidden>✎</span>
        <input
          value={text}
          onChange={e => setText(e.target.value)}
          placeholder="Try “Dentist 3pm”"
          className="min-h-11 min-w-0 flex-1 bg-transparent text-sm text-ink outline-none placeholder:text-muted"
        />
        <Button type="submit" loading={busy} disabled={!text.trim()}>Add</Button>
      </div>
      {preview && (
        <p className="px-7 pb-1 text-xs text-muted">Adds to {preview} — open the event afterwards for more detail.</p>
      )}
    </form>
  )
}

// ---------------------------------------------------------------------------
// Event chip
// ---------------------------------------------------------------------------

function EventChip({ event, colour, time24, onClick }: { event: CalendarEvent; colour: string; time24: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left flex items-center gap-1.5 px-1.5 py-0.5 rounded-md hover:bg-sunken text-xs truncate"
      style={{ borderLeft: `3px solid ${colour}` }}
    >
      {!event.is_all_day && <span className="text-muted tabular-nums flex-shrink-0">{fmtTime(event.start_at, time24)}</span>}
      <span className="truncate text-ink">{event.title}</span>
    </button>
  )
}

// ---------------------------------------------------------------------------
// Rotating schedules — one compact cycle plus date-specific exceptions.
// ---------------------------------------------------------------------------

const SHARED_CARE_PATTERN = 'PPSSPPPSSPPSSS'

function RotationBadge({ occurrence, onClick, compact = false }: {
  occurrence: RotatingScheduleOccurrence
  onClick?: () => void
  compact?: boolean
}) {
  const Tag = onClick ? 'button' : 'div'
  return (
    <Tag
      {...(onClick ? { type: 'button' as const, onClick } : {})}
      className={`flex w-full items-center gap-1.5 rounded-lg text-left ${compact ? 'min-h-7 px-1.5 py-1 text-[11px]' : 'min-h-11 px-3 py-2 text-sm'} ${onClick ? 'hover:brightness-95' : ''}`}
      style={{ borderLeft: `4px solid ${occurrence.colour}`, backgroundColor: `${occurrence.colour}18` }}
      title={`${occurrence.schedule_title}: ${occurrence.label}${occurrence.is_override ? ' (changed for this day)' : ''}`}
    >
      <span className="truncate font-semibold text-ink">{occurrence.label}</span>
      {occurrence.is_override && <span className="ml-auto flex-shrink-0 text-[10px] font-bold text-primary" aria-label="Changed day">SWAP</span>}
    </Tag>
  )
}

function RotationScheduleModal({ schedule, schedules, people, onSelect, onClose, onSaved, onError }: {
  schedule: RotatingSchedule | null
  schedules: RotatingSchedule[]
  people: Person[]
  onSelect: (id: number | 'new') => void
  onClose: () => void
  onSaved: () => void
  onError: (message: string) => void
}) {
  const [f, setF] = useState<RotatingScheduleWrite>({
    title: schedule?.title ?? 'Kids',
    primary_label: schedule?.primary_label ?? 'With us',
    secondary_label: schedule?.secondary_label ?? 'Other home',
    anchor_date: schedule?.anchor_date ?? dateKey(new Date()),
    cycle_pattern: schedule?.cycle_pattern ?? SHARED_CARE_PATTERN,
    primary_colour: schedule?.primary_colour ?? '#3F7D65',
    secondary_colour: schedule?.secondary_colour ?? '#8A718E',
    person_ids: schedule?.people.map(person => person.id) ?? [],
    visibility: schedule?.visibility ?? 'household',
    is_active: schedule?.is_active ?? true,
  })
  const [saving, setSaving] = useState(false)
  const set = <K extends keyof RotatingScheduleWrite>(key: K, value: RotatingScheduleWrite[K]) =>
    setF(previous => ({ ...previous, [key]: value }))
  const toggleDay = (index: number) => {
    const values = f.cycle_pattern.split('')
    values[index] = values[index] === 'P' ? 'S' : 'P'
    set('cycle_pattern', values.join(''))
  }
  const togglePerson = (id: number) => {
    const selected = f.person_ids ?? []
    set('person_ids', selected.includes(id) ? selected.filter(value => value !== id) : [...selected, id])
  }
  const save = async () => {
    if (!f.title.trim() || !f.primary_label.trim() || !f.secondary_label.trim()) return
    setSaving(true)
    try {
      if (schedule) await api.updateRotatingSchedule(schedule.id, f)
      else await api.createRotatingSchedule(f)
      onSaved()
    } catch (error) { onError(errMsg(error)) } finally { setSaving(false) }
  }
  const remove = async () => {
    if (!schedule || !(await confirmDialog({ title: `Delete the “${schedule.title}” rotation?`, confirmLabel: 'Delete' }))) return
    try { await api.deleteRotatingSchedule(schedule.id); onSaved() } catch (error) { onError(errMsg(error)) }
  }
  const anchor = f.anchor_date ? dateFromKey(f.anchor_date) : new Date()

  return (
    <Modal
      title={schedule ? 'Edit rotating schedule' : 'Set up a rotating schedule'}
      onClose={onClose}
      size="lg"
      footer={(
        <>
          {schedule && <button type="button" onClick={remove} className="mr-auto text-sm text-danger hover:underline">Delete</button>}
          <Button variant="ghost" size="sm" onClick={onClose}>Cancel</Button>
          <Button size="sm" onClick={save} loading={saving} disabled={!f.title.trim() || !f.anchor_date}>Save rotation</Button>
        </>
      )}
    >
      <div className="flex flex-col gap-4">
        {(schedules.length > 0 || schedule) && (
          <div className="flex gap-2 overflow-x-auto pb-1">
            {schedules.map(item => (
              <button key={item.id} type="button" onClick={() => onSelect(item.id)}
                className={`min-h-10 flex-shrink-0 rounded-xl border px-3 text-sm font-medium ${schedule?.id === item.id ? 'border-primary bg-primary-soft text-primary' : 'border-line text-muted'}`}>
                {item.title}
              </button>
            ))}
            <button type="button" onClick={() => onSelect('new')} className="min-h-10 flex-shrink-0 rounded-xl border border-dashed border-line-strong px-3 text-sm text-muted">+ Another</button>
          </div>
        )}

        <div className="rounded-xl bg-primary-soft px-3 py-2.5 text-sm text-primary">
          {schedule
            ? 'The anchor is day one of the pattern below. Tap any day to switch its normal state.'
            : `The 2 on, 2 off, 3 on, 2 off, 2 on, 3 off pattern is pre-filled. Choose the Monday starting a week where “${f.primary_label || 'primary'}” covers Monday, Tuesday and Friday–Sunday.`}
          <span className="mt-1 block font-medium">This pattern repeats continuously—the 14 nights define the cycle, not the forecast limit.</span>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Schedule name">
            <Input value={f.title} onChange={event => set('title', event.target.value)} placeholder="Kids" autoFocus />
          </Field>
          <Field label="Cycle starts (day 1)">
            <Input type="date" value={f.anchor_date} onChange={event => set('anchor_date', event.target.value)} />
          </Field>
          <Field label="Primary label">
            <Input value={f.primary_label} onChange={event => set('primary_label', event.target.value)} placeholder="With us" />
          </Field>
          <Field label="Other label">
            <Input value={f.secondary_label} onChange={event => set('secondary_label', event.target.value)} placeholder="With Dad" />
          </Field>
        </div>

        <Field label={`${f.cycle_pattern.length}-night pattern — tap any day to change it`}>
          <div className="mb-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
            <span className="flex items-center gap-1.5"><span className="h-2.5 w-5 rounded-full" style={{ backgroundColor: f.primary_colour }} />{f.primary_label}</span>
            <span className="flex items-center gap-1.5"><span className="h-2.5 w-5 rounded-full" style={{ backgroundColor: f.secondary_colour }} />{f.secondary_label}</span>
          </div>
          <div className="grid grid-cols-7 gap-1.5">
            {f.cycle_pattern.split('').map((state, index) => {
              const primary = state === 'P'
              return (
                <button key={index} type="button" onClick={() => toggleDay(index)}
                  className="min-h-[54px] overflow-hidden rounded-xl border border-line px-1 py-1.5 text-center transition-transform active:scale-95 sm:min-h-[64px]"
                  style={{ backgroundColor: `${primary ? f.primary_colour : f.secondary_colour}20`, borderColor: primary ? f.primary_colour : f.secondary_colour }}>
                  <span className="block text-[10px] text-muted">{addDays(anchor, index).toLocaleDateString(undefined, { weekday: 'short' })}</span>
                  <span className="block text-sm font-black text-ink sm:hidden">{addDays(anchor, index).getDate()}</span>
                  <span className="hidden truncate text-xs font-bold text-ink sm:block">{primary ? f.primary_label : f.secondary_label}</span>
                  <span className="sr-only">: {primary ? f.primary_label : f.secondary_label}</span>
                </button>
              )
            })}
          </div>
        </Field>

        {people.length > 0 && (
          <Field label="Who this schedule is for (optional)">
            <div className="flex flex-wrap gap-2">
              {[...people].sort((a, b) => Number(b.profile_type === 'child') - Number(a.profile_type === 'child')).map(person => {
                const selected = f.person_ids?.includes(person.id)
                return (
                  <button key={person.id} type="button" onClick={() => togglePerson(person.id)}
                    className={`min-h-10 rounded-xl border px-3 text-sm font-medium ${selected ? 'border-primary bg-primary-soft text-primary' : 'border-line text-muted'}`}>
                    {selected ? '✓ ' : ''}{person.display_name}
                  </button>
                )
              })}
            </div>
          </Field>
        )}

        <details className="rounded-xl border border-line p-3 text-sm">
          <summary className="cursor-pointer font-medium text-ink">Colours and visibility</summary>
          <div className="mt-3 grid grid-cols-2 gap-3">
            <Field label={f.primary_label || 'Primary'}>
              <ColourPicker value={f.primary_colour || '#3F7D65'} onChange={value => set('primary_colour', value)} ariaLabel={`${f.primary_label || 'Primary'} schedule colour`} />
            </Field>
            <Field label={f.secondary_label || 'Secondary'}>
              <ColourPicker value={f.secondary_colour || '#8A718E'} onChange={value => set('secondary_colour', value)} ariaLabel={`${f.secondary_label || 'Secondary'} schedule colour`} />
            </Field>
            <Field label="Visibility">
              <Select value={f.visibility} onChange={event => set('visibility', event.target.value)}>
                <option value="household">Household</option>
                <option value="private">Private</option>
              </Select>
            </Field>
            <label className="flex min-h-11 items-center gap-2 pt-5 text-sm text-ink">
              <input type="checkbox" checked={f.is_active} onChange={event => set('is_active', event.target.checked)} /> Active
            </label>
          </div>
        </details>
      </div>
    </Modal>
  )
}

function RotationExceptionModal({ occurrence, schedule, onClose, onSaved, onError }: {
  occurrence: RotatingScheduleOccurrence
  schedule: RotatingSchedule
  onClose: () => void
  onSaved: () => void
  onError: (message: string) => void
}) {
  const [state, setState] = useState<'primary' | 'secondary'>(occurrence.state)
  const [note, setNote] = useState(occurrence.note)
  const [saving, setSaving] = useState(false)
  const save = async () => {
    setSaving(true)
    try {
      await api.setRotatingScheduleException(schedule.id, occurrence.date, { state, note: note.trim() })
      onSaved()
    } catch (error) { onError(errMsg(error)) } finally { setSaving(false) }
  }
  const restore = async () => {
    setSaving(true)
    try { await api.deleteRotatingScheduleException(schedule.id, occurrence.date); onSaved() }
    catch (error) { onError(errMsg(error)) } finally { setSaving(false) }
  }
  const plannedLabel = occurrence.planned_state === 'primary' ? schedule.primary_label : schedule.secondary_label

  return (
    <Modal
      title={`Change ${dateFromKey(occurrence.date).toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' })}`}
      onClose={onClose}
      size="sm"
      footer={(
        <>
          <Button variant="ghost" size="sm" onClick={onClose}>Cancel</Button>
          <Button size="sm" onClick={save} loading={saving}>Save this day</Button>
        </>
      )}
    >
      <div className="flex flex-col gap-4">
        <div>
          <p className="font-semibold text-ink">{schedule.title}</p>
          <p className="mt-1 text-sm text-muted">The repeating plan says <strong>{plannedLabel}</strong>. Changing this date will not alter any other day.</p>
        </div>
        <div className="grid grid-cols-2 gap-2">
          {(['primary', 'secondary'] as const).map(value => {
            const label = value === 'primary' ? schedule.primary_label : schedule.secondary_label
            const colour = value === 'primary' ? schedule.primary_colour : schedule.secondary_colour
            return (
              <button key={value} type="button" onClick={() => setState(value)}
                className={`min-h-[72px] rounded-xl border p-2 text-sm font-bold ${state === value ? 'ring-2 ring-primary ring-offset-2 ring-offset-surface' : ''}`}
                style={{ borderColor: colour, backgroundColor: `${colour}20` }}>
                {state === value && '✓ '}{label}
              </button>
            )
          })}
        </div>
        <Field label="Note (optional)">
          <Input value={note} onChange={event => setNote(event.target.value)} placeholder="Agreed swap, special occasion…" />
        </Field>
        {occurrence.is_override && (
          <button type="button" onClick={restore} disabled={saving} className="min-h-11 self-start text-sm font-medium text-primary hover:underline">
            Restore the repeating plan for this day
          </button>
        )}
      </div>
    </Modal>
  )
}

// ---------------------------------------------------------------------------
// Agenda view
// ---------------------------------------------------------------------------

function AgendaView({ events, rotations, colourFor, time24, onOpen, onOpenRotation }: {
  events: CalendarEvent[]
  rotations: RotatingScheduleOccurrence[]
  colourFor: (e: CalendarEvent) => string
  time24: boolean
  onOpen: (e: CalendarEvent) => void
  onOpenRotation?: (occurrence: RotatingScheduleOccurrence) => void
}) {
  const grouped = useMemo(() => {
    const m = new Map<string, { events: CalendarEvent[]; rotations: RotatingScheduleOccurrence[] }>()
    for (const e of events) {
      const k = dateKey(new Date(e.start_at))
      if (!m.has(k)) m.set(k, { events: [], rotations: [] })
      m.get(k)!.events.push(e)
    }
    for (const occurrence of rotations) {
      if (!m.has(occurrence.date)) m.set(occurrence.date, { events: [], rotations: [] })
      m.get(occurrence.date)!.rotations.push(occurrence)
    }
    return [...m.entries()].sort(([a], [b]) => a.localeCompare(b))
  }, [events, rotations])

  if (events.length === 0 && rotations.length === 0) return <EmptyState icon="📅" title="No upcoming events" hint="Your next 60 days are clear." />

  return (
    <div className="flex flex-col gap-5">
      {grouped.map(([dateStr, items]) => (
        <div key={dateStr}>
          <h2 className="text-sm font-semibold text-muted uppercase tracking-wide mb-2">
            {dateStr === dateKey(new Date()) ? 'Today' : dateFromKey(dateStr).toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' })}
          </h2>
          <div className="flex flex-col gap-2">
            {items.rotations.map(occurrence => (
              <RotationBadge key={occurrence.id} occurrence={occurrence} onClick={onOpenRotation ? () => onOpenRotation(occurrence) : undefined} />
            ))}
            {items.events.map(e => (
              <button key={e.id} onClick={() => onOpen(e)} className="flex items-start gap-4 p-3 rounded-xl border border-line hover:bg-sunken text-left">
                <div className="w-16 text-xs text-primary font-semibold tabular-nums flex-shrink-0">{e.is_all_day ? 'All day' : fmtTime(e.start_at, time24)}</div>
                <div className="flex-1 min-w-0" style={{ borderLeft: `3px solid ${colourFor(e)}`, paddingLeft: 10 }}>
                  <p className="font-medium text-ink">{e.title}</p>
                  {e.source_node && <span className="text-xs text-muted capitalize">{e.source_node}</span>}
                </div>
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// A single day's events as a vertical list — the Day view's own content, reused by the phone
// Week view's horizontal-day-strip-plus-agenda pattern (docs/36 §6.2) so the two never drift.
// ---------------------------------------------------------------------------

function DayAgendaList({ date, dayEvents, dayRotations, colourFor, time24, canEditCalendar, onOpen, onOpenRotation }: {
  date: Date
  dayEvents: (d: Date) => CalendarEvent[]
  dayRotations: (d: Date) => RotatingScheduleOccurrence[]
  colourFor: (e: CalendarEvent) => string
  time24: boolean
  canEditCalendar: boolean
  onOpen: (e: CalendarEvent) => void
  onOpenRotation: (occurrence: RotatingScheduleOccurrence) => void
}) {
  const events = dayEvents(date)
  const rotations = dayRotations(date)
  return (
    <div className="flex flex-col gap-2">
      {rotations.map(occurrence => (
        <RotationBadge key={occurrence.id} occurrence={occurrence} onClick={canEditCalendar ? () => onOpenRotation(occurrence) : undefined} />
      ))}
      {events.length === 0 ? (
        <EmptyState icon="📅" title="No events scheduled" hint="Use the quick-add above, or “New event” for full details." />
      ) : events.map(e => (
        <button key={e.id} onClick={() => onOpen(e)} className="flex items-start gap-4 p-4 rounded-xl border border-line hover:bg-sunken text-left">
          <div className="w-16 text-xs text-primary font-semibold tabular-nums flex-shrink-0">{e.is_all_day ? 'All day' : fmtTime(e.start_at, time24)}</div>
          <div className="flex-1 min-w-0" style={{ borderLeft: `3px solid ${colourFor(e)}`, paddingLeft: 10 }}>
            <p className="font-medium text-ink">{e.title}</p>
            {e.location && <p className="text-xs text-muted">{e.location}</p>}
            {e.source_node && <span className="text-xs text-muted capitalize">{e.source_node}</span>}
          </div>
        </button>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Calendar page
// ---------------------------------------------------------------------------

const lsGet = (k: string, d: string) => localStorage.getItem(k) ?? d
const linkedDate = () => {
  const raw = new URLSearchParams(window.location.search).get('date')
  if (!raw) return null
  const d = new Date(`${raw}T00:00:00`)
  return Number.isNaN(d.getTime()) ? null : d
}
export function CalendarPage() {
  const { user } = useAuth()
  const { household } = useStacks()
  const initialLinkedDate = linkedDate()
  const [view, setView] = useState<View>(() => {
    if (initialLinkedDate) return 'day'
    const stored = localStorage.getItem('hs_cal_view')
    if (stored) return stored as View
    // docs/36 §6.2: Agenda is the default everyday reading mode on phone, independent of the
    // household's own (typically desktop-oriented) default — never overridden below either.
    return isPhoneViewport() ? 'agenda' : 'month'
  })
  const [weekStart, setWeekStart] = useState<number>(() => Number(lsGet('hs_cal_weekstart', '1')))
  const [time24, setTime24] = useState<boolean>(() => lsGet('hs_cal_24h', '0') === '1')
  const [anchor, setAnchor] = useState(() => initialLinkedDate ?? new Date())
  const [selectedMonthDay, setSelectedMonthDay] = useState(() => initialLinkedDate ?? new Date())
  const [events, setEvents] = useState<CalendarEvent[]>([])
  const [rotatingSchedules, setRotatingSchedules] = useState<RotatingSchedule[]>([])
  const [rotations, setRotations] = useState<RotatingScheduleOccurrence[]>([])
  const [people, setPeople] = useState<Person[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [hiddenSources, setHiddenSources] = useState<Set<string>>(new Set())
  const [myOnly, setMyOnly] = useState(false)
  const [personFilter, setPersonFilter] = useState(0)
  const [defaultsSaved, setDefaultsSaved] = useState(false)
  const [modal, setModal] = useState<{ event: CalendarEvent | null; date: Date | null } | null>(null)
  const [scheduleModal, setScheduleModal] = useState<number | 'new' | null>(null)
  const [exceptionModal, setExceptionModal] = useState<RotatingScheduleOccurrence | null>(null)
  const [mobileMonthDayOpen, setMobileMonthDayOpen] = useState(false)
  const monthSwipeStart = useRef<{ x: number; y: number } | null>(null)
  const monthSwipeHandled = useRef(false)
  useUrlAction('event', () => setModal({ event: null, date: initialLinkedDate ?? new Date() }))

  // Which prefs the user has explicitly chosen (captured once, before the write-effects run,
  // so we can fall back to household defaults only for prefs the user has never touched).
  const storedRef = useRef({
    view: localStorage.getItem('hs_cal_view') !== null,
    weekStart: localStorage.getItem('hs_cal_weekstart') !== null,
    time24: localStorage.getItem('hs_cal_24h') !== null,
  })
  const householdApplied = useRef(false)

  useEffect(() => { localStorage.setItem('hs_cal_view', view) }, [view])
  useEffect(() => { localStorage.setItem('hs_cal_weekstart', String(weekStart)) }, [weekStart])
  useEffect(() => { localStorage.setItem('hs_cal_24h', time24 ? '1' : '0') }, [time24])
  useEffect(() => { api.getPeople().then(setPeople).catch(() => {}) }, [])

  // Household defaults (Core Calendar §15): apply once, only for prefs the user hasn't set.
  useEffect(() => {
    if (!household || householdApplied.current) return
    householdApplied.current = true
    if (!initialLinkedDate && !storedRef.current.view && !isPhoneViewport()) setView(household.calendar_default_view)
    if (!storedRef.current.weekStart) setWeekStart(household.calendar_week_start)
    if (!storedRef.current.time24) setTime24(household.calendar_time_format === '24h')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [household])

  const isAdmin = user?.role === 'admin'
  const canEditCalendar = user?.role === 'admin' || user?.role === 'manager'
  const saveHouseholdDefaults = async () => {
    try {
      await api.updateHousehold({
        calendar_default_view: view,
        calendar_week_start: weekStart,
        calendar_time_format: time24 ? '24h' : '12h',
      })
      setDefaultsSaved(true)
      setTimeout(() => setDefaultsSaved(false), 2500)
    } catch (e) { setError(errMsg(e)) }
  }

  const toggleSource = (src: string) =>
    setHiddenSources(prev => {
      const next = new Set(prev)
      next.has(src) ? next.delete(src) : next.add(src)
      return next
    })

  // Window to fetch for the current view.
  const win = useMemo(() => {
    if (view === 'month') {
      const g = monthGrid(anchor, weekStart)
      return { start: g[0], end: addDays(g[41], 1) }
    }
    if (view === 'week') {
      const s = startOfWeek(anchor, weekStart)
      return { start: s, end: addDays(s, 7) }
    }
    if (view === 'day') return { start: startOfDay(anchor), end: addDays(startOfDay(anchor), 1) }
    return { start: startOfDay(new Date()), end: addDays(new Date(), 60) } // agenda
  }, [view, anchor, weekStart])

  const winStart = win.start.getTime()
  const winEnd = win.end.getTime()

  const reload = () => {
    setLoading(true)
    const start = new Date(winStart)
    const end = new Date(winEnd)
    Promise.all([
      api.getEvents({
        start: start.toISOString(),
        end: end.toISOString(),
        person: personFilter || undefined,
      }),
      api.getRotatingSchedules(),
      api.getRotatingScheduleOccurrences(dateKey(start), dateKey(end)),
      api.getBirthdayOccurrences(dateKey(start), dateKey(end)),
    ])
      .then(([nextEvents, nextSchedules, nextRotations, birthdays]) => {
        const birthdayEvents: CalendarEvent[] = birthdays.map((birthday, index) => ({
          id: -1000000 - index, title: birthday.title, event_kind: 'birthday', description: '',
          start_at: `${birthday.date}T00:00:00`, end_at: null, is_all_day: true, timezone: '',
          recurrence_rule: '', source_node: null, source_record_type: 'BirthdayOccurrence',
          source_record_id: birthday.contact_id || birthday.person_id, assigned_to_person_ids: birthday.person_id ? [birthday.person_id] : [],
          colour: '#C46A4A', location: '', provider: '', contact: '', visibility: 'household',
          sensitivity: 'normal', is_synced: true, created_at: '', updated_at: '',
          // Birthdays are derived locally from contacts, not mirrored from a calendar source.
          is_source_managed: false, calendar_source_id: null, calendar_source_name: '',
          calendar_source_category: '', is_range: false,
        }))
        setEvents([...nextEvents, ...birthdayEvents])
        setRotatingSchedules(nextSchedules)
        setRotations(nextRotations)
      })
      .catch(e => setError(errMsg(e)))
      .finally(() => setLoading(false))
  }
  useEffect(reload, [winStart, winEnd, personFilter])

  const personColour = useMemo(() => {
    const m: Record<number, string> = {}
    for (const p of people) if (p.colour) m[p.id] = p.colour
    return m
  }, [people])

  const familyColour = household?.family_colour || DEFAULT_COLOUR
  const defaultAssignee = personIdForUser(people, user?.id)

  // Layer/visibility filters (Core Calendar §15): hide chosen source layers, or show only mine.
  const visibleEvents = useMemo(
    () => events.filter(e => {
      if (hiddenSources.has(layerKey(e))) return false
      if (myOnly && defaultAssignee.length > 0 && !defaultAssignee.some(id => e.assigned_to_person_ids.includes(id))) return false
      return true
    }),
    [events, hiddenSources, myOnly, defaultAssignee],
  )

  // Colour precedence: explicit event colour → assigned person's colour →
  // whole-family (unassigned) uses the household family colour.
  const colourFor = (e: CalendarEvent) => {
    if (e.colour) return e.colour
    if (e.assigned_to_person_ids.length > 0)
      return personColour[e.assigned_to_person_ids[0]]
        || (e.source_node ? sourceColour(e.source_node) : '') || DEFAULT_COLOUR
    return familyColour
  }

  const eventsByDay = useMemo(() => {
    const m = new Map<string, CalendarEvent[]>()
    for (const e of visibleEvents) {
      const k = new Date(e.start_at).toDateString()
      if (!m.has(k)) m.set(k, [])
      m.get(k)!.push(e)
    }
    return m
  }, [visibleEvents])
  const dayEvents = (d: Date) => (eventsByDay.get(d.toDateString()) ?? [])

  const visibleRotations = useMemo(
    () => rotations.filter(occurrence => {
      if (hiddenSources.has('__rotation__')) return false
      if (personFilter && occurrence.person_ids.length > 0 && !occurrence.person_ids.includes(personFilter)) return false
      if (myOnly && defaultAssignee.length > 0 && !defaultAssignee.some(id => occurrence.person_ids.includes(id))) return false
      return true
    }),
    [rotations, hiddenSources, personFilter, myOnly, defaultAssignee],
  )
  const rotationsByDay = useMemo(() => {
    const map = new Map<string, RotatingScheduleOccurrence[]>()
    for (const occurrence of visibleRotations) {
      if (!map.has(occurrence.date)) map.set(occurrence.date, [])
      map.get(occurrence.date)!.push(occurrence)
    }
    return map
  }, [visibleRotations])
  const dayRotations = (date: Date) => rotationsByDay.get(dateKey(date)) ?? []

  // Source layers present in the fetched window: node sources, each subscribed/automatic
  // calendar source in its own right, and "direct" for the household's own events.
  const layersPresent = useMemo(() => {
    const set = new Set<string>()
    for (const e of events) set.add(layerKey(e))
    if (rotations.length > 0) set.add('__rotation__')
    return [...set]
  }, [events, rotations])

  // Label/colour for a layer chip. A calendar source names itself; a node keeps its own name.
  const layerMeta = useMemo(() => {
    const meta = new Map<string, { label: string; colour?: string }>()
    for (const e of events) {
      const key = layerKey(e)
      if (meta.has(key)) continue
      if (e.calendar_source_id) meta.set(key, { label: e.calendar_source_name, colour: e.colour })
      else if (e.source_node) meta.set(key, { label: e.source_node, colour: sourceColour(e.source_node) })
      else meta.set(key, { label: 'HomeStack' })
    }
    return meta
  }, [events])

  const step = (dir: -1 | 1) => {
    if (view === 'month') {
      const next = addMonths(anchor, dir)
      const lastDay = new Date(next.getFullYear(), next.getMonth() + 1, 0).getDate()
      setAnchor(next)
      setSelectedMonthDay(new Date(next.getFullYear(), next.getMonth(), Math.min(selectedMonthDay.getDate(), lastDay)))
    }
    else if (view === 'week') setAnchor(a => addDays(a, 7 * dir))
    else setAnchor(a => addDays(a, dir))
  }
  const goToday = () => {
    const today = new Date()
    setAnchor(today)
    setSelectedMonthDay(today)
  }
  const selectMonthDay = (day: Date) => {
    setSelectedMonthDay(day)
    if (day.getMonth() !== anchor.getMonth() || day.getFullYear() !== anchor.getFullYear()) setAnchor(day)
    setMobileMonthDayOpen(true)
  }
  const openSelectedDay = () => {
    setMobileMonthDayOpen(false)
    setAnchor(selectedMonthDay)
    setView('day')
  }
  const changeView = (next: View) => {
    if (next === 'month') setSelectedMonthDay(anchor)
    setView(next)
  }
  const finishMonthSwipe = (event: React.TouchEvent) => {
    const start = monthSwipeStart.current
    monthSwipeStart.current = null
    if (!start) return
    const touch = event.changedTouches[0]
    const dx = touch.clientX - start.x
    const dy = touch.clientY - start.y
    if (Math.abs(dx) > 55 && Math.abs(dx) > Math.abs(dy) * 1.4) {
      monthSwipeHandled.current = true
      step(dx < 0 ? 1 : -1)
      window.setTimeout(() => { monthSwipeHandled.current = false }, 350)
    }
  }
  const periodLabel = () => {
    if (view === 'month') return anchor.toLocaleDateString(undefined, { month: 'long', year: 'numeric' })
    if (view === 'day') return anchor.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' })
    if (view === 'week') {
      const s = startOfWeek(anchor, weekStart)
      return `${s.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })} – ${addDays(s, 6).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}`
    }
    return 'Upcoming'
  }

  const openEvent = (e: CalendarEvent) => setModal({ event: e, date: null })
  const openNew = (d: Date | null) => {
    if (canEditCalendar) setModal({ event: null, date: d })
  }
  const openRotation = (occurrence: RotatingScheduleOccurrence) => {
    if (canEditCalendar) setExceptionModal(occurrence)
  }

  const quickAdd = async (text: string) => {
    const p = parseQuickEvent(text, view === 'day' || view === 'week' ? anchor : new Date())
    try {
      await api.createEvent({
        title: p.title,
        start_at: p.startISO,
        is_all_day: p.allDay,
        assigned_to_person_ids: defaultAssignee.length > 0 ? defaultAssignee : undefined,
      })
      reload()
    } catch (e) { setError(errMsg(e)) }
  }

  const weekdayNames = useMemo(() => {
    const base = startOfWeek(new Date(), weekStart)
    return Array.from({ length: 7 }, (_, i) => addDays(base, i).toLocaleDateString(undefined, { weekday: 'short' }))
  }, [weekStart])

  const activeFilters = (personFilter ? 1 : 0) + (myOnly ? 1 : 0) + hiddenSources.size

  const chipCls = (on: boolean) =>
    `flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-xs font-medium capitalize transition-colors ${
      on ? 'border-line-strong text-ink' : 'border-line text-muted line-through opacity-60'
    }`

  const selectedSchedule = scheduleModal === 'new'
    ? null
    : rotatingSchedules.find(schedule => schedule.id === scheduleModal) ?? null
  const exceptionSchedule = exceptionModal
    ? rotatingSchedules.find(schedule => schedule.id === exceptionModal.schedule_id) ?? null
    : null
  const calendarActions = canEditCalendar ? (
    <>
      <Button variant="ghost" size="sm" onClick={() => setScheduleModal(rotatingSchedules[0]?.id ?? 'new')}>Rotation</Button>
      <Button size="sm" onClick={() => openNew(view === 'day' || view === 'week' ? anchor : view === 'month' ? selectedMonthDay : new Date())}>+ Event</Button>
    </>
  ) : null

  return (
    <div className="flex flex-col gap-4">
      <div className="hidden sm:block">
        <PageHeader title="Calendar" icon="📅" actions={calendarActions} />
      </div>

      {/* Period navigation stays generous; mobile uses one compact view picker.
          The desktop row wraps on the toolbar's own width rather than the viewport's. A `sm:`
          breakpoint only knows the browser is wide — it cannot see that the sidebar has taken
          ~256px, so at split-screen widths the single row was still applied and the controls
          crushed each other (the period label collapsed to a few characters). Each group
          instead declares a flex-basis it needs to stay comfortable; when both cannot fit, the
          second group wraps onto its own line. At genuinely wide widths they share one row
          exactly as before. */}
      <div
        data-calendar-toolbar
        className="flex flex-col gap-2 rounded-2xl border border-line bg-surface p-2.5 shadow-soft sm:flex-row sm:flex-wrap sm:items-center sm:gap-x-3"
      >
        <div className="flex min-w-0 items-center gap-1 sm:flex-1 sm:basis-80">
          {/* Agenda always shows "today + 60 days" regardless of anchor, so Previous/Next/Today
              would look interactive but silently do nothing — hidden here rather than wired up
              to fake paging (docs/36 review). */}
          {view !== 'agenda' && (
            <>
              <button onClick={() => step(-1)} className="grid h-11 w-11 flex-shrink-0 place-items-center rounded-xl text-xl text-muted-strong hover:bg-sunken" aria-label="Previous period">‹</button>
              <span data-calendar-period-label className="min-w-0 flex-1 truncate px-1 text-center text-sm font-extrabold text-ink sm:ml-1 sm:text-left">{periodLabel()}</span>
              <button onClick={() => step(1)} className="grid h-11 w-11 flex-shrink-0 place-items-center rounded-xl text-xl text-muted-strong hover:bg-sunken" aria-label="Next period">›</button>
              <button onClick={goToday} className="h-11 flex-shrink-0 rounded-xl px-2.5 text-xs font-bold text-primary hover:bg-primary-soft sm:px-3 sm:text-sm">Today</button>
            </>
          )}
          {view === 'agenda' && (
            <span data-calendar-period-label className="min-w-0 flex-1 truncate px-1 text-center text-sm font-extrabold text-ink sm:ml-1 sm:text-left">{periodLabel()}</span>
          )}
        </div>

        <div className="flex w-full items-center gap-2 sm:w-auto sm:flex-1 sm:basis-[21rem] sm:justify-end">
          <label className="relative min-w-0 flex-1 sm:hidden">
            <span className="sr-only">Calendar view</span>
            <select
              value={view}
              onChange={event => changeView(event.target.value as View)}
              className="min-h-11 w-full appearance-none rounded-xl border border-line bg-surface px-3 pr-9 text-sm font-bold capitalize text-ink"
            >
              <option value="month">Month view</option>
              <option value="week">Week view</option>
              <option value="day">Day view</option>
              <option value="agenda">Agenda</option>
            </select>
            <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-xs text-muted">▾</span>
          </label>
          <Popover
            panelClassName="w-72"
            trigger={() => (
              <>
                <span>Filter</span>
                {activeFilters > 0 && (
                  <span className="rounded-full bg-primary px-1.5 py-0.5 text-[10px] font-bold leading-none text-white">{activeFilters}</span>
                )}
              </>
            )}
          >
            {({ close }) => (
              <div className="flex flex-col gap-3 text-sm">
                <Field label="Show">
                  <select value={personFilter} onChange={e => setPersonFilter(Number(e.target.value))} className="w-full rounded-lg border border-line bg-surface px-2 py-2 text-sm text-ink">
                    <option value={0}>Everyone</option>
                    {people.map(p => <option key={p.id} value={p.id}>{p.display_name}</option>)}
                  </select>
                </Field>

                {defaultAssignee.length > 0 && (
                  <button
                    onClick={() => setMyOnly(v => !v)}
                    className={`self-start px-2.5 py-1.5 rounded-lg border text-xs font-medium transition-colors ${
                      myOnly ? 'border-primary bg-primary-soft text-primary' : 'border-line text-muted hover:text-ink'
                    }`}
                  >
                    {myOnly ? '✓ My events only' : 'My events only'}
                  </button>
                )}

                {layersPresent.length > 1 && (
                  <div className="flex flex-col gap-1.5">
                    <span className="text-xs font-semibold uppercase tracking-wide text-muted-strong">Layers</span>
                    <div className="flex flex-wrap gap-1.5">
                      {layersPresent.map(src => {
                        const label = src === '__direct__' ? 'HomeStack'
                          : src === '__rotation__' ? 'Rotations'
                            : layerMeta.get(src)?.label || src
                        const on = !hiddenSources.has(src)
                        const colour = src === '__rotation__'
                          ? rotatingSchedules[0]?.primary_colour
                          : layerMeta.get(src)?.colour
                        return (
                          <button key={src} onClick={() => toggleSource(src)} className={chipCls(on)} title={on ? `Hide ${label}` : `Show ${label}`}>
                            <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: colour || DEFAULT_COLOUR }} />
                            {label}
                          </button>
                        )
                      })}
                    </div>
                  </div>
                )}

                <div className="border-t border-line pt-3">
                  <Link
                    to="/calendar/sources"
                    className="flex min-h-11 items-center justify-between rounded-lg px-2.5 text-xs font-bold text-primary hover:bg-primary-soft"
                  >
                    Calendar sources <span aria-hidden>→</span>
                  </Link>
                </div>

                <div className="flex flex-wrap gap-1.5 border-t border-line pt-3">
                  <button onClick={() => setWeekStart(w => (w === 1 ? 0 : 1))} className="px-2.5 py-1.5 rounded-lg border border-line text-xs text-muted hover:text-ink">
                    Week starts {weekStart === 1 ? 'Mon' : 'Sun'}
                  </button>
                  <button onClick={() => setTime24(t => !t)} className="px-2.5 py-1.5 rounded-lg border border-line text-xs text-muted hover:text-ink">
                    {time24 ? '24-hour' : '12-hour'}
                  </button>
                </div>

                {isAdmin && (
                  <button
                    onClick={saveHouseholdDefaults}
                    className="self-start px-2.5 py-1.5 rounded-lg border border-line text-xs text-muted hover:text-ink"
                    title="Make the current view, week-start and time format the household default"
                  >
                    {defaultsSaved ? 'Saved ✓' : 'Set as household default'}
                  </button>
                )}

                {canEditCalendar && (
                  <button
                    type="button"
                    onClick={() => { close(); setScheduleModal(rotatingSchedules[0]?.id ?? 'new') }}
                    className="flex min-h-10 items-center justify-between rounded-xl border border-line px-3 text-left text-sm font-semibold text-ink hover:bg-sunken"
                  >
                    Rotating schedules <span className="text-muted">→</span>
                  </button>
                )}
              </div>
            )}
          </Popover>

          <div className="hidden min-w-0 flex-1 gap-1 rounded-xl bg-sunken p-1 sm:flex sm:flex-none">
            {(['month', 'week', 'day', 'agenda'] as View[]).map(v => (
              <button key={v} onClick={() => changeView(v)}
                className={`min-w-0 flex-1 rounded-lg px-2 py-1.5 text-xs font-bold capitalize transition-colors sm:flex-none sm:px-3 ${view === v ? 'bg-raised text-ink shadow-soft' : 'text-muted hover:text-ink'}`}>
                {v}
              </button>
            ))}
          </div>
        </div>
      </div>

      {error && (
        <div className="flex items-center justify-between gap-3 px-4 py-2.5 rounded-xl bg-danger-soft text-danger text-sm">
          <span>{error}</span>
          <button onClick={() => setError(null)} aria-label="Dismiss">×</button>
        </div>
      )}

      {canEditCalendar && (view === 'day' || view === 'week' || view === 'agenda') && (
        <QuickAddBar baseDate={view === 'day' || view === 'week' ? anchor : new Date()} time24={time24} onAdd={quickAdd} />
      )}

      {/* The legend explains the colours; the forecasting hint explains the arrows. They were
          sharing one row, so the row did two unrelated jobs and read as one sentence. */}
      {view === 'month' && rotatingSchedules.some(schedule => schedule.is_active) && (
        <div className="flex flex-col gap-1.5 rounded-xl border border-line bg-surface px-3 py-2 text-xs text-muted">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
            {rotatingSchedules.filter(schedule => schedule.is_active).map(schedule => (
              <div key={`month-legend-${schedule.id}`} className="flex flex-wrap items-center gap-3">
                <span className="font-semibold text-ink">{schedule.title}</span>
                <span className="flex items-center gap-1.5"><span className="h-3.5 w-3.5 rounded" style={{ backgroundColor: schedule.primary_colour }} />{schedule.primary_label}</span>
                <span className="flex items-center gap-1.5"><span className="h-3.5 w-3.5 rounded" style={{ backgroundColor: schedule.secondary_colour }} />{schedule.secondary_label}</span>
              </div>
            ))}
          </div>
          <span className="hidden border-t border-line/60 pt-1.5 sm:inline">Repeats continuously · use ‹ › to forecast any month</span>
        </div>
      )}

      {loading ? (
        <div className="h-64 rounded-2xl bg-sunken animate-pulse" />
      ) : view === 'month' ? (
        <>
          <div className="sm:hidden">
            <div
              className="-mx-4 touch-pan-y overflow-hidden border-y border-line bg-surface shadow-soft"
              onTouchStart={event => {
                const touch = event.touches[0]
                monthSwipeStart.current = { x: touch.clientX, y: touch.clientY }
              }}
              onTouchEnd={finishMonthSwipe}
              onTouchCancel={() => { monthSwipeStart.current = null }}
            >
              <div className="grid grid-cols-7 bg-sunken">
                {weekdayNames.map(day => <div key={day} className="px-1 py-2 text-center text-[10px] font-bold uppercase tracking-wide text-muted">{day.slice(0, 2)}</div>)}
              </div>
              <div className="grid grid-cols-7">
                {monthGrid(anchor, weekStart).map((day, index) => {
                  const inMonth = day.getMonth() === anchor.getMonth()
                  const occurrence = dayRotations(day)[0]
                  const dayItems = dayEvents(day)
                  const selected = sameDay(day, selectedMonthDay)
                  return (
                    <button
                      key={index}
                      type="button"
                      onClick={() => {
                        if (monthSwipeHandled.current) return
                        selectMonthDay(day)
                      }}
                      className={`relative min-h-[58px] border-b border-r border-line p-1.5 pt-2 text-left transition-colors ${selected ? 'z-[1] bg-primary-soft/70 ring-2 ring-inset ring-primary' : 'active:bg-sunken'} ${inMonth ? 'text-ink' : 'text-muted opacity-45'}`}
                      aria-pressed={selected}
                      aria-label={`${day.toLocaleDateString()}${occurrence ? `, ${occurrence.label}` : ''}${dayItems.length ? `, ${dayItems.length} events` : ''}`}
                    >
                      {occurrence && <span className="absolute inset-x-0 top-0 h-1" style={{ backgroundColor: occurrence.colour }} />}
                      <span className={`inline-grid h-6 min-w-6 place-items-center rounded-full px-1 text-xs font-bold ${isToday(day) ? 'bg-primary text-white' : ''}`}>{day.getDate()}</span>
                      {occurrence?.is_override && <span className="absolute right-1 top-2 text-[8px] font-black text-primary" aria-label="Changed day">S</span>}
                      {/* Month is for orientation, not full event content (docs/36 §6.2) — a
                          dot per event plus an overflow count, not a truncated illegible title. */}
                      {dayItems.length > 0 && (
                        <span className="absolute inset-x-1 bottom-1.5 flex min-w-0 items-center justify-center gap-0.5" aria-hidden>
                          {dayItems.slice(0, 3).map((item, i) => (
                            <span key={i} className="h-1.5 w-1.5 flex-shrink-0 rounded-full" style={{ backgroundColor: colourFor(item) }} />
                          ))}
                          {dayItems.length > 3 && <span className="flex-shrink-0 text-[8px] font-black text-muted">+{dayItems.length - 3}</span>}
                        </span>
                      )}
                    </button>
                  )
                })}
              </div>
            </div>
            <p className="mt-2 px-1 text-[11px] text-muted">Tap a date for its details · swipe sideways to change month · <strong>S</strong> marks a changed rotation day.</p>
          </div>
          <div data-calendar-grid className="hidden rounded-2xl border border-line overflow-hidden sm:block">
            <div className="grid grid-cols-7 bg-sunken">
              {weekdayNames.map(d => <div key={d} className="px-2 py-1.5 text-xs font-semibold text-muted text-center">{d}</div>)}
            </div>
            <div className="grid grid-cols-7">
              {monthGrid(anchor, weekStart).map((d, i) => {
                const inMonth = d.getMonth() === anchor.getMonth()
                const evs = dayEvents(d)
                const rotationDays = dayRotations(d)
                const occurrence = rotationDays[0]
                return (
                  <div key={i} onClick={() => { setAnchor(d); setView('day') }}
                    style={occurrence ? { borderTop: `4px solid ${occurrence.colour}` } : undefined}
                    className={`group relative min-h-[112px] border-b border-r border-line p-1 cursor-pointer hover:brightness-95 ${inMonth ? '' : 'opacity-45'}`}>
                    <div className="mb-1 flex items-start justify-between gap-1">
                      <div className={`text-xs font-semibold w-6 h-6 flex items-center justify-center rounded-full ${isToday(d) ? 'bg-primary text-white' : inMonth ? 'text-ink' : 'text-muted'}`}>
                        {d.getDate()}
                      </div>
                      {/* Adding an event on a specific day previously meant opening that day
                          first, or changing the date inside the modal. Kept faint until the cell
                          is hovered or the button focused, so the grid still reads as a month. */}
                      {canEditCalendar && (
                        <button
                          type="button"
                          onClick={event => { event.stopPropagation(); openNew(d) }}
                          className="grid h-6 w-6 flex-shrink-0 place-items-center rounded-lg text-sm font-bold text-muted opacity-0 transition-opacity hover:bg-primary-soft hover:text-primary focus-visible:opacity-100 group-hover:opacity-100"
                          aria-label={`Add an event on ${d.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' })}`}
                          title="Add an event on this day"
                        >
                          +
                        </button>
                      )}
                    </div>
                    <div className="flex flex-col gap-0.5">
                      {occurrence?.is_override && <span className="px-1 text-[9px] font-bold text-primary">SWAP</span>}
                      {evs.slice(0, 3).map(e => (
                        <div key={e.id} onClick={ev => { ev.stopPropagation(); openEvent(e) }}>
                          <EventChip event={e} colour={colourFor(e)} time24={time24} onClick={() => {}} />
                        </div>
                      ))}
                      {evs.length > 3 && <span className="text-[10px] text-muted pl-1">+{evs.length - 3} more</span>}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </>
      ) : view === 'week' ? (
        <>
          {/* Phone: a horizontal day strip (date + a dot per source, not a squeezed 7-column
              grid) plus the selected day's agenda below — docs/36 §6.2's week pattern, reusing
              the exact Day-view list so the two never drift. */}
          <div className="flex w-full min-w-0 flex-col gap-3 sm:hidden">
            <div className="flex w-full min-w-0 gap-1.5 overflow-x-auto pb-1">
              {Array.from({ length: 7 }, (_, i) => addDays(startOfWeek(anchor, weekStart), i)).map(d => {
                const selected = sameDay(d, anchor)
                const dayItems = dayEvents(d)
                const occurrence = dayRotations(d)[0]
                return (
                  <button
                    key={d.toDateString()}
                    type="button"
                    onClick={() => setAnchor(d)}
                    aria-pressed={selected}
                    className={`flex min-h-[64px] min-w-[46px] flex-shrink-0 flex-col items-center gap-1 rounded-2xl border px-2 py-2 transition-colors ${selected ? 'border-primary bg-primary-soft' : 'border-line bg-surface'}`}
                  >
                    <span className={`text-[10px] font-bold uppercase ${selected ? 'text-primary' : 'text-muted'}`}>{d.toLocaleDateString(undefined, { weekday: 'short' }).slice(0, 2)}</span>
                    <span className={`grid h-7 w-7 place-items-center rounded-full text-sm font-bold ${isToday(d) ? 'bg-primary text-white' : selected ? 'text-primary' : 'text-ink'}`}>{d.getDate()}</span>
                    <span className="flex h-1.5 gap-0.5">
                      {occurrence && <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: occurrence.colour }} />}
                      {dayItems.length > 0 && <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: colourFor(dayItems[0]) }} />}
                    </span>
                  </button>
                )
              })}
            </div>
            {/* The day strip scrolls horizontally and the top-bar period label only shows the
                week range, so without this the selected day is easy to lose track of. */}
            <h2 className="px-1 text-sm font-bold text-ink">
              {isToday(anchor) ? 'Today' : anchor.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' })}
            </h2>
            <DayAgendaList
              date={anchor} dayEvents={dayEvents} dayRotations={dayRotations} colourFor={colourFor}
              time24={time24} canEditCalendar={canEditCalendar} onOpen={openEvent} onOpenRotation={openRotation}
            />
          </div>
          <div className="hidden grid-cols-7 gap-2 sm:grid">
            {Array.from({ length: 7 }, (_, i) => addDays(startOfWeek(anchor, weekStart), i)).map(d => (
              <div
                key={d.toDateString()}
                className="rounded-xl border border-line p-2 min-h-[120px] text-left hover:bg-sunken/40"
              >
                <button type="button" onClick={() => openNew(d)} className={`mb-2 min-h-8 w-full text-left text-xs font-semibold ${isToday(d) ? 'text-primary' : 'text-muted-strong'}`}>
                  {d.toLocaleDateString(undefined, { weekday: 'short', day: 'numeric' })}
                </button>
                <div className="flex flex-col gap-1">
                  {dayRotations(d).map(occurrence => (
                    <RotationBadge key={occurrence.id} occurrence={occurrence} compact onClick={canEditCalendar ? () => openRotation(occurrence) : undefined} />
                  ))}
                  {dayEvents(d).map(e => <EventChip key={e.id} event={e} colour={colourFor(e)} time24={time24} onClick={() => openEvent(e)} />)}
                </div>
              </div>
            ))}
          </div>
        </>
      ) : view === 'day' ? (
        <DayAgendaList
          date={anchor} dayEvents={dayEvents} dayRotations={dayRotations} colourFor={colourFor}
          time24={time24} canEditCalendar={canEditCalendar} onOpen={openEvent} onOpenRotation={openRotation}
        />
      ) : (
        <AgendaView
          events={visibleEvents}
          rotations={visibleRotations}
          colourFor={colourFor}
          time24={time24}
          onOpen={openEvent}
          onOpenRotation={canEditCalendar ? openRotation : undefined}
        />
      )}

      {/* Legend */}
      <div className={`${view === 'month' ? 'hidden sm:flex' : 'flex'} flex-wrap gap-3 pt-1 text-xs text-muted`}>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-full" style={{ backgroundColor: familyColour }} /> Whole family
        </span>
        {people.filter(p => p.colour).map(p => (
          <span key={p.id} className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full" style={{ backgroundColor: p.colour }} /> {p.display_name}
          </span>
        ))}
        {rotatingSchedules.filter(schedule => schedule.is_active).map(schedule => (
          <span key={`rotation-${schedule.id}`} className="flex items-center gap-2">
            <span className="flex items-center gap-1"><span className="h-3 w-3 rounded-full" style={{ backgroundColor: schedule.primary_colour }} />{schedule.primary_label}</span>
            <span className="flex items-center gap-1"><span className="h-3 w-3 rounded-full" style={{ backgroundColor: schedule.secondary_colour }} />{schedule.secondary_label}</span>
          </span>
        ))}
      </div>

      {canEditCalendar && (
        <button
          type="button"
          onClick={() => openNew(view === 'month' ? selectedMonthDay : view === 'day' || view === 'week' ? anchor : new Date())}
          className="fixed bottom-[calc(6.25rem+env(safe-area-inset-bottom))] right-4 z-20 grid h-14 w-14 place-items-center rounded-2xl bg-primary text-3xl font-light leading-none text-white shadow-card active:scale-95 sm:hidden"
          aria-label={`Add event${view === 'month' ? ` on ${selectedMonthDay.toLocaleDateString()}` : ''}`}
        >
          +
        </button>
      )}

      {mobileMonthDayOpen && view === 'month' && (
        <Modal
          title={`${isToday(selectedMonthDay) ? 'Today' : selectedMonthDay.toLocaleDateString(undefined, { weekday: 'long' })}, ${selectedMonthDay.toLocaleDateString(undefined, { month: 'long', day: 'numeric' })}`}
          onClose={() => setMobileMonthDayOpen(false)}
          size="sm"
        >
          <div className="flex flex-col gap-2">
            {dayRotations(selectedMonthDay).map(occurrence => (
              <RotationBadge key={occurrence.id} occurrence={occurrence} onClick={canEditCalendar ? () => { setMobileMonthDayOpen(false); openRotation(occurrence) } : undefined} />
            ))}
            {dayEvents(selectedMonthDay).map(event => (
              <button key={event.id} type="button" onClick={() => { setMobileMonthDayOpen(false); openEvent(event) }} className="flex min-h-12 items-center gap-3 rounded-xl border border-line px-3 py-2 text-left active:bg-sunken">
                <span className="h-8 w-1 flex-shrink-0 rounded-full" style={{ backgroundColor: colourFor(event) }} />
                <span className="w-14 flex-shrink-0 text-xs font-bold tabular-nums text-muted-strong">{event.is_all_day ? 'All day' : fmtTime(event.start_at, time24)}</span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-semibold text-ink">{event.title}</span>
                  {event.location && <span className="block truncate text-[11px] text-muted">{event.location}</span>}
                </span>
              </button>
            ))}
            {dayEvents(selectedMonthDay).length === 0 && dayRotations(selectedMonthDay).length === 0 && (
              <p className="py-4 text-center text-sm text-muted">Nothing planned for this day.</p>
            )}
            <div className={`mt-2 grid gap-2 border-t border-line pt-3 ${canEditCalendar ? 'grid-cols-2' : 'grid-cols-1'}`}>
              <Button variant="ghost" onClick={openSelectedDay}>Day view</Button>
              {canEditCalendar && <Button onClick={() => { setMobileMonthDayOpen(false); openNew(selectedMonthDay) }}>+ Event</Button>}
            </div>
          </div>
        </Modal>
      )}

      {scheduleModal !== null && (
        <RotationScheduleModal
          key={selectedSchedule?.id ?? 'new'}
          schedule={selectedSchedule}
          schedules={rotatingSchedules}
          people={people}
          onSelect={setScheduleModal}
          onClose={() => setScheduleModal(null)}
          onError={setError}
          onSaved={() => { setScheduleModal(null); reload() }}
        />
      )}

      {exceptionModal && exceptionSchedule && (
        <RotationExceptionModal
          occurrence={exceptionModal}
          schedule={exceptionSchedule}
          onClose={() => setExceptionModal(null)}
          onError={setError}
          onSaved={() => { setExceptionModal(null); reload() }}
        />
      )}

      {modal && (
        <EventModal
          event={modal.event}
          defaultDate={modal.date}
          people={people}
          defaultAssignee={defaultAssignee}
          onClose={() => setModal(null)}
          onError={setError}
          onSaved={() => { setModal(null); reload() }}
        />
      )}
    </div>
  )
}
