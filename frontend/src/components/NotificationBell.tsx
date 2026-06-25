import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import type { AppNotification } from '../api/types'

const LEVEL_DOT: Record<string, string> = {
  success: 'bg-success', warning: 'bg-warning', danger: 'bg-danger', info: 'bg-primary',
}

export function NotificationBell() {
  const [items, setItems] = useState<AppNotification[]>([])
  const [unread, setUnread] = useState(0)
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  const load = () => api.getNotifications()
    .then(d => { setItems(d.results); setUnread(d.unread_count) })
    .catch(() => {})

  useEffect(() => {
    load()
    const id = setInterval(load, 60_000)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    const onClick = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false) }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [])

  const markRead = async (n: AppNotification) => {
    if (!n.is_read) { await api.markNotificationRead(n.id).catch(() => {}); load() }
  }
  const markAll = async () => { await api.markAllNotificationsRead().catch(() => {}); load() }

  return (
    <div className="relative" ref={ref}>
      <button onClick={() => setOpen(o => !o)}
        className="relative w-10 h-10 grid place-items-center rounded-xl hover:bg-sunken text-muted-strong"
        aria-label="Notifications">
        <span className="text-lg">🔔</span>
        {unread > 0 && (
          <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 rounded-full bg-danger text-white text-[11px] font-bold grid place-items-center">
            {unread > 9 ? '9+' : unread}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-80 max-h-96 overflow-auto bg-surface rounded-2xl shadow-soft border border-line z-30">
          <div className="flex items-center justify-between px-4 py-2.5 border-b border-line">
            <span className="text-sm font-semibold text-ink">Notifications</span>
            {unread > 0 && <button onClick={markAll} className="text-xs text-primary hover:underline">Mark all read</button>}
          </div>
          {items.length === 0 ? (
            <p className="text-sm text-muted text-center py-6">Nothing yet.</p>
          ) : (
            <ul className="divide-y divide-line/60">
              {items.map(n => (
                <li key={n.id} onClick={() => markRead(n)}
                  className={`px-4 py-3 cursor-pointer hover:bg-sunken ${n.is_read ? 'opacity-60' : ''}`}>
                  <div className="flex items-start gap-2">
                    <span className={`mt-1.5 w-2 h-2 rounded-full flex-shrink-0 ${LEVEL_DOT[n.level] ?? 'bg-primary'}`} />
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-ink">{n.title}</p>
                      <p className="text-xs text-muted">{n.message}</p>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
