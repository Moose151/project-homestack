import { useEffect, useState } from 'react'

// A tiny dependency-free toast system. A module-level store lets non-React code
// (the api client) surface errors without prop-drilling or a context provider.

export type ToastType = 'error' | 'success' | 'info'

interface ToastItem {
  id: number
  message: string
  type: ToastType
}

type Listener = (items: ToastItem[]) => void

let items: ToastItem[] = []
let listeners: Listener[] = []
let nextId = 1

function emit() {
  listeners.forEach(l => l(items))
}

export function pushToast(message: string, type: ToastType = 'error') {
  const id = nextId++
  items = [...items, { id, message, type }]
  emit()
  setTimeout(() => dismissToast(id), 6000)
}

export function dismissToast(id: number) {
  items = items.filter(t => t.id !== id)
  emit()
}

const TYPE_STYLES: Record<ToastType, string> = {
  error: 'bg-danger text-white',
  success: 'bg-success text-white',
  info: 'bg-gray-800 text-white',
}

export function ToastHost() {
  const [toasts, setToasts] = useState<ToastItem[]>(items)

  useEffect(() => {
    const listener: Listener = next => setToasts([...next])
    listeners.push(listener)
    return () => { listeners = listeners.filter(l => l !== listener) }
  }, [])

  if (toasts.length === 0) return null

  return (
    <div className="fixed z-[100] bottom-20 md:bottom-6 right-4 left-4 md:left-auto md:w-96 flex flex-col gap-2 pointer-events-none">
      {toasts.map(t => (
        <div
          key={t.id}
          role="alert"
          className={`pointer-events-auto flex items-start gap-3 rounded-xl px-4 py-3 shadow-lg text-sm ${TYPE_STYLES[t.type]}`}
        >
          <span className="flex-1">{t.message}</span>
          <button
            onClick={() => dismissToast(t.id)}
            aria-label="Dismiss"
            className="text-white/80 hover:text-white text-lg leading-none flex-shrink-0"
          >
            ×
          </button>
        </div>
      ))}
    </div>
  )
}
