import { useEffect, useState } from 'react'
import { api } from '../../../api/client'
import type { CalendarEvent } from '../../../api/types'
import { Card } from '../../../components/Card'

function groupByDate(events: CalendarEvent[]): Map<string, CalendarEvent[]> {
  const map = new Map<string, CalendarEvent[]>()
  for (const e of events) {
    const key = new Date(e.start_at).toDateString()
    if (!map.has(key)) map.set(key, [])
    map.get(key)!.push(e)
  }
  return map
}

function formatDateHeader(dateStr: string) {
  const d = new Date(dateStr)
  const today = new Date()
  const tomorrow = new Date(today)
  tomorrow.setDate(today.getDate() + 1)

  if (d.toDateString() === today.toDateString()) return 'Today'
  if (d.toDateString() === tomorrow.toDateString()) return 'Tomorrow'
  return d.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' })
}

function formatTime(iso: string, allDay: boolean) {
  if (allDay) return 'All day'
  return new Date(iso).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
}

export function CalendarPage() {
  const [events, setEvents] = useState<CalendarEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.getEvents()
      .then(data => {
        const now = new Date()
        const upcoming = data
          .filter(e => new Date(e.start_at) >= new Date(now.getFullYear(), now.getMonth(), now.getDate()))
          .sort((a, b) => new Date(a.start_at).getTime() - new Date(b.start_at).getTime())
        setEvents(upcoming)
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  const grouped = groupByDate(events)

  return (
    <div className="flex flex-col gap-5">
      <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">Calendar</h1>

      {loading && (
        <div className="flex flex-col gap-3">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-20 rounded-2xl bg-gray-100 dark:bg-gray-800 animate-pulse" />
          ))}
        </div>
      )}

      {error && <p className="text-red-500 text-sm">{error}</p>}

      {!loading && events.length === 0 && !error && (
        <Card>
          <p className="text-gray-400 text-sm text-center py-6">
            No upcoming events. Add a reminder with a date in Atlas to see it here.
          </p>
        </Card>
      )}

      {[...grouped.entries()].map(([dateStr, dayEvents]) => (
        <div key={dateStr}>
          <h2 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">
            {formatDateHeader(dateStr)}
          </h2>
          <div className="flex flex-col gap-2">
            {dayEvents.map(event => (
              <Card key={event.id} className="!p-0">
                <div className="flex items-start gap-4 p-4">
                  <div className="flex flex-col items-center justify-center w-12 flex-shrink-0">
                    <span className="text-xs text-blue-500 font-medium">
                      {formatTime(event.start_at, event.all_day)}
                    </span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-800 dark:text-gray-200 truncate">{event.title}</p>
                    {event.source_node && (
                      <span className="text-xs text-gray-400 capitalize">{event.source_node}</span>
                    )}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
