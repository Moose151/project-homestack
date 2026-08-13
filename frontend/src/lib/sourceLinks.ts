// Where a synced calendar row came from. The Calendar owns every dated household record
// (D7) and stamps the originating node + record type on each event, so one mapping serves
// the Calendar, the Hub's Upcoming card and anything else that surfaces dated items.
//
// Node accent colours come from STACK_BY_KEY — do not keep a second colour table here.
import { STACK_BY_KEY } from '../config/stacks'

export interface SourceRef {
  source_node: string | null
  source_record_type: string
  source_record_id?: number | null
  title: string
}

const SOLACE_TABS: Record<string, string> = {
  Bill: 'bills',
  BillOccurrence: 'bills',
  Payday: 'paydays',
  PlannedPurchase: 'purchases',
}

/** Deep link back to the record that owns this date, or null for a standalone event. */
export function sourcePath(ref: SourceRef): string | null {
  if (!ref.source_node) return null
  const query = encodeURIComponent(ref.title)
  switch (ref.source_node) {
    case 'atlas':
      if (ref.source_record_type === 'AtlasListItem' && ref.source_record_id) return `/atlas?tab=lists&item=${ref.source_record_id}`
      if (ref.source_record_type === 'AtlasList' && ref.source_record_id) return `/atlas?tab=lists&list=${ref.source_record_id}`
      return `/atlas?tab=reminders&q=${query}`
    case 'pets':
      if (ref.source_record_id) {
        if (ref.source_record_type === 'PetAppointment') return `/pets?tab=appointments&appointment=${ref.source_record_id}`
        if (ref.source_record_type === 'PetTreatment') return `/pets?tab=reminders&treatment=${ref.source_record_id}`
        if (ref.source_record_type === 'Pet') return `/pets?tab=pets&pet=${ref.source_record_id}`
      }
      return `/pets?tab=${ref.source_record_type === 'PetAppointment' ? 'appointments' : 'reminders'}&q=${query}`
    case 'education': {
      const tab = ref.source_record_type === 'EducationClassSession'
        ? 'timetable'
        : ref.source_record_type === 'EducationEvent' ? 'events' : 'assignments'
      if (ref.source_record_id) {
        if (ref.source_record_type === 'EducationAssessment') return `/education?tab=assignments&assessment=${ref.source_record_id}`
        if (ref.source_record_type === 'EducationClassSession') return `/education?tab=timetable&session=${ref.source_record_id}`
        if (ref.source_record_type === 'EducationEvent') return `/education?tab=events&event=${ref.source_record_id}`
      }
      return `/education?tab=${tab}&q=${query}`
    }
    case 'homestead':
      return `/homestead?tab=${ref.source_record_type === 'Improvement' ? 'improvements' : 'maintenance'}&q=${query}`
    case 'solace':
      return `/solace?tab=${SOLACE_TABS[ref.source_record_type] || 'schedule'}&q=${query}`
    case 'meridian':
      return '/meridian?tab=tasks'
    case 'travel':
      return ref.source_record_type === 'Trip' && ref.source_record_id
        ? `/travel?trip=${ref.source_record_id}`
        : '/travel'
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
