import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../../api/client'
import type {
  CalendarSource, CalendarSourceCatalogueEntry, CalendarSourcePreview,
} from '../../../api/types'
import { Button } from '../../../components/Button'
import { Card } from '../../../components/Card'
import { ColourPicker } from '../../../components/ColourPicker'
import { confirmDialog } from '../../../components/Dialogs'
import { EmptyState } from '../../../components/EmptyState'
import { Field, Input, Select } from '../../../components/Field'
import { Modal } from '../../../components/Modal'
import { PageHeader } from '../../../components/PageHeader'
import { InlineAlert, PageSkeleton } from '../../../components/PageState'
import { MobileScreenHeader } from '../../../components/mobile'
import { useAuth } from '../../auth/AuthContext'

const errMsg = (error: unknown) => error instanceof Error ? error.message : 'Something went wrong.'

// Grouping mirrors how the household thinks about calendars, not how they are stored.
const GROUPS: Array<{ key: string; label: string; kinds: CalendarSource['kind'][] }> = [
  { key: 'automatic', label: 'Automatic', kinds: ['holidays', 'school'] },
  { key: 'subscriptions', label: 'Subscriptions', kinds: ['subscription'] },
  { key: 'imported', label: 'Imported', kinds: ['import'] },
]

// Only systems with verified published term dates are offered. Adding one is a data change in
// apps/scheduling/sources/au_school.py plus an entry here — never a guess.
const SCHOOL_SYSTEMS = [
  { value: 'qld_state', label: 'Queensland State Schools' },
  { value: 'nsw_state_eastern', label: 'NSW Public Schools (Eastern division)' },
  { value: 'nsw_state_western', label: 'NSW Public Schools (Western division)' },
]

function syncLabel(source: CalendarSource) {
  if (source.sync_status === 'error') return source.sync_error || 'Last sync failed'
  if (!source.last_success_at) return 'Not synced yet'
  const then = new Date(source.last_success_at).getTime()
  const minutes = Math.round((Date.now() - then) / 60000)
  if (minutes < 1) return 'Synced just now'
  if (minutes < 60) return `Synced ${minutes} minute${minutes === 1 ? '' : 's'} ago`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `Synced ${hours} hour${hours === 1 ? '' : 's'} ago`
  return `Synced ${new Date(source.last_success_at).toLocaleDateString()}`
}

