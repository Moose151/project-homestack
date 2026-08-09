// Where a synced calendar row came from. The Calendar owns every dated household record
// (D7) and stamps the originating node + record type on each event, so one mapping serves
// the Calendar, the Hub's Upcoming card and anything else that surfaces dated items.
//
// Node accent colours come from STACK_BY_KEY — do not keep a second colour table here.
import { STACK_BY_KEY } from '../config/stacks'

export interface SourceRef {
  source_node: string | null
  source_record_type: string
  title: string
}

const SOLACE_TABS: Record<string, string> = {
  Bill: 'bills',
  BillOccurrence: 'bills',
  Payday: 'paydays',
  PlannedPurchase: 'purchases',
  Subscription: 'subscriptions',
}

/** Deep link back to the record that owns this date, or null for a standalone event. */
export function sourcePath(ref: SourceRef): string | null {
  if (!ref.source_node) return null
  const query = encodeURIComponent(ref.title)
  switch (ref.source_node) {
    case 'atlas':
      return `/atlas?tab=reminders&q=${query}`
    case 'pets':
      return `/pets?tab=${ref.source_record_type === 'PetAppointment' ? 'appointments' : 'reminders'}&q=${query}`
    case 'education': {
      const tab = ref.source_record_type === 'EducationClassSession'
        ? 'timetable'
        : ref.source_record_type === 'EducationEvent' ? 'events' : 'assignments'
      return `/education?tab=${tab}&q=${query}`
    }
    case 'homestead':
      return `/homestead?tab=${ref.source_record_type === 'Improvement' ? 'improvements' : 'maintenance'}&q=${query}`
    case 'solace':
      return `/solace?tab=${SOLACE_TABS[ref.source_record_type] || 'schedule'}&q=${query}`
    case 'meridian':
      return '/meridian?tab=tasks'
    default:
      return null
  }
}

const DEFAULT_COLOUR = '#9CA3AF'

/** Accent colour for a source node, falling back to a neutral for standalone events. */
export function sourceColour(nodeKey: string | null): string {
  return (nodeKey && STACK_BY_KEY[nodeKey]?.colour) || DEFAULT_COLOUR
}

/** Household-facing name for a source node ("Pets", "Money"), or "Calendar" when standalone. */
export function sourceLabel(nodeKey: string | null): string {
  return (nodeKey && STACK_BY_KEY[nodeKey]?.navLabel) || 'Calendar'
}
