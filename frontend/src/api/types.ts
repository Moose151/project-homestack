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
  solace_access: boolean
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
  source_record_id: number | null
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

export interface RotatingSchedulePerson {
  id: number
  display_name: string
  preferred_name: string
  colour: string
  profile_type: 'adult' | 'child' | 'other'
}

export interface RotatingSchedule {
  id: number
  title: string
  primary_label: string
  secondary_label: string
  anchor_date: string
  cycle_pattern: string
  cycle_length: number
  primary_colour: string
  secondary_colour: string
  people: RotatingSchedulePerson[]
  visibility: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface RotatingScheduleWrite {
  title: string
  primary_label: string
  secondary_label: string
  anchor_date: string
  cycle_pattern: string
  primary_colour?: string
  secondary_colour?: string
  person_ids?: number[]
  visibility?: string
  is_active?: boolean
}

export interface RotatingScheduleOccurrence {
  id: string
  schedule_id: number
  schedule_title: string
  date: string
  state: 'primary' | 'secondary'
  planned_state: 'primary' | 'secondary'
  label: string
  colour: string
  is_override: boolean
  note: string
  person_ids: number[]
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
  items: AtlasListItem[] | AtlasReminder[] | MeridianTask[] | PointsSummaryRow[] | MeridianRewardRequest[] | CalendarEvent[] | EducationAssessment[] | EducationClassSession[] | EducationEvent[] | WikiPage[] | PetTreatment[] | PetAppointment[] | MaintenanceTask[] | Appliance[] | Improvement[] | SolaceBill[] | SolaceSubscription[] | SolacePurchase[] | AppNotification[]
  meta?: {
    unread_count?: number
    title?: string
    target_date?: string
    /** Upcoming widget: selectable ranges, narrowest first. */
    horizons?: UpcomingHorizon[]
    default_horizon?: string
    window_days?: number
  }
}

/** A range the Upcoming widget can be clipped to. `until` is an inclusive YYYY-MM-DD date. */
export interface UpcomingHorizon {
  key: string
  label: string
  until: string
}

export interface HubResponse {
  widgets: HubWidget[]
}

export interface HubWidgetConfig {
  key: string
  name: string
  description: string
  source_node: string | null
  source_node_name: string
  supports_kiosk: boolean
  /** Ambient widgets render even when empty; everything else is dropped while it has nothing. */
  always_visible: boolean
  household_enabled: boolean
  household_order: number
  size: 'small' | 'medium' | 'large'
  user_hidden: boolean
  user_order: number | null
  settings: { title?: string; target_date?: string }
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
  credit_value: number
  is_completed: boolean
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

export type EducationEventType =
  | 'excursion' | 'school_event' | 'term_start' | 'term_end'
  | 'exam_session' | 'milestone' | 'holiday' | 'other'

export interface EducationEvent {
  id: number
  title: string
  event_type: EducationEventType
  course_id: number | null
  course_name: string
  course_code: string
  institution_id: number | null
  institution_name: string
  assigned_to_person_id: number | null
  start_at: string
  end_at: string | null
  is_all_day: boolean
  location: string
  description: string
  recurrence_rule: string
  calendar_event_id: number | null
  visibility: string
  created_at: string
  updated_at: string
}

export interface AcademicProfile {
  id: number
  person_id: number
  institution_id: number | null
  institution_name: string
  programme_name: string
  credits_required: number
  credits_per_course_default: number
  graduation_year: number | null
  notes: string
  current_credits: number
  created_at: string
  updated_at: string
}

export interface AcademicProfileResponse {
  profile: AcademicProfile
  courses: {
    current: EducationCourse[]
    upcoming: EducationCourse[]
    past: EducationCourse[]
  }
}

export interface AssessmentNote {
  id: number
  assessment_id: number
  body: string
  created_at: string
  updated_at: string
}

export interface AssessmentFile {
  id: number
  assessment_id: number
  label: string
  file_url: string
  original_filename: string
  file_size: number
  created_at: string
  updated_at: string
}

// ---------------------------------------------------------------------------
// Home Wiki (Milestone 3 — household knowledge base)
// ---------------------------------------------------------------------------

export interface WikiCategory {
  id: number
  name: string
  colour: string
  icon: string
  display_order: number
  is_hidden: boolean
  page_count?: number
  created_at: string
  updated_at: string
}

export interface WikiPage {
  id: number
  title: string
  body: string
  category_id: number | null
  category_name: string
  category_colour: string
  tags: string
  tag_list: string[]
  is_favourite: boolean
  is_emergency: boolean
  is_kiosk_safe: boolean
  visibility: string
  sensitivity: string
  created_at: string
  updated_at: string
}

// ---------------------------------------------------------------------------
// Pets (Milestone 3 — pet care)
// ---------------------------------------------------------------------------

export type PetSpecies = 'dog' | 'cat' | 'bird' | 'fish' | 'reptile' | 'small_mammal' | 'other'
export type TreatmentType = 'flea' | 'worming' | 'vaccination' | 'medication' | 'grooming' | 'other'

export interface Pet {
  id: number
  name: string
  species: PetSpecies
  breed: string
  avatar: string
  colour: string
  date_of_birth: string | null
  adoption_date: string | null
  notes: string
  vet_name: string
  vet_phone: string
  microchip_number: string
  insurance_provider: string
  insurance_policy_number: string
  food_notes: string
  is_archived: boolean
  visibility: string
  created_at: string
  updated_at: string
}

export interface PetTreatment {
  id: number
  pet_id: number
  pet_name: string
  treatment_type: TreatmentType
  name: string
  display_name: string
  last_done_at: string | null
  next_due_at: string | null
  recurrence_rule: string
  notes: string
  is_overdue: boolean
  calendar_event_id: number | null
  visibility: string
  created_at: string
  updated_at: string
}

export interface PetAppointment {
  id: number
  pet_id: number
  pet_name: string
  title: string
  display_title: string
  provider: string
  location: string
  start_at: string
  end_at: string | null
  notes: string
  calendar_event_id: number | null
  visibility: string
  created_at: string
  updated_at: string
}

// ---------------------------------------------------------------------------
// Homestead (home / property hub)
// ---------------------------------------------------------------------------

export type PropertyType = 'house' | 'flat' | 'bungalow' | 'maisonette' | 'other'
export type Tenure = 'freehold' | 'leasehold' | 'share_of_freehold' | 'rented' | 'other' | 'unknown'

export interface Property {
  id: number
  name: string
  address: string
  property_type: PropertyType
  tenure: Tenure
  purchase_date: string | null
  move_in_date: string | null
  year_built: string
  is_primary: boolean
  notes: string
  water_shutoff: string
  gas_shutoff: string
  electricity_consumer_unit: string
  boiler_location: string
  visibility: string
  created_at: string
  updated_at: string
}

export type ProviderTrade =
  | 'plumber' | 'electrician' | 'gas_engineer' | 'builder' | 'gardener'
  | 'cleaner' | 'roofer' | 'pest_control' | 'handyman' | 'other'

export interface ServiceProvider {
  id: number
  name: string
  trade: ProviderTrade
  company: string
  phone: string
  email: string
  website: string
  last_used_at: string | null
  notes: string
  visibility: string
  created_at: string
  updated_at: string
}

export type ApplianceCategory =
  | 'appliance' | 'heating' | 'kitchen' | 'laundry' | 'electrical'
  | 'plumbing' | 'security' | 'outdoor' | 'other'

export interface Appliance {
  id: number
  name: string
  category: ApplianceCategory
  brand: string
  model_number: string
  serial_number: string
  room: string
  purchase_date: string | null
  warranty_expires_at: string | null
  warranty_provider: string
  manual_url: string
  notes: string
  visibility: string
  created_at: string
  updated_at: string
}

export type MaintenanceCategory =
  | 'heating' | 'plumbing' | 'electrical' | 'safety' | 'garden'
  | 'exterior' | 'cleaning' | 'appliance' | 'renewal' | 'general'

export interface MaintenanceTask {
  id: number
  appliance_id: number | null
  provider_id: number | null
  assigned_to_person_id: number | null
  title: string
  category: MaintenanceCategory
  next_due_at: string | null
  is_all_day: boolean
  recurrence_rule: string
  last_done_at: string | null
  notes: string
  solace_bill_ref: number | null
  is_overdue: boolean
  calendar_event_id: number | null
  visibility: string
  created_at: string
  updated_at: string
}

export type ImprovementStatus =
  | 'idea' | 'planned' | 'in_progress' | 'on_hold' | 'done' | 'cancelled'
export type ImprovementPriority = 'low' | 'medium' | 'high'

export interface Improvement {
  id: number
  assigned_to_person_id: number | null
  title: string
  description: string
  status: ImprovementStatus
  priority: ImprovementPriority
  room: string
  target_date: string | null
  is_all_day: boolean
  project_ref: number | null
  notes: string
  is_open: boolean
  calendar_event_id: number | null
  visibility: string
  created_at: string
  updated_at: string
}

export type RoomAreaType = 'interior' | 'outdoor' | 'utility' | 'storage' | 'other'
export type RoomItemType = 'purchase' | 'maintenance' | 'renovation' | 'upgrade'
export type RoomItemStatus = 'planned' | 'in_progress' | 'completed' | 'archived'
export type RoomItemPriority = 'low' | 'medium' | 'high'

export interface RoomCostSummary {
  active_count: number
  completed_count: number
  archived_count: number
  remaining_estimated_cost: string
  completed_cost: string
  overall_cost: string
}

export interface RoomArea {
  id: number
  name: string
  area_type: RoomAreaType
  description: string
  icon: string
  colour: string
  display_order: number
  floorplan_data: Record<string, unknown>
  visibility: string
  summary: RoomCostSummary
  created_at: string
  updated_at: string
}

/** One candidate purchase behind a room job. `image_url` is a remote link, not an upload. */
export interface RoomPlanProduct {
  id: number
  plan_item_id: number
  title: string
  url: string
  image_url: string
  retailer: string
  quantity: string
  unit_cost: string
  total_cost: string
  is_chosen: boolean
  notes: string
  position: number
  created_at: string
  updated_at: string
}

export interface RoomPlanItem {
  id: number
  room_id: number
  assigned_to_person_id: number | null
  title: string
  item_type: RoomItemType
  status: RoomItemStatus
  priority: RoomItemPriority
  description: string
  quantity: string
  estimated_unit_cost: string
  estimated_total: string
  actual_cost: string | null
  effective_cost: string
  notes: string
  position: number
  completed_at: string | null
  visibility: string
  /** Shopping-list options for this job — what to buy, from where, at what price. */
  products: RoomPlanProduct[]
  created_at: string
  updated_at: string
}

export interface RoomListResponse {
  rooms: RoomArea[]
  household_summary: RoomCostSummary
}

export interface RoomDetailResponse {
  room: RoomArea
  items: RoomPlanItem[]
  summary: RoomCostSummary
}

export type InsurancePolicyType =
  | 'building' | 'contents' | 'building_contents' | 'landlord'
  | 'mortgage_protection' | 'other'
export type HomeBillingCycle =
  | 'weekly' | 'fortnightly' | 'monthly' | 'quarterly'
  | 'half_yearly' | 'yearly' | 'variable' | 'other'

export interface InsurancePolicy {
  id: number
  name: string
  policy_type: InsurancePolicyType
  provider: string
  policy_number: string
  premium_amount: string
  billing_cycle: Exclude<HomeBillingCycle, 'variable'>
  next_renewal_at: string | null
  recurrence_rule: string
  standard_excess: string
  additional_excesses: string
  coverage_summary: string
  contact_phone: string
  portal_url: string
  is_active: boolean
  solace_bill_ref: number | null
  notes: string
  visibility: string
  created_at: string
  updated_at: string
}

export type HouseholdCostType =
  | 'rates' | 'water' | 'gas' | 'electricity' | 'mortgage'
  | 'body_corporate' | 'waste' | 'internet' | 'other'

export interface HouseholdCost {
  id: number
  name: string
  cost_type: HouseholdCostType
  provider: string
  account_number: string
  amount: string
  billing_cycle: HomeBillingCycle
  next_due_at: string | null
  recurrence_rule: string
  is_active: boolean
  solace_bill_ref: number | null
  notes: string
  visibility: string
  created_at: string
  updated_at: string
}

export interface HomesteadSearchResults {
  appliances: Appliance[]
  maintenance: MaintenanceTask[]
  providers: ServiceProvider[]
  improvements: Improvement[]
  rooms: RoomArea[]
  room_items: RoomPlanItem[]
}

// ---------------------------------------------------------------------------
// Solace (finance)
// ---------------------------------------------------------------------------

export interface SolaceBill {
  id: number
  name: string
  category: string
  provider: string
  amount: string
  due_at: string | null
  is_all_day: boolean
  recurrence_rule: string
  end_date: string | null
  is_active: boolean
  is_autopay: boolean
  include_in_set_aside: boolean
  is_paid: boolean
  paid_at: string | null
  notes: string
  is_overdue: boolean
  next_due_at: string | null
  next_occurrence_id: number | null
  annual_amount: string
  fortnightly_amount: string
  source_node: string
  source_record_type: string
  source_record_id: number | null
  calendar_event_id: number | null
  visibility: string
  sensitivity: string
  created_at: string
  updated_at: string
}

export interface SolaceBillOccurrence {
  id: number
  bill_id: number
  bill_name: string
  bill_category: string
  due_at: string
  amount: string
  status: 'upcoming' | 'paid' | 'skipped'
  paid_at: string | null
  notes: string
  is_overdue: boolean
  visibility: string
  sensitivity: string
  created_at: string
  updated_at: string
}

export interface SolaceBillTimeline {
  bill: SolaceBill
  upcoming: SolaceBillOccurrence[]
  history: SolaceBillOccurrence[]
}

export interface SolaceIncomeEvent {
  payday_id: number
  title: string
  due_at: string
  amount: string
}

export interface SolaceSchedule {
  start: string
  end: string
  occurrences: SolaceBillOccurrence[]
  income_events: SolaceIncomeEvent[]
  summary: {
    bills_total: string
    paid_total: string
    unpaid_total: string
    skipped_total: string
    income_total: string
  }
}

export interface SolacePayday {
  id: number
  title: string
  expected_amount: string
  pay_at: string | null
  next_pay_at: string | null
  is_all_day: boolean
  recurrence_rule: string
  received_at: string | null
  is_active: boolean
  notes: string
  calendar_event_id: number | null
  visibility: string
  sensitivity: string
  created_at: string
  updated_at: string
}

export interface SolacePurchase {
  id: number
  name: string
  category: string
  target_amount: string
  saved_amount: string
  remaining_amount: string
  progress_percent: number
  target_date: string | null
  is_all_day: boolean
  status: string
  priority: string
  notes: string
  is_open: boolean
  calendar_event_id: number | null
  visibility: string
  sensitivity: string
  created_at: string
  updated_at: string
}

export interface SolaceBucket {
  id: number
  name: string
  category: string
  target_amount: string
  current_amount: string
  remaining_amount: string
  progress_percent: number
  allocation_method: 'percentage' | 'fixed'
  allocation_value: string
  rounding_increment: string
  cap_to_remaining: boolean
  is_active: boolean
  position: number
  notes: string
  visibility: string
  sensitivity: string
  created_at: string
  updated_at: string
}

export interface SolaceSubscription {
  id: number
  name: string
  provider: string
  amount: string
  billing_cycle: string
  next_renewal_at: string | null
  is_all_day: boolean
  recurrence_rule: string
  is_active: boolean
  notes: string
  calendar_event_id: number | null
  visibility: string
  sensitivity: string
  created_at: string
  updated_at: string
}

export interface SolaceChecklistItem {
  id: number
  title: string
  cycle_start: string | null
  source_key: string
  bucket_id: number | null
  bill_id: number | null
  amount_hint: string
  position: number
  is_complete: boolean
  completed_at: string | null
  notes: string
  visibility: string
  sensitivity: string
  created_at: string
  updated_at: string
}

export interface SolaceSearchResults {
  bills: SolaceBill[]
  paydays: SolacePayday[]
  purchases: SolacePurchase[]
  buckets: SolaceBucket[]
  subscriptions: SolaceSubscription[]
  checklist: SolaceChecklistItem[]
}

export interface SolacePlanAllocation {
  bucket_id: number
  bucket_name: string
  category: string
  allocation_method: 'percentage' | 'fixed'
  allocation_value: string
  raw_amount: string
  amount: string
  capped: boolean
}

export interface SolacePlanSource {
  payday_id: number
  title: string
  pay_dates: string[]
  income_total: string
  allocated_total: string
  remaining: string
  allocations: SolacePlanAllocation[]
}

export interface SolacePlanBucket {
  bucket_id: number
  bucket_name: string
  category: string
  amount: string
}

export interface SolacePayCyclePlan {
  cycle_start: string
  cycle_end: string
  income_total: string
  allocated_total: string
  remaining: string
  sources: SolacePlanSource[]
  buckets: SolacePlanBucket[]
  set_aside: {
    recurring_bills: string
    planned_purchases: string
    buffer: string
    required_total: string
    bills_bucket_total: string
    shortfall: string
    is_covered: boolean
  }
}

export interface SolaceSettings {
  id: number
  currency_symbol: string
  budget_year: number | null
  cycle_anchor_date: string | null
  default_buffer_amount: string
  payday_bill_handling: 'new_cycle' | 'previous_cycle'
  show_help_tips: boolean
  dashboard_reminders: boolean
  due_soon_days: number
  created_at: string
  updated_at: string
}

export interface SolaceCategory {
  id: number
  name: string
  category_type: 'bill' | 'purchase' | 'both'
  is_active: boolean
  position: number
  visibility: string
  sensitivity: string
  created_at: string
  updated_at: string
}

export interface SolaceBalanceSnapshot {
  id: number
  snapshot_date: string
  balance: string
  notes: string
  visibility: string
  sensitivity: string
  created_at: string
  updated_at: string
}

export interface SolaceBalanceForecastItem {
  kind: 'bill' | 'subscription' | 'contribution'
  name: string
  amount: string
  record_id: number
  status: string
}

export interface SolaceBalanceForecast {
  as_of: string
  forecast_start: string
  through: string
  horizon_months: number
  latest_balance: SolaceBalanceSnapshot | null
  opening_balance: string | null
  buffer_amount: string
  total_bills: string
  total_contributions: string
  required_opening_balance: string
  ending_balance: string | null
  lowest_balance: string | null
  lowest_balance_date: string
  bills_only_surplus: string | null
  safe_to_withdraw: string | null
  shortfall: string | null
  is_covered: boolean | null
  timeline: {
    date: string
    contributions: string
    bills: string
    net_change: string
    projected_balance: string | null
    items: SolaceBalanceForecastItem[]
  }[]
}

export interface SolaceChecklistPreference {
  id: number
  source_key: string
  label: string
  is_hidden: boolean
  reason: string
  visibility: string
  sensitivity: string
  created_at: string
  updated_at: string
}

export interface SolaceCycleCloseout {
  id: number
  cycle_start: string
  cycle_end: string
  status: 'open' | 'closed'
  closed_at: string | null
  notes: string
  visibility: string
  sensitivity: string
  created_at: string
  updated_at: string
}

export interface SolaceCloseoutResponse {
  plan: SolacePayCyclePlan
  bill_window: { start: string; end: string }
  occurrences: SolaceBillOccurrence[]
  checklist: SolaceChecklistItem[]
  latest_balance: SolaceBalanceSnapshot | null
  projected_balance: string | null
  closeout: SolaceCycleCloseout | null
  summary: {
    bills_total: string
    paid_total: string
    unpaid_total: string
    skipped_total: string
    unpaid_count: number
    checklist_count: number
    checklist_complete_count: number
  }
}

export interface SolaceHealth {
  status: 'healthy' | 'warning' | 'error'
  issues: { level: 'warning' | 'error'; code: string; message: string }[]
  counts: {
    active_bills: number
    active_paydays: number
    active_buckets: number
    overdue_occurrences: number
  }
  percentage_allocation_total: string
  latest_balance: SolaceBalanceSnapshot | null
}

export interface SolaceCategoryReport {
  categories: {
    category: string
    bill_count: number
    weekly_total: string
    annual_total: string
    fortnightly_total: string
    monthly_total: string
  }[]
  bill_count: number
  weekly_total: string
  annual_total: string
  fortnightly_total: string
  monthly_total: string
  active_only: boolean
  included_only: boolean
}

export interface SolaceBootstrap {
  bills: SolaceBill[]
  paydays: SolacePayday[]
  purchases: SolacePurchase[]
  buckets: SolaceBucket[]
  subscriptions: SolaceSubscription[]
  checklist: SolaceChecklistItem[]
  plan: SolacePayCyclePlan
  settings: SolaceSettings
  categories: SolaceCategory[]
  balances: SolaceBalanceSnapshot[]
  health: SolaceHealth
  category_report: SolaceCategoryReport
  closeout: SolaceCloseoutResponse
  forecast: SolaceBalanceForecast
  checklist_preferences: SolaceChecklistPreference[]
}

export interface SolaceBillImportRow {
  source_row: number
  errors: string[]
  name?: string
  amount?: string
  category?: string
  provider?: string
  due_at?: string | null
  recurrence_rule?: string
  end_date?: string | null
  is_active?: boolean
  is_autopay?: boolean
  include_in_set_aside?: boolean
  notes?: string
}

export interface SolaceBillImportPreview {
  rows: SolaceBillImportRow[]
  row_count: number
  error_count: number
  ready_count: number
}

export interface GlobalSearchResult {
  node: string
  kind: string
  id: number
  title: string
  subtitle: string
  route: string
}

export interface GlobalSearchResponse {
  results: GlobalSearchResult[]
  locked_nodes: string[]
}

// ---------------------------------------------------------------------------
// Shared attachments
// ---------------------------------------------------------------------------

export type AttachmentVisibility = 'private' | 'household' | 'role_restricted' | 'sensitive'
export type AttachmentSensitivity = 'normal' | 'financial' | 'health' | 'document' | 'private'

export interface Attachment {
  id: number
  uploaded_by: number
  filename: string
  original_filename: string
  mime_type: string
  file_size: number
  checksum: string
  linked_node: number | null
  linked_record_type: string
  linked_record_id: number | null
  visibility: AttachmentVisibility
  sensitivity: AttachmentSensitivity
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
  can_view: boolean
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
  calendar_default_view: 'month' | 'week' | 'day' | 'agenda'
  calendar_week_start: 0 | 1
  calendar_time_format: '12h' | '24h'
  created_at: string
  updated_at: string
}

// ---------------------------------------------------------------------------
// Books
// ---------------------------------------------------------------------------

export type BookShelfStatus = 'backlog' | 'reading' | 'history'

export interface Book {
  id: number
  title: string
  author: string
  pages: number | null
  genre: string
  isbn: string
  description: string
  cover_url: string
  created_at: string
  updated_at: string
}

export interface BookRating {
  id: number
  book_id: number
  user_id: number
  user_name: string
  user_colour: string
  rating: number | null
  notes: string
  created_at: string
  updated_at: string
}

export interface PersonalBookEntry {
  id: number
  book_id: number
  book: Book
  status: BookShelfStatus
  position: number
  rating: number | null
  notes: string
  source: 'personal'
  created_at: string
  updated_at: string
}

export interface BookClubMembership {
  id: number
  user_id: number
  user_name: string
  user_colour: string
  user_avatar: string
  created_at: string
}

export interface BookClub {
  id: number
  name: string
  colour: string
  description: string
  memberships: BookClubMembership[]
  created_at: string
  updated_at: string
}

export interface ClubBookEntry {
  id: number
  club_id: number
  book_id: number
  book: Book
  status: BookShelfStatus
  position: number
  added_by_id: number | null
  added_by_name: string
  added_by_colour: string
  average_rating: number | null
  my_rating: number | null
  ratings: BookRating[]
  created_at: string
  updated_at: string
}

export interface ClubQueueItem {
  id: number
  club_id: number
  club_book_id: number
  club_book: ClubBookEntry
  position: number
  created_at: string
  updated_at: string
}

export interface BooksUser {
  id: number
  display_name: string
  username: string
  colour: string
  avatar: string
}