function SourceRow({ source, canManage, onChange, onRemove, onError }: {
  source: CalendarSource
  canManage: boolean
  onChange: (next: CalendarSource) => void
  onRemove: (id: number) => void
  onError: (message: string) => void
}) {
  const [busy, setBusy] = useState(false)
  const [open, setOpen] = useState(false)

  const patch = async (data: Parameters<typeof api.updateCalendarSource>[1]) => {
    setBusy(true)
    try { onChange(await api.updateCalendarSource(source.id, data)) }
    catch (error) { onError(errMsg(error)) }
    finally { setBusy(false) }
  }

  const syncNow = async () => {
    setBusy(true)
    try {
      const updated = await api.syncCalendarSource(source.id)
      onChange(updated)
      if (updated.sync_status === 'error') onError(updated.sync_error || 'That calendar could not be synced.')
    } catch (error) { onError(errMsg(error)) }
    finally { setBusy(false) }
  }

  const remove = async () => {
    if (!await confirmDialog({
      title: `Remove "${source.name}"?`,
      message: 'Its entries are removed from your calendar. Nothing you created yourself is affected.',
      confirmLabel: 'Remove',
    })) return
    setBusy(true)
    try { await api.deleteCalendarSource(source.id); onRemove(source.id) }
    catch (error) { onError(errMsg(error)); setBusy(false) }
  }

  return (
    <div className="rounded-2xl border border-line bg-surface p-3">
      <div className="flex items-center gap-3">
        <label className="flex items-center gap-3">
          <input
            type="checkbox"
            checked={source.is_enabled}
            disabled={!canManage || busy}
            onChange={event => patch({ is_enabled: event.target.checked })}
            aria-label={`Enable ${source.name}`}
            className="h-5 w-5 flex-shrink-0"
          />
          <span className="h-8 w-2 flex-shrink-0 rounded-full" style={{ background: source.colour || 'var(--hs-primary)' }} />
        </label>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-bold text-ink">{source.name}</span>
          <span className="block truncate text-xs text-muted">
            {source.type_label} · {source.event_count} entries · {syncLabel(source)}
          </span>
        </span>
        {canManage && (
          <span className="flex flex-shrink-0 items-center gap-1">
            {source.can_sync && (
              <Button size="sm" variant="ghost" onClick={syncNow} loading={busy}>Sync now</Button>
            )}
            <Button size="sm" variant="ghost" onClick={() => setOpen(true)}>Settings</Button>
          </span>
        )}
      </div>
      {source.sync_status === 'error' && (
        <p className="mt-2 rounded-xl bg-danger-soft px-3 py-2 text-xs text-danger">{source.sync_error}</p>
      )}

      {open && (
        <Modal
          title={source.name}
          onClose={() => setOpen(false)}
          size="sm"
          footer={(
            <>
              <button onClick={remove} className="mr-auto text-sm font-semibold text-danger hover:underline">Remove</button>
              <Button variant="ghost" onClick={() => setOpen(false)}>Done</Button>
            </>
          )}
        >
          <div className="flex flex-col gap-3">
            <Field label="Name">
              <Input
                aria-label="Source name"
                defaultValue={source.name}
                onBlur={event => event.target.value.trim() && event.target.value !== source.name
                  && patch({ name: event.target.value.trim() })}
              />
            </Field>
            <Field label="Colour">
              <ColourPicker
                value={source.colour}
                onChange={value => patch({ colour: value })}
                ariaLabel="Calendar source colour"
              />
            </Field>
            {source.kind === 'school' && (
              <div className="flex flex-col gap-2">
                {([
                  ['show_terms', 'Show school terms'],
                  ['show_holidays', 'Show school holidays'],
                  ['show_student_free', 'Show student-free / pupil-free days'],
                ] as const).map(([key, label]) => (
                  <label key={key} className="flex min-h-11 items-center gap-2 text-sm text-ink">
                    <input
                      type="checkbox"
                      checked={Boolean(source.settings_json[key])}
                      onChange={event => patch({
                        settings_json: { ...source.settings_json, [key]: event.target.checked },
                      })}
                    />
                    {label}
                  </label>
                ))}
              </div>
            )}
            {source.kind === 'holidays' && (
              <div className="flex flex-col gap-2">
                {([
                  ['include_national', 'National public holidays'],
                  ['include_regional', 'State / territory holidays'],
                  ['include_local', 'Local & show holidays'],
                ] as const).map(([key, label]) => (
                  <label key={key} className="flex min-h-11 items-center gap-2 text-sm text-ink">
                    <input
                      type="checkbox"
                      checked={source.settings_json[key] !== false}
                      onChange={event => patch({
                        settings_json: { ...source.settings_json, [key]: event.target.checked },
                      })}
                    />
                    {label}
                  </label>
                ))}
                <p className="text-xs text-muted">
                  Which holidays apply comes from your household location in Settings.
                  Queensland is supported; other states are not available yet.
                </p>
              </div>
            )}
            <div className="flex flex-col gap-2 border-t border-line pt-3">
              {([
                ['show_on_calendar', 'Show on Calendar'],
                ['show_in_upcoming', 'Show in Dashboard Upcoming'],
                ['notifications_enabled', 'Send notifications'],
              ] as const).map(([key, label]) => (
                <label key={key} className="flex min-h-11 items-center gap-2 text-sm text-ink">
                  <input
                    type="checkbox"
                    checked={source[key]}
                    onChange={event => patch({ [key]: event.target.checked })}
                  />
                  {label}
                </label>
              ))}
              <p className="text-xs text-muted">
                Notifications stay off unless you turn them on, so subscribing to a season does not
                announce every fixture.
              </p>
            </div>
            {source.has_url && (
              <div className="border-t border-line pt-3">
                <p className="text-xs text-muted">Feed host: {source.url_display || 'unknown'}</p>
                <p className="mt-1 text-xs text-muted">
                  The full link is not shown — subscription links often contain a private token.
                  Paste a new link to replace it.
                </p>
                <Input
                  aria-label="Replace calendar link"
                  placeholder="https://example.com/fixtures.ics"
                  onBlur={event => event.target.value.trim() && patch({ url: event.target.value.trim() })}
                  className="mt-2"
                />
              </div>
            )}
          </div>
        </Modal>
      )}
    </div>
  )
}

