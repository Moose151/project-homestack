import type {
  InputHTMLAttributes,
  TextareaHTMLAttributes,
  SelectHTMLAttributes,
  ReactNode,
} from 'react'
import { forwardRef } from 'react'

// Shared form-control styling so every node's inputs look identical (UI/UX §5).
// One source of truth for the "field" look — do not hand-roll input classes per page.
export const fieldClass =
  'w-full min-w-0 max-w-full rounded-xl border border-line bg-surface px-3 py-2.5 text-sm text-ink placeholder:text-muted ' +
  'outline-none transition-colors focus:border-primary focus:ring-2 focus:ring-primary/30 ' +
  'disabled:opacity-60 disabled:cursor-not-allowed min-h-[44px]'

const labelClass = 'text-xs font-semibold uppercase tracking-wide text-muted-strong'

/** Label + optional hint/error wrapper around any control. */
export function Field({
  label,
  hint,
  error,
  htmlFor,
  children,
  className = '',
}: {
  label?: string
  hint?: string
  error?: string | null
  htmlFor?: string
  children: ReactNode
  className?: string
}) {
  return (
    <div className={`flex flex-col gap-1.5 ${className}`}>
      {label && (
        <label htmlFor={htmlFor} className={labelClass}>
          {label}
        </label>
      )}
      {children}
      {error ? (
        <p className="text-xs text-danger">{error}</p>
      ) : hint ? (
        <p className="text-xs text-muted">{hint}</p>
      ) : null}
    </div>
  )
}

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  function Input({ className = '', ...props }, ref) {
    return <input ref={ref} className={`${fieldClass} ${className}`} {...props} />
  },
)

/** Search control with a persistent search cue and a touch-friendly clear action. */
export const SearchField = forwardRef<
  HTMLInputElement,
  Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> & { onClear?: () => void }
>(function SearchField({ className = '', value, onClear, ...props }, ref) {
  const hasValue = String(value ?? '').length > 0

  return (
    <div className="relative w-full">
      <span className="pointer-events-none absolute inset-y-0 left-3 grid place-items-center text-muted" aria-hidden="true">
        ⌕
      </span>
      <input
        ref={ref}
        type="search"
        value={value}
        className={`${fieldClass} appearance-none pl-10 pr-10 [&::-webkit-search-cancel-button]:hidden ${className}`}
        {...props}
      />
      {hasValue && onClear && (
        <button
          type="button"
          onClick={onClear}
          className="absolute inset-y-0 right-1 grid w-10 place-items-center rounded-xl text-muted transition-colors hover:text-ink"
          aria-label="Clear search"
        >
          ✕
        </button>
      )}
    </div>
  )
})

export function Textarea({ className = '', ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={`${fieldClass} min-h-[80px] py-2 leading-relaxed ${className}`} {...props} />
}

export function Select({ className = '', children, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select className={`${fieldClass} cursor-pointer pr-8 ${className}`} {...props}>
      {children}
    </select>
  )
}
