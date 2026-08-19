import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../../../api/client'
import type { QuickLaunchShortcut, QuickLaunchTarget } from '../../../api/types'
import { Button } from '../../../components/Button'
import { confirmDialog } from '../../../components/Dialogs'
import { EmptyState } from '../../../components/EmptyState'
import { Field, Input, Select } from '../../../components/Field'
import { Modal } from '../../../components/Modal'
import { PageHeader } from '../../../components/PageHeader'
import { InlineAlert, PageSkeleton } from '../../../components/PageState'
import { MobileScreenHeader } from '../../../components/mobile'
import { STACK_BY_KEY } from '../../../config/stacks'

const errMsg = (error: unknown) => error instanceof Error ? error.message : 'Something went wrong.'

/** The user-facing product name for a target's owning area. Internal keys never surface. */
function areaName(nodeKey: string) {
  if (!nodeKey) return 'HomeStack'
  return STACK_BY_KEY[nodeKey]?.navLabel ?? 'HomeStack'
}

function AddShortcutModal({ targets, onClose, onAdded, onError }: {
  targets: QuickLaunchTarget[]
  onClose: () => void
  onAdded: (shortcut: QuickLaunchShortcut) => void
  onError: (message: string) => void
}) {
  const [targetKey, setTargetKey] = useState(targets[0]?.key ?? '')
  const [objectId, setObjectId] = useState<number | ''>('')
  const [label, setLabel] = useState('')
  const [saving, setSaving] = useState(false)

  const target = targets.find(entry => entry.key === targetKey)
  useEffect(() => { setObjectId(target?.objects[0]?.id ?? '') }, [targetKey])

  const save = async () => {
    if (!target) return
    setSaving(true)
    try {
      onAdded(await api.createQuickLaunchShortcut({
        target_key: target.key,
        target_object_id: target.requires_object ? Number(objectId) : null,
        custom_label: label.trim(),
      }))
      onClose()
    } catch (error) { onError(errMsg(error)) }
    finally { setSaving(false) }
  }

  return (
    <Modal
      title="Add a shortcut"
      onClose={onClose}
      size="full"
      footer={(
        <>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button onClick={save} loading={saving} disabled={!target || (target.requires_object && !objectId)}>
            Add
          </Button>
        </>
      )}
    >
      <div className="flex flex-col gap-3">
        <Field label="Where should it go?">
          <Select aria-label="Destination" value={targetKey} onChange={event => setTargetKey(event.target.value)}>
            {targets.map(entry => (
              <option key={entry.key} value={entry.key}>
                {areaName(entry.node_key)} — {entry.label}
              </option>
            ))}
          </Select>
        </Field>
        {target && <p className="text-xs text-muted">{target.description}</p>}

        {target?.requires_object && (
          <Field label="Which one?">
            <Select
              aria-label="Item"
              value={String(objectId)}
              onChange={event => setObjectId(Number(event.target.value))}
            >
              {target.objects.map(option => (
                <option key={option.id} value={option.id}>{option.label}</option>
              ))}
            </Select>
          </Field>
        )}

        <Field label="Name (optional)" hint="Leave blank to use the destination's own name.">
          <Input
            aria-label="Shortcut name"
            value={label}
            onChange={event => setLabel(event.target.value)}
            maxLength={60}
            placeholder="e.g. Groceries"
          />
        </Field>

        {target?.sensitive && (
          <p className="rounded-xl bg-sunken p-3 text-xs text-muted">
            This area asks for your password before it opens. The shortcut takes you there — it
            does not skip the prompt.
          </p>
        )}
        {target?.target_type === 'action' && (
          <p className="rounded-xl bg-sunken p-3 text-xs text-muted">
            This opens the form ready to fill in. Nothing is saved until you say so.
          </p>
        )}
      </div>
    </Modal>
  )
}

