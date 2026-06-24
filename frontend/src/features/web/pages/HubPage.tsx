import { useEffect, useState } from 'react'
import { api } from '../../../api/client'
import type { HubResponse, AtlasListItem, AtlasReminder } from '../../../api/types'
import { Card } from '../../../components/Card'

function formatDue(iso: string | null) {
  if (!iso) return null
  const d = new Date(iso)
  const now = new Date()
  const diff = Math.round((d.getTime() - now.getTime()) / 86400000)
  if (diff === 0) return 'Today'
  if (diff === 1) return 'Tomorrow'
  if (diff === -1) return 'Yesterday'
  if (diff < 0) return `${Math.abs(diff)}d overdue`
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

function TodoWidget({ items }: { items: AtlasListItem[] }) {
  const pending = items.filter(i => !i.is_complete)
  if (pending.length === 0) return <p className="text-sm text-gray-400 dark:text-gray-500">All done ✓</p>
  return (
    <ul className="flex flex-col gap-2">
      {pending.slice(0, 8).map(item => (
        <li key={item.id} className="flex items-center gap-3 text-sm">
          <div className="w-5 h-5 rounded-full border-2 border-gray-300 dark:border-gray-600 flex-shrink-0" />
          <span className="text-gray-700 dark:text-gray-300">{item.title}</span>
        </li>
      ))}
      {pending.length > 8 && (
        <li className="text-xs text-gray-400">+{pending.length - 8} more</li>
      )}
    </ul>
  )
}

function RemindersWidget({ items }: { items: AtlasReminder[] }) {
  if (items.length === 0) return <p className="text-sm text-gray-400 dark:text-gray-500">No upcoming reminders</p>
  return (
    <ul className="flex flex-col gap-3">
      {items.slice(0, 6).map(r => {
        const due = formatDue(r.due_at)
        return (
          <li key={r.id} className="flex items-start gap-3">
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-800 dark:text-gray-200 truncate">{r.title}</p>
              {r.body && <p className="text-xs text-gray-400 truncate">{r.body}</p>}
            </div>
            {due && (
              <span className={`text-xs px-2 py-0.5 rounded-full flex-shrink-0 ${
                due.includes('overdue')
                  ? 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400'
                  : due === 'Today'
                  ? 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400'
                  : 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400'
              }`}>
                {due}
              </span>
            )}
          </li>
        )
      })}
    </ul>
  )
}

export function HubPage() {
  const [data, setData] = useState<HubResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.hub()
      .then(setData)
      .catch(e => setError(e.message))
  }, [])

  const now = new Date()
  const greeting =
    now.getHours() < 12 ? 'Good morning' : now.getHours() < 18 ? 'Good afternoon' : 'Good evening'

  if (error) return (
    <div className="text-red-500 text-sm">{error}</div>
  )

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">{greeting}</h1>
        <p className="text-gray-500 dark:text-gray-400 text-sm mt-0.5">
          {now.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' })}
        </p>
      </div>

      {!data ? (
        <div className="flex flex-col gap-4">
          {[1, 2].map(i => (
            <div key={i} className="h-32 rounded-2xl bg-gray-100 dark:bg-gray-800 animate-pulse" />
          ))}
        </div>
      ) : data.widgets.length === 0 ? (
        <Card>
          <p className="text-gray-400 text-sm text-center py-4">No widgets configured yet.</p>
        </Card>
      ) : (
        <div className="flex flex-col gap-4">
          {data.widgets.map(w => (
            <Card key={w.key} title={w.name}>
              {w.key === 'atlas_todos'
                ? <TodoWidget items={w.items as AtlasListItem[]} />
                : <RemindersWidget items={w.items as AtlasReminder[]} />
              }
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
