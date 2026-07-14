import type { Person } from '../api/types'

interface Props {
  people: Person[]
  value: number | null // person id, or null = "Whole family"
  onChange: (v: number | null) => void
  className?: string
}

/** Assign something to a specific person or to the whole family (null). */
export function AssigneeSelect({ people, value, onChange, className }: Props) {
  return (
    <select
      value={value ?? 0}
      onChange={e => onChange(Number(e.target.value) || null)}
      className={className}
      aria-label="Assign to"
    >
      <option value={0}>👪 Whole family</option>
      {people.map(p => (
        <option key={p.id} value={p.id}>{p.display_name}</option>
      ))}
    </select>
  )
}

/** The person id linked to a given login user (for defaulting an assignee to the adder). */
export function personIdForUser(people: Person[], userId: number | undefined): number | null {
  if (!userId) return null
  const p = people.find(pp => pp.linked_user_id === userId)
  return p ? p.id : null
}
