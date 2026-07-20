// Lightweight natural-ish parsing for the Calendar quick-add bar.
// Turns "Dentist 3pm" into a title + a start time on a base day, with no external deps.
// Deliberately small: it only pulls a trailing/embedded time out of the text; the day comes
// from the calendar context (the day you're viewing, or today on the agenda).

export interface QuickEvent {
  title: string
  startISO: string
  allDay: boolean
}

const pad = (n: number) => String(n).padStart(2, '0')

/** Parse free text like "Lunch 12:30", "Standup 9am", "Football 6:30pm" against a base day. */
export function parseQuickEvent(text: string, baseDate: Date): QuickEvent {
  const raw = text.trim()
  let hours: number | null = null
  let minutes = 0
  let title = raw

  // 12-hour: "3pm", "3:30pm", "9 am"
  const ampm = raw.match(/\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b/i)
  // 24-hour: "15:00", "9:05"
  const h24 = raw.match(/\b(\d{1,2}):(\d{2})\b/)

  if (ampm) {
    let h = parseInt(ampm[1], 10)
    minutes = ampm[2] ? parseInt(ampm[2], 10) : 0
    const pm = ampm[3].toLowerCase() === 'pm'
    if (h === 12) h = 0
    if (pm) h += 12
    hours = h
    title = raw.replace(ampm[0], '').trim()
  } else if (h24) {
    const h = parseInt(h24[1], 10)
    const m = parseInt(h24[2], 10)
    if (h < 24 && m < 60) {
      hours = h
      minutes = m
      title = raw.replace(h24[0], '').trim()
    }
  }

  // Tidy trailing joiners left behind by removing the time ("Dentist at" → "Dentist").
  title = title.replace(/\s+(at|@|on)\s*$/i, '').trim()

  const d = new Date(baseDate)
  if (hours === null) {
    // No time found → all-day event on the base day.
    d.setHours(0, 0, 0, 0)
    return { title: title || raw, startISO: d.toISOString(), allDay: true }
  }
  d.setHours(hours, minutes, 0, 0)
  return { title: title || raw, startISO: d.toISOString(), allDay: false }
}

/** Human preview of what the parser found, for a subtle hint under the input. */
export function quickEventPreview(text: string, baseDate: Date, time24: boolean): string | null {
  if (!text.trim()) return null
  const p = parseQuickEvent(text, baseDate)
  const day = baseDate.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })
  if (p.allDay) return `${day} · all day`
  const t = new Date(p.startISO)
  const time = time24
    ? `${pad(t.getHours())}:${pad(t.getMinutes())}`
    : t.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit', hour12: true })
  return `${day} · ${time}`
}
