export interface KioskUser {
  person_id: number
  display_name: string
  preferred_name: string
  avatar: string
  colour: string
  profile_type: 'adult' | 'child' | 'other'
  username: string
}

export interface Person {
  id: number
  display_name: string
  preferred_name: string
  avatar: string
  colour: string
  profile_type: 'adult' | 'child' | 'other'
  linked_user_id: number | null
}

export interface AdminUser {
  id: number
  username: string
  display_name: string
  email: string
  avatar: string
  role: 'admin' | 'manager' | 'user' | 'guest'
  is_active: boolean
  is_child_account: boolean
  colour: string
  last_login: string | null
  created_at: string
  linked_person_id: number | null
  linked_person_name: string | null
  has_password: boolean
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
  atlas_list_id: number
  title: string
  notes: string
  quantity: string
  position: number
  due_at: string | null
  assigned_to_person_id: number | null
  completed_at: string | null
  completed_by_id: number | null
  is_complete: boolean
  created_at: string
  updated_at: string
}

export interface AtlasSearchResults {
  notes: AtlasNote[]
  lists: AtlasList[]
  items: AtlasListItem[]
  reminders: AtlasReminder[]
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
  is_all_day: boolean
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
  description: string
  start_at: string
  end_at: string | null
  is_all_day: boolean
  timezone: string
  recurrence_rule: string
  source_node: string | null
  source_record_type: string
  assigned_to_person_id: number | null
  colour: string
  location: string
  visibility: string
  sensitivity: string
  is_synced: boolean
  created_at: string
  updated_at: string
}

