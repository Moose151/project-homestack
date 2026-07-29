import { useEffect } from 'react'

export function UndoToast({
  message,
  onUndo,
  onDismiss,
  durationMs = 6000,
}: {
  message: string
  onUndo: () => void
  onDismiss: () => void
  durationMs?: number
}) {
  useEffect(() => {
    const timer = window.setTimeout(onDismiss, durationMs)
    return () => window.clearTimeout(timer)
  }, [durationMs, onDismiss])

  return (
    <div className="fixed bottom-20 left-1/2 z-[60] flex -translate-x-1/2 items-center gap-4 rounded-2xl bg-ink px-4 py-3 text-sm text-surface shadow-card md:bottom-6">
      <span>{message}</span>
      <button onClick={onUndo} className="font-bold text-primary-soft hover:underline">Undo</button>
      <button onClick={onDismiss} className="text-surface/70" aria-label="Dismiss">×</button>
    </div>
  )
}
