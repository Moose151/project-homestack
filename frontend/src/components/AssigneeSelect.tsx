import { useState } from 'react'
import type { Person } from '../api/types'

interface Props {
  people: Person[]
  /** Person ids. Empty = the whole household. */
  value: number[]
  onChange: (ids: number[]) => void
  className?: string
}

/** Label for a chosen set: "Whole family", a name, "Ana + Bo", or "3 people". */
export function assigneeLabel(people: Person[], ids: number[]): string {
  if (ids.length === 0) return 'Whole family'
  const names = ids
    .map(id => people.find(person => person.id === id))
    .filter((person): person is Person => Boolean(person))
    .map(person => person.preferred_name || person.display_name)
  if (names.length === 0) return 'Whole family'
  if (names.length === 1) return names[0]
  if (names.length === 2) return `${names[0]} + ${names[1]}`
  return `${names.length} people`
}

/**
 * Assign something to nobody in particular, one person, or several.
 *
 * Assignment used to be a single dropdown where "Whole family" was the absence of a person,
 * so "both of us" could not be said at all (owner request, 2026-08-09). Selecting nobody
 * still means the whole household — the common case stays one tap.
 */
export function AssigneeSelect({ people, value, onChange, className }: Props) {
  const [open, setOpen] = useState(false)

  const toggle = (id: number) => {
    onChange(value.includes(id) ? value.filter(existing => existing !== id) : [...value, id])
  }

  return (
    <div className={`relative ${className ?? ''}`}>
      <button
        type="button"
        onClick={() => setOpen(current => !current)}
        aria-expanded={open}
        aria-haspopup="true"
        className="flex min-h-11 w-full items-center justify-between gap-2 rounded-xl border border-line bg-surface px-3 py-2 text-left text-sm text-ink"
      >
        <span className="truncate">
          {value.length === 0 && <span aria-hidden className="mr-1.5">👪</span>}
          {assigneeLabel(people, value)}
        </span>
        <span aria-hidden className="flex-shrink-0 text-muted">▾</span>
      </button>

      {open && (
        <>
          {/* Click-away layer: a plain overlay keeps focus handling simple on touch. */}
          <button
            type="button"
            aria-label="Close assignee list"
            onClick={() => setOpen(false)}
            className="fixed inset-0 z-20 cursor-default"
          />
          <div className="absolute left-0 right-0 z-30 mt-1 max-h-64 overflow-auto rounded-xl border border-line bg-surface p-1 shadow-soft">
            <button
              type="button"
              onClick={() => { onChange([]); setOpen(false) }}
              className={`flex min-h-11 w-full items-center gap-2 rounded-lg px-2 text-left text-sm ${
                value.length === 0 ? 'bg-primary-soft text-primary' : 'text-ink hover:bg-sunken'
              }`}
            >
              <span aria-hidden>👪</span> Whole family
            </button>
            <div className="my-1 border-t border-line" />
            {people.map(person => {
              const checked = value.includes(person.id)
              return (
                <label
                  key={person.id}
                  className="flex min-h-11 w-full cursor-pointer items-center gap-2 rounded-lg px-2 text-sm text-ink hover:bg-sunken"
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => toggle(person.id)}
                    className="h-4 w-4 flex-shrink-0 accent-[var(--hs-primary)]"
                  />
                  <span className="truncate">{person.preferred_name || person.display_name}</span>
                </label>
              )
            })}
            {people.length === 0 && (
              <p className="px-2 py-3 text-sm text-muted">No people yet.</p>
            )}
          </div>
        </>
      )}
    </div>
  )
}

/** The person linked to a login, as a one-element list for defaulting a new item's assignee. */
export function personIdForUser(people: Person[], userId: number | undefined): number[] {
  if (!userId) return []
  const person = people.find(candidate => candidate.linked_user_id === userId)
  return person ? [person.id] : []
}