export interface CalendarEventWrite {
  title: string
  description?: string
  start_at: string
  end_at?: string | null
  is_all_day?: boolean
  recurrence_rule?: string
  assigned_to_person_id?: number | null
  colour?: string
  location?: string
  visibility?: string
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
  award_value: number
  hot_bonus_points: number
  hot_label: string
  completion_behavior: 'stay_active' | 'hide_after_approval'
  completion_scope: 'per_person' | 'household'
  availability_window: string
  is_active: boolean
  is_archived: boolean
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

export interface MeridianTaskCompletion {
  id: number
  task_id: number
  task_title: string
  person_id: number
  person_display_name: string
  status: 'submitted' | 'approved' | 'rejected'
  submitted_at: string
  reviewed_at: string | null
  reviewed_by_id: number | null
  rejection_reason: string
  review_note: string
  evidence_photo: string
  created_at: string
  updated_at: string
}

export interface MeridianReward {
  id: number
  name: string
  description: string
  cost_points: number
  category_id: number | null
  icon: string
  colour: string
  image_url: string
  is_active: boolean
  is_archived: boolean
  price_estimate: string
  store_url: string
  quantity: number | null
  allow_multiple_in_cart: boolean
  disappear_when_empty: boolean
  daily_limit_per_user: number | null
  remaining_stock: number | null
  created_at: string
  updated_at: string
}

export interface MeridianCategory {
  id: number
  name: string
  kind: 'task' | 'reward'
  colour: string
  icon: string
  position: number
}

export interface MeridianRoutine {
  id: number
  title: string
  description: string
  points: number
  assigned_to_person_id: number | null
  is_active: boolean
  visibility: string
  streak?: number
  done_today?: boolean
}

export interface MeridianGoal {
  id: number
  title: string
  description: string
  target_points: number
  price_estimate: string
  store_url: string
  image_url: string
  status: 'active' | 'funded' | 'archived'
  is_active: boolean
  total_contributed: number
  remaining_points: number
  progress_percentage: number
}

export interface MeridianWishlistItem {
  id: number
  person_id: number
  name: string
  description: string
  point_cost: number
  status: 'active' | 'funded' | 'fulfilled'
  is_active: boolean
  price_estimate: string
  store_url: string
  image_url: string
  total_saved: number
  remaining_points: number
  progress_percentage: number
}

export interface MeridianWishlistRequest {
  id: number
  person_id: number
  requested_name: string
  requested_description: string
  status: 'requested' | 'approved' | 'rejected'
  rejection_reason: string
  created_at: string
}

export interface MeridianSettings {
  points_label: string
  group_goals_enabled: boolean
  wishlist_requests_enabled: boolean
  auto_end_streaks: boolean
}

export interface MeridianAllowanceRow {
  person_id: number
  display_name: string
  amount: number
  weekday: number
  is_active: boolean
}

export interface LeaderboardRow {
  person_id: number
  display_name: string
  balance: number
  total_earned: number
  badge_count: number
}

export interface ActivityRow {
  id: number
  person_id: number
  display_name: string
  points: number
  transaction_type: string
  reason: string
  created_at: string
}

export interface MeridianReports {
  leaderboard: LeaderboardRow[]
  recent_activity: ActivityRow[]
}

export interface Badge {
  id: number
  code: string
  name: string
  description: string
  icon: string
  source: string
  position: number
}

export interface PersonBadge {
  id: number
  person_id: number
  badge: Badge
  earned_at: string
  source: string
}

export interface AppNotification {
  id: number
  title: string
  message: string
  level: 'info' | 'success' | 'warning' | 'danger'
  source_node: string
  action_url: string
  is_read: boolean
  created_at: string
}

export interface NotificationList {
  unread_count: number
  results: AppNotification[]
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
  items: AtlasListItem[] | AtlasReminder[] | MeridianTask[] | PointsSummaryRow[] | MeridianRewardRequest[] | CalendarEvent[] | EducationAssessment[] | EducationClassSession[]
}

export interface HubResponse {
  widgets: HubWidget[]
}

export interface HubWidgetConfig {
  key: string
  name: string
  description: string
  source_node: string | null
  supports_kiosk: boolean
  household_enabled: boolean
  household_order: number
  size: 'small' | 'medium' | 'large'
  user_hidden: boolean
  user_order: number | null
}

// ---------------------------------------------------------------------------
// Education (Milestone 3 — uni-first slice)
// ---------------------------------------------------------------------------

export interface EducationInstitution {
  id: number
  name: string
  institution_type: 'school' | 'university' | 'tafe' | 'other'
  location: string
  notes: string
  visibility: string
  created_at: string
  updated_at: string
}

export interface EducationCourse {
  id: number
  name: string
  code: string
  institution_id: number | null
  institution_name: string
  student_id: number | null
  student_name: string
  teacher: string
  start_date: string | null
  end_date: string | null
  colour: string
  description: string
  is_archived: boolean
  visibility: string
  created_at: string
  updated_at: string
}

export type AssessmentType = 'homework' | 'assignment' | 'exam' | 'quiz' | 'reading' | 'project' | 'other'
export type AssessmentStatus = 'todo' | 'in_progress' | 'submitted' | 'done'
export type AssessmentPriority = 'low' | 'medium' | 'high'

export interface EducationAssessment {
  id: number
  title: string
  assessment_type: AssessmentType
  course_id: number | null
  course_name: string
  course_code: string
  assigned_to_person_id: number | null
  due_at: string | null
  is_all_day: boolean
  status: AssessmentStatus
  priority: AssessmentPriority
  weight: string
  description: string
  is_complete: boolean
  calendar_event_id: number | null
  visibility: string
  sensitivity: string
  created_at: string
  updated_at: string
}

export interface EducationClassSession {
  id: number
  title: string
  display_title: string
  course_id: number | null
  course_name: string
  course_code: string
  student_id: number | null
  location: string
  start_at: string
  end_at: string | null
  recurrence_rule: string
  calendar_event_id: number | null
  visibility: string
  created_at: string
  updated_at: string
}

// ---------------------------------------------------------------------------
// Nodes (stacks) + household
// ---------------------------------------------------------------------------

export interface NodeInfo {
  key: string
  name: string
  description: string
  icon: string
  is_core: boolean
  supports_kiosk: boolean
  supports_sensitive_lock: boolean
  is_enabled: boolean
  is_hidden: boolean
  requires_reauthentication: boolean
  display_order: number
  custom_name: string
  custom_icon: string
}

export interface Household {
  id: number
  name: string
  slug: string
  timezone: string
  default_locale: string
  family_colour: string
  created_at: string
  updated_at: string
}