function AddSourceModal({ catalogue, onClose, onAdded, onError }: {
  catalogue: CalendarSourceCatalogueEntry[]
  onClose: () => void
  onAdded: (source: CalendarSource) => void
  onError: (message: string) => void
}) {
  const [mode, setMode] = useState<'automatic' | 'subscribe' | 'import'>('automatic')
  const [entryKey, setEntryKey] = useState('')
  const [name, setName] = useState('')
  const [url, setUrl] = useState('')
  const [icsText, setIcsText] = useState('')
  const [system, setSystem] = useState(SCHOOL_SYSTEMS[0].value)
  const [preview, setPreview] = useState<CalendarSourcePreview | null>(null)
  const [busy, setBusy] = useState(false)

  const automatic = catalogue.filter(entry => !entry.needs_url && entry.kind !== 'import')
  const selected = automatic.find(entry => `${entry.kind}:${entry.provider}` === entryKey) ?? automatic[0]

  const runPreview = async () => {
    setBusy(true); setPreview(null)
    try {
      setPreview(await api.previewCalendarSource(
        mode === 'subscribe' ? { url: url.trim() } : { ics_text: icsText },
      ))
    } catch (error) { onError(errMsg(error)) }
    finally { setBusy(false) }
  }

  const save = async () => {
    setBusy(true)
    try {
      if (mode === 'automatic') {
        if (!selected) return
        onAdded(await api.createCalendarSource({
          kind: selected.kind,
          provider: selected.provider,
          name: name.trim() || selected.label,
          settings_json: selected.kind === 'school' ? { system } : {},
        }))
      } else if (mode === 'subscribe') {
        onAdded(await api.createCalendarSource({
          kind: 'subscription', provider: 'ics',
          name: name.trim() || 'Subscribed calendar', url: url.trim(),
        }))
      } else {
        onAdded(await api.createCalendarSource({
          kind: 'import', provider: 'ics',
          name: name.trim() || 'Imported calendar', ics_text: icsText,
        }))
      }
      onClose()
    } catch (error) { onError(errMsg(error)) }
    finally { setBusy(false) }
  }

  const canSave = mode === 'automatic'
    ? Boolean(selected)
    : mode === 'subscribe' ? url.trim().length > 0 : icsText.trim().length > 0

  return (
    <Modal
      title="Add calendar source"
      onClose={onClose}
      size="full"
      footer={(
        <>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button onClick={save} loading={busy} disabled={!canSave}>Add</Button>
        </>
      )}
    >
      <div className="flex flex-col gap-3">
        <Field label="What kind of calendar?">
          <Select aria-label="What kind of calendar?" value={mode}
            onChange={event => { setMode(event.target.value as typeof mode); setPreview(null) }}>
            <option value="automatic">Automatic (holidays, school terms)</option>
            <option value="subscribe">Subscribe to a calendar (ICS / webcal link)</option>
            <option value="import">Import a calendar file (one-off)</option>
          </Select>
        </Field>

        {mode === 'automatic' && (
          <>
            <Field label="Calendar">
              <Select aria-label="Calendar" value={entryKey || (selected ? `${selected.kind}:${selected.provider}` : '')}
                onChange={event => setEntryKey(event.target.value)}>
                {automatic.map(entry => (
                  <option key={`${entry.kind}:${entry.provider}`} value={`${entry.kind}:${entry.provider}`}>
                    {entry.label}
                  </option>
                ))}
              </Select>
            </Field>
            {selected?.kind === 'school' && (
              <Field label="Education system" hint="Choose the division your school follows. Catholic and independent schools often differ by a day or more.">
                <Select aria-label="Education system" value={system} onChange={event => setSystem(event.target.value)}>
                  {SCHOOL_SYSTEMS.map(entry => (
                    <option key={entry.value} value={entry.value}>{entry.label}</option>
                  ))}
                </Select>
              </Field>
            )}
            {selected?.kind === 'holidays' && (
              <p className="rounded-xl bg-sunken p-3 text-xs text-muted">
                Which holidays apply is decided by your household location in Settings — country,
                state and local area. Queensland is supported; other states are not available yet.
              </p>
            )}
          </>
        )}

        {mode === 'subscribe' && (
          <>
            <Field label="Calendar link" hint="An ICS or webcal address, e.g. from a club or school.">
              <Input aria-label="Calendar link" value={url} onChange={event => setUrl(event.target.value)}
                placeholder="https://example.com/fixtures.ics" />
            </Field>
            <Button variant="secondary" onClick={runPreview} disabled={!url.trim() || busy}>Preview</Button>
          </>
        )}

        {mode === 'import' && (
          <>
            <Field label="Calendar file" hint="Read once. It will not refresh by itself.">
              <input
                type="file"
                accept=".ics,text/calendar"
                aria-label="Calendar file"
                onChange={async event => {
                  const file = event.target.files?.[0]
                  if (!file) return
                  setIcsText(await file.text())
                  setPreview(null)
                  if (!name.trim()) setName(file.name.replace(/\.ics$/i, ''))
                }}
                className="w-full text-sm"
              />
            </Field>
            <Button variant="secondary" onClick={runPreview} disabled={!icsText.trim() || busy}>Preview</Button>
          </>
        )}

        {preview && (
          <div className="rounded-2xl bg-sunken p-3 text-sm">
            <p className="font-bold text-ink">{preview.event_count} events</p>
            <p className="text-xs text-muted">{preview.future_count} upcoming · {preview.past_count} past</p>
            <ul className="mt-2 space-y-1">
              {preview.sample.map(row => (
                <li key={`${row.title}-${row.start_at}`} className="truncate text-xs text-muted-strong">
                  {row.title} — {new Date(row.start_at).toLocaleString()}
                </li>
              ))}
            </ul>
          </div>
        )}

        <Field label="Name (optional)">
          <Input aria-label="Source name" value={name} onChange={event => setName(event.target.value)} placeholder="Shown on your calendar" />
        </Field>
      </div>
    </Modal>
  )
}

