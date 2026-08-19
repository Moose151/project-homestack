import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import type { AppNotification } from '../api/types'

const LEVEL_DOT: Record<string, string> = {
  success: 'bg-success', warning: 'bg-warning', danger: 'bg-danger', info: 'bg-primary',
}

export function NotificationBell() {
  const navigate = useNavigate()
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
  const markSnapshotRead = async (snapshot = items) => {
    const throughId = snapshot.reduce((maximum, note) => Math.max(maximum, note.id), 0)
    const snapshotUnread = snapshot.filter(note => !note.is_read && note.id <= throughId).length
    if (!throughId || !snapshotUnread) return
    setItems(current => current.map(note => note.id <= throughId ? { ...note, is_read: true } : note))
    setUnread(current => Math.max(0, current - snapshotUnread))
    try {
      await api.markAllNotificationsRead(throughId)
    } catch {
      // Optimism keeps the badge responsive, but backend truth wins when persistence fails.
      load()
    }
  }
  const toggle = () => {
    setOpen(current => {
      const next = !current
      if (next) void markSnapshotRead(items)
      return next
    })
  }
  const markAll = async () => { await markSnapshotRead(items) }
  const openItem = async (notification: AppNotification) => {
    await markRead(notification)
    if (notification.action_url) {
      setOpen(false)
      navigate(notification.action_url)
    }
  }

  return (
    <div className="relative" ref={ref}>
      <button onClick={toggle}
        className="relative w-11 h-11 grid place-items-center rounded-xl hover:bg-sunken text-muted-strong"
        aria-label="Notifications">
        <span className="text-lg">🔔</span>
        {unread > 0 && (
          <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 rounded-full bg-danger text-white text-[11px] font-bold grid place-items-center">
            {unread > 9 ? '9+' : unread}
          </span>
        )}
      </button>

      {open && (
        <div className="fixed inset-x-3 top-[62px] max-h-[70vh] overflow-auto rounded-2xl border border-line bg-surface shadow-card z-30 sm:absolute sm:inset-x-auto sm:right-0 sm:top-auto sm:mt-2 sm:w-80 sm:max-h-96">
          <div className="flex items-center justify-between px-4 py-2.5 border-b border-line">
            <span className="text-sm font-semibold text-ink">Notifications</span>
            {unread > 0 && <button onClick={markAll} className="text-xs text-primary hover:underline">Mark all read</button>}
          </div>
          {items.length === 0 ? (
            <p className="text-sm text-muted text-center py-6">Nothing yet.</p>
          ) : (
            <ul className="divide-y divide-line/60">
              {items.map(n => (
                <li key={n.id} onClick={() => openItem(n)}
                  className={`px-4 py-3 cursor-pointer hover:bg-sunken ${n.is_read ? 'opacity-60' : ''}`}>
                  <div className="flex items-start gap-2">
                    <span className={`mt-1.5 w-2 h-2 rounded-full flex-shrink-0 ${LEVEL_DOT[n.level] ?? 'bg-primary'}`} />
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-ink">{n.title}</p>
                      <p className="text-xs text-muted">{n.message}</p>
                      {n.action_url && <p className="mt-1 text-[11px] font-semibold text-primary">Open →</p>}
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
