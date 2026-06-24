export interface KioskUser {
  person_id: number
  display_name: string
  preferred_name: string
  avatar: string
  colour: string
  profile_type: 'adult' | 'child' | 'other'
  username: string
}

export interface AuthUser {
  id: number
  username: string
  display_name: string
  role: string
  is_child_account: boolean
  avatar: string
  colour: string
}

export interface AtlasListItem {
  id: number
  title: string
  notes: string
  position: number
  assigned_to_person_id: number | null
  completed_at: string | null
  completed_by_id: number | null
  is_complete: boolean
  created_at: string
  updated_at: string
}

export interface AtlasList {
  id: number
  title: string
  list_type: 'todo' | 'grocery' | 'checklist' | 'shopping' | 'general'
  visibility: string
  items: AtlasListItem[]
  created_at: string
  updated_at: string
}

export interface AtlasNote {
  id: number
  title: string
  body: string
  visibility: string
  sensitivity: string
  created_at: string
  updated_at: string
}

export interface AtlasReminder {
  id: number
  title: string
  body: string
  due_at: string | null
  recurrence_rule: string
  calendar_event_id: number | null
  visibility: string
  sensitivity: string
  created_at: string
  updated_at: string
}

export interface CalendarEvent {
  id: number
  title: string
  start_at: string
  end_at: string | null
  all_day: boolean
  source_node: string | null
  source_record_type: string
  visibility: string
  recurrence_rule: string
  created_at: string
}

export interface HubWidget {
  key: string
  name: string
  size: string
  supports_kiosk: boolean
  items: AtlasListItem[] | AtlasReminder[]
}

export interface HubResponse {
  widgets: HubWidget[]
}
