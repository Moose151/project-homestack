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

// --- Meridian (Milestone 2) ---

export type MeridianTaskStatus = 'available' | 'pending' | 'approved' | 'rejected'

export interface MeridianTask {
  id: number
  title: string
  description: string
  points: number
  category_id: number | null
  assigned_to_person_id: number | null
  status: MeridianTaskStatus
  is_hot: boolean
  is_complete: boolean
  due_at: string | null
  recurrence_rule: string
  calendar_event_id: number | null
  completed_at: string | null
  completed_by_person_id: number | null
  approved_at: string | null
  approved_by_id: number | null
  rejection_reason: string
  visibility: string
  created_at: string
  updated_at: string
}

export interface MeridianReward {
  id: number
  name: string
  description: string
  cost_points: number
  icon: string
  colour: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface MeridianRewardRequest {
  id: number
  reward_id: number
  requested_by_person_id: number
  status: 'pending' | 'approved' | 'rejected'
  points_spent: number
  approved_at: string | null
  approved_by_id: number | null
  rejection_reason: string
  created_at: string
  updated_at: string
}

export interface PointsSummaryRow {
  person_id: number
  display_name: string
  balance: number
}

export interface MeridianPointsResponse {
  summary: PointsSummaryRow[]
  entries: {
    id: number
    person_id: number
    points: number
    reason: string
    source_task_id: number | null
    source_reward_request_id: number | null
    created_at: string
  }[]
}

export interface KioskMeridian {
  person_id: number | null
  points_balance: number
  tasks: MeridianTask[]
  rewards: MeridianReward[]
}

export interface HubWidget {
  key: string
  name: string
  size: string
  supports_kiosk: boolean
  items: AtlasListItem[] | AtlasReminder[] | MeridianTask[] | PointsSummaryRow[] | MeridianRewardRequest[]
}

export interface HubResponse {
  widgets: HubWidget[]
}
