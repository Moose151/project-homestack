import type { ReactNode } from 'react'

/**
 * One vocabulary for per-row actions.
 *
 * The app had three ways to offer the same destructive action — the word "Delete", a bare
 * "×" glyph, and a "clear" chip — none of them in the danger colour. A row action that
 * destroys data should look the same and read the same everywhere, and should always say
 * what it does rather than rely on a glyph.
 */
export function RowActions({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <div className={`flex flex-shrink-0 items-center gap-0.5 ${className}`}>{children}</div>
}

const base = 'grid min-h-10 place-items-center rounded-lg px-2 text-xs font-semibold transition-colors'

export function EditAction({ onClick, label, disabled }: { onClick: () => void; label: string; disabled?: boolean }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={`Edit ${label}`}
      className={`${base} text-muted hover:bg-sunken hover:text-ink disabled:opacity-40`}
    >
      Edit
    </button>
  )
}

export function DeleteAction({ onClick, label, disabled }: { onClick: () => void; label: string; disabled?: boolean }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={`Delete ${label}`}
      className={`${base} text-muted hover:bg-danger-soft hover:text-danger disabled:opacity-40`}
    >
      Delete
    </button>
  )
}

/** Non-destructive dismissal — removing something from a view, not deleting the record. */
export function RemoveAction({ onClick, label, disabled }: { onClick: () => void; label: string; disabled?: boolean }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={`Remove ${label}`}
      className={`${base} text-muted hover:bg-sunken hover:text-ink disabled:opacity-40`}
    >
      Remove
    </button>
  )
}
