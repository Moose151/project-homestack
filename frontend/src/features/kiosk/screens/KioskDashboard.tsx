import { useEffect, useState } from 'react'
import { api } from '../../../api/client'
import type { AuthUser, HubWidget, AtlasListItem as ListItem, AtlasReminder as Reminder } from '../../../api/types'
import { useInactivityTimeout } from '../hooks/useInactivityTimeout'

interface Props {
  authUser: AuthUser
  onLogout: () => void
}

function TodosWidget({ widget }: { widget: HubWidget }) {
  const items = widget.items as ListItem[]
  return (
    <div className="bg-gray-800 rounded-2xl p-6 flex-1 min-w-[280px]">
      <h2 className="text-lg font-semibold text-gray-200 mb-4">{widget.name}</h2>
      {items.length === 0 ? (
        <p className="text-gray-500 text-sm">Nothing to do 🎉</p>
      ) : (
        <ul className="space-y-3">
          {items.map((item) => (
            <li key={item.id} className="flex items-start gap-3">
              <span className="mt-1 w-4 h-4 rounded border border-gray-500 flex-shrink-0" />
              <span className="text-gray-200">{item.title}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function RemindersWidget({ widget }: { widget: HubWidget }) {
  const items = widget.items as Reminder[]

  const fmt = (dt: string) =>
    new Date(dt).toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' })

  return (
    <div className="bg-gray-800 rounded-2xl p-6 flex-1 min-w-[280px]">
      <h2 className="text-lg font-semibold text-gray-200 mb-4">{widget.name}</h2>
      {items.length === 0 ? (
        <p className="text-gray-500 text-sm">No upcoming reminders</p>
      ) : (
        <ul className="space-y-3">
          {items.map((item) => (
            <li key={item.id} className="flex flex-col gap-0.5">
              <span className="text-gray-200">{item.title}</span>
              {item.due_at && <span className="text-xs text-gray-500">{fmt(item.due_at)}</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

const WIDGET_COMPONENTS: Record<string, React.ComponentType<{ widget: HubWidget }>> = {
  atlas_todos: TodosWidget,
  atlas_reminders: RemindersWidget,
}

export function KioskDashboard({ authUser, onLogout }: Props) {
  const [widgets, setWidgets] = useState<HubWidget[]>([])
  const [loadError, setLoadError] = useState<string | null>(null)
  const [time, setTime] = useState(new Date())

  // Return to avatar selection after 5 minutes of inactivity.
  useInactivityTimeout(onLogout, 5 * 60 * 1000)

  useEffect(() => {
    const id = setInterval(() => setTime(new Date()), 60_000)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    api.kioskHub()
      .then((data) => setWidgets(data.widgets))
      .catch(() => setLoadError('Could not load hub data.'))
  }, [])

  const pad = (n: number) => String(n).padStart(2, '0')
  const timeStr = `${pad(time.getHours())}:${pad(time.getMinutes())}`

  const handleLogout = async () => {
    try { await api.logout() } catch { /* ignore */ }
    onLogout()
  }

  return (
    <div className="flex flex-col w-full h-full bg-gray-900 text-white">
      {/* Header */}
      <header className="flex items-center justify-between px-8 py-5 border-b border-gray-800">
        <div className="flex items-center gap-3">
          {authUser.avatar ? (
            <img src={authUser.avatar} alt="" className="w-10 h-10 rounded-full object-cover" />
          ) : (
            <div
              className="w-10 h-10 rounded-full flex items-center justify-center font-semibold text-sm"
              style={{ backgroundColor: authUser.colour || '#4B5563' }}
            >
              {authUser.display_name.slice(0, 2).toUpperCase()}
            </div>
          )}
          <span className="text-lg font-medium">{authUser.display_name}</span>
        </div>
        <span className="text-3xl font-thin tabular-nums text-gray-300">{timeStr}</span>
        <button
          onClick={handleLogout}
          className="px-4 py-2 rounded-lg bg-gray-700 hover:bg-gray-600 text-sm text-gray-300 transition-colors"
        >
          Sign out
        </button>
      </header>

      {/* Widgets */}
      <main className="flex-1 overflow-auto p-8">
        {loadError && <p className="text-red-400 mb-4">{loadError}</p>}
        <div className="flex flex-wrap gap-6">
          {widgets.map((w) => {
            const Component = WIDGET_COMPONENTS[w.key]
            return Component ? <Component key={w.key} widget={w} /> : null
          })}
          {widgets.length === 0 && !loadError && (
            <p className="text-gray-500">Loading…</p>
          )}
        </div>
      </main>
    </div>
  )
}
