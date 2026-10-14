/**
 * Calendar Month view presentation policy (v0.41.1).
 *
 * The Month grid renders a deliberately mixed bag: a trip the household is actually taking, a
 * bill reminder, a school term that merely describes when school is in session, a subscribed
 * fixtures feed. Treating all of that as equally important event-bar real estate is what made
 * the grid read as noise. This module is the one place that decides *how important* an event
 * looks, based on semantic fields the backend already exposes (`event_kind`, `source_node`,
 * `calendar_source_kind`) — never by pattern-matching a free-text title, which would be both
 * fragile (any provider's wording could change) and wrong (a household's own event could
 * coincidentally contain the same words).
 */
import type { CalendarEvent } from '../api/types'
import { eventDayRange, sameDay } from './calendarSpans'

export type PresentationLevel = 'prominent' | 'compact' | 'context' | 'milestone'

/** Lower = claims a lane first, and so is the last to be pushed into "+N more". */
export const PRESENTATION_PRIORITY: Record<PresentationLevel, number> = {
  prominent: 0,
  compact: 1,
  context: 2,
  milestone: 3,
}

type PresentationEvent = Pick<
  CalendarEvent,
  'event_kind' | 'source_node' | 'calendar_source_id' | 'calendar_source_kind' | 'start_at' | 'end_at'
>

/**
 * `true` once this event is a ranged (multi-day) entry — a single-day "school" source row (e.g.
 * a not-yet-shipped student-free day) has nothing to show two markers for, so it falls back to
 * `compact` rather than a degenerate one-point "milestone".
 */
function isRanged(event: PresentationEvent): boolean {
  const { start, end } = eventDayRange(event)
  return !sameDay(start, end)
}

/**
 * Classify an event for Month-view presentation. Semantics only:
 * - a Calendar-Source entry is classified by the source's fixed `kind` (school/holidays/
 *   subscription/import) plus whether the provider tagged it `event_kind: "holiday"` (a school
 *   break, or a public holiday) — see apps/scheduling/sources/{au_school,au_holidays}.py.
 * - a node-synced entry (`source_node` set) is classified by its owning node and `event_kind`.
 * - a standalone HomeStack event/appointment is `prominent` — it is literally what the
 *   household typed in as something happening.
 */
export function presentationLevel(event: PresentationEvent): PresentationLevel {
  if (event.calendar_source_id) {
    const kind = event.calendar_source_kind
    if (kind === 'school') {
      if (event.event_kind === 'holiday') return 'context' // a published break/vacation range
      return isRanged(event) ? 'milestone' : 'compact' // a term, or (future) a single-day entry
    }
    if (kind === 'holidays') return 'compact' // a public holiday — one day, still worth noting
    return 'compact' // subscription / import: a generic feed defaults to quiet-but-present
  }

  if (event.source_node) {
    // Node-synced records: an appointment is still something the household is doing.
    if (event.event_kind === 'appointment') return 'prominent'
    // Everything else synced from a node (bills, purchases, reminders, tasks, assessments,
    // maintenance, treatments) is useful but secondary to the household's own plans.
    return 'compact'
  }

  // Birthdays are synthesised locally (see CalendarPage's reload()), never calendar-source- or
  // node-owned, but still carry event_kind — compact single-day notes, not headline events.
  if (event.event_kind === 'birthday') return 'compact'

  // A hand-made HomeStack event or appointment: the primary answer to "what am I doing".
  return 'prominent'
}

const BILL_TITLE_PREFIX = 'Bill: '

/**
 * The label to show in Month view's compact lane bars. Strips a known, backend-authored,
 * purely-redundant prefix ("Bill: ", added unconditionally by Solace for every bill — see
 * apps/solace/models.py) when the event's own `source_node` already says it is a bill, so colour
 * + source already carry that meaning and the text does not have to repeat it. Never mutates the
 * underlying title — full-detail surfaces (the event editor, Agenda, Day view) keep showing it.
 */
export function monthDisplayTitle(event: Pick<CalendarEvent, 'title' | 'source_node'>): string {
  if (event.source_node === 'solace' && event.title.startsWith(BILL_TITLE_PREFIX)) {
    return event.title.slice(BILL_TITLE_PREFIX.length)
  }
  return event.title
}