function ShortcutRow({ shortcut, index, total, onMove, onChange, onRemove, onError }: {
  shortcut: QuickLaunchShortcut
  index: number
  total: number
  onMove: (from: number, to: number) => void
  onChange: (next: QuickLaunchShortcut) => void
  onRemove: (id: string) => void
  onError: (message: string) => void
}) {
  const [renaming, setRenaming] = useState(false)
  const [label, setLabel] = useState(shortcut.custom_label)
  const [busy, setBusy] = useState(false)
  const navigate = useNavigate()

  const rename = async () => {
    setBusy(true)
    try { onChange(await api.updateQuickLaunchShortcut(shortcut.id, { custom_label: label.trim() })) }
    catch (error) { onError(errMsg(error)) }
    finally { setBusy(false); setRenaming(false) }
  }

  const remove = async () => {
    if (!await confirmDialog({
      title: `Remove "${shortcut.label}"?`,
      message: 'The shortcut goes away. Nothing it pointed at is affected.',
      confirmLabel: 'Remove',
    })) return
    setBusy(true)
    try { await api.deleteQuickLaunchShortcut(shortcut.id); onRemove(shortcut.id) }
    catch (error) { onError(errMsg(error)); setBusy(false) }
  }

  const unavailable = shortcut.status === 'unavailable'

  return (
    <li
      data-quick-launch-row
      // Wraps at narrow widths: five controls and a label do not fit one row on a 320px phone,
      // and squeezing the label to nothing is worse than using a second line.
      className={`flex flex-wrap items-center gap-x-2 gap-y-1 rounded-2xl border bg-surface px-3 py-2 ${
        unavailable ? 'border-line bg-sunken/40' : 'border-line'
      }`}
    >
      <span className="grid h-10 w-10 flex-shrink-0 place-items-center rounded-xl bg-sunken text-xl" aria-hidden>
        {shortcut.icon}
      </span>
      <span className="min-w-0 flex-1 basis-40">
        <span className={`block truncate text-sm font-bold ${unavailable ? 'text-muted' : 'text-ink'}`}>
          {shortcut.label}
        </span>
        <span className="block truncate text-xs text-muted">
          {unavailable
            ? shortcut.unavailable_reason
            : shortcut.status === 'locked'
              ? `${areaName(shortcut.node_key)} · unlocks with your password`
              : areaName(shortcut.node_key)}
        </span>
      </span>
      <span className="ml-auto flex flex-shrink-0 items-center gap-0.5">
        {/* Arrows rather than drag: identical with a finger, a mouse and a keyboard. */}
        <button
          type="button"
          onClick={() => onMove(index, index - 1)}
          disabled={index === 0}
          aria-label={`Move ${shortcut.label} up`}
          className="grid h-11 w-11 place-items-center rounded-lg text-muted-strong hover:bg-sunken disabled:opacity-30"
        >↑</button>
        <button
          type="button"
          onClick={() => onMove(index, index + 1)}
          disabled={index === total - 1}
          aria-label={`Move ${shortcut.label} down`}
          className="grid h-11 w-11 place-items-center rounded-lg text-muted-strong hover:bg-sunken disabled:opacity-30"
        >↓</button>
        {!unavailable && (
          <button
            type="button"
            onClick={() => navigate(`/launch/${shortcut.id}`)}
            aria-label={`Open ${shortcut.label}`}
            className="min-h-11 rounded-lg px-2 text-xs font-bold text-primary hover:bg-primary-soft"
          >Open</button>
        )}
        <button
          type="button"
          onClick={() => { setLabel(shortcut.custom_label); setRenaming(true) }}
          aria-label={`Rename ${shortcut.label}`}
          className="min-h-11 rounded-lg px-2 text-xs font-semibold text-muted-strong hover:bg-sunken"
        >Rename</button>
        <button
          type="button"
          onClick={remove}
          disabled={busy}
          aria-label={`Remove ${shortcut.label}`}
          className="min-h-11 rounded-lg px-2 text-xs font-semibold text-danger hover:bg-danger-soft"
        >Remove</button>
      </span>

      {renaming && (
        <Modal
          title="Rename shortcut"
          onClose={() => setRenaming(false)}
          size="sm"
          footer={(
            <>
              <Button variant="ghost" onClick={() => setRenaming(false)}>Cancel</Button>
              <Button onClick={rename} loading={busy}>Save</Button>
            </>
          )}
        >
          <Field label="Name" hint="Leave blank to use the destination's own name.">
            <Input
              aria-label="Shortcut name"
              value={label}
              maxLength={60}
              onChange={event => setLabel(event.target.value)}
            />
          </Field>
        </Modal>
      )}
    </li>
  )
}