export function CalendarSourcesPage() {
  const { user } = useAuth()
  const canManage = user?.role === 'admin' || user?.role === 'manager'
  const [sources, setSources] = useState<CalendarSource[] | null>(null)
  const [catalogue, setCatalogue] = useState<CalendarSourceCatalogueEntry[]>([])
  const [error, setError] = useState<string | null>(null)
  const [adding, setAdding] = useState(false)

  const load = useCallback(() => api.getCalendarSources()
    .then(data => { setSources(data.sources); setCatalogue(data.catalogue) })
    .catch(reason => { setError(errMsg(reason)); setSources([]) }), [])
  useEffect(() => { void load() }, [load])

  const replace = (next: CalendarSource) =>
    setSources(current => current?.map(row => row.id === next.id ? next : row) ?? current)

  if (!sources) return <PageSkeleton />

  return (
    <div className="flex flex-col gap-4">
      <MobileScreenHeader className="sm:hidden" title="Calendar sources" showBack onBack="/calendar" />
      <div className="hidden sm:block">
        <PageHeader title="Calendar sources" subtitle="Holidays, school terms and subscribed calendars" icon="🗓" />
      </div>
      {error && <InlineAlert tone="danger" message={error} onDismiss={() => setError(null)} />}

      <Card title="HomeStack">
        <p className="text-sm text-muted">
          Your own events, appointments and reminders. Always on.
        </p>
        <Link to="/calendar" className="mt-2 inline-flex min-h-11 items-center text-sm font-bold text-primary hover:underline">
          Open calendar →
        </Link>
      </Card>

      {GROUPS.map(group => {
        const rows = sources.filter(source => group.kinds.includes(source.kind))
        if (!rows.length) return null
        return (
          <section key={group.key} className="flex flex-col gap-2">
            <h2 className="text-xs font-extrabold uppercase tracking-[0.15em] text-muted/70">{group.label}</h2>
            {rows.map(source => (
              <SourceRow
                key={source.id}
                source={source}
                canManage={canManage}
                onChange={replace}
                onRemove={id => setSources(current => current?.filter(row => row.id !== id) ?? current)}
                onError={setError}
              />
            ))}
          </section>
        )
      })}

      {!sources.length && (
        <EmptyState
          icon="🗓"
          title="No extra calendars yet"
          hint="Add public holidays, school terms or a subscribed calendar to see them alongside your own events."
        />
      )}

      {canManage ? (
        <Button onClick={() => setAdding(true)} className="self-start">+ Add calendar source</Button>
      ) : (
        <p className="text-xs text-muted">Only an admin or manager can add or change household calendars.</p>
      )}

      {adding && (
        <AddSourceModal
          catalogue={catalogue}
          onClose={() => setAdding(false)}
          onAdded={source => setSources(current => [...(current ?? []), source])}
          onError={setError}
        />
      )}
    </div>
  )
}
