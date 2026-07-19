import { useEffect, type ReactNode } from 'react'

/** Shared modal/dialog: backdrop, Escape-to-close, click-outside, scroll lock. */
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
  size?: 'sm' | 'md' | 'lg'
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
    }
  }, [onClose])

  const maxW = size === 'sm' ? 'max-w-sm' : size === 'lg' ? 'max-w-2xl' : 'max-w-lg'

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-0 backdrop-blur-sm sm:items-center sm:p-4"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
    >
      <div
        className={`w-full ${maxW} max-h-[92vh] overflow-y-auto rounded-t-2xl bg-surface shadow-card sm:rounded-2xl`}
        onClick={e => e.stopPropagation()}
      >
        {title && (
          <div className="sticky top-0 z-10 flex items-center justify-between gap-3 border-b border-line bg-surface/95 px-5 py-3.5 backdrop-blur">
            <h2 className="text-base font-bold text-ink">{title}</h2>
            <button
              onClick={onClose}
              className="grid h-8 w-8 flex-shrink-0 place-items-center rounded-lg text-muted transition-colors hover:bg-sunken hover:text-ink"
              aria-label="Close"
            >
              ✕
            </button>
          </div>
        )}
        <div className="p-5">{children}</div>
        {footer && (
          <div className="sticky bottom-0 flex justify-end gap-2 border-t border-line bg-surface/95 px-5 py-3.5 backdrop-blur">
            {footer}
          </div>
        )}
      </div>
    </div>
  )
}
