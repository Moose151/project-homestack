import { Button } from './Button'

export function InlineAlert({
  message,
  onRetry,
  onDismiss,
}: {
  message: string
  onRetry?: () => void
  onDismiss?: () => void
}) {
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-xl border border-danger/20 bg-danger-soft px-4 py-3 text-sm text-danger" role="alert">
      <span className="min-w-0 flex-1">{message}</span>
      {onRetry && <Button size="sm" variant="ghost" onClick={onRetry}>Retry</Button>}
      {onDismiss && <button onClick={onDismiss} className="grid h-8 w-8 place-items-center rounded-lg hover:bg-danger/10" aria-label="Dismiss">×</button>}
    </div>
  )
}

export function PageSkeleton({ cards = 3 }: { cards?: number }) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2" aria-label="Loading">
      {Array.from({ length: cards }, (_, index) => (
        <div key={index} className={`h-36 animate-pulse rounded-2xl bg-sunken ${index === 0 ? 'sm:col-span-2' : ''}`} />
      ))}
    </div>
  )
}
