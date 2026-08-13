import { useState, type ReactNode } from 'react'
import { Modal } from '../Modal'

export interface MobileAction {
  label: string
  icon?: ReactNode
  onClick: () => void
  tone?: 'default' | 'danger'
  disabled?: boolean
}

/**
 * Contextual secondary actions collapsed behind a trigger (docs/36 §5, §5.1: "if a page has more
 * than one or two contextual actions, move them to the overflow menu or a dedicated action
 * sheet"). Self-contained: manages its own open state, closes itself after an action runs.
 * Built on the shared Modal so it gets the same backdrop/Escape/focus-trap behaviour as every
 * other sheet in the app rather than a bespoke popover implementation.
 */
export function MobileActionMenu({
  actions,
  label = 'More actions',
  trigger,
}: {
  actions: MobileAction[]
  /** Accessible name for the default kebab trigger; ignored if `trigger` is supplied. */
  label?: string
  /** Custom trigger element. Receives an onClick to open the menu. */
  trigger?: (open: () => void) => ReactNode
}) {
  const [open, setOpen] = useState(false)

  return (
    <>
      {trigger ? (
        trigger(() => setOpen(true))
      ) : (
        <button
          type="button"
          onClick={() => setOpen(true)}
          aria-label={label}
          className="grid h-11 w-11 flex-shrink-0 place-items-center rounded-xl text-xl text-muted transition-colors hover:bg-sunken hover:text-ink"
        >
          ⋮
        </button>
      )}
      {open && (
        <Modal onClose={() => setOpen(false)} size="sm">
          <div className="flex flex-col gap-1">
            {actions.map((action, i) => (
              <button
                key={i}
                type="button"
                disabled={action.disabled}
                onClick={() => { setOpen(false); action.onClick() }}
                className={`flex min-h-[44px] items-center gap-3 rounded-xl px-3 py-2.5 text-left text-[15px] font-semibold transition-colors disabled:opacity-40 ${
                  action.tone === 'danger' ? 'text-danger hover:bg-danger-soft' : 'text-ink hover:bg-sunken'
                }`}
              >
                {action.icon && <span className="text-lg leading-none">{action.icon}</span>}
                {action.label}
              </button>
            ))}
          </div>
        </Modal>
      )}
    </>
  )
}
