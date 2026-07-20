import { useEffect, useRef, useState, type ReactNode } from 'react'

/**
 * Anchored dropdown panel: a trigger button + a floating panel with click-outside and
 * Escape-to-close. Used for compact toolbars (e.g. the Calendar "Filter" popover) so a row
 * of chips can collapse into one control on small screens.
 */
export function Popover({
  trigger,
  children,
  align = 'right',
  panelClassName = 'w-72',
}: {
  /** Rendered inside the trigger button; receives whether the panel is open. */
  trigger: (state: { open: boolean }) => ReactNode
  /** Panel contents; receives a `close` callback. */
  children: (state: { close: () => void }) => ReactNode
  align?: 'left' | 'right'
  panelClassName?: string
}) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false) }
    document.addEventListener('mousedown', onClick)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onClick)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        className={`flex items-center gap-1.5 rounded-xl border px-3 py-1.5 text-sm font-medium transition-colors min-h-[38px] ${
          open ? 'border-primary bg-primary-soft text-primary' : 'border-line text-muted-strong hover:text-ink'
        }`}
      >
        {trigger({ open })}
      </button>
      {open && (
        <div
          className={`absolute z-30 mt-2 rounded-2xl border border-line bg-surface p-3 shadow-card ${panelClassName} ${
            align === 'right' ? 'right-0' : 'left-0'
          }`}
        >
          {children({ close: () => setOpen(false) })}
        </div>
      )}
    </div>
  )
}
