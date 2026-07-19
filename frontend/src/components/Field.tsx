import type {
  InputHTMLAttributes,
  TextareaHTMLAttributes,
  SelectHTMLAttributes,
  ReactNode,
} from 'react'

// Shared form-control styling so every node's inputs look identical (UI/UX §5).
// One source of truth for the "field" look — do not hand-roll input classes per page.
export const fieldClass =
  'w-full rounded-xl border border-line bg-surface px-3 py-2.5 text-sm text-ink placeholder:text-muted ' +
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

export function Input({ className = '', ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={`${fieldClass} ${className}`} {...props} />
}

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