export function QuickLaunchPage() {
  const [shortcuts, setShortcuts] = useState<QuickLaunchShortcut[] | null>(null)
  const [targets, setTargets] = useState<QuickLaunchTarget[]>([])
  const [error, setError] = useState<string | null>(null)
  const [adding, setAdding] = useState(false)

  const load = useCallback(() => Promise.all([
    api.getQuickLaunchShortcuts(),
    api.getQuickLaunchTargets(),
  ])
    .then(([rows, catalogue]) => { setShortcuts(rows); setTargets(catalogue.targets) })
    .catch(reason => { setError(errMsg(reason)); setShortcuts([]) }), [])
  useEffect(() => { void load() }, [load])

  const move = async (from: number, to: number) => {
    if (!shortcuts || to < 0 || to >= shortcuts.length) return
    const next = [...shortcuts]
    const [moved] = next.splice(from, 1)
    next.splice(to, 0, moved)
    setShortcuts(next)
    try { setShortcuts(await api.reorderQuickLaunchShortcuts(next.map(row => row.id))) }
    catch (reason) { setError(errMsg(reason)); void load() }
  }

  if (!shortcuts) return <PageSkeleton />

  return (
    <div className="flex flex-col gap-4">
      <MobileScreenHeader className="sm:hidden" title="Quick Launch" showBack onBack="/settings" />
      <div className="hidden sm:block">
        <PageHeader
          title="Quick Launch"
          subtitle="Your own shortcuts to the places you go most"
          icon="🚀"
        />
      </div>
      {error && <InlineAlert tone="danger" message={error} onDismiss={() => setError(null)} />}

      <p className="text-sm text-muted">
        Shortcuts are yours alone and follow you between devices. They open the normal screen with
        the normal checks — a shortcut is a faster route, never extra access.
      </p>

      {shortcuts.length === 0 ? (
        <EmptyState
          icon="🚀"
          title="No shortcuts yet"
          hint="Add the lists, rooms and screens you open most, and they will be one tap away."
        />
      ) : (
        <ul className="flex flex-col gap-2" aria-label="Your shortcuts">
          {shortcuts.map((shortcut, index) => (
            <ShortcutRow
              key={shortcut.id}
              shortcut={shortcut}
              index={index}
              total={shortcuts.length}
              onMove={move}
              onChange={next => setShortcuts(current =>
                current?.map(row => row.id === next.id ? next : row) ?? current)}
              onRemove={id => setShortcuts(current => current?.filter(row => row.id !== id) ?? current)}
              onError={setError}
            />
          ))}
        </ul>
      )}

      <Button onClick={() => setAdding(true)} className="self-start" disabled={!targets.length}>
        + Add a shortcut
      </Button>
      {!targets.length && (
        <p className="text-xs text-muted">
          There is nothing to add yet — turn on the areas you use in Settings first.
        </p>
      )}
      <Link to="/settings" className="text-sm font-semibold text-primary hover:underline">
        Back to settings
      </Link>

      {adding && (
        <AddShortcutModal
          targets={targets}
          onClose={() => setAdding(false)}
          onAdded={shortcut => setShortcuts(current => [...(current ?? []), shortcut])}
          onError={setError}
        />
      )}
    </div>
  )
}
