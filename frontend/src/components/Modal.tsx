import { useId, type ReactNode } from 'react'
import { useDialogA11y } from './useDialogA11y'

/** Shared modal/dialog: backdrop, Escape-to-close, click-outside, focus trap, scroll lock. */
export function Modal({
  title,
  onClose,
  children,
  footer,
  size = 'md',
}: {
  title?: ReactNode
  onClose: () => void
  children: ReactNode
  footer?: ReactNode
  /** 'full' is docs/36 §5's "full-height/focused mobile form sheet" — edge-to-edge and
   * near-viewport-height on phone (a whole screen's worth of a create/edit flow), but no
   * larger than the normal 'lg' dialog on desktop, where a full-height modal would be unusual. */
  size?: 'sm' | 'md' | 'lg' | 'full'
}) {
  const titleId = useId()
  const dialogRef = useDialogA11y(onClose)

  const maxW = size === 'sm' ? 'max-w-sm' : size === 'lg' || size === 'full' ? 'max-w-2xl' : 'max-w-lg'
  const isFull = size === 'full'

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-0 backdrop-blur-sm sm:items-center sm:p-4"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby={title ? titleId : undefined}
    >
      <div
        ref={dialogRef}
        className={`flex w-full ${maxW} flex-col overflow-y-auto bg-surface shadow-card ${
          isFull
            // Edge-to-edge on phone reaches the physical top of the screen, so an installed
            // iPhone PWA/notched device needs its own top inset — the bottom padding on the
            // non-full sheet only ever had to clear the home indicator, not a notch/status bar.
            ? 'h-[100dvh] max-h-[100dvh] rounded-none pt-[env(safe-area-inset-top)] sm:h-auto sm:max-h-[92vh] sm:rounded-2xl sm:pt-0'
            : 'max-h-[92vh] rounded-t-2xl pb-[env(safe-area-inset-bottom)] sm:rounded-2xl sm:pb-0'
        }`}
        onClick={e => e.stopPropagation()}
      >
        {title && (
          <div className="sticky top-0 z-10 flex items-center justify-between gap-3 border-b border-line bg-surface/95 px-5 py-3.5 backdrop-blur">
            <h2 id={titleId} className="text-base font-bold text-ink">{title}</h2>
            <button
              onClick={onClose}
              className="grid h-11 w-11 flex-shrink-0 place-items-center rounded-lg text-muted transition-colors hover:bg-sunken hover:text-ink"
              aria-label="Close"
            >
              ✕
            </button>
          </div>
        )}
        <div className={`p-4 sm:p-5 ${isFull ? 'flex-1' : ''}`}>{children}</div>
        {footer && (
          <div className={`sticky bottom-0 flex justify-end gap-2 border-t border-line bg-surface/95 px-5 py-3.5 backdrop-blur ${isFull ? 'pb-[calc(0.875rem+env(safe-area-inset-bottom))] sm:pb-3.5' : ''}`}>
            {footer}
          </div>
        )}
      </div>
    </div>
  )
}
